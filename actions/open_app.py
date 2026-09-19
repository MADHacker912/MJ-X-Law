import time
import subprocess
import platform
import shutil

try:
    import psutil
    _PSUTIL = True
except ImportError:
    _PSUTIL = False

_SYSTEM = platform.system()

_APP_ALIASES: dict[str, dict[str, str]] = {
    # Web Browsers
    "chrome":             {"Windows": "chrome",                  "Darwin": "Google Chrome",        "Linux": "google-chrome"},
    "google chrome":      {"Windows": "chrome",                  "Darwin": "Google Chrome",        "Linux": "google-chrome"},
    "firefox":            {"Windows": "firefox",                 "Darwin": "Firefox",              "Linux": "firefox"},
    "edge":               {"Windows": "msedge",                  "Darwin": "Microsoft Edge",       "Linux": "microsoft-edge"},
    "ms edge":            {"Windows": "msedge",                  "Darwin": "Microsoft Edge",       "Linux": "microsoft-edge"},
    "microsoft edge":     {"Windows": "msedge",                  "Darwin": "Microsoft Edge",       "Linux": "microsoft-edge"},
    "brave":              {"Windows": "brave",                   "Darwin": "Brave Browser",        "Linux": "brave-browser"},
    "browser":            {"Windows": "msedge",                  "Darwin": "Safari",               "Linux": "google-chrome"},
    "internet":           {"Windows": "msedge",                  "Darwin": "Safari",               "Linux": "google-chrome"},
    "safari":             {"Windows": "msedge",                  "Darwin": "Safari",               "Linux": "firefox"},
    "opera":              {"Windows": "opera",                   "Darwin": "Opera",                "Linux": "opera"},

    # Office & Document Editors
    "wordpad":            {"Windows": "wordpad.exe",             "Darwin": "TextEdit",             "Linux": "gedit"},
    "word pad":           {"Windows": "wordpad.exe",             "Darwin": "TextEdit",             "Linux": "gedit"},
    "वर्डपैड":             {"Windows": "wordpad.exe",             "Darwin": "TextEdit",             "Linux": "gedit"},
    "word":               {"Windows": "winword",                 "Darwin": "Microsoft Word",       "Linux": "libreoffice --writer"},
    "ms word":            {"Windows": "winword",                 "Darwin": "Microsoft Word",       "Linux": "libreoffice --writer"},
    "microsoft word":     {"Windows": "winword",                 "Darwin": "Microsoft Word",       "Linux": "libreoffice --writer"},
    "excel":              {"Windows": "excel",                   "Darwin": "Microsoft Excel",      "Linux": "libreoffice --calc"},
    "ms excel":           {"Windows": "excel",                   "Darwin": "Microsoft Excel",      "Linux": "libreoffice --calc"},
    "powerpoint":         {"Windows": "powerpnt",                "Darwin": "Microsoft PowerPoint", "Linux": "libreoffice --impress"},
    "ppt":                {"Windows": "powerpnt",                "Darwin": "Microsoft PowerPoint", "Linux": "libreoffice --impress"},
    "libreoffice":        {"Windows": "soffice",                 "Darwin": "LibreOffice",          "Linux": "libreoffice"},
    "notepad":            {"Windows": "notepad.exe",             "Darwin": "TextEdit",             "Linux": "gedit"},
    "textedit":           {"Windows": "notepad.exe",             "Darwin": "TextEdit",             "Linux": "gedit"},

    # PDF & Scanning
    "acrobat":            {"Windows": "AcroRd32.exe",            "Darwin": "Adobe Acrobat Reader", "Linux": "evince"},
    "adobe":              {"Windows": "AcroRd32.exe",            "Darwin": "Adobe Acrobat Reader", "Linux": "evince"},
    "adobe reader":       {"Windows": "AcroRd32.exe",            "Darwin": "Adobe Acrobat Reader", "Linux": "evince"},
    "pdf reader":         {"Windows": "AcroRd32.exe",            "Darwin": "Adobe Acrobat Reader", "Linux": "evince"},
    "pdf":                {"Windows": "msedge",                  "Darwin": "Preview",              "Linux": "evince"},
    "scanner":            {"Windows": "wfs.exe",                 "Darwin": "Image Capture",        "Linux": "simple-scan"},
    "scan":               {"Windows": "wfs.exe",                 "Darwin": "Image Capture",        "Linux": "simple-scan"},

    # Windows System Tools & Utilities
    "explorer":           {"Windows": "explorer.exe",            "Darwin": "Finder",               "Linux": "nautilus"},
    "file explorer":      {"Windows": "explorer.exe",            "Darwin": "Finder",               "Linux": "nautilus"},
    "files":              {"Windows": "explorer.exe",            "Darwin": "Finder",               "Linux": "nautilus"},
    "finder":             {"Windows": "explorer.exe",            "Darwin": "Finder",               "Linux": "nautilus"},
    "downloads":          {"Windows": "explorer.exe shell:Downloads", "Darwin": "open ~/Downloads","Linux": "xdg-open ~/Downloads"},
    "documents":          {"Windows": "explorer.exe shell:Personal",  "Darwin": "open ~/Documents", "Linux": "xdg-open ~/Documents"},
    "my computer":        {"Windows": "explorer.exe shell:MyComputerFolder", "Darwin": "open /",    "Linux": "nautilus"},
    "this pc":            {"Windows": "explorer.exe shell:MyComputerFolder", "Darwin": "open /",    "Linux": "nautilus"},
    "control panel":      {"Windows": "control.exe",             "Darwin": "System Preferences",   "Linux": "gnome-control-center"},
    "control":            {"Windows": "control.exe",             "Darwin": "System Preferences",   "Linux": "gnome-control-center"},
    "task manager":       {"Windows": "taskmgr.exe",             "Darwin": "Activity Monitor",     "Linux": "gnome-system-monitor"},
    "settings":           {"Windows": "ms-settings:",            "Darwin": "System Preferences",   "Linux": "gnome-control-center"},
    "calculator":         {"Windows": "calc.exe",                "Darwin": "Calculator",           "Linux": "gnome-calculator"},
    "calc":               {"Windows": "calc.exe",                "Darwin": "Calculator",           "Linux": "gnome-calculator"},
    "paint":              {"Windows": "mspaint.exe",             "Darwin": "Preview",              "Linux": "gimp"},
    "printer":            {"Windows": "control printers",        "Darwin": "System Preferences",   "Linux": "system-config-printer"},
    "printers":           {"Windows": "control printers",        "Darwin": "System Preferences",   "Linux": "system-config-printer"},
    "device manager":     {"Windows": "devmgmt.msc",             "Darwin": "System Information",   "Linux": "hardinfo"},
    "camera":             {"Windows": "microsoft.windows.camera:","Darwin": "Photo Booth",         "Linux": "cheese"},

    # Communication & Remote
    "whatsapp":           {"Windows": "WhatsApp",                "Darwin": "WhatsApp",             "Linux": "whatsapp"},
    "telegram":           {"Windows": "Telegram",                "Darwin": "Telegram",             "Linux": "telegram"},
    "zoom":               {"Windows": "Zoom",                    "Darwin": "zoom.us",              "Linux": "zoom"},
    "teams":              {"Windows": "msteams",                 "Darwin": "Microsoft Teams",      "Linux": "teams"},
    "skype":              {"Windows": "skype",                   "Darwin": "Skype",                "Linux": "skype"},
    "anydesk":            {"Windows": "AnyDesk",                 "Darwin": "AnyDesk",              "Linux": "anydesk"},
    "teamviewer":         {"Windows": "TeamViewer",              "Darwin": "TeamViewer",           "Linux": "teamviewer"},
    "spotify":            {"Windows": "Spotify",                 "Darwin": "Spotify",              "Linux": "spotify"},
    "vlc":                {"Windows": "vlc",                     "Darwin": "VLC",                  "Linux": "vlc"},
}


