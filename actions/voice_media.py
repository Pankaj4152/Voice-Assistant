import logging
from typing import Any, Dict, Optional

logger = logging.getLogger(__name__)


class AIActions:
    """
    AI intent handler.
    This module intentionally does not call an LLM directly; it returns a
    structured result that downstream response/TTS layers can fulfill.
    """

    def handle(self, entities: Dict[str, Any], parsed_intent: Optional[Any] = None) -> Dict[str, Any]:
        query = (entities.get("query") or (getattr(parsed_intent, "text", "") if parsed_intent else "") or "").strip()
        action = (entities.get("action") or "general_query").strip()

        if not query:
            return {
                "success": False,
                "response_text": "No question provided.",
                "intent": getattr(parsed_intent, "intent", "AI") if parsed_intent else "AI",
                "entities": entities,
            }

        # Pass-through object: lets the caller decide how to generate an answer.
        return {
            "success": True,
            "response_text": query,
            "intent": getattr(parsed_intent, "intent", "AI") if parsed_intent else "AI",
            "entities": entities,
            "needs_ai": True,
            "ai_action": action,
        }
