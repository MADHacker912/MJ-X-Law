"""
core/updater.py — Safe Automatic Background Updater for MJ-X-Law.
================================================================
Features:
1. Automatically checks https://github.com/MADHacker912/MJ-X-Law.git on startup.
2. Applies new features and code updates automatically via fast-forward git pull.
3. Absolute Zero-Data-Loss Protection:
   - Preserves API keys (config/api_keys.json)
   - Preserves system credentials / Windows PIN (config/system_creds.json)
   - Preserves all memories, learned drafting rules, case diary, and personal data (memory/*.json).
4. Non-blocking & Failure-Tolerant:
   - Runs in a background thread; never halts or delays startup.
   - If offline or GitHub unreachable, exits silently without error.
"""

from __future__ import annotations

import os
import sys
import json
import time
import shutil
import subprocess
from pathlib import Path
from typing import Any, Callable, Dict, Optional


def _base_dir() -> Path:
    if getattr(sys, "frozen", False):
        return Path(sys.executable).parent
    return Path(__file__).resolve().parent.parent


BASE_DIR = _base_dir()
CONFIG_DIR = BASE_DIR / "config"
MEMORY_DIR = BASE_DIR / "memory"
BACKUP_DIR = MEMORY_DIR / "backups" / "pre_update_user_data"

REMOTE_URL = "https://github.com/MADHacker912/MJ-X-Law.git"
BRANCH = "main"

# Protected personal files that MUST NEVER be overwritten or wiped during updates
PROTECTED_CONFIG_FILES = [
    "api_keys.json",
    "system_creds.json",
]

PROTECTED_MEMORY_FILES = [
    "identity.json",
    "advocate_cases.json",
    "active_bhulekh.json",
    "legal_templates.json",
    "long_term.json",
    "facts.json",
    "preferences.json",
    "work.json",
    "people.json",
    "system.json",
]


def backup_user_state() -> Dict[str, Any]:
    """
    Takes in-memory snapshots and disk backups of all user API keys,
    system credentials, and personalized memory stores.
    """
    BACKUP_DIR.mkdir(parents=True, exist_ok=True)
    cache: Dict[str, Any] = {"configs": {}, "memories": {}}

    # 1. Backup configs
    for name in PROTECTED_CONFIG_FILES:
        fpath = CONFIG_DIR / name
        if fpath.exists():
            try:
                content = fpath.read_text(encoding="utf-8")
                cache["configs"][name] = content
                shutil.copy2(fpath, BACKUP_DIR / name)
            except Exception:
                pass

    # 2. Backup memories
    for name in PROTECTED_MEMORY_FILES:
        fpath = MEMORY_DIR / name
        if fpath.exists():
            try:
                content = fpath.read_text(encoding="utf-8")
                cache["memories"][name] = content
                shutil.copy2(fpath, BACKUP_DIR / name)
            except Exception:
                pass

    return cache


def restore_user_state(cache: Dict[str, Any]) -> None:
    """
    Ensures that all user API keys, credentials, and memory files
    are restored exactly to their personalized state after any update.
    """
    # Restore configs
    for name, content in cache.get("configs", {}).items():
        fpath = CONFIG_DIR / name
        try:
            CONFIG_DIR.mkdir(parents=True, exist_ok=True)
            fpath.write_text(content, encoding="utf-8")
        except Exception:
            pass

    # Restore memories
    for name, content in cache.get("memories", {}).items():
        fpath = MEMORY_DIR / name
        try:
            MEMORY_DIR.mkdir(parents=True, exist_ok=True)
            fpath.write_text(content, encoding="utf-8")
        except Exception:
            pass


def _run_git(args: list[str], timeout: int = 15) -> subprocess.CompletedProcess:
    return subprocess.run(
        ["git"] + args,
        cwd=str(BASE_DIR),
        capture_output=True,
        text=True,
        timeout=timeout,
    )


