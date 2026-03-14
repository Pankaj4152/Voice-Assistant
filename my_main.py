# my_main.py
import os
import re
import tempfile
import time
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
from telemetry.logger import TelemetryLogger

parser = IntentParser()
engine = ActionEngine()
TELEMETRY = None

# Global assistant mode. "normal" = wake-word + command, "dictate" = continuous writing.
ASSISTANT_MODE = "normal"


def set_mode(mode: str) -> None:
    global ASSISTANT_MODE
    ASSISTANT_MODE = mode
    print(f"[MODE] Switched to {ASSISTANT_MODE}")


def _is_editor_window_active() -> bool:
    """
    Best-effort check: only allow dictation typing when a text editor-like
    application is focused (Notepad, Word, VS Code, etc.).
    """
    try:
        import pygetwindow as gw

        win = gw.getActiveWindow()
        if not win or not win.title:
            return False
        title = win.title.lower()
        editor_tokens = [
            "notepad",
            "word",
            "microsoft word",
            "visual studio code",
            "vscode",
            "code",
            "editor",
            "google docs",
            "notion",
        ]
        return any(tok in title for tok in editor_tokens)
    except Exception as e:
        print(f"[Dictation] Could not inspect active window: {e}")
        return False
import pyttsx3
tts = pyttsx3.init()

