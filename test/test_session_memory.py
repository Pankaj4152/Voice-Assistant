import unittest

from actions.action_engine import ActionEngine
from intent.models import ParsedIntent, ClassificationMethod


class _FakeOSActions:
    def __init__(self):
        self.calls = []

    def handle(self, entities, parsed_intent=None):
        self.calls.append(dict(entities))
        app = entities.get("app")
        if app == "notepad":
            return {"success": True, "response_text": f"Handled {app}"}
        return {"success": False, "response_text": "No app"}


class SessionMemoryTests(unittest.TestCase):
    def setUp(self):
        self.engine = ActionEngine()
        self.fake_os = _FakeOSActions()
        self.engine.os = self.fake_os

    def _parsed(self, text: str, intent: str, entities: dict):
        return ParsedIntent(
            text=text,
            intent=intent,
            method=ClassificationMethod.RULE,
            entities=entities,
            confidence=1.0,
            error=None,
        )

    def test_close_this_resolves_to_last_opened_app(self):
        first = self._parsed(
            text="open notepad",
            intent="OS",
            entities={"action": "launch", "app": "notepad"},
        )
        first_result = self.engine.execute(first)
        self.assertTrue(first_result["success"])

        follow_up = self._parsed(
            text="close this",
            intent="OS",
            entities={"action": "close", "app": "this"},
        )
        second_result = self.engine.execute(follow_up)

        self.assertTrue(second_result["success"])
        self.assertEqual(self.fake_os.calls[-1].get("app"), "notepad")

    def test_failed_action_does_not_overwrite_memory(self):
        success = self._parsed(
            text="open notepad",
            intent="OS",
            entities={"action": "launch", "app": "notepad"},
        )
        self.engine.execute(success)

        fail = self._parsed(
            text="open unknownthing",
            intent="OS",
            entities={"action": "launch", "app": "unknownthing"},
        )
        self.engine.execute(fail)

        follow_up = self._parsed(
            text="close this",
            intent="OS",
            entities={"action": "close"},
        )
        self.engine.execute(follow_up)

        self.assertEqual(self.fake_os.calls[-1].get("app"), "notepad")


if __name__ == "__main__":
    unittest.main()
