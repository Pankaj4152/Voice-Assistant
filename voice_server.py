"""
Integrated Voice Assistant Server
Combines VoicePipeline from my_main.py with WebSocket server for Electron frontend.
"""

import asyncio
import json
import os
import re
import tempfile
import time
import threading
import numpy as np
import scipy.io.wavfile as wav
import websockets
from websockets.server import WebSocketServerProtocol
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
        whisper_model: str = "base.en",
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

    # Commands the assistant understands — helps Whisper narrow down what to expect
    _INITIAL_PROMPT = (
        "Open chrome, open YouTube, play music, pause, stop, volume up, volume down, "
        "set a timer, search for, close window, open settings, take screenshot, "
        "what time is it, open notepad, open file explorer"
    )

    def _transcribe_array(self, audio: np.ndarray) -> str:
        """Direct NumPy transcription via ASR module."""
        return self.asr.transcribe_from_array(audio, initial_prompt=self._INITIAL_PROMPT)

    def _transcribe_via_wav_file(self, audio: np.ndarray) -> str:
        """
        File-based transcription fallback.
        This works even when direct-array transcription fails in some environments.
        """
        audio_path = self._audio_to_wav(audio)
        try:
            return self.asr.transcribe_from_file(audio_path, initial_prompt=self._INITIAL_PROMPT)
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
                current_time = time.time()
                if not self._listening_for_command:
                    # If we're still in follow-up command mode, skip wake word.
                    if current_time < self._command_mode_until:
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
                    self._command_mode_until = time.time() + float(self._followup_window_sec)
                    self._listening_for_command = False
                    print(f"[Pipeline] 👂 Follow-up mode for {self._followup_window_sec}s...\n")

        except KeyboardInterrupt:
            print("\n[Pipeline] Stopped by user.")

        finally:
            self.wake_word.cleanup()


