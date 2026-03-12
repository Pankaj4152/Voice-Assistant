

from dataclasses import dataclass, field
from typing import Optional
from enum import Enum


class ClassificationMethod(str, Enum):
    """How the intent was determined."""
    RULE = "rule"    # Matched a regex pattern — instant, free
    LLM  = "llm"     # Sent to Gemini — used only for ambiguous commands
    NONE = "none"    # Empty input, no classification attempted


@dataclass
class IntentResult:
    """
    Result of intent classification.
    Returned by IntentClassifier.classify()
    """
    text: str                         # Original input command
    intent: str                       # DOCS | BROWSER | OS | AI | UNKNOWN
    method: ClassificationMethod      # How it was classified
    confidence: float = 1.0          # 1.0 = rule, 0.95 = LLM, 0.0 = failed
    error: Optional[str] = None      # Set if classification failed

    def is_known(self) -> bool:
        """Returns True if intent was successfully identified."""
        return self.intent != "UNKNOWN"

    def to_dict(self) -> dict:
        return {
            "text":       self.text,
            "intent":     self.intent,
            "method":     self.method.value,
            "confidence": self.confidence,
            "error":      self.error,
        }


@dataclass
class ParsedIntent:
    """
    Full parsed result including extracted entities.
    Returned by IntentParser.parse()
    """
    text: str                                        # Original input
    intent: str                                      # DOCS | BROWSER | OS | AI | UNKNOWN
    method: ClassificationMethod                     # rule | llm | none
    entities: dict = field(default_factory=dict)    # Extracted parameters
    confidence: float = 1.0
    error: Optional[str] = None

    def to_dict(self) -> dict:
        return {
            "text":       self.text,
            "intent":     self.intent,
            "method":     self.method.value,
            "entities":   self.entities,
            "confidence": self.confidence,
            "error":      self.error,
        }