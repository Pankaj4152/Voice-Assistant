

import re
import logging
from typing import Optional

from .classifier import IntentClassifier
from .constants import INTENT_DOCS, INTENT_BROWSER, INTENT_OS, INTENT_AI
from .models import ParsedIntent

logger = logging.getLogger(__name__)


class IntentParser:
    """
    Full intent pipeline: classify → extract entities.

    Args:
        classifier: IntentClassifier instance.
                    Auto-created if not passed.
    """

    def __init__(self, classifier: Optional[IntentClassifier] = None):
        self._clf = classifier or IntentClassifier()

    # ──────────────────────────────────────────────────────────────────
    # PUBLIC API
    # ──────────────────────────────────────────────────────────────────

    def parse(self, text: str) -> ParsedIntent:
        """
        Full pipeline: classify → extract entities.

        Args:
            text: Raw transcribed voice command.

        Returns:
            ParsedIntent with intent, method, entities dict.
        """
        result   = self._clf.classify(text)
        entities = self._extract(text, result.intent)

        logger.info(
            "Parsed | intent=%-8s | method=%-4s | entities=%s",
            result.intent, result.method.value, entities,
        )

        return ParsedIntent(
            text=result.text,
            intent=result.intent,
            method=result.method,
            entities=entities,
            confidence=result.confidence,
            error=result.error,
        )

    # ──────────────────────────────────────────────────────────────────
    # PRIVATE — ROUTER
    # ──────────────────────────────────────────────────────────────────

    def _extract(self, text: str, intent: str) -> dict:
        extractors = {
            INTENT_DOCS:    self._docs,
            INTENT_BROWSER: self._browser,
            INTENT_OS:      self._os,
            INTENT_AI:      self._ai,
        }
        fn = extractors.get(intent)
        return fn(text) if fn else {}

    # ──────────────────────────────────────────────────────────────────
    # PRIVATE — DOCS
    # ──────────────────────────────────────────────────────────────────

    def _docs(self, text: str) -> dict:
        t = text.lower()
        e: dict = {}

        # Action
        action_map = {
            "create":       r"\b(create|new|make|open)\b",
            "write":        r"\b(write|type|dictate|append|insert)\b",
            "format":       r"\b(bold|italic|underline|heading|format)\b",
            "save":         r"\b(save|export)\b",
            "delete":       r"\b(delete|remove)\b",
            "undo":         r"\bundo\b",
            "redo":         r"\bredo\b",
            "insert_table": r"\b(add|insert)\b.*(table)\b",
            "select":       r"\bselect\b",
            "close":        r"\bclose\b",
        }
        for action, pattern in action_map.items():
            if re.search(pattern, t):
                e["action"] = action
                break

        # Filename
        m = re.search(r"\b(named|called|titled|title)\s+(.+?)(\s+and|\s+with|$)", t)
        if m:
            e["filename"] = m.group(2).strip()

        # Dictated content
        m = re.search(r"\b(write|type|dictate)[:\s]+(.+)", text, re.IGNORECASE)
        if m:
            e["content"] = m.group(2).strip()

        # Export format
        for fmt in ["pdf", "docx", "txt"]:
            if fmt in t:
                e["format"] = fmt
                break

        # Format target
        for fmt in ["bold", "italic", "underline", "heading"]:
            if fmt in t:
                e["target"] = fmt
                break

        # Table dimensions
        if m := re.search(r"(\d+)\s+rows?", t):
            e["rows"] = int(m.group(1))
        if m := re.search(r"(\d+)\s+col(umns?)?", t):
            e["cols"] = int(m.group(1))

        return e

    # ──────────────────────────────────────────────────────────────────
    # PRIVATE — BROWSER
    # ──────────────────────────────────────────────────────────────────

    def _browser(self, text: str) -> dict:
        t = text.lower()
        e: dict = {}

        action_map = {
            "new_tab":   r"\bnew tab\b",
            "close_tab": r"\bclose tab\b",
            "switch_tab": r"\b(switch|go)\s+to\s+tab\b|\bswitch tab\b",
            "next_tab":  r"\bnext tab\b",
            "prev_tab":  r"\b(previous tab|prev tab)\b",
            "refresh":   r"\b(refresh|reload)\b|\brefresh page\b",
            "back":      r"\bgo back\b|\bback\b",
            "forward":   r"\bgo forward\b|\bforward\b",
            "scroll":    r"\bscroll\b",
            "zoom":      r"\bzoom\b",
            "read_selection": r"\bread selection\b|\bread selected\b",
            "read_page": r"\bread\b.*(page|article|content)\b",
            "download":  r"\bdownload\b",
            "search":    r"\bsearch\b",
            "open":      r"\b(open|go to|navigate|visit)\b",
            "click":     r"\b(click|press|tap)\b",
            "fill_form": r"\b(fill|enter|type)\b.*(field|form|input)\b",
        }
        for action, pattern in action_map.items():
            if re.search(pattern, t):
                e["action"] = action
                break

        # URL
        if m := re.search(r"(https?://\S+|www\.\S+|\b\w+\.(com|org|net|io|in)\b)", t):
            e["url"] = m.group(0)
        elif e.get("action") == "open":
            # Common site shortcuts (when user says just "youtube", "google", etc.)
            if "youtube" in t:
                e["url"] = "https://www.youtube.com"
            elif "google" in t:
                e["url"] = "https://www.google.com"
            elif "gmail" in t:
                e["url"] = "https://mail.google.com"
            elif "facebook" in t:
                e["url"] = "https://www.facebook.com"
            elif "instagram" in t:
                e["url"] = "https://www.instagram.com"

        # Browser hint: "on chrome/edge/firefox"
        if m := re.search(r"\b(on|in)\s+(chrome|edge|firefox)\b", t):
            e["browser"] = m.group(2)

        # Search query
        if m := re.search(r"\bsearch\b\s+(?:for\s+)?(.+?)(\s+on\s+\w+|$)", text, re.IGNORECASE):
            e["query"] = m.group(1).strip()

        # Click element
        if m := re.search(r"\b(click|press)\b\s+(?:the\s+)?(.+?)(\s+button|\s+link|$)", text, re.IGNORECASE):
            e["element"] = m.group(2).strip()

        # Scroll direction & times
        if m := re.search(r"\bscroll\b\s+(up|down|left|right)", t):
            e["direction"] = m.group(1)
        if m := re.search(r"(\d+)\s+times?", t):
            e["times"] = int(m.group(1))
            # Map human "N times" to a scroll amount in pixels
            e["amount"] = 400 * e["times"]
        if m := re.search(r"\btab\s+(\d{1,2})\b", t):
            e["tab_index"] = int(m.group(1))

        # Zoom percentage, e.g. "zoom to 125 percent" or "zoom 90%"
        if "zoom" in t:
            if m := re.search(r"\b(\d{2,3})\s*%?", t):
                pct = max(25, min(int(m.group(1)), 500))
                e["zoom_percent"] = pct
            if re.search(r"\b(in|inward)\b", t):
                e["zoom_direction"] = "in"
            elif re.search(r"\b(out|outward)\b", t):
                e["zoom_direction"] = "out"

        return e

    # ──────────────────────────────────────────────────────────────────
    # PRIVATE — OS
    # ──────────────────────────────────────────────────────────────────

    def _os(self, text: str) -> dict:
        t = text.lower()
        e: dict = {}

        # Accessibility-focused query actions
        if re.search(r"\b(what(?:'s| is)?|current|check)\b.*\b(volume|sound)\b", t) or re.search(r"\b(volume|sound)\s+(level|status)\b", t):
            e["action"] = "volume_status"
            e["target"] = "volume"
            return e

        if re.search(r"\b(describe|explain|read|tell me)\b.*\b(screen|display)\b", t) or re.search(r"\bwhat(?:'s| is)\b.*\bon\b.*\b(screen|display)\b", t):
            e["action"] = "describe_screen"
            e["target"] = "screen"
            return e

        if re.search(r"\b(what(?:'s| is)?|current|check)\b.*\b(battery|charge)\b", t) or re.search(r"\b(battery|charge)\s+(level|status|left|remaining)\b", t):
            e["action"] = "battery_status"
            e["target"] = "battery"
            return e

        if re.search(r"\b(what(?:'s| is)?|current|check)\b.*\b(wi\s*-?\s*fi|wifi|wireless)\b", t) or re.search(r"\b(wi\s*-?\s*fi|wifi|wireless)\b.*\b(status|signal|connected|connection|network|ssid)\b", t):
            e["action"] = "wifi_status"
            e["target"] = "wifi"
            return e

        if re.search(r"\b(internet|network)\b.*\b(status|connected|working|online)\b", t) or re.search(r"\bam i\s+(online|offline)\b", t):
            e["action"] = "network_status"
            e["target"] = "network"
            return e

        if re.search(r"\b(which|what)\s+app\b.*\b(open|active|current)\b", t) or re.search(r"\bwhere\s+am\s+i\b", t):
            e["action"] = "active_window_status"
            e["target"] = "window"
            return e

        if re.search(r"\b(what(?:'s| is)?|current|tell me)\b.*\b(time|date|day)\b", t):
            e["action"] = "date_time_status"
            e["target"] = "datetime"
            return e

        if re.search(r"\b(environment|system)\b.*\b(summary|status|report)\b", t) or re.search(r"\bstatus\s+report\b", t):
            e["action"] = "environment_summary"
            e["target"] = "environment"
            return e

        # ── File navigation ──────────────────────────────────────────────────
        _FOLDERS = ["downloads", "desktop", "documents", "pictures", "music", "videos", "home"]

        def _pick_folder(text_lower: str) -> str:
            for f in _FOLDERS:
                if f in text_lower:
                    return f
            m2 = re.search(r"\b(in|inside|of)\s+(?:the\s+)?(\w+)\b", text_lower)
            return m2.group(2) if m2 else ""

        # list_folder: "show files in downloads" / "list desktop" / "what's in documents"
        if (re.search(r"\b(list|show)\b.*(files?|folder|contents?|directory)\b", t)
                or re.search(r"\bwhat(?:'s| is|s)\b.*(in|inside)\b.*(downloads|desktop|documents|pictures|music|videos)\b", t)
                or re.search(r"\b(list|show)\b\s+(?:the\s+)?(downloads|desktop|documents|pictures|music|videos)\b", t)):
            e["action"] = "list_folder"
            e["folder"] = _pick_folder(t)
            return e

        # open_folder / go_to_folder: "open downloads" / "navigate to documents" / "go to desktop"
        if re.search(r"\b(open|navigate to|go to)\b\s+(?:the\s+)?(downloads|desktop|documents|pictures|music|videos|home)\b", t):
            e["action"] = "open_folder"
            e["folder"] = _pick_folder(t)
            return e

        # find_file: "find report.txt" / "where is budget.xlsx" / "find report on desktop"
        if m := re.search(r"\b(find|search for|where is|locate)\b\s+(.+)", t):
            e["action"] = "find_file"
            raw_query = m.group(2).strip()

            # Optional location suffixes: "in downloads", "on desktop", "inside documents"
            loc_match = re.search(
                r"\b(?:in|on|inside)\s+(?:the\s+)?(downloads|desktop|documents|pictures|music|videos|home)\b",
                raw_query,
            )
            if loc_match:
                e["folder"] = loc_match.group(1)
                raw_query = re.sub(
                    r"\b(?:in|on|inside)\s+(?:the\s+)?(downloads|desktop|documents|pictures|music|videos|home)\b",
                    "",
                    raw_query,
                ).strip()

            e["filename"] = raw_query
            return e

        # move_file: "move report.txt to downloads"
        if m := re.search(r"\bmove\b\s+(.+?)\s+to\s+(\w+)", t):
            e["action"] = "move_file"
            e["filename"] = m.group(1).strip()
            e["dest"] = m.group(2).strip()
            return e

        # copy_file: "copy report.txt to desktop"
        if m := re.search(r"\bcopy\b\s+(.+?)\s+to\s+(\w+)", t):
            e["action"] = "copy_file"
            e["filename"] = m.group(1).strip()
            e["dest"] = m.group(2).strip()
            return e

        # rename_file: "rename report.txt to final.txt"
        if m := re.search(r"\brename\b\s+(.+?)\s+to\s+(.+)", t):
            e["action"] = "rename_file"
            e["filename"] = m.group(1).strip()
            e["new_name"] = m.group(2).strip()
            return e

        # delete_file: "delete report.txt" / "remove budget.xlsx"
        if re.search(r"\b(delete|remove)\b.*(\.\w{2,4}|file\b)", t):
            e["action"] = "delete_file"
            if m := re.search(r"\b(?:delete|remove)\b\s+(.+)", t):
                name = m.group(1).strip()
                # strip trailing noise words
                name = re.sub(r"\s+(file|from\s+\w+)$", "", name).strip()
                e["filename"] = name
            return e

        # Special multi-window / global actions first
        if re.search(r"\bminimi[sz]e\b.*\ball\b|\bminimi[sz]e all\b", t):
            e["action"] = "minimize_all"
            return e
        if re.search(r"\bclose\b.*\ball\b.*\b(apps?|applications?|windows?)\b|\bclose all\b", t):
            e["action"] = "close_all_apps"
            return e

        # Timer / stopwatch
        if "timer" in t:
            if re.search(r"\b(stop|cancel|clear)\b.*\btimer\b|\bstop timer\b|\bcancel timer\b", t):
                e["action"] = "timer_cancel"
                return e
            e["action"] = "timer_set"
            if m := re.search(r"\bfor\s+(\d+)\s*(seconds?|secs?|s|minutes?|mins?|m|hours?|hrs?|h)\b", t):
                e["duration"] = int(m.group(1))
                unit = m.group(2)
                if unit.startswith(("sec", "s")):
                    e["unit"] = "seconds"
                elif unit.startswith(("min", "m")):
                    e["unit"] = "minutes"
                else:
                    e["unit"] = "hours"
            return e

        if "stopwatch" in t:
            if re.search(r"\b(start|begin|launch)\b.*\bstopwatch\b|\bstart stopwatch\b", t):
                e["action"] = "stopwatch_start"
            elif re.search(r"\b(stop|end)\b.*\bstopwatch\b|\bstop stopwatch\b", t):
                e["action"] = "stopwatch_stop"
            elif re.search(r"\b(reset|clear)\b.*\bstopwatch\b|\breset stopwatch\b", t):
                e["action"] = "stopwatch_reset"
            else:
                e["action"] = "stopwatch_start"
            return e

        # Music (kept in OS so it doesn't route to AI)
        if re.search(r"\bplay\b", t):
            if m := re.search(r"\bplay\b\s+(.+?)(\s+on\s+(spotify|youtube)|$)", t):
                name = m.group(1).strip()
                if name in ("music", "some music", "random music"):
                    name = ""
                e["action"] = "music_play"
                e["name"] = name
                if m.group(3):
                    e["platform"] = m.group(3)
                return e

        # Volume / brightness normalization (percent + synonyms)
        if re.search(r"\b(unmute|sound on|speaker on)\b", t):
            e["action"] = "unmute"
            e["target"] = "volume"
            return e
        if re.search(r"\b(mute|silence|sound off|speaker off)\b", t):
            e["action"] = "mute"
            e["target"] = "volume"
            return e

        if "volume" in t or "sound" in t or "speaker" in t:
            e["target"] = "volume"
            if m := re.search(r"(\d{1,3})\s*%?", t):
                v = max(0, min(int(m.group(1)), 100))
                e["action"] = "set"
                e["value"] = v
                return e
            if re.search(r"\b(max|maximum|full|high|loud)\b", t):
                e["action"] = "set"
                e["value"] = 100
                return e
            if re.search(r"\b(low|quiet|soft)\b", t):
                e["action"] = "set"
                e["value"] = 20
                return e
            if re.search(r"\b(up|increase|raise|turn up)\b", t):
                e["action"] = "increase"
                return e
            if re.search(r"\b(down|decrease|lower|turn down)\b", t):
                e["action"] = "decrease"
                return e

        if "brightness" in t or re.search(r"\b(dim|bright(en)?|dimmer|brighter)\b", t):
            e["target"] = "brightness"
            if m := re.search(r"(\d{1,3})\s*%?", t):
                v = max(0, min(int(m.group(1)), 100))
                e["action"] = "set"
                e["value"] = v
                return e
            if re.search(r"\b(max|maximum|full|high|bright)\b", t):
                e["action"] = "set"
                e["value"] = 100
                return e
            if re.search(r"\b(low|dim|dark)\b", t):
                e["action"] = "set"
                e["value"] = 20
                return e
            if re.search(r"\b(up|increase|raise|brighter)\b", t):
                e["action"] = "increase"
                return e
            if re.search(r"\b(down|decrease|lower|dim|dimmer)\b", t):
                e["action"] = "decrease"
                return e

        action_map = {
            "switch_app": r"\b(switch|focus)\s+to\s+(?!tab\b)",
            "launch":     r"\b(open|launch|start|run)\b",
            "close_window": r"\b(close|quit|exit)\b\s+(this|current)?\s*(window|app)\b|\bclose this\b",
            "close":      r"\b(close|quit|exit|kill)\b",
            "screenshot": r"\b(screenshot|screen capture|capture screen)\b",
            "increase":   r"\b(increase|raise)\b.*(volume|brightness)\b",
            "decrease":   r"\b(decrease|lower|reduce)\b.*(volume|brightness)\b",
            "set":        r"\b(set|change)\b.*(volume|brightness)\b",
            "mute":       r"\bmute\b",
            "unmute":     r"\bunmute\b",
            "lock":       r"\block\b",
            "shutdown":   r"\bshutdown\b",
            "restart":    r"\brestart\b",
            "sleep":      r"\bsleep\b",
            "minimize":   r"\bminimize\b",
            "maximize":   r"\bmaximize\b",
            "restore":    r"\brestore\b",
            "switch_window": r"\b(switch|next)\s+(window|app)\b|\balt tab\b",
            "previous_window": r"\b(previous|last)\s+(window|app)\b|\bback window\b",
            "task_view":  r"\btask view\b|\bshow tasks\b",
            "show_desktop": r"\b(show|go to)\s+desktop\b",
            "new_desktop": r"\b(new|create)\s+(desktop|virtual desktop)\b",
            "next_desktop": r"\bnext\s+(desktop|virtual desktop)\b",
            "previous_desktop": r"\b(previous|last)\s+(desktop|virtual desktop)\b",
            "close_desktop": r"\bclose\s+(desktop|virtual desktop)\b",
            "copy":       r"\bcopy\b(?!\b.*(file|folder|directory))",
            "paste":      r"\bpaste\b(?!\b.*(file|folder|directory))",
            "cut":        r"\bcut\b(?!\b.*(file|folder|directory))",
            "select_all": r"\bselect all\b",
            "copy_file":  r"\bcopy\b.*(file|folder)",
            "move_file":  r"\bmove\b.*(file|folder)",
            "delete_file":r"\bdelete\b.*(file|folder)",
            "rename":     r"\brename\b",
        }
        for action, pattern in action_map.items():
            if re.search(pattern, t):
                e["action"] = action
                break

        # App name (common cases + "open <app>" capture)
        known_apps = [
            "camera", "calculator", "calc", "notepad", "chrome", "edge", "firefox",
            "terminal", "cmd", "powershell", "explorer", "settings", "task manager",
            "vscode", "vs code", "word", "excel", "powerpoint", "paint", "vlc",
            "spotify", "zoom", "slack", "teams", "discord",
        ]
        for app in known_apps:
            if app in t:
                e["app"] = app
                break
        if "app" not in e:
            if m := re.search(r"\b(open|launch|start|run|close|quit|exit|switch|focus)\b\s+(?:to\s+)?(.+?)(\s+(app|application|program|window)|$)", t):
                candidate = m.group(2).strip()
                if candidate:
                    e["app"] = candidate

        # Numeric value e.g. "volume to 70"
        if m := re.search(r"\bto\s+(\d+)\b", t):
            e["value"] = int(m.group(1))

        # Target system control
        for target in ["volume", "brightness", "wifi", "bluetooth"]:
            if target in t:
                e["target"] = target
                break

        return e

    # ──────────────────────────────────────────────────────────────────
    # PRIVATE — AI
    # ──────────────────────────────────────────────────────────────────

    def _ai(self, text: str) -> dict:
        t = text.lower()
        e: dict = {"action": "general_query", "query": text}

        action_map = {
            "translate":  r"\btranslate\b",
            "calculate":  r"\b(calculate|compute|solve|evaluate)\b",
            "weather":    r"\bweather\b",
            "datetime":   r"\b(time|date|today|tomorrow)\b",
            "reminder":   r"\b(remind|reminder|alarm|schedule)\b",
            "summarize":  r"\b(summarize|summary)\b",
            "define":     r"\b(define|what is|what are)\b",
            "recommend":  r"\b(recommend|suggest)\b",
        }
        for action, pattern in action_map.items():
            if re.search(pattern, t):
                e["action"] = action
                break

        # Target language for translate
        if e["action"] == "translate":
            if m := re.search(r"\bto\s+(\w+)\b", t):
                e["target_language"] = m.group(1)

        return e