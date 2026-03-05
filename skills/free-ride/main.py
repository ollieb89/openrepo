#!/usr/bin/env python3
"""
FreeRide - Free AI for OpenClaw
Automatically manage and switch between free AI models on OpenRouter
for unlimited free AI access.
"""

from __future__ import annotations

import argparse
import json
import os
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
    USE_ORJSON = True
    
    def json_loads(data: str | bytes) -> Any:
        return orjson.loads(data)
    
    def json_dumps(obj: Any, indent: bool = False) -> str:
        option = orjson.OPT_INDENT_2 if indent else 0
        return orjson.dumps(obj, option=option).decode('utf-8')
        
except ImportError:
    USE_ORJSON = False
    json_loads = json.loads
    json_dumps = lambda obj, indent=False: json.dumps(obj, indent=2 if indent else None)

try:
    import requests
    from requests.adapters import HTTPAdapter
    from urllib3.util.retry import Retry
except ImportError:
    print("Error: requests library required. Install with: pip install requests")
    sys.exit(1)


# Constants
OPENROUTER_API_URL = "https://openrouter.ai/api/v1/models"
OPENCLAW_CONFIG_PATH = Path.home() / ".openclaw" / "openclaw.json"
CACHE_FILE = Path.home() / ".openclaw" / ".freeride-cache.json"
CACHE_DURATION_HOURS = 6

# Free model ranking criteria (higher is better)
RANKING_WEIGHTS = {
    "context_length": 0.4,      # Prefer longer context
    "capabilities": 0.3,        # Prefer more capabilities
    "recency": 0.2,            # Prefer newer models
    "provider_trust": 0.1       # Prefer trusted providers
}

# Trusted providers (in order of preference) - use tuple for immutability
TRUSTED_PROVIDERS = (
    "google", "meta-llama", "mistralai", "deepseek",
    "nvidia", "qwen", "microsoft", "allenai", "arcee-ai"
)

# Build set for O(1) lookups
TRUSTED_PROVIDERS_SET = set(TRUSTED_PROVIDERS)
TRUSTED_PROVIDERS_COUNT = len(TRUSTED_PROVIDERS)

# Provider trust scores - precomputed for O(1) lookup
PROVIDER_TRUST_SCORES = {
    provider: 1 - (idx / TRUSTED_PROVIDERS_COUNT)
    for idx, provider in enumerate(TRUSTED_PROVIDERS)
}

# Special model handling - precomputed constants
OPENROUTER_FREE_ROUTER = "openrouter/free"
OPENROUTER_PREFIX = "openrouter/"
FREE_SUFFIX = ":free"


class FreeRideSession:
    """Thread-safe session manager with connection pooling."""
    _instance = None
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._session = None
        return cls._instance
    
    @property
    def session(self) -> requests.Session:
        """Get or create session with connection pooling."""
        if self._session is None:
            self._session = requests.Session()
            # Configure retry strategy
            retry_strategy = Retry(
                total=3,
                backoff_factor=1,
                status_forcelist=[429, 500, 502, 503, 504],
            )
            adapter = HTTPAdapter(
                pool_connections=10,
                pool_maxsize=10,
                max_retries=retry_strategy
            )
            self._session.mount("https://", adapter)
            self._session.mount("http://", adapter)
        return self._session
    
    def close(self):
        """Close the session."""
        if self._session:
            self._session.close()
            self._session = None


def get_session() -> requests.Session:
    """Get the global session instance."""
    return FreeRideSession().session


def get_api_key() -> str | None:
    """Get OpenRouter API key from environment or OpenClaw config."""
    # Try environment first (fastest)
    api_key = os.environ.get("OPENROUTER_API_KEY")
    if api_key:
        return api_key

    # Try OpenClaw config
    if OPENCLAW_CONFIG_PATH.exists():
        try:
            config = json_loads(OPENCLAW_CONFIG_PATH.read_text())
            # Check env section
            api_key = config.get("env", {}).get("OPENROUTER_API_KEY")
            if api_key:
                return api_key
        except (json.JSONDecodeError, KeyError, OSError):
            pass

    return None


