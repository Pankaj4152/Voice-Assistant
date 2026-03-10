"""
intent/config.py
────────────────
Central configuration for the Intent module.
All settings in one place — never hardcode values elsewhere.
"""

from dataclasses import dataclass, field
from typing import List
import os
from dotenv import load_dotenv

load_dotenv()


@dataclass(frozen=True)
class OpenAIConfig:
    """OpenAI API settings."""
    api_key: str          = os.getenv("OPENAI_API_KEY", "")
    model: str            = "gpt-4o-mini"   # Cheapest + fastest
    max_tokens: int       = 10              # Intent = 1 word only
    temperature: float    = 0.0            # Deterministic output
    request_timeout: int  = 15             # Seconds before timeout


@dataclass(frozen=True)
class ClassifierConfig:
    """Rule-based classifier settings."""
    rule_confidence_threshold: int = 1      # Min pattern hits to confirm intent
    valid_intents: List[str] = field(
        default_factory=lambda: ["DOCS", "BROWSER", "OS", "AI"]
    )
    unknown_intent: str = "UNKNOWN"


@dataclass(frozen=True)
class IntentConfig:
    """Top-level composed config."""
    openai: OpenAIConfig        = field(default_factory=OpenAIConfig)
    classifier: ClassifierConfig = field(default_factory=ClassifierConfig)
    debug: bool                 = False


# ── Global singleton — import this everywhere ──
intent_config = IntentConfig()