class VoiceAssistantServer:
    """
    WebSocket server that runs the voice pipeline and streams
    state events to the Electron HUD in real time.

    Event protocol (JSON):
        { "type": "state",      "state": "idle|listening|wake|processing|executing|done|error" }
        { "type": "transcript", "text": "open chrome" }
        { "type": "command",    "intent": "open_app", "entities": {...}, "response": "..." }
        { "type": "latency",    "ms": 312 }
        { "type": "error",      "message": "..." }
    """

    def __init__(
        self,
        host: str = "localhost",
        port: int = 8765,
        picovoice_access_key: str = "",
        wake_word: str = "jarvis",
        whisper_model: str = "base.en",
        sample_rate: int = 16000,
        vad_aggressiveness: int = 2,
    ):
        self.host = host
        self.port = port
        self.sample_rate = sample_rate
        self.clients: set[WebSocketServerProtocol] = set()
        self.pipeline = None
        self.loop = None  # Will be set when run_async is called

        print("[Server] Initializing pipeline...")

        self.pipeline = VoicePipeline(
            picovoice_access_key=picovoice_access_key,
            wake_word=wake_word,
            whisper_model=whisper_model,
            sample_rate=sample_rate,
            vad_aggressiveness=vad_aggressiveness,
        )

        print(f"[Server] 🚀 Ready on ws://{host}:{port}")

    # ── WebSocket broadcast ───────────────────────────────────────────────────

    async def broadcast(self, msg: dict):
        """Send a message to all connected Electron clients."""
        if not self.clients:
            return
        data = json.dumps(msg)
        await asyncio.gather(
            *[client.send(data) for client in self.clients],
            return_exceptions=True
        )

    async def send_state(self, state: str):
        await self.broadcast({"type": "state", "state": state})
        print(f"[Server] → state: {state}")

    async def send_transcript(self, text: str):
        await self.broadcast({"type": "transcript", "text": text})
        print(f"[Server] → transcript: {text}")

    async def send_command(self, intent: str, entities: dict, response: str):
        await self.broadcast({
            "type": "command",
            "intent": intent,
            "entities": entities,
            "response": response
        })
        print(f"[Server] → command executed: {intent}")

    async def send_latency(self, ms: int):
        await self.broadcast({"type": "latency", "ms": ms})

    async def send_error(self, message: str):
        await self.broadcast({"type": "error", "message": message})
        print(f"[Server] → error: {message}")

    # ── Client connection handler ─────────────────────────────────────────────

    async def handle_client(self, websocket: WebSocketServerProtocol):
        self.clients.add(websocket)
        print(f"[Server] Electron client connected ({len(self.clients)} total)")

        try:
            async for message in websocket:
                # Handle any commands from Electron
                try:
                    msg = json.loads(message)
                    print(f"[Server] ← from Electron: {msg}")
                    # Add custom command handling here if needed
                except json.JSONDecodeError:
                    pass
        except websockets.ConnectionClosed:
            pass
        finally:
            self.clients.discard(websocket)
            print(f"[Server] Electron client disconnected ({len(self.clients)} total)")

    # ── Command handler ────────────────────────────────────────────────────────

    async def handle_command(self, text: str):
        """Process a voice command: Intent → Action → Response"""
        print("\n" + "═" * 60)
        print(f"🤖 COMMAND RECEIVED: '{text}'")

        try:
            await self.send_state("processing")
            await self.send_transcript(text)   # show what was heard in the HUD

            # ── Step 1: Intent parsing ─────────────────
            parsed = parser.parse(text)
            print(f"[INTENT] {parsed.intent} (conf: {parsed.confidence:.2f})")
            print(f"[ENTITIES] {parsed.entities}")

            await self.send_state("executing")

            # ── Step 2: Execute action ─────────────────
            action_result = engine.execute(parsed)
            print("[ACTION RESULT]", action_result)
            
            response_text = (action_result or {}).get("response_text") or "Done."
            await self.send_command(
                intent=parsed.intent,
                entities=parsed.entities,
                response=response_text
            )
            
            speak(response_text)
            await self.send_state("done")

        except Exception as e:
            error_msg = f"Command processing failed: {e}"
            print(f"[ERROR] {error_msg}")
            await self.send_error(error_msg)
            await self.send_state("error")

        finally:
            await self.send_state("idle")
            print("═" * 60 + "\n")

    # ── Pipeline runner (runs in blocking thread) ──────────────────────────

    def _fire(self, coro):
        """Schedule a coroutine from the blocking pipeline thread (fire-and-forget)."""
        if self.loop:
            asyncio.run_coroutine_threadsafe(coro, self.loop)

    def run_pipeline_blocking(self):
        """
        Run the voice pipeline (blocking operation).
        This will be executed in a separate thread to avoid blocking the WebSocket server.
        """
        print("[Pipeline] Starting pipeline listener...\n")
        self._fire(self.send_state("listening"))

        try:
            for audio_chunk in self.pipeline.vad.listen():
                current_time = time.time()
                if not self.pipeline._listening_for_command:
                    # If we're still in follow-up command mode, skip wake word.
                    if current_time < self.pipeline._command_mode_until:
                        self.pipeline._listening_for_command = True
                        self._fire(self.send_state("listening"))
                    else:
                        if self.pipeline.wake_word.detect(audio_chunk):
                            print("[Pipeline] Wake word detected — now listening for command...")
                            self.pipeline._listening_for_command = True
                            self._fire(self.send_state("wake"))
                else:
                    print("[Pipeline] Processing command...")
                    self._fire(self.send_state("listening"))
                    text = self.pipeline.transcribe(audio_chunk)

                    if text:
                        print(f"[Pipeline] Recognized: '{text}'")
                        # Schedule the async command handler in the main event loop
                        future = asyncio.run_coroutine_threadsafe(
                            self.handle_command(text),
                            self.loop
                        )
                        try:
                            future.result(timeout=10)
                        except Exception as e:
                            print(f"[Pipeline] Error executing command: {e}")
                    else:
                        # Nothing recognized — go back to idle
                        self._fire(self.send_state("idle"))

                    # Keep listening for follow-up commands for a short window.
                    self.pipeline._command_mode_until = time.time() + float(self.pipeline._followup_window_sec)
                    self.pipeline._listening_for_command = False
                    print(f"[Pipeline] Follow-up mode for {self.pipeline._followup_window_sec}s...\n")

        except KeyboardInterrupt:
            print("\n[Pipeline] Stopped by user.")

        finally:
            self.pipeline.wake_word.cleanup()

    async def run_async(self):
        """
        Run the WebSocket server and pipeline concurrently.
        The pipeline runs in a separate thread, and WebSocket runs in async loop.
        """
        # Store the event loop reference for the pipeline thread
        self.loop = asyncio.get_event_loop()
        
        # Start WebSocket server
        async with websockets.serve(self.handle_client, self.host, self.port):
            print(f"[Server] WebSocket server started on ws://{self.host}:{self.port}")
            
            # Run pipeline in a separate thread
            pipeline_task = self.loop.run_in_executor(None, self.run_pipeline_blocking)
            
            # Keep the server running
            try:
                await pipeline_task
            except Exception as e:
                print(f"[Server] Pipeline error: {e}")


# ── Entrypoint ───────────────────────────────────────────────────────────────

if __name__ == "__main__":
    ACCESS_KEY = os.getenv("PICOVOICE_ACCESS_KEY", "")

    if not ACCESS_KEY:
        print("ERROR: Set PICOVOICE_ACCESS_KEY in .env file")
        print("Get free key: https://console.picovoice.ai/")
        exit(1)

    server = VoiceAssistantServer(
        picovoice_access_key=ACCESS_KEY,
        wake_word="jarvis",
        whisper_model="small.en",  # English-only small model: better accuracy than base
        vad_aggressiveness=1,      # 1 = less filtering, catches accented speech better
    )

    print("Voice Assistant Server ready! Electron clients can now connect.\n")

    try:
        asyncio.run(server.run_async())
    except KeyboardInterrupt:
        print("\nServer stopped.")
