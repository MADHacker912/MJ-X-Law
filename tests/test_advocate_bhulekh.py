from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from actions.advocate_bhulekh import (
    lookup_khatauni,
    open_bhulekh_portal,
    handle_bhulekh_action,
    UP_BHULEKH_URL,
)


class AdvocateBhulekhTests(unittest.TestCase):
    def test_missing_all_details(self):
        with tempfile.TemporaryDirectory() as td:
            temp_file = Path(td) / "active_bhulekh.json"
            with patch("actions.advocate_bhulekh.ACTIVE_BHULEKH_FILE", temp_file), \
                 patch("webbrowser.open") as mock_open:
                res = lookup_khatauni()
                self.assertEqual(res.get("status"), "missing_details")
                self.assertIn("जनपद (जिला)", res.get("missing_fields", []))
                self.assertIn("तहसील", res.get("missing_fields", []))
                self.assertIn("ग्राम (गांव)", res.get("missing_fields", []))
                mock_open.assert_called_with(UP_BHULEKH_URL)

    def test_partial_details_incremental(self):
        with tempfile.TemporaryDirectory() as td:
            temp_file = Path(td) / "active_bhulekh.json"
            with patch("actions.advocate_bhulekh.ACTIVE_BHULEKH_FILE", temp_file), \
                 patch("webbrowser.open"):
                # Step 1: User provides district
                res1 = lookup_khatauni(district="लखनऊ")
                self.assertEqual(res1.get("status"), "missing_details")
                self.assertNotIn("जनपद (जिला)", res1.get("missing_fields", []))
                self.assertIn("तहसील", res1.get("missing_fields", []))

                # Step 2: User provides tehsil
                res2 = lookup_khatauni(tehsil="सदर")
                self.assertEqual(res2.get("status"), "missing_details")
                self.assertNotIn("तहसील", res2.get("missing_fields", []))
                self.assertIn("ग्राम (गांव)", res2.get("missing_fields", []))

    def test_full_details_ready_for_captcha(self):
        with tempfile.TemporaryDirectory() as td:
            temp_file = Path(td) / "active_bhulekh.json"
            with patch("actions.advocate_bhulekh.ACTIVE_BHULEKH_FILE", temp_file), \
                 patch("webbrowser.open"):
                res = lookup_khatauni(
                    district="लखनऊ",
                    tehsil="सदर",
                    village="पिपरा",
                    search_by="gata",
                    search_value="142/2",
                )
                self.assertEqual(res.get("status"), "ready_for_captcha")
                self.assertIn("कैप्चा कोड", res.get("voice_prompt", ""))
                self.assertEqual(res.get("details", {}).get("district"), "लखनऊ")
                self.assertEqual(res.get("details", {}).get("search_value"), "142/2")

    def test_handle_bhulekh_action_open(self):
        with patch("webbrowser.open") as mock_open:
            res = handle_bhulekh_action("open_portal")
            self.assertEqual(res.get("status"), "success")
            mock_open.assert_called_with(UP_BHULEKH_URL)
