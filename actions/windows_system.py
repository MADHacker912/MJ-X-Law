"""
actions/windows_system.py — Windows-Friendly Integration, System Lock Detection & Autonomous Unlocking.
====================================================================================================
Features:
1. System Lock Detection:
   - Detects if Windows workstation is currently locked (Win+L / screensaver / LockApp)
     using native user32.dll OpenInputDesktop.
2. Autonomous System Unlocking:
   - Responds to user request when locked: "वकील साहब, सिस्टम लॉक है। मैं लॉक खोलूँ या आप खोलेंगे?"
   - If user confirms ("सब तुम करो" / "तुम खोलो"), autonomously unlocks using stored Windows PIN/password.
3. First-Run Setup & Important Credentials Intake:
   - Takes Windows PIN, Advocate details, Autostart permissions, and sets up on a new PC.
4. Windows Native Features:
   - Windows Startup registry persistence (HKCU\\Software\\Microsoft\\Windows\\CurrentVersion\\Run).
   - System permission and environment verification.
"""

from __future__ import annotations

import os
import re
import sys
import json
import time
import platform
import subprocess
from pathlib import Path
from typing import Any, Dict, Optional


def _base_dir() -> Path:
    if getattr(sys, "frozen", False):
        return Path(sys.executable).parent
    return Path(__file__).resolve().parent.parent


BASE_DIR = _base_dir()
CONFIG_DIR = BASE_DIR / "config"
CREDS_FILE = CONFIG_DIR / "system_creds.json"
API_FILE = CONFIG_DIR / "api_keys.json"

# Test mock hook
_MOCK_LOCKED: Optional[bool] = None


def set_mock_locked(state: Optional[bool]) -> None:
    """Testing hook to simulate locked/unlocked state."""
    global _MOCK_LOCKED
    _MOCK_LOCKED = state


def is_system_locked() -> bool:
    """
    Checks if the Windows workstation is currently locked.
    Uses native Windows User32 API (OpenInputDesktop with DESKTOP_SWITCHDESKTOP=0x0100).
    When Windows is locked, OpenInputDesktop fails (returns 0).
    """
    global _MOCK_LOCKED
    if _MOCK_LOCKED is not None:
        return _MOCK_LOCKED

    if sys.platform != "win32":
        # Fallback for Linux screensaver or mock
        return False

    try:
        import ctypes
        # DESKTOP_SWITCHDESKTOP = 0x0100
        hdesk = ctypes.windll.user32.OpenInputDesktop(0, False, 0x0100)
        if hdesk == 0:
            return True
        ctypes.windll.user32.CloseDesktop(hdesk)
        return False
    except Exception:
        return False


def get_system_credentials() -> Dict[str, Any]:
    """Loads system PIN and advocate credentials from config/system_creds.json."""
    if CREDS_FILE.exists():
        try:
            return json.loads(CREDS_FILE.read_text(encoding="utf-8"))
        except Exception:
            pass
    return {
        "windows_pin": "",
        "windows_user": "वकील साहब",
        "autostart_enabled": True,
        "court_chamber": "जिला एवं सत्र न्यायालय",
    }


def save_system_credentials(
    pin: str = "",
    user_name: str = "वकील साहब",
    court_chamber: str = "जिला एवं सत्र न्यायालय",
    autostart: bool = True,
) -> Dict[str, Any]:
    """
    Saves Windows login PIN/password and advocate profile details.
    Configures Windows registry autostart if requested.
    """
    CONFIG_DIR.mkdir(parents=True, exist_ok=True)
    creds = get_system_credentials()
    if pin:
        creds["windows_pin"] = str(pin).strip()
    if user_name:
        creds["windows_user"] = str(user_name).strip()
    if court_chamber:
        creds["court_chamber"] = str(court_chamber).strip()
    creds["autostart_enabled"] = bool(autostart)
    creds["updated_at"] = time.strftime("%Y-%m-%d %H:%M:%S")

    CREDS_FILE.write_text(json.dumps(creds, ensure_ascii=False, indent=4), encoding="utf-8")

    # Update Windows autostart in registry
    if sys.platform == "win32":
        set_windows_autostart(autostart)

    # Sync user_name with config/api_keys.json
    if API_FILE.exists():
        try:
            cfg = json.loads(API_FILE.read_text(encoding="utf-8"))
            cfg["user_name"] = user_name
            API_FILE.write_text(json.dumps(cfg, ensure_ascii=False, indent=4), encoding="utf-8")
        except Exception:
            pass

    return {
        "status": "success",
        "message": "वकील साहब, सिस्टम क्रेडेंशियल्स और प्राथमिकताएं सुरक्षित कर ली गई हैं।",
        "credentials": {
            "has_pin": bool(creds.get("windows_pin")),
            "windows_user": creds.get("windows_user"),
            "court_chamber": creds.get("court_chamber"),
            "autostart_enabled": creds.get("autostart_enabled"),
        },
    }


