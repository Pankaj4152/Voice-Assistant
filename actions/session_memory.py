import re
import copy
from typing import Any, Dict, Optional


_PRONOUN_PATTERN = re.compile(r"\b(this|that|it|him|her)\b", re.IGNORECASE)


class SessionMemory:
    """
    In-memory context tracker for short follow-up references like
    "close this" or "delete it".
    """

    def __init__(self):
        self._last_app: Optional[str] = None
        self._last_file_name: Optional[str] = None
        self._last_file_path: Optional[str] = None
        self._last_browser_url: Optional[str] = None

    def resolve(self, parsed_intent: Any, entities: Dict[str, Any]) -> Dict[str, Any]:
        """Resolve pronoun references in entities using recent context."""
        resolved = copy.deepcopy(entities or {})
        text = (getattr(parsed_intent, "text", "") or "").strip().lower()
        intent = (getattr(parsed_intent, "intent", "") or "").strip().upper()
        action = (resolved.get("action") or "").strip().lower()

        if intent == "OS":
            app = (resolved.get("app") or "").strip().lower()
            if action in ("close", "launch", "switch_app"):
                if self._looks_like_reference(app) or (not app and self._has_reference(text)):
                    if self._last_app:
                        resolved["app"] = self._last_app

        if intent == "DOCS":
            filename = (resolved.get("filename") or resolved.get("name") or "").strip()
            if action in ("open", "delete", "close"):
                if self._looks_like_reference(filename) or (not filename and self._has_reference(text)):
                    if self._last_file_name:
                        resolved["filename"] = self._last_file_name
                    if self._last_file_path:
                        resolved["path"] = self._last_file_path

        if intent == "BROWSER":
            url = (resolved.get("url") or "").strip().lower()
            if action in ("open", "search"):
                if self._looks_like_reference(url) and self._last_browser_url:
                    resolved["url"] = self._last_browser_url

        return resolved

    def remember(self, parsed_intent: Any, entities: Dict[str, Any], result: Dict[str, Any]) -> None:
        """Update memory from successful actions only."""
        if not (result or {}).get("success", False):
            return

        intent = (getattr(parsed_intent, "intent", "") or "").strip().upper()
        action = ((entities or {}).get("action") or "").strip().lower()

        if intent == "OS":
            app = ((entities or {}).get("app") or "").strip().lower()
            if app and not self._looks_like_reference(app):
                self._last_app = app

        if intent == "DOCS":
            filename = (
                ((entities or {}).get("filename") or "").strip()
                or ((entities or {}).get("name") or "").strip()
            )
            path = ((result or {}).get("path") or (entities or {}).get("path") or "").strip()

            if filename and not self._looks_like_reference(filename):
                self._last_file_name = filename

            if path and not self._looks_like_reference(path):
                self._last_file_path = path

        if intent == "BROWSER":
            url = ((entities or {}).get("url") or "").strip()
            if action == "open" and url and not self._looks_like_reference(url):
                self._last_browser_url = url

    @staticmethod
    def _has_reference(text: str) -> bool:
        return bool(_PRONOUN_PATTERN.search(text or ""))

    @staticmethod
    def _looks_like_reference(value: str) -> bool:
        value = (value or "").strip().lower()
        if not value:
            return False
        return value in {
            "this",
            "that",
            "it",
            "this app",
            "that app",
            "this file",
            "that file",
            "this window",
            "that window",
            "this tab",
            "that tab",
        }
