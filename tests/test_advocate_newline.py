from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from actions.advocate_helper import clean_legal_text, create_legal_document
from actions.computer_control import _clean_input_text


class AdvocateNewlineTests(unittest.TestCase):
    def test_clean_legal_text_removes_slash_n(self):
        raw = "दिनांक: 19/09/2026 /n स्थान: कड़कड़डूमा कोर्ट"
        cleaned = clean_legal_text(raw)
        self.assertNotIn("/n", cleaned)
        self.assertNotIn("/ n", cleaned)
        self.assertIn("दिनांक: 19/09/2026\nस्थान: कड़कड़डूमा कोर्ट", cleaned)

    def test_clean_legal_text_removes_escaped_n(self):
        raw = "प्रार्थी \\n द्वारा अधिवक्ता"
        cleaned = clean_legal_text(raw)
        self.assertNotIn("\\n", cleaned)
        self.assertEqual(cleaned, "प्रार्थी\nद्वारा अधिवक्ता")

    def test_clean_input_text_computer_control(self):
        raw = "प्रथम पंक्ति /n द्वितीय पंक्ति \\n तृतीय पंक्ति"
        cleaned = _clean_input_text(raw)
        self.assertNotIn("/n", cleaned)
        self.assertNotIn("\\n", cleaned)
        self.assertEqual(cleaned, "प्रथम पंक्ति \n द्वितीय पंक्ति \n तृतीय पंक्ति")

    def test_multiline_legal_document(self):
        with tempfile.TemporaryDirectory() as td:
            with unittest.mock.patch("actions.advocate_helper._get_advocate_docs_dir", return_value=Path(td)):
                with unittest.mock.patch("actions.advocate_helper.open_document_in_editor", return_value="opened"):
                    res = create_legal_document(
                        doc_type="परीक्षण_आवेदन",
                        title="परीक्षण विषय",
                        court_name="न्यायालय महोदय",
                        parties="रमेश /n बनाम /n राज्य",
                        body_paragraphs=["प्रथम बिंदु /n विस्तृत विवरण", "द्वितीय बिंदु"],
                        prayer="प्रार्थना स्वीकार हो /n धन्यवाद",
                        advocate_info="प्रार्थी /n द्वारा अधिवक्ता",
                        date_place="दिनांक: 19/09/2026 /n स्थान: दिल्ली",
                    )
                    self.assertEqual(res.get("status"), "success")
                    doc_path = Path(res.get("file_path"))
                    self.assertTrue(doc_path.exists())

                    # Check that /n is not present in generated docx paragraphs/runs
                    if doc_path.suffix == ".docx":
                        import docx
                        doc = docx.Document(str(doc_path))
                        for p in doc.paragraphs:
                            for r in p.runs:
                                self.assertNotIn("/n", r.text)
                                self.assertNotIn("\\n", r.text)
