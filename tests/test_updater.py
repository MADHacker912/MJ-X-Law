from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch, MagicMock

from core.updater import (
    backup_user_state,
    restore_user_state,
    check_and_apply_updates,
    REMOTE_URL,
)


class UpdaterTests(unittest.TestCase):
    def test_backup_and_restore_user_state(self):
        with tempfile.TemporaryDirectory() as td:
            temp_config = Path(td) / "config"
            temp_memory = Path(td) / "memory"
            temp_backup = temp_memory / "backups" / "pre_update_user_data"
            temp_config.mkdir(parents=True, exist_ok=True)
            temp_memory.mkdir(parents=True, exist_ok=True)

            # Create sensitive user files
            api_file = temp_config / "api_keys.json"
            api_file.write_text(json.dumps({"gemini_api_key": "SECRET_KEY_123"}), encoding="utf-8")

            creds_file = temp_config / "system_creds.json"
            creds_file.write_text(json.dumps({"windows_pin": "5555"}), encoding="utf-8")

            cases_file = temp_memory / "advocate_cases.json"
            cases_file.write_text(json.dumps({"cases": [{"id": 1, "parties": "Ramesh vs State"}]}), encoding="utf-8")

            with patch("core.updater.CONFIG_DIR", temp_config), \
                 patch("core.updater.MEMORY_DIR", temp_memory), \
                 patch("core.updater.BACKUP_DIR", temp_backup):
                # 1. Take backup
                cache = backup_user_state()
                self.assertIn("api_keys.json", cache["configs"])
                self.assertIn("SECRET_KEY_123", cache["configs"]["api_keys.json"])
                self.assertIn("5555", cache["configs"]["system_creds.json"])
                self.assertIn("Ramesh vs State", cache["memories"]["advocate_cases.json"])

                # 2. Simulate git pull overwriting files with default repo templates
                api_file.write_text(json.dumps({"gemini_api_key": ""}), encoding="utf-8")
                creds_file.write_text(json.dumps({"windows_pin": ""}), encoding="utf-8")
                cases_file.write_text(json.dumps({"cases": []}), encoding="utf-8")

                # 3. Restore user state
                restore_user_state(cache)

                # 4. Verify user keys & memories are 100% recovered
                restored_api = json.loads(api_file.read_text(encoding="utf-8"))
                restored_creds = json.loads(creds_file.read_text(encoding="utf-8"))
                restored_cases = json.loads(cases_file.read_text(encoding="utf-8"))

                self.assertEqual(restored_api.get("gemini_api_key"), "SECRET_KEY_123")
                self.assertEqual(restored_creds.get("windows_pin"), "5555")
                self.assertEqual(len(restored_cases.get("cases", [])), 1)

    def test_check_and_apply_updates_up_to_date(self):
        with patch("core.updater._run_git") as mock_git:
            # git remote -v
            mock_git.side_effect = [
                MagicMock(returncode=0, stdout=f"origin {REMOTE_URL} (fetch)"),  # remote -v
                MagicMock(returncode=0, stdout=""),                               # fetch
                MagicMock(returncode=0, stdout="0\n"),                            # rev-list count = 0
            ]
            res = check_and_apply_updates()
            self.assertEqual(res.get("status"), "up_to_date")
            self.assertFalse(res.get("updated"))
            self.assertIn("नवीनतम संस्करण", res.get("message", ""))
