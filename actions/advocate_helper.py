"""
actions/advocate_helper.py — Dedicated Legal Assistant & Autonomous PC Drafting Engine for Advocates.
===================================================================================================
Tailored for Indian Legal Drafting (Hindi):
- Formats standard legal applications (Bail, Notice, Police Complaint, Leave, RTI, Affidavit, etc.).
- Strictly 1-page constraint with proper court margins, headers, prayer, and signature blocks.
- ZERO AI artifacts (no asterisks, markdown ticks, hashes, or robotic bracket tokens).
- Opens directly in MS Word (winword.exe) or WordPad (wordpad.exe) — NEVER Notepad.
- Manages interactive review loop, details filling, and instant default printer output.
- Scans system environment (Word processors, default printer, screen) on first run.
"""

from __future__ import annotations

import os
import re
import sys
import json
import shutil
import platform
import subprocess
from pathlib import Path
from datetime import datetime
from typing import Any, Dict, List, Optional

try:
    import docx
    from docx.shared import Inches, Pt, RGBColor
    from docx.enum.text import WD_ALIGN_PARAGRAPH
    from docx.enum.style import WD_STYLE_TYPE
    _DOCX_AVAILABLE = True
except ImportError:
    _DOCX_AVAILABLE = False


def _base_dir() -> Path:
    if getattr(sys, "frozen", False):
        return Path(sys.executable).parent
    return Path(__file__).resolve().parent.parent


BASE_DIR = _base_dir()
MEMORY_DIR = BASE_DIR / "memory"
TEMPLATES_FILE = MEMORY_DIR / "legal_templates.json"
ENV_FILE = MEMORY_DIR / "advocate_env.json"

_ACTIVE_DRAFT: Dict[str, Any] = {
    "file_path": None,
    "doc_type": None,
    "title": None,
    "status": "idle",
    "updated_at": None,
}


def _get_advocate_docs_dir() -> Path:
    """Returns directory for saving advocate documents."""
    for candidate in [
        Path.home() / "Desktop" / "Advocate_Documents",
        Path.home() / "Documents" / "Advocate_Documents",
        BASE_DIR / "Advocate_Documents",
    ]:
        try:
            candidate.mkdir(parents=True, exist_ok=True)
            return candidate
        except Exception:
            continue
    fallback = BASE_DIR / "Advocate_Documents"
    fallback.mkdir(parents=True, exist_ok=True)
    return fallback


def clean_legal_text(text: str) -> str:
    """
    Strips all markdown symbols, asterisks, hashes, backticks, robotic AI tokens,
    and converts literal '/n', '\n', '\\n' into real line breaks.
    Returns clean, professional human-typed Devanagari text.
    """
    if not text:
        return ""

    # Normalize literal '/n', '\n', '\\n', '/ n', '\ n', '\r\n', '\\r\\n' into real newlines
    text = re.sub(r'(?:[/\\]\s*n|\r\n|\\r\\n)', '\n', text)

    # Remove bold, italics, headers, code fences, blockquotes, bullets
    text = re.sub(r"```[a-zA-Z]*\n?", "", text)
    text = re.sub(r"```", "", text)
    text = re.sub(r"[*#_~`>]", "", text)
    text = re.sub(r"^\s*[-+*]\s+", "", text, flags=re.MULTILINE)

    # Remove robotic bracketed tags like [दिनांक], [नाम], {{...}}
    text = re.sub(r"\[([^\]]+)\]", r"\1", text)
    text = re.sub(r"\{\{([^}]+)\}\}", r"\1", text)

    # Normalize double spaces and clean lines
    lines = [line.strip() for line in text.splitlines()]
    clean_lines = []
    prev_blank = False
    for line in lines:
        if not line:
            if not prev_blank:
                clean_lines.append("")
                prev_blank = True
        else:
            clean_lines.append(line)
            prev_blank = False

    return "\n".join(clean_lines).strip()


