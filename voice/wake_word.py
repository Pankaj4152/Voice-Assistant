import pvporcupine
import numpy as np
import struct


class WakeWordDetector:
    """
    Wake word detector using Picovoice Porcupine.

    Listens to raw audio frames (from VAD or directly from mic) and fires
    a callback / returns True when the wake word is detected.

    Built-in wake words (free):
        "alexa", "hey google", "hey siri", "jarvis", "ok google",
        "computer", "picovoice", "bumblebee", "porcupine", "terminator"

    Custom wake words require a .ppn file from https://console.picovoice.ai/
    """

    def __init__(self, logger=None, access_key: str = "",
                 keyword: str = "jarvis", keyword_path: str = None,
                 sensitivity: float = 0.5):
        """
        access_key:    Picovoice Console API key (free tier available)
        keyword:       Built-in keyword name (ignored if keyword_path is set)
        keyword_path:  Path to custom .ppn wake word model file
        sensitivity:   0.0–1.0 (higher = more sensitive, more false positives)
        """
        self.logger = logger

        if not access_key:
            raise ValueError(
                "[WakeWord] Picovoice access_key is required.\n"
                "Get a free key at: https://console.picovoice.ai/"
            )

        # Load Porcupine with built-in or custom keyword
        if keyword_path:
            self.porcupine = pvporcupine.create(
                access_key=access_key,
                keyword_paths=[keyword_path],
                sensitivities=[sensitivity]
            )
            print(f"[WakeWord] Loaded custom keyword from: {keyword_path}")
        else:
            self.porcupine = pvporcupine.create(
                access_key=access_key,
                keywords=[keyword],
                sensitivities=[sensitivity]
            )
            print(f"[WakeWord] Listening for: '{keyword}' (sensitivity={sensitivity})")

        # Porcupine requires exactly this frame length
        self.frame_length = self.porcupine.frame_length        # typically 512 samples
        self.sample_rate = self.porcupine.sample_rate          # always 16000

        if self.logger:
            self.logger.log_event("WakeWord", f"Initialized — keyword='{keyword}'")

    def detect(self, audio_chunk: np.ndarray) -> bool:
        """
        Check a float32 audio chunk for the wake word.

        The chunk is split into Porcupine-sized frames (512 samples each).
        Returns True if wake word is detected in ANY frame of the chunk.

        Args:
            audio_chunk: float32 numpy array from VAD (any length)

        Returns:
            True if wake word detected, False otherwise
        """
        # Convert float32 → int16 PCM (Porcupine requirement)
        pcm = (audio_chunk * 32767).astype(np.int16)

        # Process in frame_length-sized windows
        for i in range(0, len(pcm) - self.frame_length, self.frame_length):
            frame = pcm[i: i + self.frame_length]
            result = self.porcupine.process(frame)

            if result >= 0:  # >= 0 means a keyword was detected (index into keywords list)
                if self.logger:
                    self.logger.log_event("WakeWord", "Wake word detected!")
                print("[WakeWord] 🔔 Wake word detected!")
                return True

        return False

    def detect_from_stream(self, stream_frame: np.ndarray) -> bool:
        """
        Optimized for direct mic streaming — pass exactly one frame at a time.
        Use this if you're NOT going through VAD (raw stream mode).

        Args:
            stream_frame: exactly self.frame_length int16 samples

        Returns:
            True if wake word detected
        """
        if len(stream_frame) != self.frame_length:
            return False

        pcm = (stream_frame * 32767).astype(np.int16)
        result = self.porcupine.process(pcm)

        if result >= 0:
            if self.logger:
                self.logger.log_event("WakeWord", "Wake word detected (stream mode)")
            print("[WakeWord] 🔔 Wake word detected!")
            return True

        return False

    def cleanup(self):
        """Release Porcupine resources — always call this on shutdown."""
        self.porcupine.delete()
        print("[WakeWord] Cleaned up Porcupine instance.")

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.cleanup()