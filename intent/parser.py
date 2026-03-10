

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
            "open":      r"\b(open|go to|navigate|visit)\b",
            "search":    r"\bsearch\b",
            "click":     r"\b(click|press|tap)\b",
            "scroll":    r"\bscroll\b",
            "fill_form": r"\b(fill|enter|type)\b.*(field|form|input)\b",
            "back":      r"\bgo back\b",
            "forward":   r"\bgo forward\b",
            "refresh":   r"\b(refresh|reload)\b",
            "new_tab":   r"\bnew tab\b",
            "close_tab": r"\bclose tab\b",
            "read_page": r"\bread\b.*(page|article|content)\b",
            "download":  r"\bdownload\b",
        }
        for action, pattern in action_map.items():
            if re.search(pattern, t):
                e["action"] = action
                break

        # URL
        if m := re.search(r"(https?://\S+|www\.\S+|\b\w+\.(com|org|net|io|in)\b)", t):
            e["url"] = m.group(0)

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

        return e

    # ──────────────────────────────────────────────────────────────────
    # PRIVATE — OS
    # ──────────────────────────────────────────────────────────────────

    def _os(self, text: str) -> dict:
        t = text.lower()
        e: dict = {}

        action_map = {
            "launch":     r"\b(open|launch|start|run)\b",
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
            "copy_file":  r"\bcopy\b.*(file|folder)",
            "move_file":  r"\bmove\b.*(file|folder)",
            "delete_file":r"\bdelete\b.*(file|folder)",
            "rename":     r"\brename\b",
        }
        for action, pattern in action_map.items():
            if re.search(pattern, t):
                e["action"] = action
                break

        # App name
        known_apps = [
            "notepad", "vscode", "vs code", "calculator", "chrome",
            "firefox", "terminal", "explorer", "file manager", "task manager",
            "settings", "word", "excel", "powerpoint", "vlc",
            "spotify", "zoom", "slack", "teams", "discord", "paint",
        ]
        for app in known_apps:
            if app in t:
                e["app"] = app
                break

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