def _normalize(raw: str) -> str:
    key = raw.lower().strip()

    if key in _APP_ALIASES:
        return _APP_ALIASES[key].get(_SYSTEM, raw)

    for alias_key, os_map in _APP_ALIASES.items():
        if alias_key in key or key in alias_key:
            return os_map.get(_SYSTEM, raw)

    return raw  

def _launch_windows(app_name: str) -> bool:
    import os

    # 1. Direct execution with arguments (e.g. "explorer.exe shell:Downloads" or "control printers")
    if " " in app_name and not os.path.exists(app_name):
        try:
            subprocess.Popen(app_name, shell=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            time.sleep(1.0)
            return True
        except Exception:
            pass

    clean_target = app_name.split()[0] if " " in app_name else app_name

    # 2. Executable in PATH
    if shutil.which(clean_target) or shutil.which(f"{clean_target}.exe"):
        try:
            subprocess.Popen(app_name, shell=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            time.sleep(1.0)
            return True
        except Exception as e:
            print(f"[open_app] subprocess failed: {e}")

    # 3. URI Scheme / Windows protocol (e.g. ms-settings:, microsoft.windows.camera:)
    if ":" in app_name and not os.path.isabs(app_name):
        try:
            subprocess.Popen(f'start "" "{app_name}"', shell=True)
            time.sleep(1.0)
            return True
        except Exception:
            pass

    # 4. Native os.startfile (Windows ShellExecuteEx - handles App Paths, protocols, registered apps)
    if hasattr(os, "startfile"):
        for target in [app_name, f"{clean_target}.exe"]:
            try:
                os.startfile(target)
                time.sleep(1.2)
                return True
            except Exception:
                pass

    # 5. Windows CMD 'start' command (searches App Paths in Registry)
    for cmd_target in [app_name, f"{clean_target}.exe"]:
        try:
            subprocess.Popen(f'start "" "{cmd_target}"', shell=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            time.sleep(1.2)
            return True
        except Exception:
            pass

    # 6. Search Windows Registry App Paths (HKCU & HKLM)
    try:
        import winreg
        for root in (winreg.HKEY_CURRENT_USER, winreg.HKEY_LOCAL_MACHINE):
            key_path = r"SOFTWARE\Microsoft\Windows\CurrentVersion\App Paths"
            try:
                with winreg.OpenKey(root, key_path) as base_key:
                    for ext in ["", ".exe"]:
                        try:
                            with winreg.OpenKey(base_key, f"{clean_target}{ext}") as app_key:
                                exe_path, _ = winreg.QueryValueEx(app_key, "")
                                if exe_path and os.path.exists(exe_path):
                                    subprocess.Popen(f'"{exe_path}"', shell=True)
                                    time.sleep(1.2)
                                    return True
                        except OSError:
                            continue
            except OSError:
                continue
    except Exception:
        pass

    # 7. Search standard Windows Program Directories (Accessories, Program Files, AppData)
    s_name = clean_target.lower().replace(".exe", "").strip()
    search_dirs = [
        r"C:\Program Files\Windows NT\Accessories", # WordPad
        os.environ.get("ProgramFiles", r"C:\Program Files"),
        os.environ.get("ProgramFiles(x86)", r"C:\Program Files (x86)"),
        os.path.join(os.environ.get("LOCALAPPDATA", ""), "Programs"),
        os.path.join(os.environ.get("APPDATA", ""), r"Microsoft\Windows\Start Menu\Programs"),
        r"C:\ProgramData\Microsoft\Windows\Start Menu\Programs",
    ]
    for sdir in search_dirs:
        if not sdir or not os.path.isdir(sdir):
            continue
        try:
            for root_p, _, files in os.walk(sdir):
                for f in files:
                    f_lower = f.lower()
                    if f_lower.endswith(".exe") and (f_lower == f"{s_name}.exe" or s_name in f_lower):
                        full_path = os.path.join(root_p, f)
                        subprocess.Popen(f'"{full_path}"', shell=True)
                        time.sleep(1.2)
                        return True
                    elif f_lower.endswith(".lnk") and s_name in f_lower:
                        full_path = os.path.join(root_p, f)
                        if hasattr(os, "startfile"):
                            os.startfile(full_path)
                            time.sleep(1.2)
                            return True
        except Exception:
            continue

    # 8. PowerShell Start-Process
    try:
        ps_cmd = f'Start-Process "{clean_target}"'
        res = subprocess.run(["powershell", "-NoProfile", "-NonInteractive", "-Command", ps_cmd], capture_output=True, timeout=4)
        if res.returncode == 0:
            time.sleep(1.2)
            return True
    except Exception:
        pass

    # 9. Last resort: Start Menu search via PyAutoGUI
    if _PYAUTOGUI:
        try:
            import pyautogui
            pyautogui.press("win")
            time.sleep(0.6)
            pyautogui.write(s_name, interval=0.03)
            time.sleep(0.8)
            pyautogui.press("enter")
            time.sleep(2.0)
            return True
        except Exception as e:
            print(f"[open_app] Start Menu search failed: {e}")

    return False


def _launch_macos(app_name: str) -> bool:

    try:
        result = subprocess.run(
            ["open", "-a", app_name],
            capture_output=True, timeout=8
        )
        if result.returncode == 0:
            time.sleep(1.0)
            return True
    except Exception:
        pass

    try:
        result = subprocess.run(
            ["open", "-a", f"{app_name}.app"],
            capture_output=True, timeout=8
        )
        if result.returncode == 0:
            time.sleep(1.0)
            return True
    except Exception:
        pass

    binary = shutil.which(app_name) or shutil.which(app_name.lower())
    if binary:
        try:
            subprocess.Popen(
                [binary],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL
            )
            time.sleep(1.0)
            return True
        except Exception:
            pass

    try:
        import pyautogui
        pyautogui.hotkey("command", "space")
        time.sleep(0.6)
        pyautogui.write(app_name, interval=0.05)
        time.sleep(0.8)
        pyautogui.press("enter")
        time.sleep(1.5)
        return True
    except Exception as e:
        print(f"[open_app] Spotlight failed: {e}")

    return False


_LINUX_TERMINAL_FALLBACKS = [
    "x-terminal-emulator", "gnome-terminal", "konsole", "xfce4-terminal",
    "xterm", "lxterminal", "mate-terminal", "tilix", "alacritty", "kitty",
]

def _launch_linux(app_name: str) -> bool:

    # terminal emulators: try common ones in order
    if app_name in ("x-terminal-emulator", "gnome-terminal", "terminal"):
        for term in _LINUX_TERMINAL_FALLBACKS:
            if shutil.which(term):
                try:
                    subprocess.Popen([term], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
                    time.sleep(1.0)
                    return True
                except Exception:
                    continue

    binary = (
        shutil.which(app_name) or
        shutil.which(app_name.lower()) or
        shutil.which(app_name.lower().replace(" ", "-")) or
        shutil.which(app_name.lower().replace(" ", "_"))
    )
    if binary:
        try:
            subprocess.Popen(
                [binary],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL
            )
            time.sleep(1.0)
            return True
        except Exception:
            pass

    try:
        subprocess.run(
            ["xdg-open", app_name],
            capture_output=True, timeout=5
        )
        return True
    except Exception:
        pass

    for desktop_name in [
        app_name.lower(),
        app_name.lower().replace(" ", "-"),
        app_name.lower().replace(" ", ""),
    ]:
        try:
            result = subprocess.run(
                ["gtk-launch", desktop_name],
                capture_output=True, timeout=5
            )
            if result.returncode == 0:
                return True
        except Exception:
            pass

    return False


def list_running_apps() -> str:
    apps = set()
    if _SYSTEM == "Linux":
        try:
            res = subprocess.run(['wmctrl', '-l'], capture_output=True, text=True, timeout=3)
            if res.returncode == 0:
                for line in res.stdout.strip().splitlines():
                    parts = line.split(None, 3)
                    if len(parts) >= 4:
                        title = parts[3].strip()
                        if title and title.lower() not in ("desktop", "n/a"):
                            apps.add(title)
        except Exception:
            pass

    if _PSUTIL:
        known_gui_apps = {
            'chrome': 'Google Chrome', 'google-chrome': 'Google Chrome', 'chromium': 'Chromium',
            'firefox': 'Firefox', 'code': 'VS Code', 'discord': 'Discord', 'spotify': 'Spotify',
            'vlc': 'VLC Media Player', 'gnome-terminal': 'Terminal', 'konsole': 'Terminal',
            'x-terminal-emulator': 'Terminal', 'slack': 'Slack', 'telegram-desktop': 'Telegram',
            'obsidian': 'Obsidian', 'blender': 'Blender', 'gimp': 'GIMP'
        }
        for proc in psutil.process_iter(['name']):
            try:
                pname = proc.info['name'].lower() if proc.info['name'] else ''
                for key, display in known_gui_apps.items():
                    if key in pname:
                        apps.add(display)
            except Exception:
                pass

    if not apps:
        return "Could not detect open GUI applications."
    return f"Currently open applications ({len(apps)} total):\n" + "\n".join(f"• {app}" for app in sorted(apps))


_OS_LAUNCHERS = {
    "Windows": _launch_windows,
    "Darwin":  _launch_macos,
    "Linux":   _launch_linux,
}

def open_app(
    parameters=None,
    response=None,
    player=None,
    session_memory=None,
) -> str:
    params   = parameters or {}
    action   = params.get("action", "").lower().strip()
    app_name = params.get("app_name", "").strip()

    if action == "list" or "list" in app_name.lower() or "open apps" in app_name.lower() or "running apps" in app_name.lower():
        return list_running_apps()

    if not app_name:
        return "No application name provided."

    launcher = _OS_LAUNCHERS.get(_SYSTEM)
    if launcher is None:
        return f"Unsupported operating system: {_SYSTEM}"

    normalized = _normalize(app_name)
    print(f"[open_app] Launching: '{app_name}' → '{normalized}' ({_SYSTEM})")

    if player:
        player.write_log(f"[open_app] {app_name}")

    try:
        if launcher(normalized):
            return f"Opened {app_name}."
        if normalized.lower() != app_name.lower():
            if launcher(app_name):
                return f"Opened {app_name}."
        return (
            f"Could not confirm that {app_name} launched. "
            f"It may still be loading, or it might not be installed."
        )
    except Exception as e:
        print(f"[open_app] Error: {e}")
        return f"Failed to open {app_name}: {e}"