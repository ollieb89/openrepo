"""
Pattern Extraction Engine — orchestration/suggest.py

Queries memU for rejection memories and workspace-state.json activity logs,
clusters by keyword frequency, and generates SOUL amendment suggestions.

Writes pending suggestions to workspace/.openclaw/<project_id>/soul-suggestions.json.
Does NOT write to soul-override.md — that is the exclusive domain of the accept
API route (ADV-06 structural gate).

CLI usage:
    python3 orchestration/suggest.py --project pumplai [--dry-run] [--lookback-days 30]
"""

# ---------------------------------------------------------------------------
# sys.path guard — must run before ANY stdlib imports
#
# When executed directly as `python3 orchestration/suggest.py`, Python inserts
# the script's parent directory (`orchestration/`) into sys.path[0]. This
# shadows the stdlib `logging` module with our local `orchestration/logging.py`,
# which breaks asyncio (asyncio → concurrent.futures → logging).
#
# Fix: replace orchestration/ on sys.path with the project root so stdlib
# names are resolved correctly and `import orchestration.*` still works.
# ---------------------------------------------------------------------------
import sys as _sys
import os as _os

_this_dir = _os.path.dirname(_os.path.abspath(__file__))
_project_root = _os.path.dirname(_this_dir)
# Replace orchestration/ with project root at the front of sys.path
if _this_dir in _sys.path:
    _idx = _sys.path.index(_this_dir)
    _sys.path[_idx] = _project_root
elif _project_root not in _sys.path:
    _sys.path.insert(0, _project_root)

import asyncio
import hashlib
import json
import re
import time
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List, Optional

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

REJECTION_QUERY = "task failed rejected error agent mistake"
MIN_CLUSTER_SIZE = 3           # ADV-01 requirement: ≥3 similar rejections
DEFAULT_LOOKBACK_DAYS = 30
MAX_CLUSTER_FRACTION = 0.5     # Discard clusters spanning >50% of memories (Pitfall 2)
DOMAIN_STOPWORDS = {           # Domain-specific stopwords beyond length filter
    "task", "agent", "error", "failed", "status", "completed",
    "the", "a", "an", "to", "in", "of", "and", "or", "was", "is",
    "that", "this", "with", "from", "for", "not", "but",
}


# ---------------------------------------------------------------------------
# Path helpers
# ---------------------------------------------------------------------------

def _suggestions_path(project_id: str) -> Path:
    """
    Return the per-project suggestions file path.

    Path: <project_root>/workspace/.openclaw/<project_id>/soul-suggestions.json

    Lazy import of _find_project_root so this module is testable without
    the full orchestration stack loaded.
    """
    from orchestration.project_config import _find_project_root  # lazy import
    root = _find_project_root()
    return root / "workspace" / ".openclaw" / project_id / "soul-suggestions.json"


# ---------------------------------------------------------------------------
# I/O helpers
# ---------------------------------------------------------------------------

def _load_suggestions(project_id: str) -> dict:
    """
    Load existing suggestions from disk.

    Returns the empty schema dict on FileNotFoundError or JSONDecodeError —
    callers always receive a valid structure.
    """
    empty = {"version": "1.0", "last_run": None, "suggestions": []}
    try:
        path = _suggestions_path(project_id)
        with open(path) as f:
            data = json.load(f)
        return data
    except (FileNotFoundError, json.JSONDecodeError):
        return empty


def _save_suggestions(
    project_id: str,
    new_suggestions: List[dict],
    dry_run: bool = False,
) -> None:
    """
    Merge new suggestions into the existing store and write to disk.

    - Loads the existing file (or empty schema if absent).
    - Deduplicates by id — existing entries are preserved, new ones appended.
    - Updates last_run to the current UTC timestamp.
    - If dry_run=True: prints the merged result as JSON without writing.
    - If not dry_run: writes atomically (write to .tmp, then rename).
    """
    existing = _load_suggestions(project_id)

    # Build id → entry index for existing suggestions
    existing_ids = {s["id"]: i for i, s in enumerate(existing["suggestions"])}

    for sug in new_suggestions:
        if sug["id"] not in existing_ids:
            existing["suggestions"].append(sug)

    existing["last_run"] = datetime.now(timezone.utc).isoformat()

    if dry_run:
        print(json.dumps(existing, indent=2))
        return

    dest = _suggestions_path(project_id)
    dest.parent.mkdir(parents=True, exist_ok=True)
    tmp = dest.with_suffix(".json.tmp")
    with open(tmp, "w") as f:
        json.dump(existing, f, indent=2)
    tmp.rename(dest)


# ---------------------------------------------------------------------------
# Keyword extraction
# ---------------------------------------------------------------------------