def fetch_all_models(api_key: str) -> list[dict]:
    """Fetch all models from OpenRouter API with connection reuse."""
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json"
    }

    try:
        session = get_session()
        response = session.get(OPENROUTER_API_URL, headers=headers, timeout=30)
        response.raise_for_status()
        data = response.json()
        return data.get("data", [])
    except requests.RequestException as e:
        print(f"Error fetching models: {e}")
        return []


def _is_free_model(model: dict) -> bool:
    """Check if a single model is free - for use in list comprehension."""
    model_id = model.get("id", "")
    
    # Fast path: check :free suffix first (cheaper than parsing pricing)
    if FREE_SUFFIX in model_id:
        return True
    
    # Check pricing.prompt == 0
    pricing = model.get("pricing", {})
    prompt_cost = pricing.get("prompt")
    if prompt_cost is not None:
        try:
            return float(prompt_cost) == 0
        except (ValueError, TypeError):
            pass
    
    return False


def filter_free_models(models: list[dict]) -> list[dict]:
    """Filter models to only include free ones using list comprehension."""
    return [m for m in models if _is_free_model(m)]


def calculate_model_score(model: dict) -> float:
    """Calculate a ranking score for a model based on multiple criteria."""
    score = 0.0
    
    # Context length score (normalized to 0-1, max 1M tokens)
    context_length = model.get("context_length", 0)
    context_score = min(context_length / 1_000_000, 1.0)
    score += context_score * RANKING_WEIGHTS["context_length"]

    # Capabilities score
    capabilities = model.get("supported_parameters", ())
    capability_count = len(capabilities) if capabilities else 0
    capability_score = min(capability_count / 10, 1.0)
    score += capability_score * RANKING_WEIGHTS["capabilities"]

    # Recency score (based on creation date)
    created = model.get("created", 0)
    if created:
        days_old = (time.time() - created) / 86400
        recency_score = max(0.0, 1.0 - (days_old / 365))
        score += recency_score * RANKING_WEIGHTS["recency"]

    # Provider trust score - O(1) lookup
    model_id = model.get("id", "")
    if "/" in model_id:
        provider = model_id.split("/", 1)[0]
        trust_score = PROVIDER_TRUST_SCORES.get(provider, 0.0)
        score += trust_score * RANKING_WEIGHTS["provider_trust"]

    return score


def rank_free_models(models: list[dict]) -> list[dict]:
    """Rank free models by quality score."""
    # Calculate scores and sort in one pass using Schwartzian transform pattern
    scored = [(calculate_model_score(m), m) for m in models]
    scored.sort(key=lambda x: x[0], reverse=True)
    return [{**m, "_score": s} for s, m in scored]


def get_cached_models() -> list[dict] | None:
    """Get cached model list if still valid."""
    if not CACHE_FILE.exists():
        return None

    try:
        cache = json_loads(CACHE_FILE.read_text())
        cached_at = datetime.fromisoformat(cache.get("cached_at", ""))
        if datetime.now() - cached_at < timedelta(hours=CACHE_DURATION_HOURS):
            return cache.get("models", [])
    except (json.JSONDecodeError, ValueError, OSError):
        pass

    return None


def save_models_cache(models: list[dict]) -> None:
    """Save models to cache file atomically."""
    CACHE_FILE.parent.mkdir(parents=True, exist_ok=True)
    cache = {
        "cached_at": datetime.now().isoformat(),
        "models": models
    }
    # Write to temp file then rename for atomicity
    temp_file = CACHE_FILE.with_suffix('.tmp')
    try:
        temp_file.write_text(json_dumps(cache, indent=True))
        temp_file.replace(CACHE_FILE)
    except OSError:
        # Fallback to direct write
        CACHE_FILE.write_text(json_dumps(cache, indent=True))


