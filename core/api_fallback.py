"""
core/api_fallback.py — Multi-Provider API Failover & Autonomous Key Recovery Engine.
=====================================================================================
Features:
1. Google Gemini <-> OpenRouter seamless automatic failover.
   - If Google Gemini hits 429 Rate Limit, Quota Exhausted, or 503, immediately falls back to OpenRouter.
2. OpenRouter client:
   - OpenAI-compatible endpoint (https://openrouter.ai/api/v1/chat/completions)
   - Supports Gemini 2.0 Flash, Claude 3.5 Sonnet, Llama 3.3 70B, DeepSeek V3, etc.
3. Autonomous API Key Autopilot Recovery:
   - When API quota is completely exhausted, alerts the advocate in Hindi:
     "वकील साहब, वर्तमान एपीआई की सीमा समाप्त हो गई है। मैं क्रोम खोलकर नया एपीआई की (API Key) बनाकर स्वतः सेट कर रही हूँ।"
   - Opens Chrome to Google AI Studio / OpenRouter.
   - Monitors clipboard / automates key capture and directly saves the new key to config/api_keys.json.
"""

from __future__ import annotations

import os
import re
import sys
import json
import time
import subprocess
import webbrowser
from pathlib import Path
from typing import Any, Dict, Optional, Tuple

import requests


def _base_dir() -> Path:
    if getattr(sys, "frozen", False):
        return Path(sys.executable).parent
    return Path(__file__).resolve().parent.parent


BASE_DIR = _base_dir()
CONFIG_PATH = BASE_DIR / "config" / "api_keys.json"


def load_api_config() -> Dict[str, Any]:
    if CONFIG_PATH.exists():
        try:
            return json.loads(CONFIG_PATH.read_text(encoding="utf-8"))
        except Exception:
            pass
    return {}


def save_api_config(config: Dict[str, Any]) -> bool:
    try:
        CONFIG_PATH.write_text(json.dumps(config, ensure_ascii=False, indent=4), encoding="utf-8")
        return True
    except Exception as e:
        print(f"[API Config] Error saving config: {e}")
        return False


def set_api_key(provider: str, key_value: str) -> bool:
    cfg = load_api_config()
    clean_key = key_value.strip()
    if provider.lower() in ("gemini", "google"):
        cfg["gemini_api_key"] = clean_key
        cfg["active_provider"] = "gemini"
    elif provider.lower() in ("openrouter", "open_router"):
        cfg["openrouter_api_key"] = clean_key
        cfg["active_provider"] = "openrouter"
    return save_api_config(cfg)


def call_openrouter(
    prompt: str,
    system_prompt: Optional[str] = None,
    model: Optional[str] = None,
    api_key: Optional[str] = None,
    timeout: int = 30,
) -> str:
    """
    Calls OpenRouter API using standard chat completions.
    """
    cfg = load_api_config()
    key = api_key or cfg.get("openrouter_api_key", "")
    if not key:
        raise ValueError("OpenRouter API key is not configured in config/api_keys.json")

    chosen_model = model or cfg.get("openrouter_model", "google/gemini-2.0-flash-001")
    endpoint = "https://openrouter.ai/api/v1/chat/completions"

    messages = []
    if system_prompt:
        messages.append({"role": "system", "content": system_prompt})
    messages.append({"role": "user", "content": prompt})

    headers = {
        "Authorization": f"Bearer {key}",
        "HTTP-Referer": "https://github.com/MADHacker912/MJ-X",
        "X-Title": "MJ-X Advocate Assistant",
        "Content-Type": "application/json",
    }
    payload = {
        "model": chosen_model,
        "messages": messages,
        "temperature": 0.3,
    }

    resp = requests.post(endpoint, json=payload, headers=headers, timeout=timeout)
    resp.raise_for_status()
    data = resp.json()
    choices = data.get("choices", [])
    if choices:
        return choices[0].get("message", {}).get("content", "").strip()
    raise ValueError("OpenRouter returned empty response.")


def call_gemini(
    prompt: str,
    system_prompt: Optional[str] = None,
    model: str = "gemini-2.0-flash",
    api_key: Optional[str] = None,
) -> str:
    """
    Calls Google Gemini using google-genai client.
    """
    cfg = load_api_config()
    key = api_key or cfg.get("gemini_api_key", "")
    if not key:
        raise ValueError("Gemini API key is not configured in config/api_keys.json")

    from google import genai
    from google.genai import types

    client = genai.Client(api_key=key)
    config = types.GenerateContentConfig()
    if system_prompt:
        config.system_instruction = system_prompt

    resp = client.models.generate_content(
        model=model,
        contents=prompt,
        config=config,
    )
    return (resp.text or "").strip()