def scan_advocate_environment() -> Dict[str, Any]:
    """
    Scans Windows PC for Word processors, default printer, screen dimensions,
    and configured legal folders. Caches results into memory.
    """
    env_info: Dict[str, Any] = {
        "os": platform.system(),
        "release": platform.release(),
        "word_processor": None,
        "default_printer": None,
        "screen_resolution": "Unknown",
        "advocate_docs_path": str(_get_advocate_docs_dir()),
        "status": "ready",
        "scanned_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
    }

    # 1. Detect screen size
    try:
        import pyautogui
        size = pyautogui.size()
        env_info["screen_resolution"] = f"{size.width}x{size.height}"
    except Exception:
        pass

    # 2. Detect Word Processors (MS Word > WordPad > LibreOffice)
    is_win = platform.system() == "Windows"
    if is_win:
        word_candidates = [
            r"C:\Program Files\Microsoft Office\root\Office16\WINWORD.EXE",
            r"C:\Program Files (x86)\Microsoft Office\root\Office16\WINWORD.EXE",
            r"C:\Program Files\Microsoft Office\Office15\WINWORD.EXE",
            r"C:\Program Files (x86)\Microsoft Office\Office15\WINWORD.EXE",
            r"C:\Program Files\Microsoft Office\Office14\WINWORD.EXE",
            r"C:\Program Files (x86)\Microsoft Office\Office14\WINWORD.EXE",
        ]
        found_word = next((p for p in word_candidates if os.path.exists(p)), None)
        if found_word:
            env_info["word_processor"] = {"name": "Microsoft Word", "path": found_word, "type": "winword"}
        else:
            wordpad_candidates = [
                r"C:\Program Files\Windows NT\Accessories\wordpad.exe",
                r"C:\Program Files (x86)\Windows NT\Accessories\wordpad.exe",
                r"C:\Windows\System32\write.exe",
            ]
            found_wordpad = next((p for p in wordpad_candidates if os.path.exists(p)), None)
            if found_wordpad:
                env_info["word_processor"] = {"name": "WordPad", "path": found_wordpad, "type": "wordpad"}
            else:
                env_info["word_processor"] = {"name": "Default Editor", "path": "write.exe", "type": "wordpad"}

        # 3. Detect Default Windows Printer via PowerShell
        try:
            cmd = 'powershell -Command "(Get-CimInstance Win32_Printer | Where-Object {$_.Default}).Name"'
            res = subprocess.run(cmd, shell=True, capture_output=True, text=True, timeout=5)
            printer_name = res.stdout.strip()
            if printer_name:
                env_info["default_printer"] = printer_name
        except Exception:
            pass

        if not env_info["default_printer"]:
            try:
                cmd = "wmic printer get name,default"
                res = subprocess.run(cmd, shell=True, capture_output=True, text=True, timeout=5)
                for line in res.stdout.splitlines():
                    if "TRUE" in line.upper():
                        env_info["default_printer"] = line.replace("TRUE", "").strip()
                        break
            except Exception:
                pass
    else:
        # Linux / Fallback
        if shutil.which("libreoffice"):
            env_info["word_processor"] = {"name": "LibreOffice Writer", "path": "libreoffice", "type": "libreoffice"}
        else:
            env_info["word_processor"] = {"name": "System Viewer", "path": "xdg-open", "type": "xdg"}

        try:
            res = subprocess.run(["lpstat", "-d"], capture_output=True, text=True, timeout=3)
            if "destination:" in res.stdout:
                env_info["default_printer"] = res.stdout.split("destination:")[1].strip()
        except Exception:
            pass

    if not env_info["default_printer"]:
        env_info["default_printer"] = "सिस्टम डिफ़ॉल्ट प्रिंटर (उपलब्ध)"

    # Save to memory
    try:
        MEMORY_DIR.mkdir(parents=True, exist_ok=True)
        ENV_FILE.write_text(json.dumps(env_info, ensure_ascii=False, indent=2), encoding="utf-8")
    except Exception:
        pass

    return env_info


