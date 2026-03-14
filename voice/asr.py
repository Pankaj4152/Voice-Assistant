import whisper
import sounddevice as sd
import numpy as np
import tempfile
import scipy.io.wavfile as wav
import os
import time
import logging

_logger = logging.getLogger(__name__)

# Phrases Whisper commonly hallucinates on short/silent audio
_HALLUCINATED_PHRASES = {
    "thank you.", "thank you", "thanks for watching.", "thanks for watching",
    "thanks.", "thanks", "subscribe.", "like and subscribe", "please subscribe",
    "you", ".", "..", "...", "(music)", "[music]", "(blank_audio)", "[blank_audio]",
    "bye.", "bye", "www.mooji.org", "subtitles by", "captions by",
    "transcribed by", "translated by",
}

# Minimum voiced audio length to attempt transcription (0.5 seconds)
_MIN_AUDIO_SAMPLES = 8000  # at 16kHz


def _is_hallucination(text: str) -> bool:
    """Return True if Whisper output looks like a hallucination."""
    if not text:
        return True
    cleaned = text.strip().lower()
    if cleaned in _HALLUCINATED_PHRASES:
        return True
    # Starts with bracket/paren (e.g. "[BLANK_AUDIO]", "(Music)")
    if cleaned.startswith(("[", "(")):
        return True
    # All punctuation / whitespace
    if all(c in " .,!?…-" for c in cleaned):
        return True
    return False


def _normalize_audio(audio: np.ndarray) -> np.ndarray:
    """
    Normalize float32 audio to [-1, 1] range.
    Also clip any extreme values that would confuse Whisper.
    """
    audio = audio.astype(np.float32)
    peak = np.abs(audio).max()
    if peak > 0:
        audio = audio / peak
    return np.clip(audio, -1.0, 1.0)


def _preprocess_audio(audio: np.ndarray) -> np.ndarray:
    """
    Pre-process audio to improve recognition:
    - Normalize amplitude
    - Reduce DC offset
    - Gentle high-pass filter to reduce low-freq noise
    """
    audio = audio.astype(np.float32)
    
    # Remove DC offset
    audio = audio - np.mean(audio)
    
    # Simple high-pass filter (emphasize speech frequencies)
    if len(audio) > 1:
        # Very simple 1st-order high-pass
        audio = np.diff(audio, prepend=audio[0]) * 0.97
    
    # Normalize
    audio = _normalize_audio(audio)
    return audio


