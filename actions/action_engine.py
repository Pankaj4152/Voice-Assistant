from intent.constants import (
    INTENT_BROWSER,
    INTENT_OS,
    INTENT_DOCS,
    INTENT_AI,
)
from .security_layer import SecurityLayer
from .voice_browser import BrowserActions
from .voice_os import OSActions
from .voice_files import FileActions
from .voice_media import AIActions
from .session_memory import SessionMemory
from tts_engine import speak

class ActionEngine:

    def __init__(self, auto_speak: bool = True):

        self.browser = BrowserActions()
        self.os = OSActions()
        self.files = FileActions()
        self.ai = AIActions()
        self.session_memory = SessionMemory()
        self.security = SecurityLayer()
        self.auto_speak = auto_speak

    def execute(self, parsed_intent):

        intent = parsed_intent.intent
        entities = self.session_memory.resolve(parsed_intent, parsed_intent.entities)
        parsed_intent.entities = entities

        security_result = self.security.check(parsed_intent)

        if not security_result["allowed"]:
            result = {
                "success": False,
                "response_text": "Sorry, this command is not allowed for security reasons.",
                "intent": intent,
                "entities": entities,
            }

        elif intent == INTENT_BROWSER:
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

        if self.auto_speak and result.get("response_text") and isinstance(result["response_text"], str):
            speak(result["response_text"])

        return result