def smart_llm_query(
    prompt: str,
    system_prompt: Optional[str] = None,
    model: Optional[str] = None,
) -> Tuple[str, str]:
    """
    Tries Google Gemini first. If an error occurs (Rate Limit, QuotaExhausted, 429),
    instantly falls back to OpenRouter!
    Returns (response_text, provider_used).
    """
    cfg = load_api_config()
    gemini_key = cfg.get("gemini_api_key", "").strip()
    openrouter_key = cfg.get("openrouter_api_key", "").strip()
    primary = cfg.get("active_provider", "gemini").lower()

    gemini_error = None
    openrouter_error = None

    # Order based on active provider preference
    providers = ["gemini", "openrouter"] if primary == "gemini" else ["openrouter", "gemini"]

    for provider in providers:
        if provider == "gemini" and gemini_key:
            try:
                text = call_gemini(prompt, system_prompt, model=model or "gemini-2.0-flash", api_key=gemini_key)
                if text:
                    return text, "gemini"
            except Exception as e:
                gemini_error = e
                print(f"[API Failover] Gemini call failed: {e}. Attempting OpenRouter fallback...")

        elif provider == "openrouter" and openrouter_key:
            try:
                text = call_openrouter(prompt, system_prompt, model=model, api_key=openrouter_key)
                if text:
                    return text, "openrouter"
            except Exception as e:
                openrouter_error = e
                print(f"[API Failover] OpenRouter call failed: {e}.")

    # If both failed or missing, check if error was quota exhaustion
    is_quota = False
    for err in (gemini_error, openrouter_error):
        if err and any(term in str(err).lower() for term in ("429", "quota", "resource_exhausted", "credit")):
            is_quota = True
            break

    if is_quota or (not gemini_key and not openrouter_key):
        print("[API Failover] All API keys exhausted. Triggering Autopilot Key Recovery...")
        recovery = recover_api_key_autopilot("gemini")
        if recovery.get("status") == "success":
            # Retry with newly saved key
            return call_gemini(prompt, system_prompt, model=model or "gemini-2.0-flash"), "gemini_recovered"

    raise RuntimeError(
        f"All LLM providers failed. Gemini error: {gemini_error} | OpenRouter error: {openrouter_error}"
    )


def recover_api_key_autopilot(target_provider: str = "gemini", timeout: int = 45) -> Dict[str, Any]:
    """
    Autopilot API Key Recovery:
    1. Alerts user in Hindi.
    2. Opens Chrome to Google AI Studio (https://aistudio.google.com/app/apikey)
       or OpenRouter (https://openrouter.ai/keys).
    3. Monitors clipboard for newly copied key.
    4. Automatically updates config/api_keys.json.
    """
    target_url = (
        "https://aistudio.google.com/app/apikey"
        if target_provider.lower() in ("gemini", "google")
        else "https://openrouter.ai/keys"
    )

    announcement = (
        "वकील साहब, वर्तमान एपीआई की सीमा समाप्त हो गई है। "
        "मैं क्रोम खोलकर नया एपीआई की (API Key) बनाकर स्वतः सेट कर रही हूँ।"
    )
    print(f"[Autopilot Recovery] {announcement}")

    # Launch Chrome on screen
    try:
        webbrowser.open(target_url)
    except Exception as e:
        print(f"[Autopilot Recovery] Could not launch browser: {e}")

    # Monitor clipboard for newly copied key
    try:
        import pyperclip
        initial_clip = pyperclip.paste().strip()
    except Exception:
        initial_clip = ""

    deadline = time.time() + timeout
    detected_key = None

    # Regex for Gemini API keys: AIzaSy[33 characters]
    # Regex for OpenRouter keys: sk-or-v1-[64 hex chars]
    gemini_pattern = re.compile(r"AIzaSy[A-Za-z0-9_-]{33}")
    openrouter_pattern = re.compile(r"sk-or-v1-[a-f0-9]{64}")

    while time.time() < deadline:
        time.sleep(1.0)
        try:
            import pyperclip
            current = pyperclip.paste().strip()
            if current and current != initial_clip:
                if gemini_pattern.search(current):
                    detected_key = gemini_pattern.search(current).group(0)
                    target_provider = "gemini"
                    break
                elif openrouter_pattern.search(current):
                    detected_key = openrouter_pattern.search(current).group(0)
                    target_provider = "openrouter"
                    break
        except Exception:
            pass

    if detected_key:
        set_api_key(target_provider, detected_key)
        confirm_msg = (
            f"वकील साहब, नया {target_provider.capitalize()} API Key स्वतः कैप्चर करके "
            "सिस्टम में सेट कर दिया गया है। कार्यप्रवाह पुनः सक्रिय है।"
        )
        return {
            "status": "success",
            "provider": target_provider,
            "key_preview": detected_key[:8] + "..." + detected_key[-4:],
            "message": confirm_msg,
        }

    return {
        "status": "awaiting_key",
        "provider": target_provider,
        "url": target_url,
        "message": (
            "वकील साहब, क्रोम में AI Studio पेज खोल दिया गया है। 'Create API Key' पर क्लिक "
            "करते ही वह स्वतः सिस्टम में सेट हो जाएगा।"
        ),
    }
