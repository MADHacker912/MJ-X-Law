import unittest
from unittest.mock import patch, MagicMock
from actions.computer_settings import computer_settings, restart_computer, shutdown_computer, ACTION_MAP
from actions.open_app import _normalize, open_app, _APP_ALIASES
from actions.computer_control import _focus_window


class TestRestartAndSoftwareControl(unittest.TestCase):

    def test_action_map_has_restart_aliases(self):
        for alias in ("restart", "reboot", "restart_computer", "restart_pc", "system_restart"):
            self.assertIn(alias, ACTION_MAP)
            self.assertEqual(ACTION_MAP[alias], restart_computer)

    def test_action_map_has_shutdown_aliases(self):
        for alias in ("shutdown", "shutdown_computer", "shutdown_pc", "poweroff"):
            self.assertIn(alias, ACTION_MAP)
            self.assertEqual(ACTION_MAP[alias], shutdown_computer)

    @patch("actions.computer_settings.subprocess.run")
    def test_computer_settings_direct_restart(self, mock_run):
        res = computer_settings({"action": "restart"})
        self.assertTrue("Restarting" in res or "Restart command sent" in res)
        mock_run.assert_called()

    @patch("actions.computer_settings.subprocess.run")
    def test_computer_settings_direct_reboot(self, mock_run):
        res = computer_settings({"action": "reboot"})
        self.assertTrue("Restarting" in res or "Restart command sent" in res)
        mock_run.assert_called()

    @patch("actions.computer_settings._OS", "Windows")
    @patch("actions.computer_settings.subprocess.run")
    def test_restart_computer_windows_flags(self, mock_run):
        mock_run.return_value = MagicMock(returncode=0)
        res = restart_computer()
        self.assertIn("Restarting", res)
        mock_run.assert_called()
        cmd = mock_run.call_args[0][0]
        self.assertIn("shutdown", cmd)
        self.assertIn("/r", cmd)
        self.assertIn("/f", cmd)
        self.assertIn("/t", cmd)

    def test_app_aliases_include_advocate_software(self):
        # WordPad
        self.assertIn("wordpad", _APP_ALIASES)
        self.assertEqual(_APP_ALIASES["wordpad"]["Windows"], "wordpad.exe")
        # Word
        self.assertIn("word", _APP_ALIASES)
        self.assertEqual(_APP_ALIASES["word"]["Windows"], "winword")
        # Excel
        self.assertIn("excel", _APP_ALIASES)
        self.assertEqual(_APP_ALIASES["excel"]["Windows"], "excel")
        # Acrobat / PDF
        self.assertIn("acrobat", _APP_ALIASES)
        self.assertEqual(_APP_ALIASES["acrobat"]["Windows"], "AcroRd32.exe")
        # Scanner
        self.assertIn("scanner", _APP_ALIASES)
        self.assertEqual(_APP_ALIASES["scanner"]["Windows"], "wfs.exe")
        # Control Panel
        self.assertIn("control panel", _APP_ALIASES)
        self.assertEqual(_APP_ALIASES["control panel"]["Windows"], "control.exe")

    @patch("actions.open_app._SYSTEM", "Windows")
    def test_normalize_aliases_windows(self):
        self.assertEqual(_normalize("wordpad"), "wordpad.exe")
        self.assertEqual(_normalize("word pad"), "wordpad.exe")
        self.assertEqual(_normalize("वर्डपैड"), "wordpad.exe")
        self.assertEqual(_normalize("word"), "winword")
        self.assertEqual(_normalize("ms word"), "winword")
        self.assertEqual(_normalize("adobe reader"), "AcroRd32.exe")
        self.assertEqual(_normalize("scanner"), "wfs.exe")
        self.assertEqual(_normalize("control panel"), "control.exe")

    @patch("actions.open_app._OS_LAUNCHERS")
    def test_open_app_dispatches_properly(self, mock_launchers):
        mock_launch = MagicMock(return_value=True)
        mock_launchers.get.return_value = mock_launch
        res = open_app({"app_name": "wordpad"})
        self.assertIn("Opened wordpad", res)
        mock_launch.assert_called()

    @patch("actions.computer_control._get_os", return_value="linux")
    @patch("actions.computer_control.subprocess.run")
    def test_focus_window_linux(self, mock_run, mock_os):
        mock_run.return_value = MagicMock(returncode=0)
        res = _focus_window("WordPad")
        self.assertIn("Focused window: WordPad", res)


if __name__ == "__main__":
    unittest.main()
