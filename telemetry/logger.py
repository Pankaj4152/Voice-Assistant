import json
import time
import uuid
from datetime import datetime, timezone
from pathlib import Path



class TelemetryLogger:
    def __init__(self, log_dir="logs"):
        self.session_id = str(uuid.uuid4())
        self.log_dir = Path(log_dir)
        self.log_dir.mkdir(exist_ok=True)

        self.log_file = self.log_dir / f"session_{self.session_id}.jsonl"

        print(f"[Telemetry] Session started: {self.session_id}")
        print(f"[Telemetry] Logging to: {self.log_file}")

    def _write(self, data: dict):
        with open(self.log_file, "a", encoding="utf-8") as f:
            f.write(json.dumps(data) + "\n")

    def log_event(self, stage: str, message: str, metadata: dict = None):
        log_entry = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "session_id": self.session_id,
            "stage": stage,
            "message": message,
            "metadata": metadata or {}
        }
        self._write(log_entry)
        print(f"[{stage}] {message}")
    
    def log_latency(self, stage: str, start_time: float):
        latency_ms = round((time.time() - start_time) * 1000, 2)

        log_entry = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "session_id": self.session_id,
            "stage": stage,
            "latency_ms": latency_ms
        }

        self._write(log_entry)
        print(f"[{stage}] Latency: {latency_ms} ms")

        return latency_ms

    def log_error(self, stage: str, error: Exception):
        log_entry = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "session_id": self.session_id,
            "stage": stage,
            "error": str(error)
        }

        self._write(log_entry)
        print(f"[ERROR - {stage}] {error}")