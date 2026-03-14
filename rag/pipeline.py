"""
RAG pipeline: index intent/ and actions/ for flexible command normalization.

- Builds index at runtime from intent.constants (and optional action discovery)
  so new intents/actions are picked up without code changes.
- Auto-refreshes when intent/ or parser files change (by mtime) so new intents
  or parser actions are picked up without restarting.
- Strips filler words and normalizes whitespace so the intent parser and
  action_engine receive a clean, desired command string.
"""
from functools import lru_cache
import os
import re
import time
import logging
from typing import List, Set, Tuple, Optional

logger = logging.getLogger(__name__)


def _intent_constants_path() -> Optional[str]:
    """Path to intent/constants.py so we can watch for changes."""
    try:
        import intent.constants as m
        return getattr(m, "__file__", None)
    except ImportError:
        return None


def _intent_parser_path() -> Optional[str]:
    """Path to intent/parser.py so we can watch for changes."""
    try:
        import intent.parser as m
        return getattr(m, "__file__", None)
    except ImportError:
        return None


def _actions_folder_path() -> Optional[str]:
    """Path to actions/ package folder."""
    try:
        import actions
        p = getattr(actions, "__file__", None)
        return os.path.dirname(p) if p else None
    except ImportError:
        return None


def _newer_than(timestamp: float, paths: List[Optional[str]]) -> bool:
    """True if any path exists and has mtime > timestamp."""
    for p in paths:
        if not p or not os.path.isfile(p):
            continue
        try:
            if os.path.getmtime(p) > timestamp:
                return True
        except OSError:
            pass
    # For actions folder, check any .py file change
    actions_dir = _actions_folder_path()
    if actions_dir and os.path.isdir(actions_dir):
        try:
            for name in os.listdir(actions_dir):
                if name.endswith(".py"):
                    p = os.path.join(actions_dir, name)
                    if os.path.getmtime(p) > timestamp:
                        return True
        except OSError:
            pass
    return False


# Filler words/phrases to strip (order matters: longer phrases first)
FILLER_PATTERNS: List[str] = [
    r"\bcan you (please)?\b",
    r"\bcould you (please)?\b",
    r"\bwould you (please)?\b",
    r"\bwill you (please)?\b",
    r"\bI want you to\b",
    r"\bI need you to\b",
    r"\bplease\b",
    r"\bhey\s+\w+\b",  # "hey jarvis" etc. (wake word often already dropped)
    r"\bum+\b",
    r"\buh+\b",
    r"\bah+\b",
    r"\blike\s+",  # "like open" -> "open" (space so we don't kill "something like X")
    r"\byou know\b",
    r"\bokay\s+so\s+",
    r"\bso\s+",  # leading "so" (e.g. "so open chrome")
    r"\bactually\s+",
    r"\bbasically\s+",
    r"\bjust\s+",  # "just open" -> "open"
    r"\breally\s+",
    r"\bkind of\b",
    r"\bsort of\b",
    r"\bI mean\b",
    r"\bright\b",  # "open chrome right now" -> keep "now" or drop both
    r"\bthen\b",  # "and then open" -> "and open" or "open"
]

# Standalone filler words to remove when they are not the command
FILLER_WORDS: Set[str] = {
    "um", "uh", "ah", "er", "eh", "like", "you", "know", "please",
    "okay", "ok", "so", "well", "actually", "basically", "just", "really",
    "right", "yeah", "yep", "yes", "no", "maybe", "kind", "sort", "mean",
}

def _load_intent_index() -> Tuple[dict, list, set]:
    """
    Load intent patterns and labels from intent.constants.
    Returns (intent_patterns, intent_labels, command_verbs).
    """
    try:
        from intent.constants import ALL_INTENTS, INTENT_PATTERNS
    except ImportError as e:
        logger.warning("RAG: could not load intent.constants: %s", e)
        return {}, [], set()

    labels = [i for i in ALL_INTENTS if i != "UNKNOWN"]
    # Extract likely "command" verbs from regex patterns so we don't strip them
    verbs: Set[str] = set()
    for intent, patterns in (INTENT_PATTERNS or {}).items():
        for pat in patterns or []:
            # Extract words from (word|word2) groups in the pattern string
            for m in re.finditer(r"\(([^)]+)\)", pat):
                for part in m.group(1).split("|"):
                    part = part.strip().strip('"').strip("\\")
                    if part and len(part) >= 2 and part.isalpha():
                        verbs.add(part.lower())
    return INTENT_PATTERNS or {}, labels, verbs