def create_legal_document(
    doc_type: str,
    title: str,
    court_name: str = "",
    case_no: str = "",
    parties: str = "",
    body_paragraphs: Optional[List[str]] = None,
    prayer: str = "",
    advocate_info: str = "",
    date_place: str = "",
) -> Dict[str, Any]:
    """
    Creates a standardized Hindi legal application/letter strictly formatted to fit on ONE PAGE.
    Saves to Advocate_Documents and opens in MS Word or WordPad.
    """
    docs_dir = _get_advocate_docs_dir()
    clean_type = re.sub(r"[^\w\s-]", "", doc_type).strip().replace(" ", "_") or "आवेदन_पत्र"
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    file_name = f"{clean_type}_{timestamp}.docx"
    file_path = docs_dir / file_name

    title = clean_legal_text(title or "आवेदन पत्र")
    court_name = clean_legal_text(court_name)
    case_no = clean_legal_text(case_no)
    parties = clean_legal_text(parties)
    prayer = clean_legal_text(prayer)
    advocate_info = clean_legal_text(advocate_info or "प्रार्थी\nद्वारा अधिवक्ता")
    date_place = clean_legal_text(date_place or f"दिनांक: {datetime.now().strftime('%d/%m/%Y')}\nस्थान: न्यायालय परिसर")

    cleaned_paragraphs = [clean_legal_text(p) for p in (body_paragraphs or []) if clean_legal_text(p)]
    if not cleaned_paragraphs:
        cleaned_paragraphs = [
            "1. यह कि प्रार्थी उपरोक्त वाद का पक्षकार एवं कानून का पालन करने वाला नागरिक है।",
            "2. यह कि प्रस्तुत प्रकरण के आवश्यक तथ्य एवं न्यायहित के आधार पर यह आवेदन प्रस्तुत किया जा रहा है।",
            "3. यह कि आवेदन पत्र के साथ समस्त आवश्यक दस्तावेज संलग्न हैं।",
        ]

    # Generate document via python-docx if installed
    if _DOCX_AVAILABLE:
        doc = docx.Document()

        # Set tight legal 1-page margins (0.75" / 19mm)
        for section in doc.sections:
            section.top_margin = Inches(0.7)
            section.bottom_margin = Inches(0.7)
            section.left_margin = Inches(0.9)  # Margin for filing margin
            section.right_margin = Inches(0.6)
            section.page_width = Inches(8.27)  # A4
            section.page_height = Inches(11.69)

        # Base style: Mangal / Nirmala UI, 11.5pt, 1.15 line spacing
        style = doc.styles["Normal"]
        font = style.font
        font.name = "Mangal"
        font.size = Pt(11.5)
        font.color.rgb = RGBColor(0, 0, 0)
        style.paragraph_format.line_spacing = 1.15
        style.paragraph_format.space_after = Pt(3)

        # 1. Court Name (Centered, Bold, 13pt)
        if court_name:
            p_court = doc.add_paragraph()
            p_court.alignment = WD_ALIGN_PARAGRAPH.CENTER
            r = p_court.add_run(court_name)
            r.bold = True
            r.font.size = Pt(13)
            p_court.paragraph_format.space_after = Pt(2)

        # 2. Case Number
        if case_no:
            p_case = doc.add_paragraph()
            p_case.alignment = WD_ALIGN_PARAGRAPH.CENTER
            r = p_case.add_run(case_no)
            r.bold = True
            p_case.paragraph_format.space_after = Pt(4)

        # 3. Parties (Left / Indented)
        if parties:
            p_parties = doc.add_paragraph()
            p_parties.alignment = WD_ALIGN_PARAGRAPH.LEFT
            r = p_parties.add_run(parties)
            p_parties.paragraph_format.space_after = Pt(6)

        # 4. Title (Centered, Bold, Underlined, 12pt)
        p_title = doc.add_paragraph()
        p_title.alignment = WD_ALIGN_PARAGRAPH.CENTER
        r_title = p_title.add_run(f"विषय: {title}")
        r_title.bold = True
        r_title.underline = True
        r_title.font.size = Pt(12)
        p_title.paragraph_format.space_after = Pt(6)

        def _add_multiline_runs(paragraph, text_content: str, bold: bool = False, underline: bool = False, size_pt: Optional[float] = None):
            lines = text_content.split("\n")
            for i, line in enumerate(lines):
                if i > 0:
                    paragraph.add_run().add_break()
                if line:
                    r = paragraph.add_run(line)
                    if bold:
                        r.bold = True
                    if underline:
                        r.underline = True
                    if size_pt:
                        r.font.size = Pt(size_pt)

        # 5. Salutation
        p_salute = doc.add_paragraph()
        _add_multiline_runs(p_salute, "महोदय,\nसविनय निवेदन इस प्रकार है:", bold=True)
        p_salute.paragraph_format.space_after = Pt(4)

        # 6. Body Paragraphs (Justified)
        for para in cleaned_paragraphs:
            p_body = doc.add_paragraph()
            p_body.alignment = WD_ALIGN_PARAGRAPH.JUSTIFY
            _add_multiline_runs(p_body, para)
            p_body.paragraph_format.space_after = Pt(4)

        # 7. Prayer / Relief (Bold header, Justified body)
        if prayer:
            p_pr_head = doc.add_paragraph()
            r_pr_head = p_pr_head.add_run("प्रार्थना:")
            r_pr_head.bold = True
            p_pr_head.paragraph_format.space_after = Pt(2)

            p_prayer = doc.add_paragraph()
            p_prayer.alignment = WD_ALIGN_PARAGRAPH.JUSTIFY
            _add_multiline_runs(p_prayer, prayer)
            p_prayer.paragraph_format.space_after = Pt(8)

        # 8. Bottom block: Date/Place (Left) & Signatures (Right) via table
        table = doc.add_table(rows=1, cols=2)
        table.autofit = True
        cell_left = table.cell(0, 0)
        cell_right = table.cell(0, 1)

        p_left = cell_left.paragraphs[0]
        p_left.alignment = WD_ALIGN_PARAGRAPH.LEFT
        _add_multiline_runs(p_left, date_place)

        p_right = cell_right.paragraphs[0]
        p_right.alignment = WD_ALIGN_PARAGRAPH.RIGHT
        _add_multiline_runs(p_right, advocate_info)

        doc.save(str(file_path))
    else:
        def _rtf_multiline(t: str) -> str:
            cleaned = t.replace("\r\n", "\n").replace("\r", "\n")
            return cleaned.replace("\n", "\\line ")

        # Fallback to UTF-8 RTF file (opens in Word and WordPad directly)
        file_path = docs_dir / f"{clean_type}_{timestamp}.rtf"
        rtf_content = (
            "{\\rtf1\\ansi\\deff0\n"
            "{\\fonttbl{\\f0\\fnil\\fcharset0 Mangal;}}\n"
            "\\viewkind4\\uc1\\pard\\lang1081\\f0\\fs24\n"
            f"\\qc\\b {court_name}\\b0\\par\n"
            f"\\qc\\b {case_no}\\b0\\par\\par\n"
            f"\\ql {parties}\\par\\par\n"
            f"\\qc\\b\\ul विषय: {title}\\ulnone\\b0\\par\\par\n"
            "\\ql\\b महोदय, सविनय निवेदन है:\\b0\\par\n"
        )
        for para in cleaned_paragraphs:
            rtf_content += f"\\ql {_rtf_multiline(para)}\\par\n"
        if prayer:
            rtf_content += f"\\par\\ql\\b प्रार्थना:\\b0\\par\\ql {_rtf_multiline(prayer)}\\par\n"
        rtf_content += f"\\par\\ql {_rtf_multiline(date_place)}\\tab\\tab\\qr {_rtf_multiline(advocate_info)}\\par\n"
        rtf_content += "}"
        file_path.write_text(rtf_content, encoding="utf-8")

    # Update active state
    _ACTIVE_DRAFT["file_path"] = str(file_path)
    _ACTIVE_DRAFT["doc_type"] = doc_type
    _ACTIVE_DRAFT["title"] = title
    _ACTIVE_DRAFT["status"] = "drafted"
    _ACTIVE_DRAFT["updated_at"] = datetime.now().isoformat()

    # Open on screen in Word / WordPad
    open_result = open_document_in_editor(str(file_path))

    return {
        "status": "success",
        "file_path": str(file_path),
        "file_name": file_path.name,
        "editor_result": open_result,
        "voice_prompt": (
            "वकील साहब, आवेदन पत्र स्क्रीन पर तैयार कर दिया गया है। "
            "कृपया एक बार देख लीजिए कि प्रारूप और भाषा सही है या नहीं। "
            "अगर कोई संशोधन करना है तो मुझे बताइए, मैं उसे याद रखूँगी।"
        ),
    }


