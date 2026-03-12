import asyncio
import json
import time
import websockets
from websockets.server import WebSocketServerProtocol

from voice.vad import VAD
from voice.wake_word import WakeWordDetector
from voice.asr import WhisperASR

import numpy as np
import scipy.io.wavfile as wav
import tempfile
import os


class PipelineServer:
    """
    WebSocket server that runs the voice pipeline and streams
    state events to the Electron HUD in real time.

    Event protocol (JSON):
        { "type": "state",      "state": "idle|listening|wake|processing|executing|done|error" }
        { "type": "transcript", "text": "open chrome" }
        { "type": "latency",    "ms": 312 }
        { "type": "error",      "message": "..." }
    """

    def __init__(
        self,
        host: str = "localhost",
        port: int = 8765,
        picovoice_access_key: str = "",
        wake_word: str = "jarvis",
        whisper_model: str = "base",
        sample_rate: int = 16000,
        vad_aggressiveness: int = 1,
        wake_sensitivity: float = 0.65,
    ):
        self.host = host
        self.port = port
        self.sample_rate = sample_rate
        self.clients: set[WebSocketServerProtocol] = set()

        print("[Server] Initializing pipeline components...")

        self.vad = VAD(sample_rate=sample_rate, aggressiveness=vad_aggressiveness)
        self.wake_word = WakeWordDetector(
            access_key=picovoice_access_key,
            keyword=wake_word,
            sensitivity=wake_sensitivity
        )
        self.asr = WhisperASR(model_size=whisper_model, sample_rate=sample_rate)

        self._listening_for_command = False
        print(f"[Server] Ready on ws://{host}:{port}")

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

    async def send_latency(self, ms: int):
        await self.broadcast({"type": "latency", "ms": ms})

    async def send_error(self, message: str):
        await self.broadcast({"type": "error", "message": message})

    # ── Client connection handler ─────────────────────────────────────────────

    async def handle_client(self, websocket: WebSocketServerProtocol):
        self.clients.add(websocket)
        print(f"[Server] Electron client connected ({len(self.clients)} total)")

        try:
            async for message in websocket:
                # Handle any commands from Electron (future use)
                try:
                    msg = json.loads(message)
                    print(f"[Server] ← from Electron: {msg}")
                except json.JSONDecodeError:
                    pass
        except websockets.ConnectionClosed:
            pass
        finally:
            self.clients.discard(websocket)
            print(f"[Server] Electron client disconnected ({len(self.clients)} total)")

    # ── Pipeline loop (runs in thread, posts events via asyncio) ─────────────

    def _audio_to_wav(self, audio: np.ndarray) -> str:
        with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as f:
            wav.write(f.name, self.sample_rate, (audio * 32767).astype(np.int16))
            return f.name

    def _transcribe_array(self, audio: np.ndarray) -> str:
        audio_path = self._audio_to_wav(audio)
        result = self.asr.model.transcribe(audio_path)
        os.unlink(audio_path)  # Clean up temp file
        return result.get("text", "").strip()

    async def run_pipeline(self):
        """Async pipeline loop — integrates VAD generator with WebSocket events."""
        await self.send_state("idle")
        print("[Server] Pipeline running. Say the wake word to begin.")

        loop = asyncio.get_event_loop()

        # Run VAD generator in a thread (it's blocking)
        vad_queue = asyncio.Queue()

        def vad_thread():
            for audio_chunk in self.vad.listen():
                loop.call_soon_threadsafe(vad_queue.put_nowait, audio_chunk)

        import threading
        t = threading.Thread(target=vad_thread, daemon=True)
        t.start()

        await self.send_state("listening")

        while True:
            audio_chunk = await vad_queue.get()

            if not self._listening_for_command:
                # Check for wake word
                detected = await loop.run_in_executor(
                    None, self.wake_word.detect, audio_chunk
                )
                if detected:
                    self._listening_for_command = True
                    await self.send_state("wake")
                    print("[Server] Wake word detected — awaiting command...")

            else:
                # Transcribe the command
                start = time.time()
                await self.send_state("processing")

                try:
                    text = await loop.run_in_executor(
                        None, self._transcribe_array, audio_chunk
                    )
                    elapsed_ms = int((time.time() - start) * 1000)

                    if text:
                        await self.send_transcript(text)
                        await self.send_latency(elapsed_ms)
                        await self.send_state("executing")

                        # ── Plug intent engine here (Layer 3) ──
                        # intent = await intent_engine.parse(text)
                        # await action_router.execute(intent)

                        await asyncio.sleep(0.5)  # Placeholder for action execution
                        await self.send_state("done")
                        await asyncio.sleep(1.5)

                    self._listening_for_command = False
                    await self.send_state("listening")

                except Exception as e:
                    await self.send_error(str(e))
                    self._listening_for_command = False
                    await self.send_state("idle")

    # ── Start server ──────────────────────────────────────────────────────────

    async def start(self):
        async with websockets.serve(self.handle_client, self.host, self.port):
            print(f"[Server] WebSocket server listening on ws://{self.host}:{self.port}")
            await self.run_pipeline()  # Runs forever


# ── Entrypoint ────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    import os

    ACCESS_KEY = os.environ.get("PICOVOICE_ACCESS_KEY", "")
    if not ACCESS_KEY:
        print("ERROR: Set PICOVOICE_ACCESS_KEY environment variable.")
        exit(1)

    server = PipelineServer(
        picovoice_access_key=ACCESS_KEY,
        wake_word="jarvis",
        whisper_model="base",
        wake_sensitivity=0.65,
    )

    asyncio.run(server.start())