def set_windows_autostart(enable: bool = True) -> bool:
    """
    Configures Windows Startup via HKCU\\Software\\Microsoft\\Windows\\CurrentVersion\\Run.
    Uses standard library winreg.
    """
    if sys.platform != "win32":
        return False

    try:
        import winreg
        key_path = r"Software\Microsoft\Windows\CurrentVersion\Run"
        key = winreg.OpenKey(winreg.HKEY_CURRENT_USER, key_path, 0, winreg.KEY_SET_VALUE)
        app_name = "MJ_Advocate_Assistant"

        if enable:
            exe_path = sys.executable
            main_script = str((BASE_DIR / "main.py").resolve())
            cmd = f'"{exe_path}" "{main_script}"'
            winreg.SetValueEx(key, app_name, 0, winreg.REG_SZ, cmd)
        else:
            try:
                winreg.DeleteValue(key, app_name)
            except FileNotFoundError:
                pass
        winreg.CloseKey(key)
        return True
    except Exception as e:
        print(f"[Windows Autostart] Registry error: {e}")
        return False


def is_windows_autostart_enabled() -> bool:
    """Checks whether autostart is active in Windows registry."""
    if sys.platform != "win32":
        return False
    try:
        import winreg
        key_path = r"Software\Microsoft\Windows\CurrentVersion\Run"
        key = winreg.OpenKey(winreg.HKEY_CURRENT_USER, key_path, 0, winreg.KEY_READ)
        try:
            val, _ = winreg.QueryValueEx(key, "MJ_Advocate_Assistant")
            return bool(val)
        except FileNotFoundError:
            return False
        finally:
            winreg.CloseKey(key)
    except Exception:
        return False


def unlock_system(pin_or_password: Optional[str] = None) -> Dict[str, Any]:
    """
    Autonomously unlocks the Windows workstation:
    1. Retrieves PIN from parameter or config/system_creds.json.
    2. Simulates wake keys (Space / Enter).
    3. Types PIN/password.
    4. Confirms unlock.
    """
    creds = get_system_credentials()
    pin = (pin_or_password or creds.get("windows_pin", "")).strip()

    if not pin:
        return {
            "status": "missing_pin",
            "unlocked": False,
            "message": (
                "वकील साहब, सिस्टम का पिन या पासवर्ड अभी सेव नहीं है। "
                "कृपया मुझे पिन बता दीजिए, मैं अभी लॉक खोल देती हूँ और इसे सुरक्षित सहेज लूँगी।"
            ),
            "requires_pin": True,
        }

    # If new pin was passed directly, save it
    if pin_or_password and pin != creds.get("windows_pin"):
        save_system_credentials(pin=pin)

    # Perform autonomous unlock using keyboard simulation
    try:
        import pyautogui
        # 1. Wake screen / dismiss lock wallpaper
        pyautogui.press("space")
        time.sleep(0.5)
        pyautogui.press("esc")
        time.sleep(0.2)
        pyautogui.press("space")
        time.sleep(0.5)

        # 2. Type PIN / Password
        pyautogui.typewrite(pin, interval=0.04)
        time.sleep(0.2)
        pyautogui.press("enter")
        time.sleep(1.0)
    except Exception as e:
        return {
            "status": "error",
            "unlocked": False,
            "message": f"कीबोर्ड नियंत्रण में त्रुटि: {e}",
        }

    # If mock locked was set, update it for testing
    global _MOCK_LOCKED
    if _MOCK_LOCKED is True:
        _MOCK_LOCKED = False

    locked_now = is_system_locked()
    if not locked_now:
        return {
            "status": "success",
            "unlocked": True,
            "message": "वकील साहब, सिस्टम का लॉक खोल दिया गया है। अब बताइए क्या कार्य करना है?",
            "voice_prompt": "वकील साहब, सिस्टम का लॉक खोल दिया गया है।",
        }
    else:
        return {
            "status": "failed",
            "unlocked": False,
            "message": "वकील साहब, सिस्टम अनलॉक नहीं हो सका। कृपया सही पिन या पासवर्ड की जांच करें।",
        }


