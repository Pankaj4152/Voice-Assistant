"""
OS-level actions (Windows-focused).

Design:
- This module receives normalized entities from `intent/parser.py`.
- Each method returns a dict result object with at least:
  `success: bool`, `response_text: str`
So the caller can feed `response_text` into TTS.
"""

import os
import logging
import subprocess
import time
import urllib.parse
from datetime import datetime

logger = logging.getLogger(__name__)

from .voice_timer import TimerActions


class OSActions:

    def __init__(self):
        self.timer = TimerActions()

    def handle(self, entities, parsed_intent=None):
        action = entities.get("action")
        target = entities.get("target")
        value = entities.get("value")

        if action in ("timer_set", "timer_cancel", "stopwatch_start", "stopwatch_stop", "stopwatch_reset"):
            return self.timer.handle(entities, parsed_intent=parsed_intent)

        if action == "music_play":
            return self.music_play(entities)

        # Map parsed intent actions to implemented primitives
        if action == "screenshot":
            return self.screenshot()
        if action in ("mute", "unmute"):
            return self.mute(mute=(action == "mute"))
        if action == "increase" and target == "volume":
            return self.volume_up()
        if action == "decrease" and target == "volume":
            return self.volume_down()
        if action == "set" and target == "volume":
            return self.volume_set(value)
        if action in ("increase", "decrease", "set") and target == "brightness":
            return self.brightness(action=action, value=value)
        if action == "minimize":
            return self.minimize()
        if action == "minimize_all":
            return self.minimize_all()
        if action == "maximize":
            return self.maximize()
        if action == "restore":
            return self.restore()
        if action == "launch":
            return self.launch_app(entities)
        if action == "switch_app":
            return self.switch_to_app(entities)
        if action == "close":
            return self.close_app(entities)
        if action == "close_window":
            return self.close_window()
        if action in ("switch_window", "next_window"):
            return self.switch_window(previous=False)
        if action == "previous_window":
            return self.switch_window(previous=True)
        if action == "task_view":
            return self.task_view()
        if action == "show_desktop":
            return self.show_desktop()
        if action == "new_desktop":
            return self.new_virtual_desktop()
        if action == "next_desktop":
            return self.switch_virtual_desktop(next_desktop=True)
        if action == "previous_desktop":
            return self.switch_virtual_desktop(next_desktop=False)
        if action == "close_desktop":
            return self.close_virtual_desktop()
        if action == "copy":
            return self.clipboard_shortcut("copy")
        if action == "paste":
            return self.clipboard_shortcut("paste")
        if action == "cut":
            return self.clipboard_shortcut("cut")
        if action == "select_all":
            return self.clipboard_shortcut("select_all")
        if action == "close_all_apps":
            return self.close_all_apps()
        if action == "lock":
            return self.lock()
        if action == "shutdown":
            return self.shutdown()
        if action == "restart":
            return self.restart()
        if action == "sleep":
            return self.sleep()

        return {
            "success": False,
            "response_text": f"OS action '{action}' not supported yet",
            "intent": getattr(parsed_intent, "intent", "OS") if parsed_intent else "OS",
            "entities": entities,
        }

    # ─────────────────────────────

    def screenshot(self):

        try:
            import pyautogui

            timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
            name = f"Screenshot_{timestamp}.png"

            path = os.path.join(os.getcwd(), name)

            img = pyautogui.screenshot()
            img.save(path)

            logger.info("Screenshot saved: %s", path)

            return {
                "success": True,
                "response_text": f"Screenshot saved as {name}",
                "path": path
            }

        except Exception as e:

            logger.error("Screenshot failed: %s", e)

            return {
                "success": False,
                "response_text": "Failed to take screenshot"
            }

    # ─────────────────────────────

    def mute(self, mute: bool = True):

        try:
            import pyautogui
            # Toggle mute key (Windows media key). For unmute, same key is used.
            pyautogui.press("volumemute")

            logger.info("System mute=%s", mute)

            return {
                "success": True,
                "response_text": "Volume muted" if mute else "Volume unmuted",
            }

        except Exception as e:

            logger.error("Mute failed: %s", e)

            return {
                "success": False,
                "response_text": "Failed to mute volume"
            }

    # ─────────────────────────────

    def volume_up(self):

        try:
            import pyautogui
            pyautogui.press("volumeup")

            logger.info("Volume increased")

            return {
                "success": True,
                "response_text": "Volume increased"
            }

        except Exception as e:

            logger.error("Volume up failed: %s", e)

            return {
                "success": False,
                "response_text": "Failed to increase volume"
            }

    # ─────────────────────────────

    def volume_down(self):

        try:
            import pyautogui
            pyautogui.press("volumedown")

            logger.info("Volume decreased")

            return {
                "success": True,
                "response_text": "Volume decreased"
            }

        except Exception as e:

            logger.error("Volume down failed: %s", e)

            return {
                "success": False,
                "response_text": "Failed to decrease volume"
            }

    # ─────────────────────────────

    def volume_set(self, value):
        try:
            import pyautogui
            level = max(0, min(int(value), 100))
            # Approximate: Windows volume steps vary; assume ~2% per keypress.
            for _ in range(60):
                pyautogui.press("volumedown")
            for _ in range(int(level / 2)):
                pyautogui.press("volumeup")
            return {"success": True, "response_text": f"Volume set to {level}%."}
        except Exception as e:
            logger.error("Volume set failed: %s", e)
            return {"success": False, "response_text": "Failed to set volume."}

    def minimize(self):

        try:
            import pygetwindow as gw

            win = gw.getActiveWindow()

            if win:
                win.minimize()

                logger.info("Window minimized")

                return {
                    "success": True,
                    "response_text": "Window minimized"
                }

            return {
                "success": False,
                "response_text": "No active window found"
            }

        except Exception as e:

            logger.error("Minimize failed: %s", e)

            return {
                "success": False,
                "response_text": "Failed to minimize window"
            }

    # ─────────────────────────────

    def minimize_all(self):
        try:
            import pyautogui
            pyautogui.hotkey("win", "d")
            return {"success": True, "response_text": "Minimized all windows."}
        except Exception as e:
            logger.error("Minimize all failed: %s", e)
            return {"success": False, "response_text": "Failed to minimize all windows."}

    def maximize(self):
        try:
            import pygetwindow as gw
            win = gw.getActiveWindow()
            if win:
                try:
                    win.maximize()
                    return {"success": True, "response_text": "Window maximized."}
                except Exception:
                    pass
            import pyautogui
            pyautogui.hotkey("win", "up")
            return {"success": True, "response_text": "Window maximized."}
        except Exception as e:
            logger.error("Maximize failed: %s", e)
            return {"success": False, "response_text": "Failed to maximize window."}

    def restore(self):
        try:
            import pygetwindow as gw
            win = gw.getActiveWindow()
            if win:
                try:
                    win.restore()
                    return {"success": True, "response_text": "Window restored."}
                except Exception:
                    pass
            import pyautogui
            pyautogui.hotkey("win", "down")
            return {"success": True, "response_text": "Window restored."}
        except Exception as e:
            logger.error("Restore failed: %s", e)
            return {"success": False, "response_text": "Failed to restore window."}

    def close_window(self):
        try:
            import pyautogui
            pyautogui.hotkey("alt", "f4")
            return {"success": True, "response_text": "Closed active window."}
        except Exception as e:
            logger.error("Close window failed: %s", e)
            return {"success": False, "response_text": "Failed to close active window."}

    def switch_window(self, previous: bool = False):
        try:
            import pyautogui
            if previous:
                pyautogui.hotkey("alt", "shift", "tab")
                return {"success": True, "response_text": "Switched to previous window."}
            pyautogui.hotkey("alt", "tab")
            return {"success": True, "response_text": "Switched window."}
        except Exception as e:
            logger.error("Switch window failed: %s", e)
            return {"success": False, "response_text": "Failed to switch window."}

    def task_view(self):
        try:
            import pyautogui
            pyautogui.hotkey("win", "tab")
            return {"success": True, "response_text": "Opened task view."}
        except Exception as e:
            logger.error("Task view failed: %s", e)
            return {"success": False, "response_text": "Failed to open task view."}

    def show_desktop(self):
        try:
            import pyautogui
            pyautogui.hotkey("win", "d")
            return {"success": True, "response_text": "Showing desktop."}
        except Exception as e:
            logger.error("Show desktop failed: %s", e)
            return {"success": False, "response_text": "Failed to show desktop."}

    def new_virtual_desktop(self):
        try:
            import pyautogui
            pyautogui.hotkey("win", "ctrl", "d")
            return {"success": True, "response_text": "Opened new desktop."}
        except Exception as e:
            logger.error("New desktop failed: %s", e)
            return {"success": False, "response_text": "Failed to open new desktop."}

    def switch_virtual_desktop(self, next_desktop: bool = True):
        try:
            import pyautogui
            if next_desktop:
                pyautogui.hotkey("win", "ctrl", "right")
                return {"success": True, "response_text": "Switched to next desktop."}
            pyautogui.hotkey("win", "ctrl", "left")
            return {"success": True, "response_text": "Switched to previous desktop."}
        except Exception as e:
            logger.error("Switch desktop failed: %s", e)
            return {"success": False, "response_text": "Failed to switch desktop."}

    def close_virtual_desktop(self):
        try:
            import pyautogui
            pyautogui.hotkey("win", "ctrl", "f4")
            return {"success": True, "response_text": "Closed current desktop."}
        except Exception as e:
            logger.error("Close desktop failed: %s", e)
            return {"success": False, "response_text": "Failed to close current desktop."}

    def clipboard_shortcut(self, operation: str):
        try:
            import pyautogui
            key_map = {
                "copy": ("ctrl", "c"),
                "paste": ("ctrl", "v"),
                "cut": ("ctrl", "x"),
                "select_all": ("ctrl", "a"),
            }
            combo = key_map.get(operation)
            if not combo:
                return {"success": False, "response_text": "Clipboard action not supported."}
            pyautogui.hotkey(*combo)
            labels = {
                "copy": "Copied selection.",
                "paste": "Pasted from clipboard.",
                "cut": "Cut selection.",
                "select_all": "Selected all.",
            }
            return {"success": True, "response_text": labels.get(operation, "Done.")}
        except Exception as e:
            logger.error("Clipboard action failed: %s", e)
            return {"success": False, "response_text": "Failed clipboard action."}

    def launch_app(self, entities):
        app = (entities.get("app") or "").strip().lower()
        if not app:
            return {"success": False, "response_text": "No app specified"}
        try:
            app_map = {
                "calculator": "calc",
                "calc": "calc",
                "camera": "microsoft.windows.camera:",
                "settings": "ms-settings:",
                "chrome": "chrome",
                "edge": "msedge",
                "notepad": "notepad",
                "terminal": "wt",
                "cmd": "cmd",
                "powershell": "powershell",
                "explorer": "explorer",
                "task manager": "taskmgr",
                "vscode": "code",
                "vs code": "code",
            }
            target = app_map.get(app, app)
            subprocess.Popen(f'start "" "{target}"', shell=True)
            return {"success": True, "response_text": f"Opening {app}"}
        except Exception as e:
            logger.error("Launch failed: %s", e)
            return {"success": False, "response_text": "Failed to launch app"}

    def switch_to_app(self, entities):
        app = (entities.get("app") or "").strip().lower()
        if not app:
            return {"success": False, "response_text": "No app specified"}

        try:
            import pygetwindow as gw

            tokens = self._window_match_tokens(app)
            windows = [w for w in gw.getAllWindows() if getattr(w, "title", "")]

            for win in reversed(windows):
                title = (win.title or "").lower()
                if any(token in title for token in tokens):
                    try:
                        if getattr(win, "isMinimized", False):
                            win.restore()
                    except Exception:
                        pass
                    try:
                        win.activate()
                    except Exception:
                        pass
                    return {
                        "success": True,
                        "response_text": f"Switched to {app}",
                    }

            launch_result = self.launch_app({"app": app})
            if launch_result.get("success"):
                return {
                    "success": True,
                    "response_text": f"{app} was not open. Opening it now.",
                }

            return {"success": False, "response_text": f"Could not switch to {app}"}

        except Exception as e:
            logger.error("Switch app failed: %s", e)
            return {"success": False, "response_text": "Failed to switch app."}

    def _window_match_tokens(self, app: str):
        alias_map = {
            "vscode": ["visual studio code", "vscode", "code"],
            "vs code": ["visual studio code", "vscode", "code"],
            "terminal": ["terminal", "windows terminal", "cmd", "powershell"],
            "cmd": ["command prompt", "cmd"],
            "explorer": ["file explorer", "explorer"],
            "task manager": ["task manager"],
            "edge": ["microsoft edge", "edge"],
            "chrome": ["google chrome", "chrome"],
        }
        return alias_map.get(app, [app])

    def close_app(self, entities):
        app = (entities.get("app") or "").strip().lower()
        if not app:
            return {"success": False, "response_text": "No app specified"}
        try:
            # Best-effort: attempt taskkill by image name if provided like "chrome.exe"
            image_map = {
                "chrome": "chrome.exe",
                "edge": "msedge.exe",
                "calculator": "calculatorapp.exe",
                "camera": "windowscamera.exe",
                "notepad": "notepad.exe",
                "explorer": "explorer.exe",
                "vscode": "code.exe",
                "vs code": "code.exe",
            }
            image = image_map.get(app, app if app.endswith(".exe") else f"{app}.exe")
            subprocess.run(["taskkill", "/IM", image, "/F"], capture_output=True, text=True, shell=False)
            return {"success": True, "response_text": f"Closing {app}"}
        except Exception as e:
            logger.error("Close failed: %s", e)
            return {"success": False, "response_text": "Failed to close app"}

    def close_all_apps(self):
        # Dangerous to truly "close everything" via taskkill; do a safe UI-based close loop.
        try:
            import pyautogui
            pyautogui.hotkey("win", "d")
            for _ in range(10):
                pyautogui.hotkey("alt", "f4")
                time.sleep(0.1)
            return {"success": True, "response_text": "Tried closing open apps."}
        except Exception as e:
            logger.error("Close all apps failed: %s", e)
            return {"success": False, "response_text": "Failed to close all apps."}

    def lock(self):
        try:
            subprocess.run(["rundll32.exe", "user32.dll,LockWorkStation"], check=False)
            return {"success": True, "response_text": "Locking computer."}
        except Exception as e:
            logger.error("Lock failed: %s", e)
            return {"success": False, "response_text": "Failed to lock computer."}

    def shutdown(self):
        try:
            subprocess.run(["shutdown", "/s", "/t", "0"], check=False)
            return {"success": True, "response_text": "Shutting down."}
        except Exception as e:
            logger.error("Shutdown failed: %s", e)
            return {"success": False, "response_text": "Failed to shutdown."}

    def restart(self):
        try:
            subprocess.run(["shutdown", "/r", "/t", "0"], check=False)
            return {"success": True, "response_text": "Restarting."}
        except Exception as e:
            logger.error("Restart failed: %s", e)
            return {"success": False, "response_text": "Failed to restart."}

    def sleep(self):
        try:
            subprocess.run(["rundll32.exe", "powrprof.dll,SetSuspendState", "0,1,0"], check=False)
            return {"success": True, "response_text": "Going to sleep."}
        except Exception as e:
            logger.error("Sleep failed: %s", e)
            return {"success": False, "response_text": "Failed to sleep."}

    def brightness(self, action: str, value=None):
        try:
            if action == "set" and value is not None:
                level = max(0, min(int(value), 100))
            else:
                # relative changes; Windows WMI expects absolute 0-100
                level = 70 if action == "increase" else 30
            ps = (
                "(Get-WmiObject -Namespace root/WMI -Class WmiMonitorBrightnessMethods)"
                f".WmiSetBrightness(1,{level})"
            )
            subprocess.run(["powershell", "-NoProfile", "-Command", ps], check=False)
            return {"success": True, "response_text": "Brightness updated."}
        except Exception as e:
            logger.error("Brightness failed: %s", e)
            return {"success": False, "response_text": "Failed to change brightness."}

    def music_play(self, entities):
        platform = (entities.get("platform") or "").strip().lower()
        name = (entities.get("name") or "").strip()
        if not platform:
            platform = "youtube"
        try:
            if platform == "spotify":
                query = name or "music"
                # App URI (if desktop app exists). If not, Windows may open web/store.
                uri = f"spotify:search:{query.replace(' ', '%20')}"
                subprocess.Popen(f'start "" "{uri}"', shell=True)
                return {"success": True, "response_text": f"Playing {query} on Spotify."}

            # YouTube: open first actual watch URL (more reliable than just results page)
            if not name:
                subprocess.Popen('start "" "https://music.youtube.com/"', shell=True)
                return {"success": True, "response_text": "Playing music on YouTube."}

            video_url = self._youtube_first_video_url(name)
            if not video_url:
                url = f"https://www.youtube.com/results?search_query={urllib.parse.quote(name)}"
                subprocess.Popen(f'start "" "{url}"', shell=True)
                return {"success": True, "response_text": f"Searching {name} on YouTube."}

            subprocess.Popen(f'start "" "{video_url}"', shell=True)
            return {"success": True, "response_text": f"Playing {name} on YouTube."}
        except Exception as e:
            logger.error("Music play failed: %s", e)
            return {"success": False, "response_text": "Failed to play music."}

    def _youtube_first_video_url(self, name: str) -> str:
        try:
            import requests
            from bs4 import BeautifulSoup

            query = urllib.parse.quote(name)
            search_url = f"https://www.youtube.com/results?search_query={query}"
            response = requests.get(search_url, timeout=10)
            soup = BeautifulSoup(response.text, "html.parser")

            for link in soup.find_all("a"):
                href = link.get("href")
                if href and href.startswith("/watch"):
                    return f"https://www.youtube.com{href}"
            return ""
        except Exception:
            return ""