def _discover_action_keywords() -> Set[str]:
    """
    Discover action-related keywords from the parser / actions layer
    so we don't strip them. Uses intent constants and known app names.
    """
    keywords: Set[str] = set()
    try:
        from intent.constants import INTENT_PATTERNS
        for patterns in (INTENT_PATTERNS or {}).values():
            for p in patterns or []:
                # Simple: extract obvious words from pattern (e.g. open, close, volume)
                for m in re.finditer(r"[\w']+", p):
                    w = m.group(0).lower()
                    if len(w) >= 2 and w not in ("br", "in", "to", "or", "be", "on", "up", "it"):
                        keywords.add(w)
    except ImportError:
        pass
    # Known app names / targets from parser (keep these)
    known = {
        "chrome", "firefox", "notepad", "vscode", "calculator", "terminal",
        "explorer", "settings", "word", "excel", "powerpoint", "spotify",
        "zoom", "slack", "teams", "discord", "volume", "brightness", "timer",
        "stopwatch", "screenshot", "music", "youtube", "search", "open",
        "launch", "start", "run", "close", "mute", "unmute", "read", "write",
        "dictation", "screen", "page", "dictate",
        # Common folders so phrases like "open documents" survive normalization
        "documents", "downloads", "desktop", "pictures", "photos", "videos",
    }
    keywords.update(known)
    return keywords


class RAGPipeline:
    """
    RAG pipeline that indexes intent/ and actions/ and normalizes
    transcribed voice commands for the intent parser and action engine.

    Index is built at init from intent.constants (and optional discovery).
    Auto-refreshes when intent/constants.py, intent/parser.py, or any file in
    actions/ is modified (by mtime), so new intents or actions are picked up
    without restarting. You can also call refresh_index() manually.
    """

    def __init__(self, auto_refresh: bool = True):
        self._intent_patterns: dict = {}
        self._intent_labels: List[str] = []
        self._command_verbs: Set[str] = set()
        self._action_keywords: Set[str] = set()
        self._filler_re: re.Pattern | None = None
        self._last_index_mtime: float = 0.0
        self._auto_refresh = auto_refresh
        self._watch_paths: List[Optional[str]] = [
            _intent_constants_path(),
            _intent_parser_path(),
        ]
        self.refresh_index()

    def refresh_index(self) -> None:
        """
        (Re)build index from intent folder and action-related keywords.
        Called automatically when intent/ or actions/ files change, or call manually.
        """
        self._intent_patterns, self._intent_labels, self._command_verbs = _load_intent_index()
        self._action_keywords = _discover_action_keywords()
        # Compile filler patterns into one regex (alternation)
        combined = "|".join(FILLER_PATTERNS)
        self._filler_re = re.compile(combined, re.IGNORECASE)
        self._last_index_mtime = time.time()
        logger.debug(
            "RAG index refreshed: %d intents, %d command verbs, %d action keywords",
            len(self._intent_patterns),
            len(self._command_verbs),
            len(self._action_keywords),
        )
    @lru_cache(maxsize=256)
    def normalize(self, text: str) -> str:
        """
        Strip filler words and normalize whitespace. Returns a clean command
        string suitable for the intent parser and action_engine.

        - Auto-refreshes index when intent/ or actions/ files have changed.
        - Removes leading/trailing and duplicate spaces.
        - Strips known filler phrases and standalone filler words at boundaries.
        - Preserves words that look like command verbs or action keywords.
        """
        if not text or not text.strip():
            return text or ""

        # Auto-update index when intent/ or actions/ changed (new intents/actions picked up)
        if self._auto_refresh and _newer_than(self._last_index_mtime, self._watch_paths):
            logger.info("RAG: intent/ or actions/ changed, refreshing index")
            self.refresh_index()

        original = text
        t = text.strip()

        # Apply phrase-level filler removal (case-insensitive)
        if self._filler_re:
            t = self._filler_re.sub(" ", t)

        # Normalize whitespace and trim
        t = " ".join(t.split())

        # Remove leading/trailing standalone filler words (avoid stripping "open", "set", etc.)
        words = t.split()
        if not words:
            return original

        # Drop leading filler words (never strip command/action keywords)
        while words:
            w = words[0].lower()
            if w in self._command_verbs or w in self._action_keywords:
                break
            if w in FILLER_WORDS:
                words.pop(0)
                continue
            break

        # Drop trailing filler words
        while words:
            w = words[-1].lower()
            if w in self._command_verbs or w in self._action_keywords:
                break
            if w in FILLER_WORDS:
                words.pop()
                continue
            break

        t = " ".join(words).strip()
        if not t:
            return original
        return t
