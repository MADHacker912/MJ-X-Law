import os
import unittest

os.environ["QT_QPA_PLATFORM"] = "offscreen"
from PyQt6.QtWidgets import QApplication, QLineEdit
from ui import CustomizeOverlay


class TestCustomizeOverlayOpenRouter(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication([])

    def test_openrouter_field_initialization(self):
        ov = CustomizeOverlay(
            api_key="AIzaSy123456789012",
            openrouter_api_key="sk-or-v1-abcdef12345678",
        )
        self.assertEqual(ov._openrouter_input.text(), "sk-or-v1-abcdef12345678")
        self.assertEqual(ov._openrouter_input.echoMode(), QLineEdit.EchoMode.Password)

    def test_openrouter_visibility_toggle(self):
        ov = CustomizeOverlay()
        self.assertEqual(ov._openrouter_input.echoMode(), QLineEdit.EchoMode.Password)
        ov._or_toggle.setChecked(True)
        self.assertEqual(ov._openrouter_input.echoMode(), QLineEdit.EchoMode.Normal)
        self.assertEqual(ov._or_toggle.text(), "HIDE")
        ov._or_toggle.setChecked(False)
        self.assertEqual(ov._openrouter_input.echoMode(), QLineEdit.EchoMode.Password)
        self.assertEqual(ov._or_toggle.text(), "SHOW")

    def test_openrouter_saved_signal_emission(self):
        ov = CustomizeOverlay(
            assistant_name="MJ",
            user_name="वकील साहब",
            api_key="AIzaSy123456789012",
            openrouter_api_key="sk-or-v1-sample-token-123456",
        )
        captured = []
        ov.saved.connect(lambda *args: captured.append(args))
        ov._save()
        self.assertEqual(len(captured), 1)
        name, user, color, gemini_key, openrouter_key, voice = captured[0]
        self.assertEqual(name, "MJ")
        self.assertEqual(user, "वकील साहब")
        self.assertEqual(gemini_key, "AIzaSy123456789012")
        self.assertEqual(openrouter_key, "sk-or-v1-sample-token-123456")


if __name__ == "__main__":
    unittest.main()
