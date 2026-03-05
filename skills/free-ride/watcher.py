#!/usr/bin/env python3
"""
FreeRide Watcher
Monitors for rate limits and automatically rotates models.
Can run as a daemon or be called periodically via cron.
"""

from __future__ import annotations

import argparse
import json
import os
import signal
import sys
import time
from collections import OrderedDict
from datetime import datetime, timedelta
from functools import lru_cache
from pathlib import Path
from typing import Any

# Try to use orjson for faster JSON serialization if available
try:
    import orjson
    
    def json_loads(data: str | bytes) -> Any:
        return orjson.loads(data)
    
    def json_dumps(obj: Any, indent: bool = False) -> str:
        option = orjson.OPT_INDENT_2 if indent else 0
        return orjson.dumps(obj, option=option).decode('utf-8')
        
except ImportError:
    import json
    json_loads = json.loads
    json_dumps = lambda obj, indent=False: json.dumps(obj, indent=2 if indent else None)

try:
    import requests
    from requests.adapters import HTTPAdapter
    from urllib3.util.retry import Retry
except ImportError:
    print("Error: requests library required")
    sys.exit(1)


# Import from main module - import only what's needed
from main import (
    get_api_key,
    get_free_models,
    load_openclaw_config,
    save_openclaw_config,
    ensure_config_structure,
    format_model_for_openclaw,
    FreeRideSession,
    get_session,
    OPENCLAW_CONFIG_PATH,
    OPENROUTER_FREE_ROUTER,
)


# Constants
STATE_FILE = Path.home() / ".openclaw" / ".freeride-watcher-state.json"
RATE_LIMIT_COOLDOWN_MINUTES = 30
CHECK_INTERVAL_SECONDS = 60
OPENROUTER_CHAT_URL = "https://openrouter.ai/api/v1/chat/completions"

# Pre-computed constants
RATE_LIMIT_COOLDOWN = timedelta(minutes=RATE_LIMIT_COOLDOWN_MINUTES)


def load_state() -> dict:
    """Load watcher state."""
    if STATE_FILE.exists():
        try:
            return json_loads(STATE_FILE.read_text())
        except (json.JSONDecodeError, OSError):
            pass
    return {"rate_limited_models": {}, "rotation_count": 0}


def save_state(state: dict) -> None:
    """Save watcher state atomically."""
    STATE_FILE.parent.mkdir(parents=True, exist_ok=True)
    temp_file = STATE_FILE.with_suffix('.tmp')
    try:
        temp_file.write_text(json_dumps(state, indent=True))
        temp_file.replace(STATE_FILE)
    except OSError:
        STATE_FILE.write_text(json_dumps(state, indent=True))


def is_model_rate_limited(state: dict, model_id: str) -> bool:
    """Check if a model is currently in rate-limit cooldown."""
    rate_limited = state.get("rate_limited_models")
    if not rate_limited:
        return False
        
    limited_at_str = rate_limited.get(model_id)
    if not limited_at_str:
        return False

    try:
        limited_at = datetime.fromisoformat(limited_at_str)
        return datetime.now() < limited_at + RATE_LIMIT_COOLDOWN
    except (ValueError, TypeError):
        return False


def mark_rate_limited(state: dict, model_id: str) -> None:
    """Mark a model as rate limited."""
    rate_limited = state.setdefault("rate_limited_models", {})
    rate_limited[model_id] = datetime.now().isoformat()
    save_state(state)


# Cache for test results to avoid redundant API calls
_test_result_cache: dict[str, tuple[bool, str | None, float]] = {}
TEST_CACHE_TTL_SECONDS = 30


def test_model(api_key: str, model_id: str) -> tuple[bool, str | None]:
    """
    Test if a model is available by making a minimal API call.
    Returns (success, error_type).
    Uses short-term caching to avoid redundant checks.
    """
    global _test_result_cache
    
    # Check cache
    now = time.time()
    cached = _test_result_cache.get(model_id)
    if cached and (now - cached[2]) < TEST_CACHE_TTL_SECONDS:
        return cached[0], cached[1]

    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
        "HTTP-Referer": "https://github.com/Shaivpidadi/FreeRide",
        "X-Title": "FreeRide Health Check"
    }

    payload = {
        "model": model_id,
        "messages": [{"role": "user", "content": "Hi"}],
        "max_tokens": 5,
        "stream": False
    }

    try:
        session = get_session()
        response = session.post(
            OPENROUTER_CHAT_URL,
            headers=headers,
            json=payload,
            timeout=10  # Shorter timeout for health checks
        )

        if response.status_code == 200:
            result = (True, None)
        elif response.status_code == 429:
            result = (False, "rate_limit")
        elif response.status_code == 503:
            result = (False, "unavailable")
        else:
            result = (False, f"error_{response.status_code}")

    except requests.Timeout:
        result = (False, "timeout")
    except requests.RequestException:
        result = (False, "request_error")

    # Cache result
    _test_result_cache[model_id] = (result[0], result[1], now)
    return result


