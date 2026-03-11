from intent.constants import (
    INTENT_BROWSER,
    INTENT_OS,
    INTENT_DOCS,
    INTENT_AI,
)

from .voice_browser import BrowserActions
from .voice_os import OSActions
from .voice_files import FileActions
from .voice_media import AIActions


class ActionEngine:

    def __init__(self):

        self.browser = BrowserActions()
        self.os = OSActions()
        self.files = FileActions()
        self.ai = AIActions()

    def execute(self, parsed_intent):

        intent = parsed_intent.intent
        entities = parsed_intent.entities

        if intent == INTENT_BROWSER:
            return self.browser.handle(entities, parsed_intent=parsed_intent)

        elif intent == INTENT_OS:
            return self.os.handle(entities, parsed_intent=parsed_intent)

        elif intent == INTENT_DOCS:
            return self.files.handle(entities, parsed_intent=parsed_intent)

        elif intent == INTENT_AI:
            return self.ai.handle(entities, parsed_intent=parsed_intent)

        return {
            "success": False,
            "response_text": "No handler for this intent",
            "intent": intent,
            "entities": entities,
        }