def get_free_models(api_key: str, force_refresh: bool = False) -> list[dict]:
    """Get ranked free models (from cache or API)."""
    if not force_refresh:
        cached = get_cached_models()
        if cached is not None:
            return cached

    all_models = fetch_all_models(api_key)
    free_models = filter_free_models(all_models)
    ranked_models = rank_free_models(free_models)

    save_models_cache(ranked_models)
    return ranked_models


@lru_cache(maxsize=1)
def load_openclaw_config_cached() -> dict:
    """Load OpenClaw configuration with caching."""
    if not OPENCLAW_CONFIG_PATH.exists():
        return {}

    try:
        return json_loads(OPENCLAW_CONFIG_PATH.read_text())
    except (json.JSONDecodeError, OSError):
        return {}


def load_openclaw_config() -> dict:
    """Load OpenClaw configuration (fresh read, no cache)."""
    if not OPENCLAW_CONFIG_PATH.exists():
        return {}

    try:
        return json_loads(OPENCLAW_CONFIG_PATH.read_text())
    except (json.JSONDecodeError, OSError):
        return {}


def save_openclaw_config(config: dict) -> None:
    """Save OpenClaw configuration atomically."""
    OPENCLAW_CONFIG_PATH.parent.mkdir(parents=True, exist_ok=True)
    temp_file = OPENCLAW_CONFIG_PATH.with_suffix('.tmp')
    try:
        temp_file.write_text(json_dumps(config, indent=True))
        temp_file.replace(OPENCLAW_CONFIG_PATH)
    except OSError:
        OPENCLAW_CONFIG_PATH.write_text(json_dumps(config, indent=True))
    # Invalidate cache after save
    load_openclaw_config_cached.cache_clear()


def format_model_for_openclaw(model_id: str, with_provider_prefix: bool = True) -> str:
    """Format model ID for OpenClaw config efficiently."""
    # Handle openrouter/free special case
    if model_id in ("openrouter/free", "openrouter/free:free"):
        return "openrouter/openrouter/free" if with_provider_prefix else "openrouter/free"

    # Remove existing openrouter/ prefix if present
    if model_id.startswith(OPENROUTER_PREFIX):
        base_id = model_id[len(OPENROUTER_PREFIX):]
    else:
        base_id = model_id

    # Ensure :free suffix
    if FREE_SUFFIX not in base_id:
        base_id = f"{base_id}{FREE_SUFFIX}"

    if with_provider_prefix:
        return f"openrouter/{base_id}"
    return base_id


def get_current_model(config: dict | None = None) -> str | None:
    """Get currently configured model in OpenClaw."""
    if config is None:
        config = load_openclaw_config()
    try:
        return config["agents"]["defaults"]["model"]["primary"]
    except (KeyError, TypeError):
        return None


def get_current_fallbacks(config: dict | None = None) -> list[str]:
    """Get currently configured fallback models."""
    if config is None:
        config = load_openclaw_config()
    try:
        return config["agents"]["defaults"]["model"]["fallbacks"]
    except (KeyError, TypeError):
        return []


def ensure_config_structure(config: dict) -> dict:
    """Ensure the config has the required nested structure."""
    # Use setdefault for efficient nested dict creation
    defaults = config.setdefault("agents", {}).setdefault("defaults", {})
    defaults.setdefault("model", {})
    defaults.setdefault("models", {})
    return config


def setup_openrouter_auth(config: dict) -> dict:
    """Set up OpenRouter auth profile if not exists."""
    auth_profiles = config.setdefault("auth", {}).setdefault("profiles", {})
    
    if "openrouter:default" not in auth_profiles:
        auth_profiles["openrouter:default"] = {
            "provider": "openrouter",
            "mode": "api_key"
        }
        print("Added OpenRouter auth profile.")

    return config


