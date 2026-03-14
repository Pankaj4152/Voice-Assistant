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

    def test_volume_status_query(self):
        entities = self.parser._os("what is volume")
        self.assertEqual(entities.get("action"), "volume_status")
        self.assertEqual(entities.get("target"), "volume")

    def test_describe_screen_query(self):
        entities = self.parser._os("what is on screen")
        self.assertEqual(entities.get("action"), "describe_screen")
        self.assertEqual(entities.get("target"), "screen")

    def test_battery_status_query(self):
        entities = self.parser._os("what is battery status")
        self.assertEqual(entities.get("action"), "battery_status")
        self.assertEqual(entities.get("target"), "battery")

    def test_wifi_status_query(self):
        entities = self.parser._os("check wifi status")
        self.assertEqual(entities.get("action"), "wifi_status")
        self.assertEqual(entities.get("target"), "wifi")

    def test_network_status_query(self):
        entities = self.parser._os("am i online")
        self.assertEqual(entities.get("action"), "network_status")
        self.assertEqual(entities.get("target"), "network")

    def test_active_window_status_query(self):
        entities = self.parser._os("where am i")
        self.assertEqual(entities.get("action"), "active_window_status")
        self.assertEqual(entities.get("target"), "window")

    def test_date_time_status_query(self):
        entities = self.parser._os("what is the time now")
        self.assertEqual(entities.get("action"), "date_time_status")
        self.assertEqual(entities.get("target"), "datetime")

    def test_environment_summary_query(self):
        entities = self.parser._os("give me environment status report")
        self.assertEqual(entities.get("action"), "environment_summary")
        self.assertEqual(entities.get("target"), "environment")

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


class VoiceOSIntentPipelineTests(unittest.TestCase):
    def setUp(self):
        self.parser = IntentParser()

    def test_parse_routes_volume_status_to_os(self):
        parsed = self.parser.parse("what is volume")
        self.assertEqual(parsed.intent, "OS")
        self.assertEqual(parsed.entities.get("action"), "volume_status")

    def test_parse_routes_battery_status_to_os(self):
        parsed = self.parser.parse("what is battery status")
        self.assertEqual(parsed.intent, "OS")
        self.assertEqual(parsed.entities.get("action"), "battery_status")

    def test_parse_routes_screen_description_to_os(self):
        parsed = self.parser.parse("what is on screen")
        self.assertEqual(parsed.intent, "OS")
        self.assertEqual(parsed.entities.get("action"), "describe_screen")


if __name__ == "__main__":
    unittest.main()