"""
Browser actions for the voice assistant.

These are intentionally implemented as:
- URL launches (reliable) for open/search
- hotkeys (pyautogui) for tab/navigation/scroll, best-effort on the active browser window
"""

import webbrowser
import logging
import subprocess
import time
import urllib.parse
from typing import Dict, Any

try:
    import pyautogui
except Exception:  # pragma: no cover - runtime dependency may be unavailable in tests
    pyautogui = None

logger = logging.getLogger(__name__)


class BrowserActions:
    """Browser actions suitable for a voice assistant."""

    def handle(self, entities: Dict[str, Any], parsed_intent: Any = None) -> Dict[str, Any]:

        action = entities.get("action", "")

        handlers = {
            "open": self._open_site,
            "search": self._search,
            "back": self._navigate_back,
            "forward": self._navigate_forward,
            "refresh": self._refresh,
            "new_tab": self._new_tab,
            "close_tab": self._close_tab,
            "switch_tab": self._switch_tab,
            "next_tab": self._next_tab,
            "prev_tab": self._prev_tab,
            "scroll": self._scroll,
            "download": self._download,
            "read_selection": self._read_selection,
        }

        handler = handlers.get(action)

        if handler:
            return handler(entities)

        return {
            "success": False,
            "response_text": f"Browser action '{action}' not supported yet",
            "intent": getattr(parsed_intent, "intent", "BROWSER") if parsed_intent else "BROWSER",
            "entities": entities,
        }

    # --------------------------------------------------

    def _activate_browser(self, browser: str | None = None) -> None:
        try:
            import pygetwindow as gw
            title = "Chrome" if not browser else ("Firefox" if browser == "firefox" else "Edge" if browser == "edge" else "Chrome")
            wins = gw.getWindowsWithTitle(title)
            if wins:
                win = wins[-1]
                try:
                    win.activate()
                except Exception:
                    pass
        except Exception:
            # Best-effort only; hotkeys still apply to current active window.
            pass

    def _open_in_browser(self, url: str, browser: str | None = None) -> None:
        if browser in ("chrome", "edge", "firefox"):
            exe = "chrome" if browser == "chrome" else "msedge" if browser == "edge" else "firefox"
            subprocess.Popen([exe, url])
        else:
            webbrowser.open(url)

    def _open_site(self, entities: Dict[str, Any]) -> Dict[str, Any]:

        url = entities.get("url") or entities.get("site")
        browser = (entities.get("browser") or "").strip().lower() or None

        if not url:
            return {
                "success": False,
                "response_text": "No website specified"
            }

        if not url.startswith(("http://", "https://")):
            url = f"https://{url}"

        try:
            self._open_in_browser(url, browser=browser)

            logger.info("Opened site: %s", url)

            return {
                "success": True,
                "response_text": f"Opening {url}"
            }

        except Exception as e:

            logger.error("Open failed: %s", e)

            return {
                "success": False,
                "response_text": "Failed to open website"
            }

    # --------------------------------------------------

    def _search(self, entities: Dict[str, Any]) -> Dict[str, Any]:

        query = entities.get("query")
        browser = (entities.get("browser") or "").strip().lower() or None

        if not query:
            return {
                "success": False,
                "response_text": "No search query provided"
            }

        encoded = urllib.parse.quote(query)
        url = f"https://www.google.com/search?q={encoded}"

        try:
            self._open_in_browser(url, browser=browser)

            logger.info("Search query: %s", query)

            return {
                "success": True,
                "response_text": f"Searching for {query}"
            }

        except Exception as e:

            logger.error("Search failed: %s", e)

            return {
                "success": False,
                "response_text": "Search failed"
            }

    # --------------------------------------------------

    def _navigate_back(self, entities: Dict[str, Any]) -> Dict[str, Any]:

        try:
            self._activate_browser(entities.get("browser"))

            pyautogui.hotkey("alt", "left")

            return {
                "success": True,
                "response_text": "Going back"
            }

        except Exception:

            return {
                "success": False,
                "response_text": "Could not go back"
            }

    # --------------------------------------------------

    def _navigate_forward(self, entities: Dict[str, Any]) -> Dict[str, Any]:

        try:
            self._activate_browser(entities.get("browser"))

            pyautogui.hotkey("alt", "right")

            return {
                "success": True,
                "response_text": "Going forward"
            }

        except Exception:

            return {
                "success": False,
                "response_text": "Could not go forward"
            }

    # --------------------------------------------------

    def _refresh(self, entities: Dict[str, Any]) -> Dict[str, Any]:

        try:
            self._activate_browser(entities.get("browser"))

            pyautogui.hotkey("ctrl", "r")

            return {
                "success": True,
                "response_text": "Page refreshed"
            }

        except Exception:

            return {
                "success": False,
                "response_text": "Could not refresh page"
            }

    # --------------------------------------------------

    def _new_tab(self, entities: Dict[str, Any]) -> Dict[str, Any]:

        try:
            self._activate_browser(entities.get("browser"))

            pyautogui.hotkey("ctrl", "t")

            return {
                "success": True,
                "response_text": "Opened new tab"
            }

        except Exception:

            return {
                "success": False,
                "response_text": "Could not open new tab"
            }

    # --------------------------------------------------

    def _close_tab(self, entities: Dict[str, Any]) -> Dict[str, Any]:

        try:
            self._activate_browser(entities.get("browser"))

            pyautogui.hotkey("ctrl", "w")

            return {
                "success": True,
                "response_text": "Closed tab"
            }

        except Exception:

            return {
                "success": False,
                "response_text": "Could not close tab"
            }

    def _next_tab(self, entities: Dict[str, Any]) -> Dict[str, Any]:

        try:
            self._activate_browser(entities.get("browser"))
            pyautogui.hotkey("ctrl", "tab")
            return {"success": True, "response_text": "Next tab"}
        except Exception:
            return {"success": False, "response_text": "Could not switch tab"}

    def _switch_tab(self, entities: Dict[str, Any]) -> Dict[str, Any]:

        try:
            self._activate_browser(entities.get("browser"))
            tab_index = entities.get("tab_index")
            if isinstance(tab_index, int) and 1 <= tab_index <= 9:
                pyautogui.hotkey("ctrl", str(tab_index))
                return {"success": True, "response_text": f"Switched to tab {tab_index}"}
            pyautogui.hotkey("ctrl", "tab")
            return {"success": True, "response_text": "Switched tab"}
        except Exception:
            return {"success": False, "response_text": "Could not switch tab"}

    def _prev_tab(self, entities: Dict[str, Any]) -> Dict[str, Any]:

        try:
            self._activate_browser(entities.get("browser"))
            pyautogui.hotkey("ctrl", "shift", "tab")
            return {"success": True, "response_text": "Previous tab"}
        except Exception:
            return {"success": False, "response_text": "Could not switch tab"}

    # --------------------------------------------------

    def _scroll(self, entities: Dict[str, Any]) -> Dict[str, Any]:

        direction = entities.get("direction", "down")
        amount = entities.get("amount", 500)

        try:
            self._activate_browser(entities.get("browser"))

            if direction == "up":
                pyautogui.scroll(amount)

            else:
                pyautogui.scroll(-amount)

            return {
                "success": True,
                "response_text": f"Scrolled {direction}"
            }

        except Exception:

            return {
                "success": False,
                "response_text": "Scrolling failed"
            }

    # --------------------------------------------------

    def _download(self, entities: Dict[str, Any]) -> Dict[str, Any]:

        try:
            self._activate_browser(entities.get("browser"))

            pyautogui.hotkey("ctrl", "s")

            return {
                "success": True,
                "response_text": "Opening download dialog"
            }

        except Exception:

            return {
                "success": False,
                "response_text": "Download failed"
            }

    def _read_selection(self, entities: Dict[str, Any]) -> Dict[str, Any]:
        try:
            self._activate_browser(entities.get("browser"))
            pyautogui.hotkey("ctrl", "c")
            import tkinter as tk
            r = tk.Tk()
            r.withdraw()
            text = r.clipboard_get()
            r.destroy()
            text = (text or "").strip()
            if not text:
                return {"success": False, "response_text": "No selection to read."}
            return {"success": True, "response_text": text, "selection": text}
        except Exception:
            return {"success": False, "response_text": "Could not read selection."}