def _build_fallback_list(
    free_models: list[dict],
    formatted_primary: str,
    formatted_for_list: str,
    current_primary: str | None,
    fallback_count: int,
    models_dict: dict
) -> list[str]:
    """Build fallback list efficiently."""
    new_fallbacks = []
    free_router = OPENROUTER_FREE_ROUTER
    free_router_primary = format_model_for_openclaw("openrouter/free", with_provider_prefix=True)
    
    # Always add openrouter/free as first fallback (if not primary)
    if formatted_primary != free_router_primary and formatted_for_list != free_router:
        new_fallbacks.append(free_router)
        models_dict[free_router] = {}

    # Pre-compute skip conditions
    skip_primary = formatted_for_list
    skip_primary_prefixed = formatted_primary
    skip_current = current_primary if current_primary else None
    
    for m in free_models:
        if len(new_fallbacks) >= fallback_count:
            break

        m_id = m["id"]
        
        # Skip openrouter/free (already added as first)
        if OPENROUTER_FREE_ROUTER in m_id:
            continue

        m_formatted = format_model_for_openclaw(m_id, with_provider_prefix=False)
        m_formatted_primary = format_model_for_openclaw(m_id, with_provider_prefix=True)

        # Skip if it's the new primary or current primary
        if m_formatted == skip_primary or m_formatted_primary == skip_primary_prefixed:
            continue
        if skip_current and m_formatted_primary == skip_current:
            continue

        new_fallbacks.append(m_formatted)
        models_dict[m_formatted] = {}

    return new_fallbacks


def update_model_config(
    model_id: str,
    as_primary: bool = True,
    add_fallbacks: bool = True,
    fallback_count: int = 5,
    setup_auth: bool = False
) -> bool:
    """Update OpenClaw config with the specified model."""
    config = load_openclaw_config()
    config = ensure_config_structure(config)

    if setup_auth:
        config = setup_openrouter_auth(config)

    formatted_primary = format_model_for_openclaw(model_id, with_provider_prefix=True)
    formatted_for_list = format_model_for_openclaw(model_id, with_provider_prefix=False)

    if as_primary:
        config["agents"]["defaults"]["model"]["primary"] = formatted_primary
        config["agents"]["defaults"]["models"][formatted_for_list] = {}

    if add_fallbacks:
        api_key = get_api_key()
        if api_key:
            free_models = get_free_models(api_key)
            models_dict = config["agents"]["defaults"]["models"]
            current_primary = config["agents"]["defaults"]["model"].get("primary")

            new_fallbacks = _build_fallback_list(
                free_models,
                formatted_primary,
                formatted_for_list,
                current_primary,
                fallback_count,
                models_dict
            )

            # If not setting as primary, prepend new model to fallbacks
            if not as_primary and formatted_for_list not in new_fallbacks:
                insert_pos = 1 if OPENROUTER_FREE_ROUTER in new_fallbacks else 0
                new_fallbacks.insert(insert_pos, formatted_for_list)
                models_dict[formatted_for_list] = {}

            config["agents"]["defaults"]["model"]["fallbacks"] = new_fallbacks

    save_openclaw_config(config)
    return True


# ============== Command Handlers ==============

def _format_context(context: int) -> str:
    """Format context length for display."""
    if context >= 1_000_000:
        return f"{context // 1_000_000}M tokens"
    elif context >= 1_000:
        return f"{context // 1_000}K tokens"
    return f"{context} tokens"