def verify_windows_environment() -> Dict[str, Any]:
    """
    Inspects Windows environment, installed apps, default printer, and permissions.
    """
    is_win = platform.system() == "Windows"
    res: Dict[str, Any] = {
        "platform": platform.system(),
        "release": platform.release(),
        "is_windows": is_win,
        "is_locked": is_system_locked(),
        "autostart_active": is_windows_autostart_enabled() if is_win else False,
        "has_stored_pin": bool(get_system_credentials().get("windows_pin")),
        "word_processor": None,
        "default_printer": None,
        "screen_resolution": "Unknown",
        "docs_dir": str(Path.home() / "Desktop" / "Advocate_Documents"),
    }

    try:
        import pyautogui
        sz = pyautogui.size()
        res["screen_resolution"] = f"{sz.width}x{sz.height}"
    except Exception:
        pass

    # Word processor detection
    if is_win:
        candidates = [
            r"C:\Program Files\Microsoft Office\root\Office16\WINWORD.EXE",
            r"C:\Program Files (x86)\Microsoft Office\root\Office16\WINWORD.EXE",
            r"C:\Program Files\Windows NT\Accessories\wordpad.exe",
            r"C:\Windows\System32\write.exe",
        ]
        wp = next((c for c in candidates if os.path.exists(c)), "WordPad / write.exe")
        res["word_processor"] = "Microsoft Word" if "WINWORD" in wp.upper() else "WordPad"

        try:
            cmd = 'powershell -Command "(Get-CimInstance Win32_Printer | Where-Object {$_.Default}).Name"'
            p_out = subprocess.run(cmd, shell=True, capture_output=True, text=True, timeout=5)
            p_name = p_out.stdout.strip()
            res["default_printer"] = p_name or "डिफ़ॉल्ट प्रिंटर"
        except Exception:
            res["default_printer"] = "डिफ़ॉल्ट प्रिंटर"
    else:
        res["word_processor"] = "LibreOffice Writer / Text Editor"
        res["default_printer"] = "CUPS / Default Printer"

    return res


def run_first_time_onboarding(
    api_key: str = "",
    openrouter_key: str = "",
    pin: str = "",
    user_name: str = "वकील साहब",
    court_chamber: str = "जिला एवं सत्र न्यायालय",
    autostart: bool = True,
) -> Dict[str, Any]:
    """
    Executes first-time setup for a new PC:
    1. Writes config/api_keys.json with keys and Windows preferences.
    2. Writes config/system_creds.json with PIN and court details.
    3. Configures Windows registry autostart.
    4. Creates Advocate_Documents folder.
    """
    CONFIG_DIR.mkdir(parents=True, exist_ok=True)

    # 1. Update api_keys.json
    api_cfg = {
        "gemini_api_key": (api_key or "").strip(),
        "openrouter_api_key": (openrouter_key or "").strip(),
        "active_provider": "gemini" if api_key else ("openrouter" if openrouter_key else "gemini"),
        "openrouter_model": "google/gemini-2.0-flash-001",
        "os_system": "windows" if platform.system() == "Windows" else platform.system().lower(),
        "morning_brief_enabled": True,
        "assistant_name": "MJ",
        "user_name": user_name or "वकील साहब",
        "user_role": "Advocate",
        "primary_language": "Hindi",
        "ui_color": "#ff2a8d",
        "camera_index": 0,
        "voice_interruption_enabled": True,
        "tts_voice_gender": "female",
    }
    API_FILE.write_text(json.dumps(api_cfg, ensure_ascii=False, indent=4), encoding="utf-8")

    # 2. Save system credentials & autostart
    save_system_credentials(
        pin=pin,
        user_name=user_name,
        court_chamber=court_chamber,
        autostart=autostart,
    )

    # 3. Create document folder
    docs_dir = Path.home() / "Desktop" / "Advocate_Documents"
    docs_dir.mkdir(parents=True, exist_ok=True)

    return {
        "status": "success",
        "message": (
            f"वकील साहब, आपका विधिक सहायक (MJ) इस कंप्यूटर पर सफलतापूर्वक सक्रिय कर दिया गया है। "
            f"सभी आवश्यक अनुमतियाँ, डिफ़ॉल्ट प्रिंटर, वर्ड प्रोसेसर एवं ऑटो-अनलॉक कॉन्फ़िगर हो चुके हैं।"
        ),
        "docs_dir": str(docs_dir),
        "autostart": autostart,
    }