def check_and_apply_updates(log_fn: Optional[Callable[[str], None]] = None) -> Dict[str, Any]:
    """
    Checks GitHub (https://github.com/MADHacker912/MJ-X-Law.git) for new updates.
    If updates are present, applies them safely while keeping all API keys & memories intact.
    """
    def log(msg: str):
        print(f"[Updater] {msg}")
        if log_fn:
            try:
                log_fn(msg)
            except Exception:
                pass

    # 1. Verify git repository presence
    git_dir = BASE_DIR / ".git"
    if not git_dir.exists():
        return {"status": "no_git", "updated": False, "message": "Git repository not found."}

    # 2. Ensure remote URL is set to MJ-X-Law
    try:
        remotes = _run_git(["remote", "-v"]).stdout
        if REMOTE_URL not in remotes:
            _run_git(["remote", "set-url", "origin", REMOTE_URL])
            log(f"Configured remote URL to: {REMOTE_URL}")
    except Exception:
        pass

    # 3. Create user safety backup before touching repository
    user_cache = backup_user_state()

    # 4. Fetch updates from remote
    try:
        fetch_res = _run_git(["fetch", "origin", BRANCH], timeout=20)
        if fetch_res.returncode != 0:
            # Network issue, offline, or auth required
            return {
                "status": "network_unavailable",
                "updated": False,
                "message": "इंटरनेट या GitHub से कनेक्शन नहीं हो सका।",
            }
    except Exception as e:
        return {"status": "fetch_error", "updated": False, "message": str(e)}

    # 5. Check if local HEAD is behind origin/main
    try:
        rev_res = _run_git(["rev-list", f"HEAD..origin/{BRANCH}", "--count"])
        if rev_res.returncode != 0:
            return {"status": "rev_error", "updated": False}

        commits_behind = int(rev_res.stdout.strip() or "0")
        if commits_behind == 0:
            log("System is up-to-date with GitHub.")
            return {
                "status": "up_to_date",
                "updated": False,
                "message": "वकील साहब, आपका सिस्टम पहले से ही नवीनतम संस्करण पर है। कोई नया अपडेट लंबित नहीं है।",
            }

        log(f"Updates available! Found {commits_behind} new commit(s). Applying updates...")

        # 6. Apply updates safely
        # Fast-forward merge to pull only clean code changes
        merge_res = _run_git(["merge", "--ff-only", f"origin/{BRANCH}"])
        if merge_res.returncode != 0:
            # If local tracking changes prevent fast-forward, stash and pull
            _run_git(["stash"])
            pull_res = _run_git(["pull", "--ff-only", "origin", BRANCH])
            _run_git(["stash", "pop"])
            if pull_res.returncode != 0:
                log("Could not fast-forward cleanly. Keeping current local version.")
                return {
                    "status": "merge_conflict",
                    "updated": False,
                    "message": "स्थानीय संशोधनों के कारण स्वतः अपडेट नहीं हो सका।",
                }

        # 7. Restoring user state (Guarantees API keys and memories are NEVER modified)
        restore_user_state(user_cache)
        log(f"Successfully updated! {commits_behind} new commit(s) applied. API keys and memories preserved.")

        return {
            "status": "updated",
            "updated": True,
            "commits_applied": commits_behind,
            "message": (
                f"वकील साहब, सिस्टम को GitHub से {commits_behind} नए फीचर्स के साथ "
                "सफलतापूर्वक अपडेट कर दिया गया है। आपकी सभी एपीआई कुंजियाँ और याददाश्त सुरक्षित हैं।"
            ),
        }

    except Exception as e:
        restore_user_state(user_cache)
        log(f"Update failed with error: {e}")
        return {"status": "error", "updated": False, "message": str(e)}


def start_background_updater(callback: Optional[Callable[[Dict[str, Any]], None]] = None) -> None:
    """Launches the update check in a non-blocking daemon thread."""
    import threading

    def _worker():
        # Brief pause to let initial UI/audio initialization settle
        time.sleep(4.0)
        res = check_and_apply_updates()
        if callback:
            try:
                callback(res)
            except Exception:
                pass

    threading.Thread(target=_worker, daemon=True, name="MJ_AutoUpdater").start()