class WhisperASR:
    def __init__(self, logger=None, model_size="base.en", sample_rate=16000,
                 duration=5, language="en", retry_attempts=2):
        self.logger = logger
        self.sample_rate = sample_rate
        self.duration = duration
        self.language = language
        self.retry_attempts = retry_attempts

        print(f"[ASR] Loading Whisper model '{model_size}'..")
        try:
            self.model = whisper.load_model(model_size)
            print("[ASR] ✓ Model loaded successfully.")
        except Exception as e:
            _logger.error(f"Failed to load Whisper model: {e}")
            print(f"[ASR] ❌ Error loading model: {e}")
            raise

    # ─── low-level helpers ────────────────────────────────────────────────

    def record_audio(self) -> np.ndarray:
        """Fixed-duration mic recording (used for standalone testing)."""
        if self.logger:
            self.logger.log_event("ASR", "Recording started")
        print(f"[ASR] Recording {self.duration}s...")
        try:
            audio = sd.rec(
                int(self.duration * self.sample_rate),
                samplerate=self.sample_rate,
                channels=1,
                dtype="float32"
            )
            sd.wait()
            print("[ASR] ✓ Recording complete.")
            return np.squeeze(audio)
        except Exception as e:
            _logger.error(f"Recording error: {e}")
            print(f"[ASR] ❌ Recording failed: {e}")
            raise

    def _whisper_options(self, initial_prompt: str = None) -> dict:
        """
        Shared Whisper decode options.

        - fp16=False       → use float32 (avoids errors on CPU)
        - language         → skip language-detection step for speed & accuracy
        - temperature=0    → deterministic (greedy), no random sampling
        - condition_on_previous_text=False → prevents hallucinated context loops
        - no_speech_threshold=0.6 → mark segment as no-speech if prob > 0.6
        - compression_ratio_threshold=2.0 → reject overly repetitive output
        - logprob_threshold=-1.0 → reject very low-confidence tokens
        - initial_prompt   → bias Whisper toward expected vocabulary
        """
        opts = dict(
            fp16=False,
            language=self.language,
            temperature=0,
            condition_on_previous_text=False,
            no_speech_threshold=0.6,
            compression_ratio_threshold=2.0,
            logprob_threshold=-1.0,

        if initial_prompt:
            opts["initial_prompt"] = initial_prompt
        return opts

    # ─── main API ─────────────────────────────────────────────────────────

    def transcribe_from_array(self, audio: np.ndarray, initial_prompt: str = None) -> str:
        """
        Transcribe a float32 NumPy array directly.
        Returns empty string if audio is too short or result is a hallucination.
        Includes retry logic for robustness.
        """
        if len(audio) < _MIN_AUDIO_SAMPLES:
            print(f"[ASR] Audio too short ({len(audio)} samples < {_MIN_AUDIO_SAMPLES}), skipping")
            return ""

        # Pre-process audio
        audio = _preprocess_audio(audio)

        for attempt in range(self.retry_attempts):
            try:
                result = self.model.transcribe(audio, **self._whisper_options(initial_prompt))
                text = (result.get("text") or "").strip()

                if _is_hallucination(text):
                    print(f"[ASR] Hallucination detected, discarding: '{text}'")
                    return ""

                print(f"[ASR] ✓ Transcribed: '{text}'")
                return text

            except Exception as e:
                if self.logger:
                    self.logger.log_error("ASR", e)
                error_msg = str(e).lower()
                
                if "cuda" in error_msg or "gpu" in error_msg:
                    print(f"[ASR] GPU error (attempt {attempt+1}/{self.retry_attempts}): Falling back to CPU mode")
                    continue
                elif attempt < self.retry_attempts - 1:
                    print(f"[ASR] Transcription failed (attempt {attempt+1}/{self.retry_attempts}), retrying...")
                    time.sleep(0.5)
                    continue
                else:
                    print(f"[ASR] ❌ transcribe_from_array error after {self.retry_attempts} attempts: {e}")
                    return ""

        return ""

    def transcribe_from_file(self, audio_path: str, initial_prompt: str = None) -> str:
        """File-based transcription (reliable fallback)."""
        try:
            result = self.model.transcribe(audio_path, **self._whisper_options(initial_prompt))
            text = (result.get("text") or "").strip()
            if _is_hallucination(text):
                print(f"[ASR] Hallucination detected, discarding: '{text}'")
                return ""
            print(f"[ASR] ✓ File transcription: '{text}'")
            return text
        except Exception as e:
            if self.logger:
                self.logger.log_error("ASR", e)
            print(f"[ASR] ❌ transcribe_from_file error: {e}")
            return ""

    def transcribe(self) -> str:
        """Record from mic then transcribe (standalone mode)."""
        start_time = time.time()
        try:
            audio_data = self.record_audio()

            with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as tmp:
                wav.write(tmp.name, self.sample_rate,
                          (audio_data * 32767).astype(np.int16))
                audio_path = tmp.name

            if self.logger:
                self.logger.log_event("ASR", "Transcription started")

            text = self.transcribe_from_array(audio_data) or self.transcribe_from_file(audio_path)

            try:
                os.remove(audio_path)
            except Exception:
                pass

            if self.logger:
                self.logger.log_latency("ASR", start_time)
                self.logger.log_event("ASR", f"Transcription result: {text}")

            print(f"[ASR] Final result: '{text}'")
            return text

        except Exception as e:
            if self.logger:
                self.logger.log_error("ASR", e)
            print(f"[ASR] ❌ Error: {e}")
            return ""