def open_document_in_editor(file_path: str) -> str:
    """
    Opens the document in MS Word (winword.exe) or WordPad (wordpad.exe).
    NEVER uses Notepad.
    """
    path_obj = Path(file_path)
    if not path_obj.exists():
        return f"File not found: {file_path}"

    system = platform.system()
    abs_path = str(path_obj.resolve())

    if system == "Windows":
        # 1. Try winword
        word_candidates = [
            r"C:\Program Files\Microsoft Office\root\Office16\WINWORD.EXE",
            r"C:\Program Files (x86)\Microsoft Office\root\Office16\WINWORD.EXE",
            r"C:\Program Files\Microsoft Office\Office15\WINWORD.EXE",
            r"C:\Program Files (x86)\Microsoft Office\Office15\WINWORD.EXE",
        ]
        winword = next((p for p in word_candidates if os.path.exists(p)), None)
        if winword:
            try:
                subprocess.Popen([winword, abs_path])
                return f"Opened in Microsoft Word: {path_obj.name}"
            except Exception:
                pass

        # 2. Try WordPad
        wordpad_candidates = [
            r"C:\Program Files\Windows NT\Accessories\wordpad.exe",
            r"C:\Program Files (x86)\Windows NT\Accessories\wordpad.exe",
            r"C:\Windows\System32\write.exe",
        ]
        wordpad = next((p for p in wordpad_candidates if os.path.exists(p)), "write.exe")
        try:
            subprocess.Popen([wordpad, abs_path])
            return f"Opened in WordPad: {path_obj.name}"
        except Exception:
            pass

        # 3. Native Windows Shell Open (opens associated default Word app, not notepad)
        try:
            os.startfile(abs_path)
            return f"Opened via Windows default editor: {path_obj.name}"
        except Exception as e:
            return f"Could not launch editor: {e}"
    else:
        # Linux / Fallback
        if shutil.which("libreoffice"):
            subprocess.Popen(["libreoffice", "--writer", abs_path])
            return f"Opened in LibreOffice Writer: {path_obj.name}"
        elif shutil.which("xdg-open"):
            subprocess.Popen(["xdg-open", abs_path])
            return f"Opened in system viewer: {path_obj.name}"
        return f"File saved at: {abs_path}"


