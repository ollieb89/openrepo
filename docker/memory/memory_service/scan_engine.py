"""
Memory health scan engine — pure Python algorithms with no FastAPI/pydantic deps.

This module is importable without pydantic, fastapi, or memu being installed,
which allows the scan logic to be unit-tested in the root environment.

The only runtime dependencies are:
  - pendulum (optional, used for ISO timestamp parsing — stdlib datetime.fromisoformat
    is used as primary parser and handles Python 3.11+ extended ISO format)
  - numpy + memu.database.inmemory.vector.cosine_topk (used by _find_conflicts,
    imported lazily so that _check_staleness tests work without numpy)
"""

from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Any

logger = logging.getLogger(__name__)


def _parse_datetime(value: str) -> datetime:
    """Parse an ISO 8601 datetime string to a timezone-aware datetime.

    Tries stdlib datetime.fromisoformat() first (Python 3.11+ handles 'Z' suffix),
    then falls back to pendulum.parse() for edge cases.
    """
    # Normalise 'Z' suffix to '+00:00' so fromisoformat handles it on all Python versions
    normalised = value.replace("Z", "+00:00") if value.endswith("Z") else value
    try:
        dt = datetime.fromisoformat(normalised)
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        return dt
    except ValueError:
        # Fallback to pendulum for non-standard formats
        import pendulum

        parsed = pendulum.parse(value)
        if parsed.tzinfo is None:
            parsed = parsed.replace(tzinfo=timezone.utc)
        return parsed


def _check_staleness(
    item: Any,
    age_threshold_days: int,
    retrieval_window_days: int,
    now: datetime,
) -> float | None:
    """Check whether a single memory item is stale.

    Returns:
        age_score (float, >1.0 means well past threshold) if the item is stale,
        or None if it is not stale.

    Staleness criteria:
        - Item must be older than age_threshold_days (necessary condition)
        - AND it must not have been retrieved recently (within retrieval_window_days)

    When last_reinforced_at is absent, created_at is used as the retrieval proxy
    to avoid false positives on items that have never been reinforced (Pitfall 2).
    """
    # Normalise created_at to UTC-aware datetime for arithmetic
    created_at = item.created_at
    if hasattr(created_at, "tzinfo") and created_at.tzinfo is None:
        created_at = created_at.replace(tzinfo=timezone.utc)

    item_age_days = (now - created_at).total_seconds() / 86400

    if item_age_days < age_threshold_days:
        return None  # Not old enough to be considered stale

    extra = item.extra or {}
    last_reinforced_str = extra.get("last_reinforced_at")

    if last_reinforced_str:
        try:
            last_reinforced = _parse_datetime(str(last_reinforced_str))
            days_since_retrieval = (now - last_reinforced).total_seconds() / 86400
            if days_since_retrieval < retrieval_window_days:
                return None  # Retrieved recently enough — not stale
        except (ValueError, TypeError, Exception):
            pass  # Unparseable timestamp — treat as not retrieved

    # No last_reinforced_at: use created_at as proxy.
    # If item age is within the retrieval window it's "fresh enough" — not stale.
    if item_age_days < retrieval_window_days:
        return None

    age_score = item_age_days / age_threshold_days
    return age_score


def _find_conflicts(
    items: list[Any],
    similarity_min: float,
    similarity_max: float,
) -> list[tuple[str, str, float]]:
    """Find conflicting memory pairs via cosine similarity.

    Builds a corpus of (id, embedding) tuples once and uses cosine_topk()
    for O(n * k) comparisons rather than O(n^2) embedding fetches.

    Deduplication: pair (A, B) and (B, A) are collapsed to a single entry
    using a canonical sorted-tuple key (Pitfall 3).

    Returns:
        List of (id_a, id_b, similarity) triples for conflicting pairs.
    """
    # Import cosine_topk lazily — only needed at call time, not import time
    from memu.database.inmemory.vector import cosine_topk

    corpus = [(item.id, item.embedding) for item in items if item.embedding is not None]
    seen_pairs: set[tuple[str, str]] = set()
    conflicts: list[tuple[str, str, float]] = []

    for item in items:
        if item.embedding is None:
            continue

        neighbors = cosine_topk(item.embedding, corpus, k=10)
        for neighbor_id, score in neighbors:
            if neighbor_id == item.id:
                continue  # Exclude self-matches
            if not (similarity_min <= score <= similarity_max):
                continue  # Outside conflict similarity window

            # Deduplicate: canonical pair key
            pair_key: tuple[str, str] = tuple(sorted([item.id, neighbor_id]))  # type: ignore[assignment]
            if pair_key in seen_pairs:
                continue
            seen_pairs.add(pair_key)
            conflicts.append((item.id, neighbor_id, score))

    return conflicts
