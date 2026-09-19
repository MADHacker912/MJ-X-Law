from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from actions.windows_system import (
    is_system_locked,
    set_mock_locked,
    unlock_system,
    save_system_credentials,
    get_system_credentials,
    verify_windows_environment,
    run_first_time_onboarding,
)


class WindowsSystemTests(unittest.TestCase):
    def setUp(self):
        set_mock_locked(None)

    def tearDown(self):
        set_mock_locked(None)

    def test_lock_detection_mock(self):
        set_mock_locked(True)
        self.assertTrue(is_system_locked())

        set_mock_locked(False)
        self.assertFalse(is_system_locked())

    def test_unlock_missing_pin(self):
        with patch("actions.windows_system.get_system_credentials", return_value={"windows_pin": ""}):
            res = unlock_system(pin_or_password="")
            self.assertEqual(res.get("status"), "missing_pin")
            self.assertFalse(res.get("unlocked"))
            self.assertIn("पिन या पासवर्ड", res.get("message", ""))

    def test_unlock_with_pin_mock(self):
        set_mock_locked(True)
        mock_pyautogui = unittest.mock.MagicMock()
        with patch.dict("sys.modules", {"pyautogui": mock_pyautogui}):
            res = unlock_system(pin_or_password="1234")
            self.assertEqual(res.get("status"), "success")
            self.assertTrue(res.get("unlocked"))
            self.assertFalse(is_system_locked())

    def test_credentials_save_and_get(self):
        with tempfile.TemporaryDirectory() as td:
            temp_creds = Path(td) / "creds.json"
            temp_api = Path(td) / "api.json"
            with patch("actions.windows_system.CREDS_FILE", temp_creds), \
                 patch("actions.windows_system.API_FILE", temp_api), \
                 patch("actions.windows_system.CONFIG_DIR", Path(td)):
                save_system_credentials(
                    pin="9999",
                    user_name="वरिष्ठ अधिवक्ता",
                    court_chamber="उच्च न्यायालय",
                    autostart=False,
                )
                creds = get_system_credentials()
                self.assertEqual(creds.get("windows_pin"), "9999")
                self.assertEqual(creds.get("windows_user"), "वरिष्ठ अधिवक्ता")
                self.assertEqual(creds.get("court_chamber"), "उच्च न्यायालय")
                self.assertFalse(creds.get("autostart_enabled"))

    def test_verify_windows_environment(self):
        env = verify_windows_environment()
        self.assertIn("is_locked", env)
        self.assertIn("docs_dir", env)
        self.assertIn("word_processor", env)
        self.assertIn("default_printer", env)

    def test_first_time_onboarding(self):
        with tempfile.TemporaryDirectory() as td:
            temp_api = Path(td) / "api.json"
            temp_creds = Path(td) / "creds.json"
            with patch("actions.windows_system.CONFIG_DIR", Path(td)), \
                 patch("actions.windows_system.API_FILE", temp_api), \
                 patch("actions.windows_system.CREDS_FILE", temp_creds):
                res = run_first_time_onboarding(
                    api_key="AIzaSyTestKey123",
                    openrouter_key="",
                    pin="4321",
                    user_name="वकील साहब",
                    court_chamber="सत्र न्यायालय",
                    autostart=True,
                )
                self.assertEqual(res.get("status"), "success")
                self.assertTrue(temp_api.exists())
                api_data = json.loads(temp_api.read_text(encoding="utf-8"))
                self.assertEqual(api_data.get("gemini_api_key"), "AIzaSyTestKey123")
                self.assertEqual(api_data.get("user_name"), "वकील साहब")
