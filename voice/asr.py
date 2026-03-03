import whisper
import sounddevice as sd
import numpy as np
import tempfile
import scipy.io.wavfile as wav
import time


class WhisperASR:
    def __init__(self, logger=None, model_size="base", sample_rate=16000, duration=5):
        self.logger = logger
        self.sample_rate = sample_rate
        self.duration = duration

        print("[ASR] Loading Whisper model..")
        self.model = whisper.load_model(model_size)
        print("[ASR] Model Loaded.")

    def record_audio(self):
        if self.logger:
            self.logger.log_event("ASR", "Recording started")

        print("🎙 Recording...")
        audio = sd.rec(
            int(self.duration * self.sample_rate),
            samplerate=self.sample_rate,
            channels=1,
            dtype="float32"
        )
        sd.wait()

        print("Recording complete.")

        return np.squeeze(audio)
    
    def transcribe(self):
        try:
            start_time = time.time()

            audio_data = self.record_audio()

            # Save temporary WAV file
            with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as temp_audio:
                wav.write(
                    temp_audio.name,
                    self.sample_rate,
                    (audio_data * 32767).astype(np.int16)
                )
                audio_path = temp_audio.name

            if self.logger:
                self.logger.log_event("ASR", "Transcription started")

            result = self.model.transcribe(audio_path)

            text = result.get("text", "").strip()

            if self.logger:
                self.logger.log_latency("ASR", start_time)
                self.logger.log_event("ASR", f"Transcription result: {text}")

            print(f"You said: {text}")

            return text

        except Exception as e:
            if self.logger:
                self.logger.log_error("ASR", e)
            print("ASR Error:", e)
            return None