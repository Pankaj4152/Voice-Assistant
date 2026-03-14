"""
General accessibility-focused commands.

This module keeps read-only utility commands in one place, such as:
- Current system volume status
- Describing what is on the screen for blind/low-vision users
"""

import ctypes
import logging
import os
import socket
import subprocess
import tempfile
from datetime import datetime
from typing import Optional

logger = logging.getLogger(__name__)


class GeneralCommands:
    """Read-only OS commands intended to improve accessibility."""

    def __init__(self):
        self.gemini_api_key = os.getenv("GEMINI_API_KEY", "").strip()
        self.gemini_model = os.getenv("GEMINI_VISION_MODEL", "models/gemini-2.0-flash")

    def volume_status(self) -> dict:
        """Return current output volume level as percentage."""
        try:
            volume = ctypes.c_uint()
            result = ctypes.windll.winmm.waveOutGetVolume(0, ctypes.byref(volume))
            if result != 0:
                return {
                    "success": False,
                    "response_text": "I could not read the current volume level.",
                }

            raw = volume.value
            left = raw & 0xFFFF
            right = (raw >> 16) & 0xFFFF

            left_percent = round((left / 65535) * 100)
            right_percent = round((right / 65535) * 100)
            avg_percent = round((left_percent + right_percent) / 2)

            return {
                "success": True,
                "response_text": f"Current volume is about {avg_percent} percent.",
                "volume_left": left_percent,
                "volume_right": right_percent,
                "volume_percent": avg_percent,
            }
        except Exception as e:
            logger.error("Volume status failed: %s", e)
            return {
                "success": False,
                "response_text": "I could not read the current volume level.",
            }

    def describe_screen(self) -> dict:
        """Describe current on-screen context, with Gemini vision when available."""
        overview = self._active_window_overview()
        vision_description = self._describe_screen_with_gemini()

        if vision_description:
            response = f"{overview} {vision_description}".strip()
        else:
            response = (
                f"{overview} I can give a richer description if Gemini vision is configured."
            ).strip()

        return {
            "success": True,
            "response_text": response,
            "vision_enabled": bool(vision_description),
        }

    def battery_status(self) -> dict:
        """Return battery and charging information on Windows."""

        class SYSTEM_POWER_STATUS(ctypes.Structure):
            _fields_ = [
                ("ACLineStatus", ctypes.c_byte),
                ("BatteryFlag", ctypes.c_byte),
                ("BatteryLifePercent", ctypes.c_byte),
                ("Reserved1", ctypes.c_byte),
                ("BatteryLifeTime", ctypes.c_ulong),
                ("BatteryFullLifeTime", ctypes.c_ulong),
            ]

        try:
            status = SYSTEM_POWER_STATUS()
            ok = ctypes.windll.kernel32.GetSystemPowerStatus(ctypes.byref(status))
            if not ok:
                return {
                    "success": False,
                    "response_text": "I could not read battery status.",
                }

            percent = int(status.BatteryLifePercent)
            charging = status.ACLineStatus == 1
            unknown_percent = percent == 255

            if unknown_percent:
                battery_part = "Battery percentage is not available"
            else:
                battery_part = f"Battery is at {percent} percent"

            power_part = "and charging" if charging else "and not charging"

            return {
                "success": True,
                "response_text": f"{battery_part}, {power_part}.",
                "battery_percent": None if unknown_percent else percent,
                "charging": charging,
            }
        except Exception as e:
            logger.error("Battery status failed: %s", e)
            return {
                "success": False,
                "response_text": "I could not read battery status.",
            }

    def wifi_status(self) -> dict:
        """Return Wi-Fi connection state, SSID, and signal if available."""
        try:
            result = subprocess.run(
                ["netsh", "wlan", "show", "interfaces"],
                capture_output=True,
                text=True,
                timeout=6,
                check=False,
            )
            text = (result.stdout or "") + "\n" + (result.stderr or "")
            lowered = text.lower()

            if "there is no wireless interface on the system" in lowered:
                return {
                    "success": True,
                    "response_text": "No wireless adapter is detected on this system.",
                }

            state = self._extract_colon_value(text, "State")
            ssid = self._extract_colon_value(text, "SSID")
            bssid = self._extract_colon_value(text, "BSSID")
            signal = self._extract_colon_value(text, "Signal")

            if state and state.lower() == "connected":
                parts = ["Wi-Fi is connected"]
                if ssid:
                    parts.append(f"to {ssid}")
                if signal:
                    parts.append(f"with signal {signal}")
                response = " ".join(parts) + "."
            elif state:
                response = f"Wi-Fi state is {state}."
            else:
                response = "I could not determine Wi-Fi status."

            return {
                "success": True,
                "response_text": response,
                "wifi_state": state,
                "ssid": ssid,
                "bssid": bssid,
                "signal": signal,
            }
        except Exception as e:
            logger.error("Wi-Fi status failed: %s", e)
            return {
                "success": False,
                "response_text": "I could not read Wi-Fi status.",
            }

    def network_status(self) -> dict:
        """Simple internet reachability check."""
        try:
            with socket.create_connection(("8.8.8.8", 53), timeout=2):
                online = True
        except OSError:
            online = False

        if online:
            response = "Internet appears to be connected."
        else:
            response = "Internet appears to be disconnected."

        return {
            "success": True,
            "response_text": response,
            "online": online,
        }

    def active_window_status(self) -> dict:
        """Return what app/window is currently in focus."""
        return {
            "success": True,
            "response_text": self._active_window_overview(),
        }

    def date_time_status(self) -> dict:
        """Return local date and time in TTS-friendly wording."""
        now = datetime.now()
        spoken_time = now.strftime("%I:%M %p").lstrip("0")
        spoken_date = now.strftime("%A, %d %B %Y")
        return {
            "success": True,
            "response_text": f"It is {spoken_time}. Today is {spoken_date}.",
            "iso_time": now.isoformat(),
        }

    def environment_summary(self) -> dict:
        """Accessibility summary for commonly asked environment questions."""
        active_text = self.active_window_status().get("response_text", "")
        battery_text = self.battery_status().get("response_text", "")
        wifi_text = self.wifi_status().get("response_text", "")
        net_text = self.network_status().get("response_text", "")
        time_text = self.date_time_status().get("response_text", "")

        parts = [
            part.strip()
            for part in [active_text, battery_text, wifi_text, net_text, time_text]
            if isinstance(part, str) and part.strip()
        ]

        response = " ".join(parts) if parts else "I could not gather environment details right now."

        return {
            "success": True,
            "response_text": response,
        }

    def _active_window_overview(self) -> str:
        """Best-effort quick summary even when vision model is unavailable."""
        try:
            import pygetwindow as gw

            active = gw.getActiveWindow()
            title = (active.title if active else "") if active is not None else ""
            title = (title or "").strip()

            if title:
                return f"You are currently on the {title} window."
            return "I can detect an active window, but it has no readable title."
        except Exception:
            return "I cannot read the active window title right now."

    def _describe_screen_with_gemini(self) -> Optional[str]:
        """Capture screenshot and ask Gemini for an accessibility-first description."""
        if not self.gemini_api_key:
            return None

        temp_path: Optional[str] = None

        try:
            import pyautogui
            from google import genai
            from google.genai import types

            with tempfile.NamedTemporaryFile(suffix=".png", delete=False) as temp_file:
                temp_path = temp_file.name

            screenshot = pyautogui.screenshot()
            screenshot.save(temp_path)

            with open(temp_path, "rb") as f:
                image_bytes = f.read()

            prompt = (
                "You are assisting a blind user. Describe this screen in plain, concise speech. "
                "Prioritize: active app, visible text the user should know, major buttons/inputs, "
                "alerts/errors, and what they can do next. Keep it under 90 words."
            )

            client = genai.Client(api_key=self.gemini_api_key)
            response = client.models.generate_content(
                model=self.gemini_model,
                contents=[
                    types.Part.from_bytes(data=image_bytes, mime_type="image/png"),
                    prompt,
                ],
                config=types.GenerateContentConfig(
                    temperature=0.2,
                    max_output_tokens=220,
                ),
            )

            text = (response.text or "").strip()
            return text or None

        except Exception as e:
            logger.error("Gemini screen description failed: %s", e)
            return None

        finally:
            if temp_path and os.path.exists(temp_path):
                try:
                    os.remove(temp_path)
                except OSError:
                    logger.warning("Could not clean up temp screenshot: %s", temp_path)

    @staticmethod
    def _extract_colon_value(text: str, key: str) -> Optional[str]:
        for raw_line in text.splitlines():
            line = raw_line.strip()
            if not line.lower().startswith(f"{key.lower()} ") and not line.lower().startswith(f"{key.lower()}:"):
                continue
            if ":" not in line:
                continue
            _, value = line.split(":", 1)
            cleaned = value.strip()
            if cleaned:
                return cleaned
        return None