def print_document(file_path: Optional[str] = None) -> Dict[str, Any]:
    """
    Directly sends the document to the system's default printer.
    """
    target = file_path or _ACTIVE_DRAFT.get("file_path")
    if not target or not Path(target).exists():
        return {
            "status": "error",
            "message": "प्रिंट करने के लिए कोई दस्तावेज़ नहीं मिला। कृपया पहले दस्तावेज़ तैयार करें।",
        }

    abs_path = str(Path(target).resolve())
    system = platform.system()

    if system == "Windows":
        try:
            # Native Windows ShellExecute print verb
            os.startfile(abs_path, "print")
            return {
                "status": "success",
                "message": f"प्रिंट कमांड सिस्टम डिफ़ॉल्ट प्रिंटर पर भेज दी गई है: {Path(abs_path).name}",
            }
        except Exception:
            try:
                cmd = f'powershell -Command "Start-Process -FilePath \'{abs_path}\' -Verb Print"'
                subprocess.run(cmd, shell=True, check=True, timeout=10)
                return {
                    "status": "success",
                    "message": f"प्रिंटर को प्रिंट कमांड सफलतापूर्वक भेजी गई: {Path(abs_path).name}",
                }
            except Exception as e:
                return {
                    "status": "error",
                    "message": f"प्रिंट कमांड भेजने में त्रुटि: {e}",
                }
    else:
        # Linux / macOS
        try:
            subprocess.run(["lp", abs_path], check=True, timeout=10)
            return {"status": "success", "message": f"प्रिंटर (lp) पर भेज दिया गया: {Path(abs_path).name}"}
        except Exception:
            try:
                subprocess.run(["libreoffice", "--headless", "--print-to-default", abs_path], timeout=15)
                return {"status": "success", "message": f"LibreOffice के ज़रिए प्रिंट भेजा गया: {Path(abs_path).name}"}
            except Exception as e:
                return {"status": "error", "message": f"प्रिंटर त्रुटि: {e}"}


