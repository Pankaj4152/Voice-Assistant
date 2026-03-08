import tempfile
import numpy as np
import scipy.io.wavfile as wav

from voice.vad import VAD
from voice.wake_word import WakeWordDetector
from voice.asr import WhisperASR
import os
from dotenv import load_dotenv
load_dotenv()

class VoicePipeline:
    """
    Full pipeline: Mic → VAD → Wake Word → ASR → (Intent → Action)

    Flow:
        1. VAD continuously listens and yields voiced audio segments
        2. Each segment is checked for the wake word (Porcupine)
        3. If wake word found → ASR transcribes the NEXT speech segment
        4. Transcribed text is passed to your intent/action handler

    Usage:
        pipeline = VoicePipeline(access_key="YOUR_PICOVOICE_KEY")
        pipeline.run(on_command=my_handler)
    """

    def __init__(
        self,
        logger=None,
        picovoice_access_key: str = "",
        wake_word: str = "jarvis",
        wake_word_path: str = None,
        wake_sensitivity: float = 0.5,
        whisper_model: str = "base",
        sample_rate: int = 16000,
        vad_aggressiveness: int = 2,
    ):
        self.logger = logger
        self.sample_rate = sample_rate
        self._listening_for_command = False  # State: waiting for wake word OR command

        print("[Pipeline] Initializing components...")

        # 1. VAD
        self.vad = VAD(
            logger=logger,
            sample_rate=sample_rate,
            aggressiveness=vad_aggressiveness
        )

        # 2. Wake Word
        self.wake_word = WakeWordDetector(
            logger=logger,
            access_key=picovoice_access_key,
            keyword=wake_word,
            keyword_path=wake_word_path,
            sensitivity=wake_sensitivity
        )

        # 3. ASR
        self.asr = WhisperASR(
            logger=logger,
            model_size=whisper_model,
            sample_rate=sample_rate
        )

        print("[Pipeline] ✅ All components ready.")
        print(f"[Pipeline] Say '{wake_word}' to activate.\n")

    def _audio_to_wav(self, audio: np.ndarray) -> str:
        """Save a float32 numpy array to a temp WAV file, return path."""
        with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as f:
            wav.write(f.name, self.sample_rate, (audio * 32767).astype(np.int16))
            return f.name

    def _transcribe_array(self, audio: np.ndarray) -> str:
        """Transcribe a numpy audio array directly (no re-recording)."""
        audio_path = self._audio_to_wav(audio)
        result = self.asr.model.transcribe(audio_path)
        return result.get("text", "").strip()

    def run(self, on_command=None):
        """
        Start the pipeline loop.

        Args:
            on_command: callable(text: str) — called with transcribed text
                        after wake word is detected. If None, just prints.

        The loop runs forever until KeyboardInterrupt.
        """
        print("[Pipeline] 🚀 Running. Press Ctrl+C to stop.\n")

        try:
            for audio_chunk in self.vad.listen():
                # ── STATE 1: Waiting for wake word ──────────────────────────
                if not self._listening_for_command:
                    if self.wake_word.detect(audio_chunk):
                        print("[Pipeline] ✅ Wake word heard — listening for command...")
                        self._listening_for_command = True

                # ── STATE 2: Wake word heard — transcribe next utterance ─────
                else:
                    print("[Pipeline] 🧠 Transcribing command...")
                    text = self._transcribe_array(audio_chunk)

                    if text:
                        print(f"[Pipeline] 📝 Command: '{text}'")

                        if self.logger:
                            self.logger.log_event("Pipeline", f"Command: {text}")

                        if on_command:
                            on_command(text)
                        else:
                            print(f"[Pipeline] (no handler) Got: {text}")

                    # Reset — wait for wake word again
                    self._listening_for_command = False
                    print("[Pipeline] 👂 Waiting for wake word...\n")

        except KeyboardInterrupt:
            print("\n[Pipeline] Stopped by user.")

        finally:
            self.wake_word.cleanup()


# ── Entrypoint ────────────────────────────────────────────────────────────────

if __name__ == "__main__":

    ACCESS_KEY = os.getenv("PICOVOICE_ACCESS_KEY", "")

    if not ACCESS_KEY:
        print("ERROR: Set PICOVOICE_ACCESS_KEY environment variable.")
        print("Get a free key at: https://console.picovoice.ai/")
        exit(1)

    def handle_command(text: str):
        """
        Plug your Intent + Action logic here.
        Example: pass text to an LLM, run a regex intent parser, etc.
        """
        print(f"\n🤖 Handling: '{text}'")
        # TODO: intent = IntentEngine().parse(text)
        # TODO: ActionRouter().execute(intent)

    pipeline = VoicePipeline(
        picovoice_access_key=ACCESS_KEY,
        wake_word="jarvis",
        whisper_model="base",
        vad_aggressiveness=2,
    )

    pipeline.run(on_command=handle_command)