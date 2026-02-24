"""
Unit tests for orchestration/suggest.py — pattern extraction engine.

All tests are pure unit tests:
- No asyncio / pytest-asyncio required
- No live memU connection
- No filesystem writes (pure in-memory)
- Import functions directly from openclaw.cli.suggest

Run with:
    python3 -m pytest tests/test_suggest.py -v
"""

import time

from openclaw.cli.suggest import (
    _build_suggestion,
    _cluster_memories,
    _extract_keywords,
    _fingerprint,
    _should_suppress,
    MAX_CLUSTER_FRACTION,
    MIN_CLUSTER_SIZE,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_memory(content: str, offset_seconds: int = 0) -> dict:
    """Create a memory dict with a recent timestamp (within the last day)."""
    return {
        "content": content,
        "created_at": time.time() - offset_seconds,
        "task_id": "T-test",
    }


# ---------------------------------------------------------------------------
# Test 1: Keyword extraction — stopwords filtered
# ---------------------------------------------------------------------------

def test_extract_keywords_filters_stopwords():
    """
    Short words ('the', 'to') must NOT appear in output because they are under
    the 4-character minimum.
    'complete' should appear — it is long enough and not a domain stopword.
    """
    text = "the agent failed to complete the task"
    result = _extract_keywords(text)

    assert "the" not in result, "stopword 'the' should be filtered (length < 4)"
    assert "to" not in result, "'to' should be filtered (length < 4)"
    assert "complete" in result, "'complete' is not a stopword and should appear"


def test_extract_keywords_filters_domain_stopwords():
    """
    'agent' and 'failed' are in DOMAIN_STOPWORDS and must be filtered.
    'complete' (not in stopwords) should appear.
    """
    text = "the agent failed to complete the task"
    result = _extract_keywords(text)

    assert "agent" not in result, "'agent' is a domain stopword and should be filtered"
    assert "failed" not in result, "'failed' is a domain stopword and should be filtered"
    assert "task" not in result, "'task' is a domain stopword and should be filtered"
    assert "complete" in result, "'complete' is not a stopword and should appear"


# ---------------------------------------------------------------------------
# Test 2: Keyword extraction — minimum length
# ---------------------------------------------------------------------------

def test_extract_keywords_min_length():
    """Words under 4 characters ('fix', 'it') must be filtered out."""
    result = _extract_keywords("fix it")
    assert result == [], f"Expected empty list, got {result!r}"


# ---------------------------------------------------------------------------
# Test 3: Cluster threshold — only clusters with >= MIN_CLUSTER_SIZE returned
# ---------------------------------------------------------------------------

def test_cluster_memories_threshold():
    """
    5 memories containing 'filepath' → cluster returned (size >= MIN_CLUSTER_SIZE=3).
    2 memories containing 'retry' only → cluster absent (size < MIN_CLUSTER_SIZE).

    We use 12 total memories so 'filepath' (5/12 ≈ 42%) stays below
    MAX_CLUSTER_FRACTION=0.5 and is not discarded as too generic.
    """
    now = time.time()
    filepath_mems = [
        {"content": f"filepath issue number {i}", "created_at": now, "task_id": f"T-{i}"}
        for i in range(5)
    ]
    retry_mems = [
        {"content": f"retry attempt number {i}", "created_at": now, "task_id": f"T-R{i}"}
        for i in range(2)
    ]
    # Padding memories (unrelated content) to keep filepath below 50% of total
    padding_mems = [
        {"content": f"network timeout during request {i}", "created_at": now, "task_id": f"T-P{i}"}
        for i in range(5)
    ]
    all_mems = filepath_mems + retry_mems + padding_mems

    clusters = _cluster_memories(all_mems, lookback_days=30)

    assert "filepath" in clusters, "filepath cluster should meet threshold (5 occurrences)"
    # retry has only 2 — below MIN_CLUSTER_SIZE=3
    assert "retry" not in clusters, "retry cluster should be below threshold (2 < 3)"


# ---------------------------------------------------------------------------
# Test 4: Cluster lookback filter — old memories excluded
# ---------------------------------------------------------------------------

def test_cluster_memories_lookback_filter():
    """
    1 memory within lookback window, 4 outside it.
    Clusters for keywords in old memories should not meet threshold.
    """
    now = time.time()
    recent_mem = {"content": "filepath resolution issue", "created_at": now, "task_id": "T-recent"}
    # 4 old memories (outside 30-day window)
    old_mems = [
        {"content": "filepath old problem number {i}", "created_at": now - (40 * 86400), "task_id": f"T-old-{i}"}
        for i in range(4)
    ]
    all_mems = [recent_mem] + old_mems

    clusters = _cluster_memories(all_mems, lookback_days=30)

    # Only 1 recent memory with 'filepath' — cluster size = 1, below MIN_CLUSTER_SIZE=3
    assert "filepath" not in clusters, (
        "filepath cluster should be absent — only 1 recent memory, below threshold"
    )


# ---------------------------------------------------------------------------
# Test 5: Cluster discards too-generic clusters
# ---------------------------------------------------------------------------

def test_cluster_discards_too_generic():
    """
    10 recent memories all containing a word NOT in DOMAIN_STOPWORDS but present
    in every single memory → spans 100% of total, exceeds MAX_CLUSTER_FRACTION=0.5,
    should be discarded.

    We use 'xpath' as a non-stopword word present in every memory.
    """
    now = time.time()
    # All 10 memories contain 'xpath'
    mems = [
        {"content": f"xpath parse failure case {i}", "created_at": now, "task_id": f"T-{i}"}
        for i in range(10)
    ]

    clusters = _cluster_memories(mems, lookback_days=30)

    # 'xpath' appears in 10/10 = 100% of memories, which is > MAX_CLUSTER_FRACTION=0.5
    assert "xpath" not in clusters, (
        "'xpath' cluster spans 100% of memories and should be discarded as too generic"
    )


# ---------------------------------------------------------------------------
# Test 6: Build suggestion schema completeness
# ---------------------------------------------------------------------------

def test_build_suggestion_schema():
    """
    _build_suggestion returns a dict with all required schema fields.
    """
    memories = [
        {"content": "Ignored path", "task_id": "T-1"},
        {"content": "Wrong dir", "task_id": "T-2"},
        {"content": "Hardcoded path", "task_id": "T-3"},
    ]
    sug = _build_suggestion("filepath", memories)

    # id starts with "sug-"
    assert sug["id"].startswith("sug-"), f"id should start with 'sug-', got {sug['id']!r}"

    # status is "pending"
    assert sug["status"] == "pending", f"status should be 'pending', got {sug['status']!r}"

    # evidence_count matches number of memories
    assert sug["evidence_count"] == 3, f"evidence_count should be 3, got {sug['evidence_count']}"

    # diff_text starts with ## BEHAVIORAL PROTOCOLS
    assert sug["diff_text"].startswith("## BEHAVIORAL PROTOCOLS"), (
        f"diff_text should start with '## BEHAVIORAL PROTOCOLS', got {sug['diff_text'][:50]!r}"
    )

    # evidence_examples has <= 3 items
    assert len(sug["evidence_examples"]) <= 3, (
        f"evidence_examples should have <= 3 items, got {len(sug['evidence_examples'])}"
    )

    # nullable fields are None
    assert sug["rejected_at"] is None
    assert sug["accepted_at"] is None
    assert sug["rejection_reason"] is None
    assert sug["suppressed_until_count"] is None

    # All required keys present
    required_keys = {
        "id", "status", "created_at", "pattern_description",
        "evidence_count", "evidence_examples", "diff_text",
        "rejected_at", "rejection_reason", "suppressed_until_count", "accepted_at",
    }
    missing = required_keys - set(sug.keys())
    assert not missing, f"Missing schema keys: {missing}"


# ---------------------------------------------------------------------------
# Test 7: Suppression active — cluster below threshold
# ---------------------------------------------------------------------------

def test_should_suppress_active():
    """
    Rejected entry for keyword 'filepath' with suppressed_until_count=6.
    cluster_size=4 → should suppress (4 < 6).
    """
    import hashlib
    keyword = "filepath"
    suggestion_id = "sug-" + hashlib.md5(keyword.encode()).hexdigest()[:6]

    existing = {
        "version": "1.0",
        "last_run": None,
        "suggestions": [
            {
                "id": suggestion_id,
                "status": "rejected",
                "evidence_count": 3,
                "suppressed_until_count": 6,
            }
        ],
    }

    result = _should_suppress("filepath", cluster_size=4, existing=existing)
    assert result is True, "Should suppress: cluster_size=4 < suppressed_until_count=6"


# ---------------------------------------------------------------------------
# Test 8: Suppression cleared — cluster above threshold
# ---------------------------------------------------------------------------

def test_should_suppress_cleared():
    """
    Same rejected entry for 'filepath' with suppressed_until_count=6.
    cluster_size=8 → should NOT suppress (8 >= 6).
    """
    import hashlib
    keyword = "filepath"
    suggestion_id = "sug-" + hashlib.md5(keyword.encode()).hexdigest()[:6]

    existing = {
        "version": "1.0",
        "last_run": None,
        "suggestions": [
            {
                "id": suggestion_id,
                "status": "rejected",
                "evidence_count": 3,
                "suppressed_until_count": 6,
            }
        ],
    }

    result = _should_suppress("filepath", cluster_size=8, existing=existing)
    assert result is False, "Should NOT suppress: cluster_size=8 >= suppressed_until_count=6"


# ---------------------------------------------------------------------------
# Test 9: No suppression — no rejected entries for keyword
# ---------------------------------------------------------------------------

def test_should_suppress_no_rejected_entries():
    """No rejected entries for the keyword → should not suppress."""
    existing = {
        "version": "1.0",
        "last_run": None,
        "suggestions": [],
    }

    result = _should_suppress("filepath", cluster_size=5, existing=existing)
    assert result is False, "Should NOT suppress: no rejected entries exist"


# ---------------------------------------------------------------------------
# Test 10: Fingerprint format
# ---------------------------------------------------------------------------

def test_fingerprint_format():
    """_fingerprint returns the expected 'keyword:count' string."""
    result = _fingerprint("filepath", 7)
    assert result == "filepath:7", f"Expected 'filepath:7', got {result!r}"