def cmd_list(args: argparse.Namespace) -> None:
    """List available free models ranked by quality."""
    api_key = get_api_key()
    if not api_key:
        print("Error: OPENROUTER_API_KEY not set")
        print("Set it via: export OPENROUTER_API_KEY='sk-or-...'")
        print("Or get a free key at: https://openrouter.ai/keys")
        sys.exit(1)

    print("Fetching free models from OpenRouter...")
    models = get_free_models(api_key, force_refresh=args.refresh)

    if not models:
        print("No free models available.")
        return

    current = get_current_model()
    fallbacks = get_current_fallbacks()
    fallback_set = set(fallbacks)  # O(1) lookups
    limit = args.limit if args.limit else 15

    print(f"\nTop {min(limit, len(models))} Free AI Models (ranked by quality):\n")
    print(f"{'#':<3} {'Model ID':<50} {'Context':<12} {'Score':<8} {'Status'}")
    print("-" * 90)

    for i, model in enumerate(models[:limit], 1):
        model_id = model.get("id", "unknown")
        context_str = _format_context(model.get("context_length", 0))
        score = model.get("_score", 0)

        # Check status with O(1) set lookup
        formatted = format_model_for_openclaw(model_id, with_provider_prefix=True)
        formatted_fallback = format_model_for_openclaw(model_id, with_provider_prefix=False)

        if current and formatted == current:
            status = "[PRIMARY]"
        elif formatted_fallback in fallback_set or formatted in fallback_set:
            status = "[FALLBACK]"
        else:
            status = ""

        print(f"{i:<3} {model_id:<50} {context_str:<12} {score:.3f}    {status}")

    if len(models) > limit:
        print(f"\n... and {len(models) - limit} more. Use --limit to see more.")

    print(f"\nTotal free models available: {len(models)}")
    print("\nCommands:")
    print("  freeride switch <model>      Set as primary model")
    print("  freeride switch <model> -f   Add to fallbacks only (keep current primary)")
    print("  freeride auto                Auto-select best model")


def cmd_switch(args: argparse.Namespace) -> None:
    """Switch to a specific free model."""
    api_key = get_api_key()
    if not api_key:
        print("Error: OPENROUTER_API_KEY not set")
        sys.exit(1)

    model_id = args.model
    as_fallback = args.fallback_only

    # Validate model exists and is free
    models = get_free_models(api_key)
    model_ids = [m["id"] for m in models]
    model_set = set(model_ids)  # O(1) lookup

    # Check for exact match first (fast path)
    matched_model = model_id if model_id in model_set else None
    
    # Try partial match if no exact match
    if matched_model is None:
        model_id_lower = model_id.lower()
        for m_id in model_ids:
            if model_id_lower in m_id.lower():
                matched_model = m_id
                break

    if not matched_model:
        print(f"Error: Model '{model_id}' not found in free models list.")
        print("Use 'freeride list' to see available models.")
        sys.exit(1)

    if as_fallback:
        print(f"Adding to fallbacks: {matched_model}")
    else:
        print(f"Setting as primary: {matched_model}")

    if update_model_config(
        matched_model,
        as_primary=not as_fallback,
        add_fallbacks=not args.no_fallbacks,
        setup_auth=args.setup_auth
    ):
        config = load_openclaw_config()

        if as_fallback:
            print("Success! Added to fallbacks.")
            print(f"Primary model (unchanged): {get_current_model(config)}")
        else:
            print("Success! OpenClaw config updated.")
            print(f"Primary model: {get_current_model(config)}")

        fallbacks = get_current_fallbacks(config)
        if fallbacks:
            print(f"Fallback models ({len(fallbacks)}):")
            for fb in fallbacks[:5]:
                print(f"  - {fb}")
            if len(fallbacks) > 5:
                print(f"  ... and {len(fallbacks) - 5} more")

        print("\nRestart OpenClaw for changes to take effect.")
    else:
        print("Error: Failed to update OpenClaw config.")
        sys.exit(1)


