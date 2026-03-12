import unittest

from intent.parser import IntentParser


class VoiceOSIntentExtractionTests(unittest.TestCase):
    def setUp(self):
        self.parser = IntentParser()

    def test_switch_window_action(self):
        entities = self.parser._os("switch window")
        self.assertEqual(entities.get("action"), "switch_window")

    def test_switch_to_named_app_action(self):
        entities = self.parser._os("switch to notepad")
        self.assertEqual(entities.get("action"), "switch_app")
        self.assertEqual(entities.get("app"), "notepad")

    def test_close_this_window_action(self):
        entities = self.parser._os("close this window")
        self.assertEqual(entities.get("action"), "close_window")

    def test_show_desktop_action(self):
        entities = self.parser._os("show desktop")
        self.assertEqual(entities.get("action"), "show_desktop")

    def test_new_desktop_action(self):
        entities = self.parser._os("create new desktop")
        self.assertEqual(entities.get("action"), "new_desktop")

    def test_copy_file_not_misparsed_as_clipboard_copy(self):
        entities = self.parser._os("copy file to downloads")
        self.assertEqual(entities.get("action"), "copy_file")

    def test_switch_to_tab_with_index(self):
        entities = self.parser._browser("switch to tab 3")
        self.assertEqual(entities.get("action"), "switch_tab")
        self.assertEqual(entities.get("tab_index"), 3)


if __name__ == "__main__":
    unittest.main()