def get_next_available_model(
    api_key: str, 
    state: dict, 
    exclude_model: str | None = None
) -> str | None:
    """Get the next best model that isn't rate limited."""
    models = get_free_models(api_key)

    for model in models:
        model_id = model["id"]

        # Skip the openrouter/free router - we want specific models
        if OPENROUTER_FREE_ROUTER in model_id:
            continue

        # Skip if same as excluded model
        if exclude_model and model_id == exclude_model:
            continue

        # Skip if in cooldown
        if is_model_rate_limited(state, model_id):
            continue

        # Test if actually available
        success, error = test_model(api_key, model_id)
        if success:
            return model_id

        # Mark as rate limited if that's the error
        if error == "rate_limit":
            mark_rate_limited(state, model_id)

    return None


def rotate_to_next_model(
    api_key: str, 
    state: dict, 
    reason: str = "manual"
) -> bool:
    """Rotate to the next available model."""
    config = load_openclaw_config()
    config = ensure_config_structure(config)
    current = config.get("agents", {}).get("defaults", {}).get("model", {}).get("primary")

    # Extract base model ID from OpenClaw format
    current_base = None
    if current:
        # openrouter/provider/model:free -> provider/model:free
        if current.startswith("openrouter/"):
            current_base = current[len("openrouter/"):]
        else:
            current_base = current

    now = datetime.now().isoformat()
    print(f"[{now}] Rotating from: {current_base or 'none'}")
    print(f"  Reason: {reason}")

    next_model = get_next_available_model(api_key, state, current_base)

    if not next_model:
        print("  Error: No available models found!")
        return False

    print(f"  New model: {next_model}")

    # Update config - primary uses provider prefix, fallbacks don't
    formatted_primary = format_model_for_openclaw(next_model, with_provider_prefix=True)
    config["agents"]["defaults"]["model"]["primary"] = formatted_primary

    # Add to models allowlist
    formatted_for_list = format_model_for_openclaw(next_model, with_provider_prefix=False)
    config["agents"]["defaults"]["models"][formatted_for_list] = {}

    # Build fallbacks from remaining models efficiently
    models = get_free_models(api_key)
    models_dict = config["agents"]["defaults"]["models"]
    fallbacks = []

    # Always add openrouter/free as first fallback
    fallbacks.append(OPENROUTER_FREE_ROUTER)
    models_dict[OPENROUTER_FREE_ROUTER] = {}

    for m in models:
        m_id = m["id"]
        if m_id == next_model or OPENROUTER_FREE_ROUTER in m_id:
            continue
        if is_model_rate_limited(state, m_id):
            continue

        fb_formatted = format_model_for_openclaw(m_id, with_provider_prefix=False)
        fallbacks.append(fb_formatted)
        models_dict[fb_formatted] = {}

        if len(fallbacks) >= 5:
            break

    config["agents"]["defaults"]["model"]["fallbacks"] = fallbacks

    save_openclaw_config(config)

    # Update state
    state["rotation_count"] = state.get("rotation_count", 0) + 1
    state["last_rotation"] = datetime.now().isoformat()
    state["last_rotation_reason"] = reason
    save_state(state)

    print(f"  Success! Rotated to {next_model}")
    print(f"  Total rotations this session: {state['rotation_count']}")

    return True


def check_and_rotate(api_key: str, state: dict) -> bool:
    """Check current model and rotate if needed."""
    config = load_openclaw_config()
    current = config.get("agents", {}).get("defaults", {}).get("model", {}).get("primary")

    if not current:
        print("No primary model configured. Running initial setup...")
        return rotate_to_next_model(api_key, state, "initial_setup")

    # Extract base model ID
    if current.startswith("openrouter/"):
        current_base = current[len("openrouter/"):]
    else:
        current_base = current

    # Check if current model is rate limited
    if is_model_rate_limited(state, current_base):
        return rotate_to_next_model(api_key, state, "cooldown_active")

    # Test current model
    now = datetime.now().isoformat()
    print(f"[{now}] Testing: {current_base}")
    success, error = test_model(api_key, current_base)

    if success:
        print("  Status: OK")
        return False  # No rotation needed
    else:
        print(f"  Status: {error}")
        if error == "rate_limit":
            mark_rate_limited(state, current_base)
        return rotate_to_next_model(api_key, state, error)


