import webrtcvad
import sounddevice as sd
import numpy as np
import collections
import logging

_logger = logging.getLogger(__name__)


class VAD:
    """
    Voice Activity Detector — continuously reads from mic in small chunks,
    buffers them, and yields only segments where speech is detected.

    Uses WebRTC VAD (very lightweight, works offline).
    Improved: Better audio preprocessing, auto-calibration, detailed debugging.
    """

    def __init__(self, logger=None, sample_rate=16000, aggressiveness=1,
                 frame_duration_ms=30, padding_duration_ms=500,
                 min_segment_ms=350, start_trigger_ratio=0.5,
                 end_trigger_ratio=0.7, enable_noise_suppression=True):
        """
        sample_rate: 16000Hz (WebRTC VAD requirement)
        aggressiveness: 0-3 (0 = least aggressive, allows more; 3 = most aggressive, filters more)
                       → Default 1 (less filtering) for better sensitivity
        frame_duration_ms: 10, 20, or 30ms — WebRTC VAD requirement
        padding_duration_ms: silence padding before cutting off speech (500ms default)
        enable_noise_suppression: Pre-process audio to reduce background noise
        """
        self.min_segment_samples = int(sample_rate * min_segment_ms / 1000)
        self.logger = logger
        self.sample_rate = sample_rate
        self.frame_duration_ms = frame_duration_ms
        self.frame_size = int(sample_rate * frame_duration_ms / 1000)
        self.padding_duration_ms = padding_duration_ms
        self.num_padding_frames = padding_duration_ms // frame_duration_ms
        self.start_trigger_ratio = float(start_trigger_ratio)
        self.end_trigger_ratio = float(end_trigger_ratio)
        self.enable_noise_suppression = enable_noise_suppression
        self.noise_floor = 0.01  # Auto-calibrated if needed; lower = more sensitive
        
        # Enforce aggressiveness bounds: 0-3, default to 1 for better sensitivity
        self.aggressiveness = max(0, min(3, int(aggressiveness)))
        self.vad = webrtcvad.Vad(self.aggressiveness)

        self.ring_buffer = collections.deque(maxlen=self.num_padding_frames)
        self.triggered = False
        self.frame_count = 0
        self.silent_frame_count = 0

        if self.logger:
            self.logger.log_event("VAD", f"Initialized (aggressiveness={self.aggressiveness})")

        print(f"[VAD] Initialized — aggressiveness={self.aggressiveness}, "
              f"frame={frame_duration_ms}ms, padding={padding_duration_ms}ms, "
              f"min_segment={min_segment_ms}ms, noise_suppression={'ON' if enable_noise_suppression else 'OFF'}")

    def _read_frame(self, stream) -> np.ndarray:
        """Read exactly one frame from the audio stream."""
        try:
            frame, _ = stream.read(self.frame_size)
            return np.squeeze(frame)
        except Exception as e:
            _logger.error(f"Error reading frame: {e}")
            return np.array([], dtype=np.float32)

    def _is_speech(self, frame: np.ndarray) -> bool:
        """Convert float32 frame to int16 PCM and check for speech."""
        try:
            frame = np.asarray(frame, dtype=np.float32)
            
            # Noise suppression: remove low-amplitude noise
            if self.enable_noise_suppression and frame.size > 0:
                rms = np.sqrt(np.mean(frame ** 2))
                if rms < self.noise_floor:
                    self.silent_frame_count += 1
                    return False
                self.silent_frame_count = 0
            
            # Convert to int16 PCM
            frame = np.clip(frame, -1.0, 1.0)
            pcm = (frame * 32767).astype(np.int16).tobytes()
            return self.vad.is_speech(pcm, self.sample_rate)
        except Exception as e:
            _logger.debug(f"VAD._is_speech error: {e}")
            return False

    def _auto_calibrate_noise_floor(self, stream, num_frames=20):
        """Auto-detect noise floor by analyzing first N silent frames."""
        print("[VAD] 🔊 Calibrating noise floor (keep quiet for ~1 second)...")
        rms_values = []
        try:
            for _ in range(num_frames):
                frame = self._read_frame(stream)
                rms = np.sqrt(np.mean(frame ** 2)) if frame.size > 0 else 0
                rms_values.append(rms)
            
            if rms_values:
                # Use median (50th percentile) × 1.8 — less aggressive than 75th×1.5
                # which was cutting off real speech in moderately noisy environments
                self.noise_floor = np.percentile(rms_values, 50) * 1.8
                # Hard cap: never set noise floor above 0.05 or below 0.005
                self.noise_floor = max(0.005, min(0.05, self.noise_floor))
                print(f"[VAD] ✓ Noise floor calibrated: {self.noise_floor:.4f}")
            else:
                self.noise_floor = 0.01
        except Exception as e:
            _logger.error(f"Error during noise floor calibration: {e}")
            self.noise_floor = 0.02

    def listen(self):
        """
        Generator — opens mic and yields numpy arrays of voiced audio segments.
        Improved: Audio preprocessing, noise calibration, better error handling.

        Usage:
            for audio_chunk in vad.listen():
                asr.transcribe_from_array(audio_chunk)
        """
        print("[VAD] 🎙️ Listening... (press Ctrl+C to stop)")

        try:
            with sd.InputStream(
                samplerate=self.sample_rate,
                channels=1,
                dtype="float32",
                blocksize=self.frame_size
            ) as stream:
                
                # Auto-calibrate noise floor on first startup
                if self.enable_noise_suppression:
                    self._auto_calibrate_noise_floor(stream, num_frames=15)

                voiced_frames = []

                while True:
                    frame = self._read_frame(stream)
                    if frame.size == 0:
                        continue
                    
                    is_speech = self._is_speech(frame)

                    if not self.triggered:
                        self.ring_buffer.append((frame, is_speech))

                        # Start listening once we detect enough voiced frames
                        num_voiced = sum(1 for _, speech in self.ring_buffer if speech)
                        if num_voiced > self.start_trigger_ratio * self.ring_buffer.maxlen:
                            self.triggered = True
                            voiced_frames = [f for f, _ in self.ring_buffer]
                            self.ring_buffer.clear()

                            if self.logger:
                                self.logger.log_event("VAD", "Speech start detected")
                            print("[VAD] 🎙️ Speech detected")

                    else:
                        voiced_frames.append(frame)
                        self.ring_buffer.append((frame, is_speech))

                        # End capture once the tail is mostly silence
                        num_unvoiced = sum(1 for _, speech in self.ring_buffer if not speech)
                        if num_unvoiced > self.end_trigger_ratio * self.ring_buffer.maxlen:
                            self.triggered = False
                            self.ring_buffer.clear()

                            audio_segment = np.concatenate(voiced_frames)
                            voiced_frames = []

                            # Skip segments too short — likely noise, not real speech
                            if len(audio_segment) < self.min_segment_samples:
                                print(f"[VAD] Segment too short ({len(audio_segment)} samples), skipping")
                                continue

                            if self.logger:
                                self.logger.log_event("VAD", f"Speech end — {len(audio_segment)} samples")
                            print(f"[VAD] Speech segment ready ({len(audio_segment)} samples)")

                            yield audio_segment  # Hand off to wake word / ASR

        except KeyboardInterrupt:
            print("\n[VAD] Stopped by user")
        except Exception as e:
            _logger.error(f"VAD listen error: {e}")
            print(f"[VAD] ❌ Error: {e}")
            raise