def cmd_auto(args: argparse.Namespace) -> None:
    """Automatically select the best free model."""
    api_key = get_api_key()
    if not api_key:
        print("Error: OPENROUTER_API_KEY not set")
        sys.exit(1)

    config = load_openclaw_config()
    current_primary = get_current_model(config)

    print("Finding best free model...")
    models = get_free_models(api_key, force_refresh=True)

    if not models:
        print("Error: No free models available.")
        sys.exit(1)

    # Find best SPECIFIC model (skip openrouter/free router)
    best_model = None
    for m in models:
        if OPENROUTER_FREE_ROUTER not in m["id"]:
            best_model = m
            break

    if not best_model:
        best_model = models[0]

    model_id = best_model["id"]
    context = best_model.get("context_length", 0)
    score = best_model.get("_score", 0)

    as_fallback = args.fallback_only

    if not as_fallback:
        if current_primary:
            print(f"\nReplacing current primary: {current_primary}")
        print(f"\nBest free model: {model_id}")
        print(f"Context length: {context:,} tokens")
        print(f"Quality score: {score:.3f}")
    else:
        print(f"\nKeeping current primary, adding fallbacks only.")
        print(f"Best available: {model_id} ({context:,} tokens, score: {score:.3f})")

    if update_model_config(
        model_id,
        as_primary=not as_fallback,
        add_fallbacks=True,
        fallback_count=args.fallback_count,
        setup_auth=args.setup_auth
    ):
        config = load_openclaw_config()

        if as_fallback:
            print("\nFallbacks configured!")
            print(f"Primary (unchanged): {get_current_model(config)}")
            print("First fallback: openrouter/free (smart router - auto-selects best available)")
        else:
            print("\nOpenClaw config updated!")
            print(f"Primary: {get_current_model(config)}")

        fallbacks = get_current_fallbacks(config)
        if fallbacks:
            print(f"Fallbacks ({len(fallbacks)}):")
            for fb in fallbacks:
                print(f"  - {fb}")

        print("\nRestart OpenClaw for changes to take effect.")
    else:
        print("Error: Failed to update config.")
        sys.exit(1)


def cmd_status(args: argparse.Namespace) -> None:
    """Show current configuration status."""
    api_key = get_api_key()
    config = load_openclaw_config()
    current = get_current_model(config)
    fallbacks = get_current_fallbacks(config)

    print("FreeRide Status")
    print("=" * 50)

    # API Key status
    if api_key:
        masked = f"{api_key[:8]}...{api_key[-4:]}" if len(api_key) > 12 else "***"
        print(f"OpenRouter API Key: {masked}")
    else:
        print("OpenRouter API Key: NOT SET")
        print("  Set with: export OPENROUTER_API_KEY='sk-or-...'")

    # Auth profile status
    auth_profiles = config.get("auth", {}).get("profiles", {})
    if "openrouter:default" in auth_profiles:
        print("OpenRouter Auth Profile: Configured")
    else:
        print("OpenRouter Auth Profile: Not set (use --setup-auth to add)")

    # Current model
    print(f"\nPrimary Model: {current or 'Not configured'}")

    # Fallbacks
    if fallbacks:
        print(f"Fallback Models ({len(fallbacks)}):")
        for fb in fallbacks:
            print(f"  - {fb}")
    else:
        print("Fallback Models: None configured")

    # Cache status
    if CACHE_FILE.exists():
        try:
            cache = json_loads(CACHE_FILE.read_text())
            cached_at = datetime.fromisoformat(cache.get("cached_at", ""))
            models_count = len(cache.get("models", []))
            age = datetime.now() - cached_at
            hours = age.seconds // 3600
            mins = (age.seconds % 3600) // 60
            print(f"\nModel Cache: {models_count} models (updated {hours}h {mins}m ago)")
        except (json.JSONDecodeError, ValueError, OSError):
            print("\nModel Cache: Invalid")
    else:
        print("\nModel Cache: Not created yet")

    # OpenClaw config path
    print(f"\nOpenClaw Config: {OPENCLAW_CONFIG_PATH}")
    print(f"  Exists: {'Yes' if OPENCLAW_CONFIG_PATH.exists() else 'No'}")


def cmd_refresh(args: argparse.Namespace) -> None:
    """Force refresh the model cache."""
    api_key = get_api_key()
    if not api_key:
        print("Error: OPENROUTER_API_KEY not set")
        sys.exit(1)

    print("Refreshing free models cache...")
    models = get_free_models(api_key, force_refresh=True)
    print(f"Cached {len(models)} free models.")
    print(f"Cache expires in {CACHE_DURATION_HOURS} hours.")