def _extract_keywords(text: str) -> List[str]:
    """
    Normalize text and return meaningful keywords.

    Rules:
    - Lowercase the text
    - Extract tokens matching [a-z][a-z_-]+
    - Keep only tokens with len >= 4 AND not in DOMAIN_STOPWORDS
    """
    text = text.lower()
    words = re.findall(r"[a-z][a-z_-]+", text)
    return [w for w in words if len(w) >= 4 and w not in DOMAIN_STOPWORDS]


# ---------------------------------------------------------------------------
# Clustering
# ---------------------------------------------------------------------------

def _cluster_memories(
    memories: List[dict],
    lookback_days: int,
) -> Dict[str, List[dict]]:
    """
    Cluster memories by keyword frequency.

    Steps:
    1. Filter to memories within the lookback window.
    2. Build keyword → [memory, ...] buckets.
    3. Discard clusters spanning > MAX_CLUSTER_FRACTION of recent memories (too generic).
    4. Return only clusters with len >= MIN_CLUSTER_SIZE.

    Returns {keyword: [memory, ...]} for clusters that pass both filters.
    """
    cutoff = time.time() - (lookback_days * 86400)

    recent: List[dict] = []
    for m in memories:
        ts = m.get("created_at") or m.get("timestamp", 0)
        # Handle both int/float unix timestamps and ISO string timestamps
        if isinstance(ts, str):
            try:
                ts = datetime.fromisoformat(ts.replace("Z", "+00:00")).timestamp()
            except (ValueError, AttributeError):
                ts = 0
        if ts >= cutoff:
            recent.append(m)

    if not recent:
        return {}

    keyword_to_memories: Dict[str, List[dict]] = defaultdict(list)
    for mem in recent:
        content = mem.get("content", mem.get("resource_url", ""))
        for kw in _extract_keywords(content):
            keyword_to_memories[kw].append(mem)

    total = len(recent)
    result: Dict[str, List[dict]] = {}
    for kw, mems in keyword_to_memories.items():
        # Discard too-generic clusters
        if len(mems) >= MAX_CLUSTER_FRACTION * total:
            continue
        # Keep only clusters meeting minimum threshold
        if len(mems) >= MIN_CLUSTER_SIZE:
            result[kw] = mems

    return result


# ---------------------------------------------------------------------------
# Suppression helpers
# ---------------------------------------------------------------------------

def _fingerprint(keyword: str, evidence_count: int) -> str:
    """Return a fingerprint string for rejection-suppression lookup."""
    return f"{keyword}:{evidence_count}"


def _should_suppress(keyword: str, cluster_size: int, existing: dict) -> bool:
    """
    Return True if a rejected suggestion for this keyword should suppress
    re-generation of a new suggestion.

    Suppression is active when:
    - An existing suggestion has status == "rejected"
    - Its id was generated from the same keyword (checked via id prefix derived from md5)
    - The current cluster_size < rejected_entry["suppressed_until_count"]

    Re-surfaces once cluster_size >= suppressed_until_count.
    """
    target_id_prefix = "sug-" + hashlib.md5(keyword.encode()).hexdigest()[:6]

    for sug in existing.get("suggestions", []):
        if sug.get("status") != "rejected":
            continue
        if sug.get("id") != target_id_prefix:
            continue
        suppressed_until = sug.get("suppressed_until_count")
        if suppressed_until is not None and cluster_size < suppressed_until:
            return True

    return False


# ---------------------------------------------------------------------------
# Suggestion builder
# ---------------------------------------------------------------------------

def _build_suggestion(keyword: str, memories: List[dict]) -> dict:
    """
    Build a suggestion dict from a keyword cluster.

    Schema matches RESEARCH.md soul-suggestions.json spec.
    """
    suggestion_id = "sug-" + hashlib.md5(keyword.encode()).hexdigest()[:6]

    pattern_description = (
        f"Agents frequently encounter '{keyword}'-related issues "
        f"({len(memories)} occurrences)"
    )

    evidence_examples = []
    for m in memories[:3]:
        content = m.get("content", m.get("resource_url", ""))
        evidence_examples.append({
            "task_id": m.get("task_id", "unknown"),
            "excerpt": content[:120],
        })

    readable_keyword = keyword.replace("-", " ").replace("_", " ").title()
    diff_text = (
        "## BEHAVIORAL PROTOCOLS\n"
        f"- **{readable_keyword} Awareness:** Review task context for "
        f"{keyword}-related edge cases before committing output. "
        "If uncertain, verify by running tests or checking prior task logs."
    )

    return {
        "id": suggestion_id,
        "status": "pending",
        "created_at": time.time(),
        "pattern_description": pattern_description,
        "evidence_count": len(memories),
        "evidence_examples": evidence_examples,
        "diff_text": diff_text,
        "rejected_at": None,
        "rejection_reason": None,
        "suppressed_until_count": None,
        "accepted_at": None,
    }


