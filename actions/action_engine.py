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
from .session_memory import SessionMemory


class ActionEngine:

    def __init__(self):

        self.browser = BrowserActions()
        self.os = OSActions()
        self.files = FileActions()
        self.ai = AIActions()
        self.session_memory = SessionMemory()

    def execute(self, parsed_intent):

        intent = parsed_intent.intent
        entities = self.session_memory.resolve(parsed_intent, parsed_intent.entities)
        parsed_intent.entities = entities

        if intent == INTENT_BROWSER:
            result = self.browser.handle(entities, parsed_intent=parsed_intent)

        elif intent == INTENT_OS:
            result = self.os.handle(entities, parsed_intent=parsed_intent)

        elif intent == INTENT_DOCS:
            result = self.files.handle(entities, parsed_intent=parsed_intent)

        elif intent == INTENT_AI:
            result = self.ai.handle(entities, parsed_intent=parsed_intent)

        else:
            result = {
                "success": False,
                "response_text": "No handler for this intent",
                "intent": intent,
                "entities": entities,
            }

        self.session_memory.remember(parsed_intent, entities, result)
        return result