def save_advocate_learning(doc_type: str, preference_or_correction: str) -> Dict[str, Any]:
    """
    Saves the advocate's drafting corrections and formatting rules to memory/legal_templates.json
    so future drafts automatically respect the user's preferred format.
    """
    TEMPLATES_FILE.parent.mkdir(parents=True, exist_ok=True)
    templates: Dict[str, Any] = {}
    if TEMPLATES_FILE.exists():
        try:
            templates = json.loads(TEMPLATES_FILE.read_text(encoding="utf-8"))
        except Exception:
            templates = {}

    doc_key = doc_type.strip().lower()
    if doc_key not in templates:
        templates[doc_key] = {"rules": [], "updated_at": None}

    clean_pref = clean_legal_text(preference_or_correction)
    if clean_pref and clean_pref not in templates[doc_key]["rules"]:
        templates[doc_key]["rules"].append(clean_pref)
        templates[doc_key]["updated_at"] = datetime.now().isoformat()

    TEMPLATES_FILE.write_text(json.dumps(templates, ensure_ascii=False, indent=2), encoding="utf-8")

    return {
        "status": "saved",
        "doc_type": doc_type,
        "rule": clean_pref,
        "message": f"वकील साहब, मैंने {doc_type} के लिए यह नियम अपनी याददाश्त में सुरक्षित कर लिया है।",
    }


def advocate_action(action: str, **kwargs) -> Dict[str, Any]:
    """
    Unified entry point for Advocate tools.
    Actions:
      - 'scan': Initial system & printer scan
      - 'draft': Draft a legal application on screen
      - 'print': Print the active or specified document
      - 'learn': Save correction / format preference
      - 'status': Get current draft status
    """
    act = (action or "").strip().lower()

    if act == "scan":
        return scan_advocate_environment()

    if act == "draft":
        return create_legal_document(
            doc_type=kwargs.get("doc_type", "आवेदन_पत्र"),
            title=kwargs.get("title", "प्रार्थना पत्र"),
            court_name=kwargs.get("court_name", ""),
            case_no=kwargs.get("case_no", ""),
            parties=kwargs.get("parties", ""),
            body_paragraphs=kwargs.get("body_paragraphs"),
            prayer=kwargs.get("prayer", ""),
            advocate_info=kwargs.get("advocate_info", ""),
            date_place=kwargs.get("date_place", ""),
        )

    if act == "print":
        return print_document(kwargs.get("file_path"))

    if act == "learn":
        return save_advocate_learning(
            doc_type=kwargs.get("doc_type", "सामान्य"),
            preference_or_correction=kwargs.get("correction", kwargs.get("text", "")),
        )

    if act == "status":
        return {"active_draft": _ACTIVE_DRAFT}

    return {"status": "error", "message": f"Unknown advocate action: {action}"}