# ---------------------------------------------------------------------------
# Activity log helpers
# ---------------------------------------------------------------------------

def _load_activity_memories(project_id: str) -> List[dict]:
    """
    Load failed/interrupted task activity log entries from workspace-state.json
    and shape them as memory-like dicts for clustering.

    Returns [] on any error (file missing, JSON error, project not found).
    Per RESEARCH.md: activity log is the primary corpus; memU is supplementary.
    """
    try:
        from orchestration.project_config import get_state_path  # lazy import
        state_path = get_state_path(project_id)
        with open(state_path) as f:
            state = json.load(f)
    except Exception:
        return []

    activity_memories: List[dict] = []
    tasks = state.get("tasks", {})
    for task_id, task_data in tasks.items():
        if not isinstance(task_data, dict):
            continue
        activity_log = task_data.get("activity_log", [])
        for entry in activity_log:
            if not isinstance(entry, dict):
                continue
            entry_status = str(entry.get("status", "")).lower()
            if "failed" in entry_status or "interrupted" in entry_status:
                activity_memories.append({
                    "content": entry.get("entry", ""),
                    "created_at": entry.get("timestamp", 0),
                    "task_id": task_id,
                })

    return activity_memories


def _dedup_memories(memories: List[dict]) -> List[dict]:
    """
    Deduplicate a list of memory dicts by content hash.

    Later entries with the same content as an earlier entry are discarded.
    """
    seen: set = set()
    result: List[dict] = []
    for m in memories:
        content = m.get("content", m.get("resource_url", ""))
        h = hashlib.md5(content.encode()).hexdigest()
        if h not in seen:
            seen.add(h)
            result.append(m)
    return result


# ---------------------------------------------------------------------------
# Main extraction pipeline
# ---------------------------------------------------------------------------

async def run_extraction(
    project_id: str,
    memu_url: str,
    lookback_days: int = DEFAULT_LOOKBACK_DAYS,
) -> List[dict]:
    """
    Full extraction pipeline.

    1. Query memU for rejection-related memories.
    2. Load activity log entries from workspace-state.json (primary corpus).
    3. Merge and deduplicate by content hash.
    4. Cluster by keyword frequency.
    5. Apply suppression check against existing suggestions.
    6. Return list of NEW suggestion dicts (not including already-stored ones).
    """
    from orchestration.memory_client import MemoryClient, AgentType  # lazy import

    # --- memU memories (supplementary) ---
    try:
        async with MemoryClient(memu_url, project_id, AgentType.L2_PM) as client:
            memu_memories = await client.retrieve(REJECTION_QUERY)
    except Exception:
        memu_memories = []

    # --- Activity log memories (primary) ---
    activity_memories = _load_activity_memories(project_id)

    # --- Merge and dedup ---
    all_memories = _dedup_memories(activity_memories + memu_memories)

    # --- Cluster ---
    clusters = _cluster_memories(all_memories, lookback_days)

    # --- Suppression check ---
    existing = _load_suggestions(project_id)
    suggestions: List[dict] = []
    for keyword, mems in clusters.items():
        if _should_suppress(keyword, len(mems), existing):
            continue
        suggestions.append(_build_suggestion(keyword, mems))

    return suggestions


# ---------------------------------------------------------------------------
# CLI entry point
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    import argparse
    import sys

    # Ensure parent directory is on path for direct invocation
    sys.path.insert(0, str(Path(__file__).parent.parent))

    from orchestration.project_config import get_active_project_id, get_memu_config

    parser = argparse.ArgumentParser(
        description="Generate SOUL amendment suggestions from task failure patterns"
    )
    parser.add_argument(
        "--project",
        help="Project ID (default: active project from openclaw.json)",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Print suggestions as JSON without writing soul-suggestions.json",
    )
    parser.add_argument(
        "--lookback-days",
        type=int,
        default=DEFAULT_LOOKBACK_DAYS,
        help=f"Number of days of task history to analyse (default: {DEFAULT_LOOKBACK_DAYS})",
    )
    args = parser.parse_args()

    project_id = args.project or get_active_project_id()

    memu_cfg = get_memu_config()
    memu_url = memu_cfg.get("memu_api_url", "")
    if not memu_url:
        print(
            "ERROR: memu_api_url not configured in openclaw.json memory section",
            file=sys.stderr,
        )
        sys.exit(1)

    suggestions = asyncio.run(
        run_extraction(project_id, memu_url, args.lookback_days)
    )

    _save_suggestions(project_id, suggestions, dry_run=args.dry_run)

    if args.dry_run:
        # _save_suggestions already printed the JSON; add count line to stderr
        print(
            f"Dry run: {len(suggestions)} suggestion(s) found",
            file=sys.stderr,
        )
    else:
        print(f"Saved {len(suggestions)} suggestion(s) to soul-suggestions.json")
