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
from .general_commands import GeneralCommands


class OSActions:

    def __init__(self):
        self.timer = TimerActions()
        self.general = GeneralCommands()

    def handle(self, entities, parsed_intent=None):
        action = entities.get("action")
        target = entities.get("target")
        value = entities.get("value")

        if action in ("timer_set", "timer_cancel", "stopwatch_start", "stopwatch_stop", "stopwatch_reset"):
            return self.timer.handle(entities, parsed_intent=parsed_intent)

        if action == "volume_status":
            return self.general.volume_status()
        if action == "describe_screen":
            return self.general.describe_screen()
        if action == "battery_status":
            return self.general.battery_status()
        if action == "wifi_status":
            return self.general.wifi_status()
        if action == "network_status":
            return self.general.network_status()
        if action == "active_window_status":
            return self.general.active_window_status()
        if action == "date_time_status":
            return self.general.date_time_status()
        if action == "environment_summary":
            return self.general.environment_summary()

        if action == "music_play":
            return self.music_play(entities)
        if action == "open_explorer":
            return self.open_explorer(entities)
        if action == "open_special_folder":
            return self.open_special_folder(entities)
        if action == "open_path":
            return self.open_path(entities)

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
        if action == "camera_capture":
            return self.camera_capture()

        return {
            "success": False,
            "response_text": f"OS action '{action}' not supported yet",
            "intent": getattr(parsed_intent, "intent", "OS") if parsed_intent else "OS",
            "entities": entities,
        }

    # ─────────────────────────────────────────────────────────────────────────
    # SCREENSHOT
    # ─────────────────────────────────────────────────────────────────────────

    def screenshot(self):
        try:
            import pyautogui
            timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
            name = f"Screenshot_{timestamp}.png"
            path = os.path.join(os.getcwd(), name)
            img = pyautogui.screenshot()
            img.save(path)
            logger.info("Screenshot saved: %s", path)
            return {"success": True, "response_text": f"Screenshot saved as {name}", "path": path}
        except Exception as e:
            logger.error("Screenshot failed: %s", e)
            return {"success": False, "response_text": "Failed to take screenshot"}

    # ─────────────────────────────────────────────────────────────────────────
    # VOLUME
    # ─────────────────────────────────────────────────────────────────────────

    def mute(self, mute: bool = True):
        try:
            import pyautogui
            pyautogui.press("volumemute")
            logger.info("System mute=%s", mute)
            return {"success": True, "response_text": "Volume muted" if mute else "Volume unmuted"}
        except Exception as e:
            logger.error("Mute failed: %s", e)
            return {"success": False, "response_text": "Failed to mute volume"}

    def volume_up(self):
        try:
            import pyautogui
            pyautogui.press("volumeup")
            return {"success": True, "response_text": "Volume increased"}
        except Exception as e:
            logger.error("Volume up failed: %s", e)
            return {"success": False, "response_text": "Failed to increase volume"}

    def volume_down(self):
        try:
            import pyautogui
            pyautogui.press("volumedown")
            return {"success": True, "response_text": "Volume decreased"}
        except Exception as e:
            logger.error("Volume down failed: %s", e)
            return {"success": False, "response_text": "Failed to decrease volume"}

    def volume_set(self, value):
        try:
            import pyautogui
            level = max(0, min(int(value), 100))
            for _ in range(60):
                pyautogui.press("volumedown")
            for _ in range(int(level / 2)):
                pyautogui.press("volumeup")
            return {"success": True, "response_text": f"Volume set to {level}%."}
        except Exception as e:
            logger.error("Volume set failed: %s", e)
            return {"success": False, "response_text": "Failed to set volume."}

    # ─────────────────────────────────────────────────────────────────────────
    # WINDOW MANAGEMENT
    # ─────────────────────────────────────────────────────────────────────────

    def minimize(self):
        try:
            import pygetwindow as gw
            win = gw.getActiveWindow()
            if win:
                win.minimize()
                return {"success": True, "response_text": "Window minimized"}
            return {"success": False, "response_text": "No active window found"}
        except Exception as e:
            logger.error("Minimize failed: %s", e)
            return {"success": False, "response_text": "Failed to minimize window"}

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

    # ─────────────────────────────────────────────────────────────────────────
    # CLIPBOARD
    # ─────────────────────────────────────────────────────────────────────────

    def clipboard_shortcut(self, operation: str):
        try:
            import pyautogui
            key_map = {
                "copy":       ("ctrl", "c"),
                "paste":      ("ctrl", "v"),
                "cut":        ("ctrl", "x"),
                "select_all": ("ctrl", "a"),
            }
            combo = key_map.get(operation)
            if not combo:
                return {"success": False, "response_text": "Clipboard action not supported."}
            pyautogui.hotkey(*combo)
            labels = {
                "copy":       "Copied selection.",
                "paste":      "Pasted from clipboard.",
                "cut":        "Cut selection.",
                "select_all": "Selected all.",
            }
            return {"success": True, "response_text": labels.get(operation, "Done.")}
        except Exception as e:
            logger.error("Clipboard action failed: %s", e)
            return {"success": False, "response_text": "Failed clipboard action."}

    # ─────────────────────────────────────────────────────────────────────────
    # APP LAUNCH / SWITCH / CLOSE
    # ─────────────────────────────────────────────────────────────────────────

    # Canonical executable / URI map for launch_app
    _LAUNCH_MAP = {
        # Browsers
        "chrome":           "chrome",
        "google chrome":    "chrome",
        "edge":             "msedge",
        "microsoft edge":   "msedge",
        "firefox":          "firefox",
        "opera":            "opera",
        "brave":            "brave",

        # Microsoft Office
        "word":             "winword",
        "microsoft word":   "winword",
        "excel":            "excel",
        "microsoft excel":  "excel",
        "powerpoint":       "powerpnt",
        "ppt":              "powerpnt",
        "microsoft powerpoint": "powerpnt",
        "outlook":          "outlook",
        "microsoft outlook":"outlook",
        "onenote":          "onenote",
        "microsoft onenote":"onenote",
        "teams":            "ms-teams:",
        "microsoft teams":  "ms-teams:",
        "access":           "msaccess",
        "publisher":        "mspub",

        # Dev tools
        "vscode":           "code",
        "vs code":          "code",
        "visual studio code": "code",
        "visual studio":    "devenv",
        "terminal":         "wt",
        "windows terminal": "wt",
        "cmd":              "cmd",
        "command prompt":   "cmd",
        "powershell":       "powershell",
        "pycharm":          "pycharm64",
        "intellij":         "idea64",
        "intellij idea":    "idea64",
        "android studio":   "studio64",
        "postman":          "postman",
        "git bash":         r"C:\Program Files\Git\git-bash.exe",

        # Communication
        "telegram":         os.path.expandvars(r"%LOCALAPPDATA%\Telegram Desktop\Telegram.exe"),
        "telegram desktop": os.path.expandvars(r"%LOCALAPPDATA%\Telegram Desktop\Telegram.exe"),
        "whatsapp":         os.path.expandvars(r"%LOCALAPPDATA%\WhatsApp\WhatsApp.exe"),
        "discord":          os.path.expandvars(r"%LOCALAPPDATA%\Discord\Update.exe --processStart Discord.exe"),
        "slack":            os.path.expandvars(r"%LOCALAPPDATA%\slack\slack.exe"),
        "zoom":             os.path.expandvars(r"%APPDATA%\Zoom\bin\Zoom.exe"),
        "skype":            "skype:",
        "signal":           os.path.expandvars(r"%LOCALAPPDATA%\Programs\signal-desktop\Signal.exe"),

        # Media
        "spotify":          os.path.expandvars(r"%APPDATA%\Spotify\Spotify.exe"),
        "vlc":              r"C:\Program Files\VideoLAN\VLC\vlc.exe",
        "media player":     "wmplayer",
        "windows media player": "wmplayer",

        # System / Utilities
        "explorer":         "explorer",
        "file explorer":    "explorer",
        "task manager":     "taskmgr",
        "settings":         "ms-settings:",
        "windows settings": "ms-settings:",
        "control panel":    "control",
        "notepad":          "notepad",
        "notepad++":        r"C:\Program Files\Notepad++\notepad++.exe",
        "paint":            "mspaint",
        "mspaint":          "mspaint",
        "calculator":       "calc",
        "calc":             "calc",
        "camera":           "microsoft.windows.camera:",
        "store":            "ms-windows-store:",
        "microsoft store":  "ms-windows-store:",
        "snipping tool":    "snippingtool",
        "snip & sketch":    "ms-screensketch:",

        # Creative / Design
        "figma":            os.path.expandvars(r"%LOCALAPPDATA%\Figma\Figma.exe"),
        "blender":          r"C:\Program Files\Blender Foundation\Blender\blender.exe",
        "photoshop":        r"C:\Program Files\Adobe\Adobe Photoshop 2024\Photoshop.exe",
        "adobe photoshop":  r"C:\Program Files\Adobe\Adobe Photoshop 2024\Photoshop.exe",
        "illustrator":      r"C:\Program Files\Adobe\Adobe Illustrator 2024\Support Files\Contents\Windows\Illustrator.exe",
        "adobe illustrator":r"C:\Program Files\Adobe\Adobe Illustrator 2024\Support Files\Contents\Windows\Illustrator.exe",
        "premiere":         r"C:\Program Files\Adobe\Adobe Premiere Pro 2024\Adobe Premiere Pro.exe",
        "premiere pro":     r"C:\Program Files\Adobe\Adobe Premiere Pro 2024\Adobe Premiere Pro.exe",
        "after effects":    r"C:\Program Files\Adobe\Adobe After Effects 2024\Support Files\AfterFX.exe",

        # Productivity
        "notion":           os.path.expandvars(r"%LOCALAPPDATA%\Programs\Notion\Notion.exe"),
        "obsidian":         os.path.expandvars(r"%LOCALAPPDATA%\Obsidian\Obsidian.exe"),
    }

    # Window title tokens map for switch_to_app
    _WINDOW_TOKENS = {
        # Browsers
        "chrome":               ["google chrome", "chrome"],
        "google chrome":        ["google chrome", "chrome"],
        "edge":                 ["microsoft edge", "edge"],
        "microsoft edge":       ["microsoft edge", "edge"],
        "firefox":              ["firefox", "mozilla firefox"],
        "opera":                ["opera"],
        "brave":                ["brave"],

        # Microsoft Office
        "word":                 ["word", "microsoft word", "winword"],
        "microsoft word":       ["word", "microsoft word"],
        "excel":                ["excel", "microsoft excel"],
        "microsoft excel":      ["excel", "microsoft excel"],
        "powerpoint":           ["powerpoint", "microsoft powerpoint", "ppt"],
        "ppt":                  ["powerpoint", "microsoft powerpoint", "ppt"],
        "microsoft powerpoint": ["powerpoint", "microsoft powerpoint"],
        "outlook":              ["outlook", "microsoft outlook"],
        "onenote":              ["onenote", "microsoft onenote"],
        "teams":                ["microsoft teams", "teams"],
        "access":               ["microsoft access", "access"],
        "publisher":            ["microsoft publisher", "publisher"],

        # Dev tools
        "vscode":               ["visual studio code", "vscode", "code"],
        "vs code":              ["visual studio code", "vscode", "code"],
        "visual studio code":   ["visual studio code", "vscode", "code"],
        "visual studio":        ["visual studio", "devenv"],
        "terminal":             ["windows terminal", "terminal"],
        "cmd":                  ["command prompt", "cmd"],
        "powershell":           ["powershell", "windows powershell"],
        "pycharm":              ["pycharm"],
        "intellij":             ["intellij idea", "intellij"],
        "android studio":       ["android studio"],
        "postman":              ["postman"],

        # Communication
        "telegram":             ["telegram"],
        "whatsapp":             ["whatsapp"],
        "discord":              ["discord"],
        "slack":                ["slack"],
        "zoom":                 ["zoom"],
        "skype":                ["skype"],
        "signal":               ["signal"],

        # Media
        "spotify":              ["spotify"],
        "vlc":                  ["vlc media player", "vlc"],
        "media player":         ["windows media player", "media player"],

        # System
        "explorer":             ["file explorer", "explorer"],
        "file explorer":        ["file explorer", "explorer"],
        "task manager":         ["task manager"],
        "settings":             ["settings"],
        "notepad":              ["notepad"],
        "notepad++":            ["notepad++"],
        "paint":                ["paint", "mspaint"],
        "calculator":           ["calculator"],

        # Creative
        "figma":                ["figma"],
        "blender":              ["blender"],
        "photoshop":            ["adobe photoshop", "photoshop"],
        "illustrator":          ["adobe illustrator", "illustrator"],
        "premiere":             ["adobe premiere", "premiere pro"],
        "after effects":        ["adobe after effects", "after effects"],

        # Productivity
        "notion":               ["notion"],
        "obsidian":             ["obsidian"],
    }

    # Process image names for close_app
    _CLOSE_MAP = {
        "chrome":           "chrome.exe",
        "google chrome":    "chrome.exe",
        "edge":             "msedge.exe",
        "microsoft edge":   "msedge.exe",
        "firefox":          "firefox.exe",
        "opera":            "opera.exe",
        "brave":            "brave.exe",
        "word":             "winword.exe",
        "excel":            "excel.exe",
        "powerpoint":       "powerpnt.exe",
        "ppt":              "powerpnt.exe",
        "outlook":          "outlook.exe",
        "onenote":          "onenote.exe",
        "teams":            "teams.exe",
        "access":           "msaccess.exe",
        "vscode":           "code.exe",
        "vs code":          "code.exe",
        "visual studio code": "code.exe",
        "terminal":         "wt.exe",
        "cmd":              "cmd.exe",
        "powershell":       "powershell.exe",
        "pycharm":          "pycharm64.exe",
        "intellij":         "idea64.exe",
        "android studio":   "studio64.exe",
        "postman":          "postman.exe",
        "telegram":         "telegram.exe",
        "whatsapp":         "whatsapp.exe",
        "discord":          "discord.exe",
        "slack":            "slack.exe",
        "zoom":             "zoom.exe",
        "skype":            "skype.exe",
        "signal":           "signal.exe",
        "spotify":          "spotify.exe",
        "vlc":              "vlc.exe",
        "notepad":          "notepad.exe",
        "notepad++":        "notepad++.exe",
        "paint":            "mspaint.exe",
        "calculator":       "calculatorapp.exe",
        "camera":           "windowscamera.exe",
        "explorer":         "explorer.exe",
        "task manager":     "taskmgr.exe",
        "photoshop":        "photoshop.exe",
        "illustrator":      "illustrator.exe",
        "blender":          "blender.exe",
        "figma":            "figma.exe",
        "notion":           "notion.exe",
        "obsidian":         "obsidian.exe",
    }

    # def launch_app(self, entities):
    #     app = (entities.get("app") or "").strip().lower()
    #     if not app:
    #         return {"success": False, "response_text": "No app specified"}
    #     try:
    #         target = self._LAUNCH_MAP.get(app, app)
    #         # If the target is an absolute path, check it exists before launching
    #         if os.path.isabs(target) and not os.path.exists(target):
    #             logger.warning("App path not found: %s", target)
    #             return {
    #                 "success": False,
    #                 "response_text": f"Could not find {app} on this computer. It may not be installed.",
    #             }
    #         subprocess.Popen(f'start "" "{target}"', shell=True)
    #         logger.info("Launched: %s -> %s", app, target)
    #         return {"success": True, "response_text": f"Opening {app}"}
    #     except Exception as e:
    #         logger.error("Launch failed: %s", e)
    #         return {"success": False, "response_text": f"Failed to launch {app}"}

    def _window_match_tokens(self, app: str):
        return self._WINDOW_TOKENS.get(app, [app])

    def switch_to_app(self, entities):
        app = (entities.get("app") or "").strip().lower()
        if not app:
            return {"success": False, "response_text": "No app specified"}

        try:
            import pygetwindow as gw
            import win32gui
            import win32con
            import win32process
            import ctypes

            tokens = self._window_match_tokens(app)
            windows = [w for w in gw.getAllWindows() if getattr(w, "title", "")]

            for win in reversed(windows):
                title = (win.title or "").lower()
                if any(token in title for token in tokens):
                    hwnd = win._hWnd

                    # Restore if minimized
                    if win32gui.IsIconic(hwnd):
                        win32gui.ShowWindow(hwnd, win32con.SW_RESTORE)

                    # Force foreground via AttachThreadInput trick —
                    # without this, Windows only flashes the taskbar button
                    foreground_hwnd  = win32gui.GetForegroundWindow()
                    foreground_tid   = win32process.GetWindowThreadProcessId(foreground_hwnd)[0]
                    target_tid       = win32process.GetWindowThreadProcessId(hwnd)[0]
                    current_tid      = ctypes.windll.kernel32.GetCurrentThreadId()

                    attached_fg  = False
                    attached_tgt = False

                    if foreground_tid and foreground_tid != current_tid:
                        ctypes.windll.user32.AttachThreadInput(current_tid, foreground_tid, True)
                        attached_fg = True
                    if target_tid and target_tid != current_tid:
                        ctypes.windll.user32.AttachThreadInput(current_tid, target_tid, True)
                        attached_tgt = True

                    win32gui.ShowWindow(hwnd, win32con.SW_SHOW)
                    win32gui.SetForegroundWindow(hwnd)
                    win32gui.BringWindowToTop(hwnd)
                    win32gui.SetFocus(hwnd)

                    if attached_fg:
                        ctypes.windll.user32.AttachThreadInput(current_tid, foreground_tid, False)
                    if attached_tgt:
                        ctypes.windll.user32.AttachThreadInput(current_tid, target_tid, False)

                    logger.info("Switched to window: %s", win.title)
                    return {"success": True, "response_text": f"Switched to {app}"}

            # Window not found — try launching
            launch_result = self.launch_app({"app": app})
            if launch_result.get("success"):
                return {"success": True, "response_text": f"{app} was not open. Opening it now."}

            return {"success": False, "response_text": f"Could not find or open {app}"}

        except Exception as e:
            logger.error("Switch app failed: %s", e)
            return {"success": False, "response_text": f"Failed to switch to {app}"}

    def close_app(self, entities):
        app = (entities.get("app") or "").strip().lower()
        if not app:
            return {"success": False, "response_text": "No app specified"}
        try:
            image = self._CLOSE_MAP.get(app, app if app.endswith(".exe") else f"{app}.exe")
            result = subprocess.run(
                ["taskkill", "/IM", image, "/F"],
                capture_output=True, text=True, shell=False
            )
            if result.returncode == 0:
                logger.info("Closed app: %s (%s)", app, image)
                return {"success": True, "response_text": f"Closed {app}."}
            else:
                # taskkill failed — app may not be running
                logger.warning("taskkill returned %d for %s: %s", result.returncode, image, result.stderr.strip())
                return {"success": False, "response_text": f"{app} doesn't appear to be running."}
        except Exception as e:
            logger.error("Close failed: %s", e)
            return {"success": False, "response_text": f"Failed to close {app}"}

    def close_all_apps(self):
        try:
            import pyautogui
            pyautogui.hotkey("win", "d")
            for _ in range(10):
                pyautogui.hotkey("alt", "f4")
                time.sleep(0.15)
            return {"success": True, "response_text": "Tried closing open apps."}
        except Exception as e:
            logger.error("Close all apps failed: %s", e)
            return {"success": False, "response_text": "Failed to close all apps."}

    # ─────────────────────────────────────────────────────────────────────────
    # SYSTEM POWER
    # ─────────────────────────────────────────────────────────────────────────

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

    # ─────────────────────────────────────────────────────────────────────────
    # CAMERA & APP LAUNCH (timeout-safe)
    # ─────────────────────────────────────────────────────────────────────────

    def camera_capture(self):
        """
        Open the Windows Camera app (if needed) and take a photo.
        Uses the Space-bar shutter shortcut built into the Windows Camera app.
        Separate from "open camera" — this both opens AND clicks the shutter.
        """
        try:
            import pyautogui
            import pygetwindow as gw
            import win32gui
            import win32con
            import win32process
            import ctypes

            CAMERA_URI = "microsoft.windows.camera:"
            WINDOW_TOKENS = ["camera", "windows camera"]
            OPEN_TIMEOUT = 8    # seconds to wait for the window to appear
            FOCUS_DELAY = 0.8   # seconds after focusing before pressing shutter

            def _find_camera_window():
                for w in gw.getAllWindows():
                    title = (w.title or "").lower()
                    if any(tok in title for tok in WINDOW_TOKENS):
                        return w
                return None

            win = _find_camera_window()

            if win is None:
                subprocess.Popen(f'start "" "{CAMERA_URI}"', shell=True)
                logger.info("camera_capture: launched camera app, waiting for window…")
                deadline = time.time() + OPEN_TIMEOUT
                while time.time() < deadline:
                    win = _find_camera_window()
                    if win:
                        break
                    time.sleep(0.4)

            if win is None:
                logger.warning("camera_capture: camera window did not appear within %ds", OPEN_TIMEOUT)
                return {
                    "success": False,
                    "response_text": "Camera didn't open in time. Please try again.",
                }

            try:
                hwnd = win._hWnd
                if win32gui.IsIconic(hwnd):
                    win32gui.ShowWindow(hwnd, win32con.SW_RESTORE)

                fg_hwnd = win32gui.GetForegroundWindow()
                fg_tid = win32process.GetWindowThreadProcessId(fg_hwnd)[0]
                tgt_tid = win32process.GetWindowThreadProcessId(hwnd)[0]
                cur_tid = ctypes.windll.kernel32.GetCurrentThreadId()

                attached = []
                for tid in (fg_tid, tgt_tid):
                    if tid and tid != cur_tid:
                        ctypes.windll.user32.AttachThreadInput(cur_tid, tid, True)
                        attached.append(tid)

                win32gui.ShowWindow(hwnd, win32con.SW_SHOW)
                win32gui.SetForegroundWindow(hwnd)
                win32gui.BringWindowToTop(hwnd)

                for tid in attached:
                    ctypes.windll.user32.AttachThreadInput(cur_tid, tid, False)
            except Exception as focus_err:
                logger.warning("camera_capture: focus via win32 failed (%s), trying window.activate()", focus_err)
                try:
                    win.activate()
                except Exception:
                    pass

            time.sleep(FOCUS_DELAY)
            pyautogui.press("space")
            logger.info("camera_capture: shutter fired")
            return {"success": True, "response_text": "Photo taken!"}

        except Exception as e:
            logger.error("camera_capture failed: %s", e)
            return {"success": False, "response_text": "Failed to take photo."}

    def launch_app(self, entities):
        """
        Launch an application by name using Windows shell.
        Uses a background thread + join-timeout so a hung shell call
        never freezes the assistant — control returns after `timeout` seconds.
        """
        app = (entities.get("app") or "").strip().lower()
        timeout = int(entities.get("timeout", 10))   # default 10 s, set by parser

        if not app:
            return {"success": False, "response_text": "No app specified."}

        target = self._LAUNCH_MAP.get(app, app)

        # Reject missing absolute paths immediately — no need to even try
        if os.path.isabs(target) and not os.path.exists(target):
            logger.warning("launch_app: path not found: %s", target)
            return {
                "success": False,
                "response_text": f"Could not find {app}. It may not be installed.",
            }

        result = {"success": False, "response_text": f"Launching {app} timed out."}
        error_holder = [None]

        def _do_launch():
            try:
                subprocess.Popen(f'start "" "{target}"', shell=True)
                result["success"] = True
                result["response_text"] = f"Opening {app}"
            except Exception as exc:
                error_holder[0] = exc

        import threading

        thread = threading.Thread(target=_do_launch, daemon=True)
        thread.start()
        thread.join(timeout=timeout)

        if thread.is_alive():
            logger.error("launch_app: timed out after %ds launching '%s'", timeout, app)
            return {"success": False, "response_text": f"Opening {app} is taking too long. Skipping."}

        if error_holder[0]:
            logger.error("launch_app: exception launching '%s': %s", app, error_holder[0])
            return {"success": False, "response_text": f"Failed to launch {app}."}

        logger.info("launch_app: launched '%s' → '%s'", app, target)
        return result

    # ─────────────────────────────────────────────────────────────────────────
    # BRIGHTNESS
    # ─────────────────────────────────────────────────────────────────────────

    def brightness(self, action: str, value=None):
        try:
            if action == "set" and value is not None:
                level = max(0, min(int(value), 100))
            elif action == "increase":
                # Read current brightness first, increment by 20
                level = self._get_brightness()
                level = min(level + 20, 100) if level is not None else 70
            elif action == "decrease":
                level = self._get_brightness()
                level = max(level - 20, 0) if level is not None else 30
            else:
                level = 50

            ps = (
                "(Get-WmiObject -Namespace root/WMI -Class WmiMonitorBrightnessMethods)"
                f".WmiSetBrightness(1,{level})"
            )
            result = subprocess.run(
                ["powershell", "-NoProfile", "-Command", ps],
                capture_output=True, text=True, check=False
            )
            if result.returncode != 0:
                logger.warning("Brightness PS error: %s", result.stderr.strip())
                return {"success": False, "response_text": "Could not change brightness. This may not be supported on your display."}
            return {"success": True, "response_text": f"Brightness set to {level}%."}
        except Exception as e:
            logger.error("Brightness failed: %s", e)
            return {"success": False, "response_text": "Failed to change brightness."}

    def _get_brightness(self):
        """Returns current brightness level (0-100) or None on failure."""
        try:
            ps = "(Get-WmiObject -Namespace root/WMI -Class WmiMonitorBrightness).CurrentBrightness"
            result = subprocess.run(
                ["powershell", "-NoProfile", "-Command", ps],
                capture_output=True, text=True, check=False
            )
            return int(result.stdout.strip())
        except Exception:
            return None

    # ─────────────────────────────────────────────────────────────────────────
    # FILE / FOLDER NAVIGATION (hierarchical)
    # ─────────────────────────────────────────────────────────────────────────

    def open_path(self, entities):
        """
        Open any file or folder path.
        - If it's a folder  → open in Explorer
        - If it's a file    → open with its default associated app (os.startfile)
        - Supports env-var expansion and ~ home dir
        """
        raw = (entities.get("path") or entities.get("target") or "").strip()
        if not raw:
            return {"success": False, "response_text": "No path specified."}

        path = os.path.expandvars(os.path.expanduser(raw))

        if not os.path.exists(path):
            # Try to locate the item inside common roots as a fallback
            found = self._search_path_hierarchy(raw)
            if found:
                path = found
            else:
                return {
                    "success": False,
                    "response_text": f"Could not find '{raw}'. Please check the path.",
                }

        try:
            if os.path.isdir(path):
                subprocess.Popen(f'explorer "{path}"', shell=True)
                logger.info("Opened folder: %s", path)
                return {"success": True, "response_text": f"Opening folder: {os.path.basename(path) or path}"}
            else:
                os.startfile(path)
                logger.info("Opened file: %s", path)
                return {"success": True, "response_text": f"Opening {os.path.basename(path)}"}
        except Exception as e:
            logger.error("open_path failed for %s: %s", path, e)
            return {"success": False, "response_text": f"Failed to open '{os.path.basename(path)}'."}

    def _search_path_hierarchy(self, name: str) -> str:
        """
        Walk common root directories to find a file or folder by name.
        Returns the full path if found, else empty string.
        """
        userprofile = os.environ.get("USERPROFILE") or os.path.expanduser("~")
        search_roots = [
            userprofile,
            os.path.join(userprofile, "Desktop"),
            os.path.join(userprofile, "Documents"),
            os.path.join(userprofile, "Downloads"),
            os.path.join(userprofile, "Pictures"),
            os.path.join(userprofile, "Videos"),
            os.path.join(userprofile, "Music"),
        ]
        name_lower = name.lower().replace("\\", os.sep).replace("/", os.sep)
        for root in search_roots:
            if not os.path.isdir(root):
                continue
            for dirpath, dirnames, filenames in os.walk(root):
                # Prune hidden and system dirs to keep search fast
                dirnames[:] = [d for d in dirnames if not d.startswith(".") and d not in (
                    "AppData", "node_modules", "__pycache__", "$Recycle.Bin"
                )]
                for item in dirnames + filenames:
                    if item.lower() == name_lower or os.path.join(dirpath, item).lower().endswith(name_lower):
                        return os.path.join(dirpath, item)
        return ""

    def open_explorer(self, entities):
        """Open File Explorer at a specific drive or path, or at This PC."""
        drive = (entities.get("drive") or "").strip()
        path  = (entities.get("path")  or "").strip()
        target = drive or path

        try:
            if target:
                target = os.path.expandvars(os.path.expanduser(target))
                if not os.path.exists(target):
                    return {
                        "success": False,
                        "response_text": f"Path '{target}' does not exist.",
                    }
                subprocess.Popen(f'explorer "{target}"', shell=True)
                return {"success": True, "response_text": f"Opening {target} in File Explorer."}
            subprocess.Popen("explorer", shell=True)
            return {"success": True, "response_text": "Opening File Explorer."}
        except Exception as e:
            logger.error("open_explorer failed: %s", e)
            return {"success": False, "response_text": "Failed to open File Explorer."}

    def open_special_folder(self, entities):
        """
        Open common user folders (Downloads, Documents, Desktop, etc.)
        Supports fuzzy name matching so 'my docs', 'document', 'docs' all resolve.
        """
        name = (entities.get("folder_name") or "").strip().lower()
        userprofile = os.environ.get("USERPROFILE") or os.path.expanduser("~")

        special_map = {
            "downloads":    os.path.join(userprofile, "Downloads"),
            "download":     os.path.join(userprofile, "Downloads"),
            "documents":    os.path.join(userprofile, "Documents"),
            "document":     os.path.join(userprofile, "Documents"),
            "docs":         os.path.join(userprofile, "Documents"),
            "my documents": os.path.join(userprofile, "Documents"),
            "desktop":      os.path.join(userprofile, "Desktop"),
            "pictures":     os.path.join(userprofile, "Pictures"),
            "picture":      os.path.join(userprofile, "Pictures"),
            "photos":       os.path.join(userprofile, "Pictures"),
            "music":        os.path.join(userprofile, "Music"),
            "songs":        os.path.join(userprofile, "Music"),
            "videos":       os.path.join(userprofile, "Videos"),
            "video":        os.path.join(userprofile, "Videos"),
            "movies":       os.path.join(userprofile, "Videos"),
            "appdata":      os.path.join(userprofile, "AppData"),
            "temp":         os.path.expandvars(r"%TEMP%"),
            "startup":      os.path.expandvars(r"%APPDATA%\Microsoft\Windows\Start Menu\Programs\Startup"),
        }

        target = special_map.get(name)
        if not target:
            # Partial match fallback
            for key, path in special_map.items():
                if name in key or key in name:
                    target = path
                    break

        if not target:
            return {"success": False, "response_text": f"I don't know a special folder called '{name}'."}

        if not os.path.isdir(target):
            return {"success": False, "response_text": f"The {name} folder could not be found on this PC."}

        try:
            subprocess.Popen(f'explorer "{target}"', shell=True)
            logger.info("Opened special folder: %s -> %s", name, target)
            return {"success": True, "response_text": f"Opening your {name} folder."}
        except Exception as e:
            logger.error("open_special_folder failed: %s", e)
            return {"success": False, "response_text": f"Failed to open the {name} folder."}

    # ─────────────────────────────────────────────────────────────────────────
    # MUSIC
    # ─────────────────────────────────────────────────────────────────────────

    def music_play(self, entities):
        try:
            import pywhatkit
        except ImportError:
            return {"success": False, "response_text": "pywhatkit is not installed. Run: pip install pywhatkit"}

        platform = (entities.get("platform") or "").strip().lower()
        name     = (entities.get("name")     or "").strip()
        if not platform:
            platform = "youtube"

        try:
            if platform == "spotify":
                query = name or "music"
                uri = f"spotify:search:{urllib.parse.quote(query)}"
                subprocess.Popen(f'start "" "{uri}"', shell=True)
                return {"success": True, "response_text": f"Searching {query} on Spotify."}

            if not name:
                subprocess.Popen('start "" "https://music.youtube.com/"', shell=True)
                return {"success": True, "response_text": "Opening YouTube Music."}

            pywhatkit.playonyt(name)
            return {"success": True, "response_text": f"Playing {name} on YouTube."}
        except Exception as e:
            logger.error("Music play failed: %s", e)
            return {"success": False, "response_text": "Failed to play music."}

    def _youtube_first_video_url(self, name: str) -> str:
        try:
            import requests
            from bs4 import BeautifulSoup
            query      = urllib.parse.quote(name)
            search_url = f"https://www.youtube.com/results?search_query={query}"
            response   = requests.get(search_url, timeout=10)
            soup       = BeautifulSoup(response.text, "html.parser")
            for link in soup.find_all("a"):
                href = link.get("href")
                if href and href.startswith("/watch"):
                    return f"https://www.youtube.com{href}"
            return ""
        except Exception:
            return ""
