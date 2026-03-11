# my_main.py
import os
import re
import tempfile
import numpy as np
import scipy.io.wavfile as wav
from dotenv import load_dotenv
load_dotenv()

# ── Voice components ─────────────────────────────────────────────────────
from voice.vad import VAD
from voice.wake_word import WakeWordDetector
from voice.asr import WhisperASR

# ── Intent + Action system ─────────────────────────────────────────────
from intent.parser import IntentParser
from actions.action_engine import ActionEngine

parser = IntentParser()
engine = ActionEngine()


def speak(text: str) -> None:
    """Best-effort TTS. Falls back to console print if unavailable."""
    try:
        import pyttsx3
        tts = pyttsx3.init()
        tts.say(text)
        tts.runAndWait()
    except Exception:
        print(f"[TTS] {text}")

class VoicePipeline:
    """
    Full pipeline: Mic → VAD → Wake Word → ASR → (Intent → Action)
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
        followup_window_sec: int = 20,
    ):
        self.logger = logger
        self.sample_rate = sample_rate
        self._listening_for_command = False
        self._followup_window_sec = followup_window_sec
        self._command_mode_until = 0.0

        print("[Pipeline] Initializing components...")

        self.vad = VAD(
            logger=logger,
            sample_rate=sample_rate,
            aggressiveness=vad_aggressiveness
        )

        self.wake_word = WakeWordDetector(
            logger=logger,
            access_key=picovoice_access_key,
            keyword=wake_word,
            keyword_path=wake_word_path,
            sensitivity=wake_sensitivity
        )

        self.asr = WhisperASR(
            logger=logger,
            model_size=whisper_model,
            sample_rate=sample_rate
        )

        print("[Pipeline] ✅ All components ready.")
        print(f"[Pipeline] Say '{wake_word}' to activate.\n")

    def _audio_to_wav(self, audio: np.ndarray) -> str:
        """Save float32 audio array to temp WAV, return file path."""
        with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as f:
            wav.write(f.name, self.sample_rate, (audio * 32767).astype(np.int16))
            return f.name

    # Commands the assistant understands — helps Whisper context
    _INITIAL_PROMPT = (
        "Open chrome, open YouTube, play music, pause, stop, volume up, volume down, "
        "set a timer, search for, close window, open settings, take screenshot, "
        "what time is it, open notepad, open file explorer"
    )

    def _transcribe_array(self, audio: np.ndarray) -> str:
        """Direct NumPy transcription (fast path)."""
        try:
            # Require at least 0.5s of audio — anything shorter is noise/breath
            if len(audio) < self.sample_rate // 2:
                print("[ASR] Audio too short, skipping...")
                return ""

            # Normalize so quiet mic doesn't kill accuracy
            max_val = np.abs(audio).max()
            if max_val > 0:
                audio = audio / max_val

            print(f"[ASR] Transcribing {len(audio)/self.sample_rate:.1f}s audio...")

            result = self.asr.model.transcribe(
                audio,
                fp16=False,
                language=None,                    # auto-detect; handles accents/Hinglish
                temperature=0,                    # deterministic output, no hallucinations
                condition_on_previous_text=False, # prevent hallucination loops
                initial_prompt=self._INITIAL_PROMPT,
            )
            text = result.get("text", "").strip()

            if text:
                print(f"[ASR] Success: '{text}'")
            else:
                print("[ASR] No text recognized")

            return text
        except Exception as e:
            print(f"[ASR] Error: {e}")
            return ""

    def _transcribe_via_wav_file(self, audio: np.ndarray) -> str:
        """
        File-based transcription fallback.
        This works even when direct-array transcription fails in some environments.
        """
        audio_path = self._audio_to_wav(audio)
        try:
            result = self.asr.model.transcribe(
                audio_path,
                fp16=False,
                language=None,
                temperature=0,
                condition_on_previous_text=False,
                initial_prompt=self._INITIAL_PROMPT,
            )
            return (result.get("text", "") or "").strip()
        except Exception as e:
            print(f"[ASR] File-based transcription error: {e}")
            return ""
        finally:
            try:
                os.remove(audio_path)
            except Exception:
                pass

    def transcribe(self, audio: np.ndarray) -> str:
        """Try direct-array transcription first, then file-based fallback."""
        text = self._transcribe_array(audio)
        return text if text else self._transcribe_via_wav_file(audio)

    def run(self, on_command=None):
        print("[Pipeline] 🚀 Running. Press Ctrl+C to stop.\n")

        try:
            for audio_chunk in self.vad.listen():
                now = __import__("time").time()
                if not self._listening_for_command:
                    # If we're still in follow-up command mode, skip wake word.
                    if now < self._command_mode_until:
                        self._listening_for_command = True
                    else:
                        if self.wake_word.detect(audio_chunk):
                            print("[Pipeline] ✅ Wake word detected — now listening for command...")
                            self._listening_for_command = True
                else:
                    print("[Pipeline] 🧠 Processing command...")
                    text = self.transcribe(audio_chunk)

                    if text:
                        print(f"[Pipeline] 📝 Recognized: '{text}'")
                        
                        if on_command:
                            on_command(text)
                        else:
                            print("[Pipeline] (no handler) → text ignored")

                    # Keep listening for follow-up commands for a short window.
                    self._command_mode_until = __import__("time").time() + float(self._followup_window_sec)
                    self._listening_for_command = False
                    print(f"[Pipeline] 👂 Follow-up mode for {self._followup_window_sec}s...\n")

        except KeyboardInterrupt:
            print("\n[Pipeline] Stopped by user.")

        finally:
            self.wake_word.cleanup()


# ── Simple console handler for testing ───────────────────────────────────
def handle_command(text: str):
    print("\n" + "═" * 60)
    print(f"🤖 COMMAND RECEIVED: '{text}'")

    try:
        # ── Step 1: Intent parsing ─────────────────
        parsed = parser.parse(text)
        print(f"[INTENT] {parsed.intent} (conf: {parsed.confidence:.2f})")
        print(f"[ENTITIES] {parsed.entities}")

        # ── Step 2: Execute action ─────────────────
        action_result = engine.execute(parsed)
        print("[ACTION RESULT]", action_result)
        speak((action_result or {}).get("response_text") or "Done.")

    except Exception as e:
        print("[ERROR] Command processing failed:", e)

    print("═" * 60 + "\n")

# ── Entrypoint ───────────────────────────────────────────────────────────

if __name__ == "__main__":
    ACCESS_KEY = os.getenv("PICOVOICE_ACCESS_KEY", "")

    if not ACCESS_KEY:
        print("ERROR: Set PICOVOICE_ACCESS_KEY in .env file")
        print("Get free key: https://console.picovoice.ai/")
        exit(1)

    pipeline = VoicePipeline(
        picovoice_access_key=ACCESS_KEY,
        wake_word="jarvis",
        whisper_model="small",   # base is too inaccurate; small handles accents better
        vad_aggressiveness=1,    # 2 was too aggressive; 1 catches more speech frames
    )

    print("Voice Assistant ready! Say 'jarvis' + command...\n")

    try:
        pipeline.run(on_command=handle_command)
    except KeyboardInterrupt:
        print("\nGoodbye!")