import json
import signal
import unittest
from unittest.mock import patch

import fkill


class FkillTests(unittest.TestCase):
    def sample_processes(self):
        return [
            fkill.Process(pid=101, ppid=1, user="localuser", cpu=2.5, mem=1.1, command="/Applications/Google Chrome.app/Contents/MacOS/Google Chrome"),
            fkill.Process(pid=102, ppid=1, user="localuser", cpu=0.3, mem=0.2, command="/usr/bin/python3 /tmp/tool.py"),
            fkill.Process(pid=103, ppid=101, user="localuser", cpu=1.0, mem=0.9, command="/Applications/Google Chrome Helper.app/Contents/MacOS/Google Chrome Helper"),
        ]

    def test_filters_processes_case_insensitively_by_query(self):
        matches = fkill.filter_processes(self.sample_processes(), "chrome")

        self.assertEqual([process.pid for process in matches], [101, 103])

    def test_filter_does_not_match_query_only_in_arguments(self):
        processes = self.sample_processes() + [
            fkill.Process(pid=104, ppid=1, user="localuser", cpu=0.0, mem=0.1, command="/usr/local/bin/extension-host chrome-extension://abcdef"),
        ]

        matches = fkill.filter_processes(processes, "chrome")

        self.assertEqual([process.pid for process in matches], [101, 103])

    def test_builds_script_filter_items_with_kill_all_first_for_query(self):
        output = json.loads(fkill.script_filter_json(self.sample_processes(), "chrome", current_pid=999))

        self.assertEqual(output["items"][0]["title"], "Force kill all matching processes: chrome")
        self.assertEqual(output["items"][0]["arg"], "query:chrome")
        self.assertEqual(output["items"][1]["arg"], "pid:101")
        self.assertEqual(output["items"][2]["arg"], "pid:103")

    def test_sorts_foreground_app_then_heavy_apps_then_background_processes(self):
        processes = [
            fkill.Process(pid=201, ppid=1, user="localuser", cpu=1.0, mem=2.0, command="/usr/sbin/syslogd"),
            fkill.Process(pid=202, ppid=1, user="localuser", cpu=9.0, mem=3.0, command="/Applications/Slack.app/Contents/MacOS/Slack"),
            fkill.Process(pid=203, ppid=1, user="localuser", cpu=0.5, mem=0.5, command="/Applications/Notes.app/Contents/MacOS/Notes"),
            fkill.Process(pid=204, ppid=1, user="localuser", cpu=7.0, mem=8.0, command="/usr/local/bin/worker"),
            fkill.Process(pid=205, ppid=1, user="localuser", cpu=0.1, mem=0.2, command="/Applications/Notes.app/Contents/Frameworks/Notes Helper.app/Contents/MacOS/Notes Helper"),
            fkill.Process(pid=206, ppid=1, user="localuser", cpu=30.0, mem=4.0, command="/Applications/Arc.app/Contents/Frameworks/Arc Helper (Renderer).app/Contents/MacOS/Arc Helper (Renderer)"),
            fkill.Process(pid=207, ppid=1, user="localuser", cpu=40.0, mem=4.0, command="/System/Library/CoreServices/ControlCenter.app/Contents/MacOS/ControlCenter"),
            fkill.Process(pid=209, ppid=1, user="localuser", cpu=4.0, mem=1.0, command="/Applications/Surge.app/Contents/MacOS/Surge"),
        ]

        ordered = fkill.sort_processes(processes, foreground_app="Notes", visible_apps={"Notes", "Slack"})

        self.assertEqual([process.pid for process in ordered], [203, 202, 209, 207, 206, 204, 201, 205])

    def test_nested_helper_app_is_not_a_primary_app_process(self):
        helper = fkill.Process(
            pid=206,
            ppid=1,
            user="localuser",
            cpu=30.0,
            mem=4.0,
            command="/Applications/Arc.app/Contents/Frameworks/Arc Helper (Renderer).app/Contents/MacOS/Arc Helper (Renderer)",
        )

        self.assertFalse(helper.is_primary_app_process)

    def test_outer_app_framework_helper_is_not_a_primary_app_process(self):
        helper = fkill.Process(
            pid=207,
            ppid=1,
            user="localuser",
            cpu=0.0,
            mem=0.0,
            command="/Applications/Codex.app/Contents/Frameworks/Codex Framework.framework/Versions/149.0/Helpers/browser_crashpad_handler",
        )

        self.assertFalse(helper.is_primary_app_process)

    def test_app_prefixed_helper_executable_is_not_a_primary_app_process(self):
        helper = fkill.Process(
            pid=208,
            ppid=1,
            user="localuser",
            cpu=0.0,
            mem=0.0,
            command="/Applications/codeg.app/Contents/MacOS/codeg-mcp --parent-pid 123",
        )

        self.assertFalse(helper.is_primary_app_process)

    def test_script_filter_uses_foreground_app_for_empty_query_sorting(self):
        processes = [
            fkill.Process(pid=201, ppid=1, user="localuser", cpu=1.0, mem=2.0, command="/usr/sbin/syslogd"),
            fkill.Process(pid=202, ppid=1, user="localuser", cpu=9.0, mem=3.0, command="/Applications/Slack.app/Contents/MacOS/Slack"),
            fkill.Process(pid=203, ppid=1, user="localuser", cpu=0.5, mem=0.5, command="/Applications/Notes.app/Contents/MacOS/Notes"),
        ]

        output = json.loads(
            fkill.script_filter_json(
                processes,
                "",
                current_pid=999,
                foreground_app="Notes",
                visible_apps={"Notes", "Slack"},
            )
        )

        self.assertEqual([item["arg"] for item in output["items"][:3]], ["pid:203", "pid:202", "pid:201"])

    def test_script_filter_omits_current_process_and_pid_one(self):
        processes = self.sample_processes() + [
            fkill.Process(pid=1, ppid=0, user="root", cpu=0.0, mem=0.0, command="/sbin/launchd"),
            fkill.Process(pid=999, ppid=1, user="localuser", cpu=0.0, mem=0.0, command="python fkill.py"),
        ]

        output = json.loads(fkill.script_filter_json(processes, "", current_pid=999))
        args = [item["arg"] for item in output["items"]]

        self.assertNotIn("pid:1", args)
        self.assertNotIn("pid:999", args)

    def test_script_filter_omits_parent_wrapper_process(self):
        processes = self.sample_processes() + [
            fkill.Process(pid=998, ppid=1, user="localuser", cpu=0.0, mem=0.0, command="/bin/zsh -lc ./fkill.py filter chrome"),
            fkill.Process(pid=999, ppid=998, user="localuser", cpu=0.0, mem=0.0, command="python3 ./fkill.py filter chrome"),
        ]

        output = json.loads(fkill.script_filter_json(processes, "chrome", current_pid=999))
        args = [item["arg"] for item in output["items"]]

        self.assertNotIn("pid:998", args)
        self.assertNotIn("pid:999", args)

    def test_kill_selection_force_kills_single_pid(self):
        with patch("fkill.os.kill") as kill:
            message = fkill.kill_selection("pid:101", self.sample_processes())

        kill.assert_called_once_with(101, signal.SIGKILL)
        self.assertEqual(message, "Killed PID 101")

    def test_kill_selection_force_kills_all_matching_processes(self):
        with patch("fkill.os.kill") as kill:
            message = fkill.kill_selection("query:chrome", self.sample_processes())

        self.assertEqual(
            [call.args for call in kill.call_args_list],
            [(101, signal.SIGKILL), (103, signal.SIGKILL)],
        )
        self.assertEqual(message, "Killed 2 matching processes for 'chrome'")


if __name__ == "__main__":
    unittest.main()
