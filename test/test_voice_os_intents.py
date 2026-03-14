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


class FileNavIntentExtractionTests(unittest.TestCase):
    def setUp(self):
        self.parser = IntentParser()

    def test_list_folder_downloads(self):
        e = self.parser._os("show files in downloads")
        self.assertEqual(e.get("action"), "list_folder")
        self.assertEqual(e.get("folder"), "downloads")

    def test_list_folder_desktop(self):
        e = self.parser._os("list desktop files")
        self.assertEqual(e.get("action"), "list_folder")
        self.assertEqual(e.get("folder"), "desktop")

    def test_list_folder_whats_in(self):
        e = self.parser._os("what's in documents")
        self.assertEqual(e.get("action"), "list_folder")
        self.assertEqual(e.get("folder"), "documents")

    def test_open_folder_downloads(self):
        e = self.parser._os("open downloads")
        self.assertEqual(e.get("action"), "open_folder")
        self.assertEqual(e.get("folder"), "downloads")

    def test_open_folder_navigate(self):
        e = self.parser._os("navigate to desktop")
        self.assertEqual(e.get("action"), "open_folder")
        self.assertEqual(e.get("folder"), "desktop")

    def test_find_file_by_name(self):
        e = self.parser._os("find report.txt")
        self.assertEqual(e.get("action"), "find_file")
        self.assertEqual(e.get("filename"), "report.txt")

    def test_find_file_where_is(self):
        e = self.parser._os("where is budget.xlsx")
        self.assertEqual(e.get("action"), "find_file")
        self.assertEqual(e.get("filename"), "budget.xlsx")

    def test_find_file_with_folder_phrase(self):
        e = self.parser._os("find report.txt on desktop")
        self.assertEqual(e.get("action"), "find_file")
        self.assertEqual(e.get("filename"), "report.txt")
        self.assertEqual(e.get("folder"), "desktop")

    def test_move_file_to_folder(self):
        e = self.parser._os("move report.txt to downloads")
        self.assertEqual(e.get("action"), "move_file")
        self.assertEqual(e.get("filename"), "report.txt")
        self.assertEqual(e.get("dest"), "downloads")

    def test_copy_file_to_folder(self):
        e = self.parser._os("copy budget.xlsx to desktop")
        self.assertEqual(e.get("action"), "copy_file")
        self.assertEqual(e.get("filename"), "budget.xlsx")
        self.assertEqual(e.get("dest"), "desktop")

    def test_rename_file(self):
        e = self.parser._os("rename report.txt to final.txt")
        self.assertEqual(e.get("action"), "rename_file")
        self.assertEqual(e.get("filename"), "report.txt")
        self.assertEqual(e.get("new_name"), "final.txt")

    def test_delete_file(self):
        e = self.parser._os("delete report.txt")
        self.assertEqual(e.get("action"), "delete_file")
        self.assertEqual(e.get("filename"), "report.txt")


class FileNavIntentPipelineTests(unittest.TestCase):
    def setUp(self):
        self.parser = IntentParser()

    def test_pipeline_list_folder(self):
        parsed = self.parser.parse("show files in downloads")
        self.assertEqual(parsed.intent, "OS")
        self.assertEqual(parsed.entities.get("action"), "list_folder")
        self.assertEqual(parsed.entities.get("folder"), "downloads")

    def test_pipeline_find_file(self):
        parsed = self.parser.parse("find report.txt")
        self.assertEqual(parsed.intent, "OS")
        self.assertEqual(parsed.entities.get("action"), "find_file")

    def test_pipeline_move_file(self):
        parsed = self.parser.parse("move notes.txt to desktop")
        self.assertEqual(parsed.intent, "OS")
        self.assertEqual(parsed.entities.get("action"), "move_file")
        self.assertEqual(parsed.entities.get("filename"), "notes.txt")
        self.assertEqual(parsed.entities.get("dest"), "desktop")

    def test_pipeline_rename_file(self):
        parsed = self.parser.parse("rename draft.txt to final.txt")
        self.assertEqual(parsed.intent, "OS")
        self.assertEqual(parsed.entities.get("action"), "rename_file")


if __name__ == "__main__":
    unittest.main()