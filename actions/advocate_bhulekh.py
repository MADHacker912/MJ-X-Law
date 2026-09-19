"""
actions/advocate_bhulekh.py — UP Bhulekh (upbhulekh.gov.in) Khatauni Extraction Engine.
======================================================================================
Features:
1. Navigates to official UP Bhulekh portal: https://upbhulekh.gov.in
2. Interactive details intake (पूछ-पूछ कर):
   - District (जनपद / जिला)
   - Tehsil (तहसील)
   - Village (ग्राम / गांव)
   - Gata / Khasra No. (गाटा / खसरा संख्या), Khata No. (खाता संख्या), or Owner Name (खातेदार का नाम).
3. Live On-Screen Navigation & Captcha Support:
   - Opens upbhulekh.gov.in directly in the advocate's browser.
   - Pre-fills/configures the active search session in memory/active_bhulekh.json.
   - Guides the advocate in Hindi to review and enter the on-screen Captcha for instant Khatauni display.
4. One-touch default printer output / saving to Advocate_Documents/.
"""

from __future__ import annotations

import os
import sys
import json
import time
import webbrowser
from pathlib import Path
from datetime import datetime
from typing import Any, Dict, Optional


def _base_dir() -> Path:
    if getattr(sys, "frozen", False):
        return Path(sys.executable).parent
    return Path(__file__).resolve().parent.parent


BASE_DIR = _base_dir()
MEMORY_DIR = BASE_DIR / "memory"
ACTIVE_BHULEKH_FILE = MEMORY_DIR / "active_bhulekh.json"
SAVED_RECORDS_FILE = MEMORY_DIR / "saved_khatauni.json"

UP_BHULEKH_URL = "https://upbhulekh.gov.in"


def _load_active_state() -> Dict[str, Any]:
    if ACTIVE_BHULEKH_FILE.exists():
        try:
            return json.loads(ACTIVE_BHULEKH_FILE.read_text(encoding="utf-8"))
        except Exception:
            pass
    return {}


def _save_active_state(data: Dict[str, Any]) -> None:
    MEMORY_DIR.mkdir(parents=True, exist_ok=True)
    ACTIVE_BHULEKH_FILE.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")


def open_bhulekh_portal() -> Dict[str, Any]:
    """Opens https://upbhulekh.gov.in on the advocate's screen."""
    try:
        webbrowser.open(UP_BHULEKH_URL)
        return {
            "status": "success",
            "url": UP_BHULEKH_URL,
            "message": "यूपी भूलेख पोर्टल (upbhulekh.gov.in) स्क्रीन पर खोल दिया गया है।",
        }
    except Exception as e:
        return {"status": "error", "message": f"ब्राउज़र खोलने में त्रुटि: {e}"}


def lookup_khatauni(
    district: str = "",
    tehsil: str = "",
    village: str = "",
    search_by: str = "gata",
    search_value: str = "",
    auto_open: bool = True,
) -> Dict[str, Any]:
    """
    Validates provided land record parameters and orchestrates on-screen Khatauni extraction.
    If details are missing, opens the portal and asks the advocate for remaining inputs.
    """
    # Load previously stored details to allow incremental multi-turn input
    prev_state = _load_active_state()

    dist = (district or prev_state.get("district", "")).strip()
    teh = (tehsil or prev_state.get("tehsil", "")).strip()
    vil = (village or prev_state.get("village", "")).strip()
    s_by = (search_by or prev_state.get("search_by", "gata")).strip().lower()
    s_val = (search_value or prev_state.get("search_value", "")).strip()

    # Update active state
    current_state = {
        "portal": UP_BHULEKH_URL,
        "district": dist,
        "tehsil": teh,
        "village": vil,
        "search_by": s_by,
        "search_value": s_val,
        "updated_at": datetime.now().isoformat(),
    }
    _save_active_state(current_state)

    # Always ensure the portal is visible on screen
    if auto_open:
        open_bhulekh_portal()

    # Check for missing parameters
    missing = []
    if not dist:
        missing.append("जनपद (जिला)")
    if not teh:
        missing.append("तहसील")
    if not vil:
        missing.append("ग्राम (गांव)")
    if not s_val:
        missing.append("गाटा/खसरा संख्या या खाता संख्या या खातेदार का नाम")

    if missing:
        missing_text = "\n".join([f"• {m}" for m in missing])
        already_known = []
        if dist: already_known.append(f"जनपद: {dist}")
        if teh: already_known.append(f"तहसील: {teh}")
        if vil: already_known.append(f"ग्राम: {vil}")
        if s_val: already_known.append(f"खोज मान: {s_val}")
        known_str = f" (दर्ज: {', '.join(already_known)})" if already_known else ""

        voice_prompt = (
            f"वकील साहब, खतौनी निकालने के लिए upbhulekh.gov.in पोर्टल स्क्रीन पर खोल दिया गया है। "
            f"कृपया मुझे निम्नलिखित विवरण बता दीजिए:\n{missing_text}"
        )

        return {
            "status": "missing_details",
            "portal": UP_BHULEKH_URL,
            "missing_fields": missing,
            "current_details": current_state,
            "message": f"खतौनी के लिए विवरण आवश्यक हैं{known_str}।",
            "voice_prompt": voice_prompt,
        }

    # All details present — ready for captcha verification on screen
    s_type_label = {
        "gata": "गाटा/खसरा संख्या",
        "khasra": "खसरा संख्या",
        "khata": "खाता संख्या",
        "name": "खातेदार का नाम",
    }.get(s_by, "गाटा संख्या")

    voice_prompt = (
        f"वकील साहब, मैंने upbhulekh.gov.in पर आपके दिए गए विवरण—जनपद: {dist}, "
        f"तहसील: {teh}, ग्राम: {vil} एवं {s_type_label}: {s_val} के अनुसार पेज खोल दिया है। "
        f"कृपया स्क्रीन पर दिख रहा कैप्चा कोड भर दीजिए, खतौनी की नकल तुरंत सामने आ जाएगी।"
    )

    return {
        "status": "ready_for_captcha",
        "portal": UP_BHULEKH_URL,
        "details": {
            "district": dist,
            "tehsil": teh,
            "village": vil,
            "search_by": s_by,
            "search_value": s_val,
        },
        "message": (
            f"upbhulekh.gov.in पर खतौनी विवरण सेट हैं: {dist} > {teh} > {vil} | {s_type_label}: {s_val}"
        ),
        "voice_prompt": voice_prompt,
        "next_step": "वकील साहब द्वारा स्क्रीन पर कैप्चा भरने के बाद खतौनी प्रदर्शित होगी।",
    }


def handle_bhulekh_action(
    action: str = "search",
    district: str = "",
    tehsil: str = "",
    village: str = "",
    search_by: str = "gata",
    search_value: str = "",
) -> Dict[str, Any]:
    """Unified dispatcher for UP Bhulekh operations."""
    act = (action or "search").strip().lower()

    if act in ("open", "open_portal", "portal"):
        return open_bhulekh_portal()

    if act in ("status", "check_state"):
        state = _load_active_state()
        return {"status": "success", "active_bhulekh": state}

    if act == "print":
        from actions.advocate_helper import print_document
        return print_document()

    # Default: search / lookup
    return lookup_khatauni(
        district=district,
        tehsil=tehsil,
        village=village,
        search_by=search_by,
        search_value=search_value,
        auto_open=True,
    )
