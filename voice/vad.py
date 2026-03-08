import webrtcvad
import sounddevice as sd
import numpy as np
import collections


class VAD:
    """
    Voice Activity Detector — continuously reads from mic in small chunks,
    buffers them, and yields only segments where speech is detected.

    Uses WebRTC VAD (very lightweight, works offline).
    """

    def __init__(self, logger=None, sample_rate=16000, aggressiveness=2,
                 frame_duration_ms=30, padding_duration_ms=300):
        """
        sample_rate: 16000Hz (WebRTC VAD requirement)
        aggressiveness: 0-3 (0 = least aggressive filtering, 3 = most aggressive)
        frame_duration_ms: 10, 20, or 30ms — WebRTC VAD requirement
        padding_duration_ms: silence padding before cutting off speech

        """
        self.logger = logger
        self.sample_rate = sample_rate
        self.frame_duration_ms = frame_duration_ms
        self.frame_size = int(sample_rate * frame_duration_ms / 1000)  # samples per frame
        self.padding_duration_ms = padding_duration_ms
        self.num_padding_frames = padding_duration_ms // frame_duration_ms

        self.vad = webrtcvad.Vad(aggressiveness)

        # Ring buffer to hold recent frames for context
        self.ring_buffer = collections.deque(maxlen=self.num_padding_frames)
        self.triggered = False

        if self.logger:
            self.logger.log_event("VAD", f"Initialized (aggressiveness={aggressiveness})")

        print(f"[VAD] Initialized — aggressiveness={aggressiveness}, "
              f"frame={frame_duration_ms}ms, padding={padding_duration_ms}ms")

    def _is_speech(self, frame: np.ndarray) -> bool:
        """Convert float32 frame to int16 PCM and check for speech."""
        pcm = (frame * 32767).astype(np.int16).tobytes()
        try:
            return self.vad.is_speech(pcm, self.sample_rate)
        except Exception:
            return False

    def _read_frame(self, stream) -> np.ndarray:
        """Read exactly one frame from the audio stream."""
        frame, _ = stream.read(self.frame_size)
        return np.squeeze(frame)

    def listen(self):
        """
        Generator — opens mic and yields numpy arrays of voiced audio segments.

        Usage:
            for audio_chunk in vad.listen():
                asr.transcribe_from_array(audio_chunk)
        """
        print("[VAD] Listening... (press Ctrl+C to stop)")

        with sd.InputStream(
            samplerate=self.sample_rate,
            channels=1,
            dtype="float32",
            blocksize=self.frame_size
        ) as stream:

            voiced_frames = []

            while True:
                frame = self._read_frame(stream)
                is_speech = self._is_speech(frame)

                if not self.triggered:
                    self.ring_buffer.append((frame, is_speech))

                    # If >90% of the ring buffer is speech → start capturing
                    num_voiced = sum(1 for _, speech in self.ring_buffer if speech)
                    if num_voiced > 0.9 * self.ring_buffer.maxlen:
                        self.triggered = True
                        voiced_frames = [f for f, _ in self.ring_buffer]
                        self.ring_buffer.clear()

                        if self.logger:
                            self.logger.log_event("VAD", "Speech start detected")
                        print("[VAD] 🎙 Speech detected")

                else:
                    voiced_frames.append(frame)
                    self.ring_buffer.append((frame, is_speech))

                    # If >90% of ring buffer is silence → end of utterance
                    num_unvoiced = sum(1 for _, speech in self.ring_buffer if not speech)
                    if num_unvoiced > 0.9 * self.ring_buffer.maxlen:
                        self.triggered = False
                        self.ring_buffer.clear()

                        audio_segment = np.concatenate(voiced_frames)
                        voiced_frames = []

                        if self.logger:
                            self.logger.log_event("VAD", f"Speech end — {len(audio_segment)} samples")
                        print("[VAD] ✅ Speech segment ready")

                        yield audio_segment  # Hand off to wake word / ASR