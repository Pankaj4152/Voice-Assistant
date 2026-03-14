"""
intent/classifier.py
─────────────────────
Rule-Only Intent Classifier (no external API calls)

Pipeline:
    1. Rule-based regex scoring  — instant, free, works offline
    2. AI fallback               — unrecognised speech → AI intent
                                   (treats the full phrase as a question)

No Gemini / LLM dependency. Zero quota issues.
"""

import re
import logging

from .config import intent_config
from .constants import ALL_INTENTS, INTENT_UNKNOWN, INTENT_AI, INTENT_PATTERNS
from .exceptions import EmptyInputError
from .models import IntentResult, ClassificationMethod

logger = logging.getLogger(__name__)


class IntentClassifier:
    """
    Rule-only intent classifier.

    If no regex pattern matches the input, the command is routed to the
    AI intent handler so it can be processed as a conversational query —
    rather than silently failing or calling an external API.
    """

    def __init__(self):
        self._clf_cfg = intent_config.classifier
        logger.debug("IntentClassifier ready (rule-only mode)")

    # ──────────────────────────────────────────────────────────────────
    # PUBLIC API
    # ──────────────────────────────────────────────────────────────────

    def classify(self, text: str) -> IntentResult:
        """
        Classify a voice command into an intent.

        Returns:
            IntentResult — intent is always one of DOCS/BROWSER/OS/AI.
            Never raises due to quota / network issues.
        """
        text = text.strip()
        if not text:
            raise EmptyInputError()

        logger.info("Classifying → '%s'", text)

        # ── Rule-based pass ────────────────────
        intent, confidence = self._rule_classify(text)
        if intent != INTENT_UNKNOWN:
            logger.info("Rule match → %s (confidence=%.2f)", intent, confidence)
            return IntentResult(
                text=text,
                intent=intent,
                method=ClassificationMethod.RULE,
                confidence=confidence,
            )

        # ── Smart fallback: treat as AI question ──────────────────────
        # Unrecognised spoken phrases are almost always general questions.
        # Route to AI so the assistant can answer rather than do nothing.
        logger.info("No rule matched → AI fallback for: '%s'", text)
        return IntentResult(
            text=text,
            intent=INTENT_AI,
            method=ClassificationMethod.RULE,
            confidence=0.5,
        )

    # ──────────────────────────────────────────────────────────────────
    # PRIVATE — RULE-BASED SCORING
    # ──────────────────────────────────────────────────────────────────

    def _rule_classify(self, text: str) -> tuple[str, float]:
        """
        Score intents by counting matched regex patterns.

        Returns:
            (best_intent, confidence) or (UNKNOWN, 0.0)
        """
        text_lower = text.lower()
        scores: dict[str, int] = {intent: 0 for intent in ALL_INTENTS}
        total_matches = 0

        for intent, patterns in INTENT_PATTERNS.items():
            for pattern in patterns:
                if re.search(pattern, text_lower):
                    scores[intent] += 1
                    total_matches += 1

        best_intent = max(scores, key=scores.get)
        best_score  = scores[best_intent]

        if best_score < self._clf_cfg.rule_confidence_threshold:
            return INTENT_UNKNOWN, 0.0

        confidence = best_score / total_matches if total_matches > 0 else 1.0
        return best_intent, min(round(confidence, 2), 1.0)