def cmd_fallbacks(args: argparse.Namespace) -> None:
    """Configure fallback models for rate limit handling."""
    api_key = get_api_key()
    if not api_key:
        print("Error: OPENROUTER_API_KEY not set")
        sys.exit(1)

    config = load_openclaw_config()
    current = get_current_model(config)

    if not current:
        print("Warning: No primary model configured.")
        print("Fallbacks will still be added.")

    print(f"Current primary: {current or 'None'}")
    print(f"Setting up {args.count} fallback models...")

    models = get_free_models(api_key)
    config = ensure_config_structure(config)

    # Get fallbacks excluding current model
    fallbacks = []
    models_dict = config["agents"]["defaults"]["model"]["models"]

    # Always add openrouter/free as first fallback (smart router)
    free_router = OPENROUTER_FREE_ROUTER
    free_router_primary = format_model_for_openclaw("openrouter/free", with_provider_prefix=True)
    if not current or current != free_router_primary:
        fallbacks.append(free_router)
        models_dict[free_router] = {}

    for m in models:
        formatted = format_model_for_openclaw(m["id"], with_provider_prefix=False)
        formatted_primary = format_model_for_openclaw(m["id"], with_provider_prefix=True)

        if current and formatted_primary == current:
            continue
        if OPENROUTER_FREE_ROUTER in m["id"]:
            continue
        if len(fallbacks) >= args.count:
            break

        fallbacks.append(formatted)
        models_dict[formatted] = {}

    config["agents"]["defaults"]["model"]["fallbacks"] = fallbacks
    save_openclaw_config(config)

    print(f"\nConfigured {len(fallbacks)} fallback models:")
    for i, fb in enumerate(fallbacks, 1):
        print(f"  {i}. {fb}")

    print("\nWhen rate limited, OpenClaw will automatically try these models.")
    print("Restart OpenClaw for changes to take effect.")


def main():
    parser = argparse.ArgumentParser(
        prog="freeride",
        description="FreeRide - Free AI for OpenClaw. Manage free models from OpenRouter."
    )
    subparsers = parser.add_subparsers(dest="command", help="Available commands")

    # list command
    list_parser = subparsers.add_parser("list", help="List available free models")
    list_parser.add_argument("--limit", "-n", type=int, default=15,
                            help="Number of models to show (default: 15)")
    list_parser.add_argument("--refresh", "-r", action="store_true",
                            help="Force refresh from API (ignore cache)")

    # switch command
    switch_parser = subparsers.add_parser("switch", help="Switch to a specific model")
    switch_parser.add_argument("model", help="Model ID to switch to")
    switch_parser.add_argument("--fallback-only", "-f", action="store_true",
                              help="Add to fallbacks only, don't change primary")
    switch_parser.add_argument("--no-fallbacks", action="store_true",
                              help="Don't configure fallback models")
    switch_parser.add_argument("--setup-auth", action="store_true",
                              help="Also set up OpenRouter auth profile")

    # auto command
    auto_parser = subparsers.add_parser("auto", help="Auto-select best free model")
    auto_parser.add_argument("--fallback-count", "-c", type=int, default=5,
                            help="Number of fallback models (default: 5)")
    auto_parser.add_argument("--fallback-only", "-f", action="store_true",
                            help="Add to fallbacks only, don't change primary")
    auto_parser.add_argument("--setup-auth", action="store_true",
                            help="Also set up OpenRouter auth profile")

    # status command
    subparsers.add_parser("status", help="Show current configuration")

    # refresh command
    subparsers.add_parser("refresh", help="Refresh model cache")

    # fallbacks command
    fallbacks_parser = subparsers.add_parser("fallbacks", help="Configure fallback models")
    fallbacks_parser.add_argument("--count", "-c", type=int, default=5,
                                 help="Number of fallback models (default: 5)")

    args = parser.parse_args()

    try:
        if args.command == "list":
            cmd_list(args)
        elif args.command == "switch":
            cmd_switch(args)
        elif args.command == "auto":
            cmd_auto(args)
        elif args.command == "status":
            cmd_status(args)
        elif args.command == "refresh":
            cmd_refresh(args)
        elif args.command == "fallbacks":
            cmd_fallbacks(args)
        else:
            parser.print_help()
            sys.exit(1)
    finally:
        # Clean up session
        FreeRideSession().close()


if __name__ == "__main__":
    main()