def speak(text: str) -> None:
    """Best-effort TTS. Falls back to console print if unavailable."""
    try:
        
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
        wake_word: str = "michael",
        wake_word_path: str = os.path.join(os.path.dirname(__file__), "voice", "michael_en_windows_v4_0_0.ppn"),
        wake_sensitivity: float = 0.65,
        whisper_model: str = "base",
        sample_rate: int = 16000,
        vad_aggressiveness: int = 1,
        followup_window_sec: int = 6,
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
        if self.logger:
            self.logger.log_event(
                "Pipeline",
                "Pipeline initialized",
                metadata={
                    "wake_word": wake_word,
                    "wake_sensitivity": wake_sensitivity,
                    "whisper_model": whisper_model,
                    "sample_rate": sample_rate,
                    "vad_aggressiveness": vad_aggressiveness,
                    "followup_window_sec": followup_window_sec,
                },
            )

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
            # max_val = np.abs(audio).max()
            # if max_val > 0:
            #     audio = audio / max_val
            audio = np.clip(audio, -1.0, 1.0)
            audio = audio / np.max(np.abs(audio))
            print(f"[ASR] Transcribing {len(audio)/self.sample_rate:.1f}s audio...")

            result = self.asr.model.transcribe(
                audio,
                fp16=False,
                language="en",                    # auto-detect; handles accents/Hinglish
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
        started = time.time()
        text = self._transcribe_array(audio)
        if not text:
            text = self._transcribe_via_wav_file(audio)

        if self.logger:
            self.logger.log_latency("ASR", started)
            self.logger.log_event(
                "ASR",
                "Transcription completed",
                metadata={
                    "text_present": bool(text),
                    "text_length": len(text or ""),
                },
            )
        return text

    def run(self, on_command=None):
        print("[Pipeline] 🚀 Running. Press Ctrl+C to stop.\n")
        if self.logger:
            self.logger.log_event("Pipeline", "Run loop started")

        try:
            global ASSISTANT_MODE
            for audio_chunk in self.vad.listen():
                now = time.time()

                # ── Dictation mode: continuous speech-to-text typing ───────────
                if ASSISTANT_MODE == "dictate":
                    text = self.transcribe(audio_chunk)
                    if not text:
                        continue

                    lowered = text.lower().strip()
                    # Treat short utterances like "end" / "and" as stop signal.
                    words = lowered.split()
                    if len(words) <= 3 and re.search(r"\bend\b", lowered):
                        ASSISTANT_MODE = "normal"
                        print("[Dictation] Stop keyword detected → back to wake-word mode.")
                        speak("Stopped writing. I'm back to wake word mode.")
                        continue

                    if not _is_editor_window_active():
                        print("[Dictation] Active window is not a text editor; skipping typing.")
                        speak("I only write into editor apps like Notepad or Word. Please focus an editor window or say stop dictation.")
                        continue

                    print(f"[Dictation] Typing: '{text}'")
                    try:
                        import pyautogui

                        pyautogui.typewrite(text + " ")
                    except Exception as e:
                        print(f"[Dictation] Typing failed: {e}")
                        speak("I couldn't type that text.")
                    continue

                # ── Normal mode: wake word → single command ────────────────────
                if not self._listening_for_command:
                    # If we're still in follow-up command mode, skip wake word.
                    if now < self._command_mode_until:
                        self._listening_for_command = True
                    else:
                        if self.wake_word.detect(audio_chunk):
                            print("[Pipeline] ✅ Wake word detected — now listening for command...")
                            if self.logger:
                                self.logger.log_event("Pipeline", "Wake accepted")
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
                    self._command_mode_until = time.time() + float(self._followup_window_sec)
                    self._listening_for_command = False
                    print(f"[Pipeline] 👂 Follow-up mode for {self._followup_window_sec}s...\n")

        except KeyboardInterrupt:
            print("\n[Pipeline] Stopped by user.")
            if self.logger:
                self.logger.log_event("Pipeline", "Run loop interrupted by user")

        except Exception as e:
            if self.logger:
                self.logger.log_error("Pipeline", e)
            raise

        finally:
            self.wake_word.cleanup()
            if self.logger:
                self.logger.log_event("Pipeline", "Run loop stopped")


# ── Simple console handler for testing ───────────────────────────────────
def handle_command(text: str):
    print("\n" + "═" * 60)
    print(f"🤖 COMMAND RECEIVED: '{text}'")
    command_started = time.time()

    if TELEMETRY:
        TELEMETRY.log_event(
            "Command",
            "Command received",
            metadata={"text": text},
        )

    try:
        # ── Step 1: Intent parsing ─────────────────
        parse_started = time.time()
        parsed = parser.parse(text)
        if TELEMETRY:
            TELEMETRY.log_latency("IntentParse", parse_started)
            TELEMETRY.log_event(
                "Intent",
                "Intent parsed",
                metadata={
                    "intent": parsed.intent,
                    "method": parsed.method.value,
                    "confidence": parsed.confidence,
                    "entities": parsed.entities,
                },
            )

        print(f"[INTENT] {parsed.intent} (conf: {parsed.confidence:.2f})")
        print(f"[ENTITIES] {parsed.entities}")

        # ── Step 2: Execute action ─────────────────
        action_started = time.time()
        action_result = engine.execute(parsed)
        if TELEMETRY:
            TELEMETRY.log_latency("Action", action_started)
            TELEMETRY.log_event(
                "Action",
                "Action executed",
                metadata={
                    "success": bool((action_result or {}).get("success", False)),
                    "response_text": (action_result or {}).get("response_text", ""),
                    "intent": parsed.intent,
                },
            )

        print("[ACTION RESULT]", action_result)
        speak((action_result or {}).get("response_text") or "Done.")

        # Some actions (like dictation) can request a mode change for the main loop.
        mode_change = (action_result or {}).get("dictation_mode")
        if mode_change == "start":
            set_mode("dictate")
        elif mode_change == "stop":
            set_mode("normal")

    except Exception as e:
        print("[ERROR] Command processing failed:", e)
        if TELEMETRY:
            TELEMETRY.log_error("Command", e)

    finally:
        if TELEMETRY:
            TELEMETRY.log_latency("CommandTotal", command_started)

    print("═" * 60 + "\n")

# ── Entrypoint ───────────────────────────────────────────────────────────

if __name__ == "__main__":
    TELEMETRY = TelemetryLogger()
    ACCESS_KEY = os.getenv("PICOVOICE_ACCESS_KEY", "")

    if not ACCESS_KEY:
        print("ERROR: Set PICOVOICE_ACCESS_KEY in .env file")
        print("Get free key: https://console.picovoice.ai/")
        exit(1)

    pipeline = VoicePipeline(
        logger=TELEMETRY,
        picovoice_access_key=ACCESS_KEY,
        wake_word="michael",
        wake_word_path=os.path.join(os.path.dirname(__file__), "voice", "michael_en_windows_v4_0_0.ppn"),
        whisper_model="small",   # base is too inaccurate; small handles accents better
        vad_aggressiveness=1,    # 2 was too aggressive; 1 catches more speech frames
    )

    print("Voice Assistant ready! Say 'michael' + command...\n")

    try:
        pipeline.run(on_command=handle_command)
    except KeyboardInterrupt:
        print("\nGoodbye!")
        if TELEMETRY:
            TELEMETRY.log_event("Pipeline", "Application shutdown")