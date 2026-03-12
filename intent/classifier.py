"""
intent/classifier.py
─────────────────────
Hybrid Intent Classifier: Rule-Based → Gemini fallback

Pipeline:
    1. Rule-based  — regex pattern scoring, instant, free (handles ~90% commands)
    2. Gemini fallback — only for ambiguous commands rules can't handle

Usage:
    from intent.classifier import IntentClassifier

    clf = IntentClassifier()
    result = clf.classify("open youtube and search python")
    print(result.intent)      # BROWSER
    print(result.method)      # ClassificationMethod.RULE
    print(result.confidence)  # 1.0
"""

import re
import logging
from typing import Optional

from .config import intent_config
from .constants import ALL_INTENTS, INTENT_UNKNOWN, INTENT_PATTERNS, LLM_SYSTEM_PROMPT
from .exceptions import APIKeyMissingError, APIRequestError, ClassificationTimeoutError, EmptyInputError
from .models import IntentResult, ClassificationMethod

logger = logging.getLogger(__name__)


class IntentClassifier:
    """
    Hybrid intent classifier.

    Step 1 → Rule-based regex scoring  (instant, zero cost)
    Step 2 → Gemini                     (only if Step 1 fails)
    """

    def __init__(self):
        self._cfg = intent_config.gemini
        self._clf_cfg = intent_config.classifier

        if not self._cfg.api_key:
            logger.warning(
                "GEMINI_API_KEY not found in environment. "
                "LLM fallback will raise APIKeyMissingError if triggered."
            )

        logger.debug("IntentClassifier ready | model=%s", self._cfg.model)

    # ──────────────────────────────────────────────────────────────────
    # PUBLIC API
    # ──────────────────────────────────────────────────────────────────

    def classify(self, text: str) -> IntentResult:
        """
        Classify a voice command into an intent.

        Args:
            text: Raw transcribed voice command.

        Returns:
            IntentResult — intent, method, confidence.

        Raises:
            EmptyInputError: If text is empty.
            APIKeyMissingError: If LLM triggered but API key not set.
        """
        text = text.strip()
        if not text:
            raise EmptyInputError()

        logger.info("Classifying → '%s'", text)

        # ── Step 1: Rule-based ─────────────────
        intent, confidence = self._rule_classify(text)
        if intent != INTENT_UNKNOWN:
            logger.info("Rule match → %s (confidence=%.2f)", intent, confidence)
            return IntentResult(
                text=text,
                intent=intent,
                method=ClassificationMethod.RULE,
                confidence=confidence,
            )

        # ── Step 2: Gemini fallback ────────────
        logger.info("No rule matched → Gemini fallback (%s)...", self._cfg.model)
        return self._gemini_classify(text)

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

    # ──────────────────────────────────────────────────────────────────
    # PRIVATE — GEMINI FALLBACK
    # ──────────────────────────────────────────────────────────────────

    def _gemini_classify(self, text: str) -> IntentResult:
        """
        Classify using Gemini.
        Only called when rule-based fails (~10% of commands).
        """
        if not self._cfg.api_key:
            raise APIKeyMissingError()

        try:
            import google.generativeai as genai

            genai.configure(api_key=self._cfg.api_key)
            model = genai.GenerativeModel(self._cfg.model)

            response = model.generate_content(
                [
                    LLM_SYSTEM_PROMPT,
                    f"User command: {text}",
                ],
                generation_config=genai.GenerationConfig(
                    temperature=self._cfg.temperature,
                    max_output_tokens=self._cfg.max_tokens,
                ),
                request_options={"timeout": self._cfg.request_timeout},
            )

            raw = ((getattr(response, "text", "") or "").strip().upper())
            logger.debug("Gemini raw response: '%s'", raw)

            detected = next(
                (intent for intent in ALL_INTENTS if intent in raw),
                INTENT_UNKNOWN,
            )

            logger.info("Gemini → %s", detected)
            return IntentResult(
                text=text,
                intent=detected,
                method=ClassificationMethod.LLM,
                confidence=0.95,
            )

        except Exception as e:
            err = str(e).lower()
            if "deadline" in err or "timed out" in err or "timeout" in err:
                raise ClassificationTimeoutError(self._cfg.request_timeout)
            if "api" in err or "permission" in err or "quota" in err or "key" in err:
                raise APIRequestError(str(e))

            logger.error("Gemini classification failed: %s", e)
            return IntentResult(
                text=text,
                intent=INTENT_UNKNOWN,
                method=ClassificationMethod.LLM,
                confidence=0.0,
                error=str(e),
            )