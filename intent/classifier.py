"""
intent/classifier.py
─────────────────────
Hybrid Intent Classifier: Rule-Based → OpenAI GPT-4o-mini fallback

Pipeline:
    1. Rule-based  — regex pattern scoring, instant, free (handles ~90% commands)
    2. OpenAI fallback — GPT-4o-mini, only for ambiguous commands rules can't handle

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
    Step 2 → OpenAI GPT-4o-mini        (only if Step 1 fails)
    """

    def __init__(self):
        self._cfg = intent_config.openai
        self._clf_cfg = intent_config.classifier

        if not self._cfg.api_key:
            logger.warning(
                "OPENAI_API_KEY not found in environment. "
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

        # ── Step 2: OpenAI fallback ────────────
        logger.info("No rule matched → OpenAI fallback (gpt-4o-mini)...")
        return self._openai_classify(text)

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
    # PRIVATE — OPENAI FALLBACK
    # ──────────────────────────────────────────────────────────────────

    def _openai_classify(self, text: str) -> IntentResult:
        """
        Classify using OpenAI GPT-4o-mini.
        Only called when rule-based fails (~10% of commands).
        """
        if not self._cfg.api_key:
            raise APIKeyMissingError()

        try:
            from openai import OpenAI, APITimeoutError, APIStatusError

            client = OpenAI(
                api_key=self._cfg.api_key,
                timeout=self._cfg.request_timeout,
            )

            response = client.chat.completions.create(
                model=self._cfg.model,
                messages=[
                    {"role": "system", "content": LLM_SYSTEM_PROMPT},
                    {"role": "user",   "content": text},
                ],
                max_tokens=self._cfg.max_tokens,
                temperature=self._cfg.temperature,
            )

            raw = response.choices[0].message.content.strip().upper()
            logger.debug("OpenAI raw response: '%s'", raw)

            detected = next(
                (intent for intent in ALL_INTENTS if intent in raw),
                INTENT_UNKNOWN,
            )

            logger.info("OpenAI → %s", detected)
            return IntentResult(
                text=text,
                intent=detected,
                method=ClassificationMethod.LLM,
                confidence=0.95,
            )

        except APITimeoutError:
            raise ClassificationTimeoutError(self._cfg.request_timeout)

        except APIStatusError as e:
            raise APIRequestError(str(e))

        except Exception as e:
            logger.error("OpenAI classification failed: %s", e)
            return IntentResult(
                text=text,
                intent=INTENT_UNKNOWN,
                method=ClassificationMethod.LLM,
                confidence=0.0,
                error=str(e),
            )