def cleanup_old_rate_limits(state: dict) -> None:
    """Remove rate limit entries that have expired."""
    rate_limited = state.get("rate_limited_models")
    if not rate_limited:
        return
        
    current_time = datetime.now()
    expired = []

    for model_id, limited_at_str in rate_limited.items():
        try:
            limited_at = datetime.fromisoformat(limited_at_str)
            if current_time - limited_at > RATE_LIMIT_COOLDOWN:
                expired.append(model_id)
        except (ValueError, TypeError):
            expired.append(model_id)

    if expired:
        for model_id in expired:
            del rate_limited[model_id]
            print(f"  Cleared cooldown: {model_id}")
        save_state(state)


def run_once() -> None:
    """Run a single check and rotate cycle."""
    api_key = get_api_key()
    if not api_key:
        print("Error: OPENROUTER_API_KEY not set")
        sys.exit(1)

    state = load_state()
    cleanup_old_rate_limits(state)
    check_and_rotate(api_key, state)


def run_daemon() -> None:
    """Run as a continuous daemon."""
    api_key = get_api_key()
    if not api_key:
        print("Error: OPENROUTER_API_KEY not set")
        sys.exit(1)

    print("FreeRide Watcher started")
    print(f"Check interval: {CHECK_INTERVAL_SECONDS}s")
    print(f"Rate limit cooldown: {RATE_LIMIT_COOLDOWN_MINUTES}m")
    print("-" * 50)

    # Handle graceful shutdown
    running = True
    def signal_handler(signum, frame):
        nonlocal running
        print("\nShutting down watcher...")
        running = False

    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)

    state = load_state()
    last_cleanup = time.time()

    try:
        while running:
            try:
                # Cleanup old rate limits every 5 minutes
                now = time.time()
                if now - last_cleanup > 300:
                    cleanup_old_rate_limits(state)
                    last_cleanup = now
                    
                check_and_rotate(api_key, state)
            except Exception as e:
                print(f"Error during check: {e}")

            # Sleep in small increments to allow graceful shutdown
            for _ in range(CHECK_INTERVAL_SECONDS):
                if not running:
                    break
                time.sleep(1)
    finally:
        # Clean up session
        FreeRideSession().close()

    print("Watcher stopped.")


def show_status() -> None:
    """Show watcher status."""
    state = load_state()
    print("FreeRide Watcher Status")
    print("=" * 40)
    print(f"Total rotations: {state.get('rotation_count', 0)}")
    print(f"Last rotation: {state.get('last_rotation', 'Never')}")
    print(f"Last reason: {state.get('last_rotation_reason', 'N/A')}")
    print("\nModels in cooldown:")
    rate_limited = state.get("rate_limited_models", {})
    if rate_limited:
        for model, limited_at in rate_limited.items():
            print(f"  - {model} (since {limited_at})")
    else:
        print("  None")


def clear_cooldowns() -> None:
    """Clear all rate limit cooldowns."""
    state = load_state()
    state["rate_limited_models"] = {}
    save_state(state)
    print("Cleared all rate limit cooldowns.")


def force_rotate() -> None:
    """Force rotate to next model."""
    api_key = get_api_key()
    if not api_key:
        print("Error: OPENROUTER_API_KEY not set")
        sys.exit(1)
    state = load_state()
    rotate_to_next_model(api_key, state, "manual_rotation")


def main():
    parser = argparse.ArgumentParser(
        prog="freeride-watcher",
        description="FreeRide Watcher - Monitor and auto-rotate free AI models"
    )
    parser.add_argument("--daemon", "-d", action="store_true",
                       help="Run as continuous daemon")
    parser.add_argument("--rotate", "-r", action="store_true",
                       help="Force rotate to next model")
    parser.add_argument("--status", "-s", action="store_true",
                       help="Show watcher status")
    parser.add_argument("--clear-cooldowns", action="store_true",
                       help="Clear all rate limit cooldowns")

    args = parser.parse_args()

    try:
        if args.status:
            show_status()
        elif args.clear_cooldowns:
            clear_cooldowns()
        elif args.rotate:
            force_rotate()
        elif args.daemon:
            run_daemon()
        else:
            run_once()
    finally:
        # Ensure session cleanup
        FreeRideSession().close()


if __name__ == "__main__":
    main()
