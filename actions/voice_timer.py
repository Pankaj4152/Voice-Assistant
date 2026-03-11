"""
Timer / stopwatch actions.

Notes:
- The timer is implemented in-process via `threading.Timer` (reliable).
- We also open the Windows Clock UI (`ms-clock:`) for user visibility.
- When the timer ends, we beep using `winsound` (Windows).
"""

import logging
import threading
import time
import subprocess
import winsound
from typing import Any, Dict, Optional

logger = logging.getLogger(__name__)

_active_timer: Optional[threading.Timer] = None
_stopwatch_start: Optional[float] = None


class TimerActions:
    def handle(self, entities: Dict[str, Any], parsed_intent: Optional[Any] = None) -> Dict[str, Any]:
        action = entities.get("action")

        if action == "timer_set":
            return self.timer_set(entities)
        if action == "timer_cancel":
            return self.timer_cancel()
        if action == "stopwatch_start":
            return self.stopwatch_start()
        if action == "stopwatch_stop":
            return self.stopwatch_stop()
        if action == "stopwatch_reset":
            return self.stopwatch_reset()

        return {"success": False, "response_text": f"Timer action '{action}' not supported"}

    def timer_set(self, entities: Dict[str, Any]) -> Dict[str, Any]:
        global _active_timer

        duration = int(entities.get("duration") or 0)
        unit = (entities.get("unit") or "seconds").lower()
        if duration <= 0:
            return {"success": False, "response_text": "Please tell me a timer duration."}

        seconds = duration * (3600 if unit == "hours" else 60 if unit == "minutes" else 1)

        try:
            if _active_timer:
                _active_timer.cancel()
        except Exception:
            pass

        def _done():
            logger.info("Timer finished (%ss)", seconds)
            try:
                winsound.Beep(1200, 800)
                winsound.Beep(1500, 600)
            except Exception:
                pass

        _active_timer = threading.Timer(seconds, _done)
        _active_timer.daemon = True
        _active_timer.start()

        try:
            subprocess.Popen('start "" "ms-clock:"', shell=True)
        except Exception:
            pass

        return {"success": True, "response_text": f"Timer set for {duration} {unit}."}

    def timer_cancel(self) -> Dict[str, Any]:
        global _active_timer
        if not _active_timer:
            return {"success": False, "response_text": "No active timer."}
        try:
            _active_timer.cancel()
        finally:
            _active_timer = None
        return {"success": True, "response_text": "Timer cancelled."}

    def stopwatch_start(self) -> Dict[str, Any]:
        global _stopwatch_start
        _stopwatch_start = time.time()
        try:
            subprocess.Popen('start "" "ms-clock:"', shell=True)
        except Exception:
            pass
        return {"success": True, "response_text": "Stopwatch started."}

    def stopwatch_stop(self) -> Dict[str, Any]:
        global _stopwatch_start
        if not _stopwatch_start:
            return {"success": False, "response_text": "Stopwatch is not running."}
        elapsed = time.time() - _stopwatch_start
        mins, secs = divmod(int(elapsed), 60)
        return {"success": True, "response_text": f"Stopwatch stopped at {mins} minutes {secs} seconds.", "elapsed": elapsed}

    def stopwatch_reset(self) -> Dict[str, Any]:
        global _stopwatch_start
        _stopwatch_start = None
        return {"success": True, "response_text": "Stopwatch reset."}
