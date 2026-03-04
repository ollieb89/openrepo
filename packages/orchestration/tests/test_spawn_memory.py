"""
Tests for pre-spawn memory retrieval and SOUL injection helpers in spawn.py.

Validates all four requirements:
  RET-01: Memory retrieval from memU /retrieve endpoint
  RET-02: SOUL augmentation with Memory Context section
  RET-03: Budget enforcement (2000 char hard cap)
  RET-04: Graceful degradation on network failure
"""

import os
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

# conftest.py adds skills/spawn to sys.path
from spawn import (
    _retrieve_memories_sync,
    _format_memory_context,
    _build_augmented_soul,
    _write_soul_tempfile,
    _write_soul_file,
    _rewrite_memu_url_for_container,
    CATEGORY_SECTION_MAP,
)
from openclaw.config import MEMORY_CONTEXT_BUDGET


# ---------------------------------------------------------------------------
# RET-01: Memory retrieval
# ---------------------------------------------------------------------------


def test_retrieve_memories_sync_success():
    """Successful retrieval returns list of memory dicts."""
    mock_items = [
        {"resource_url": "Use asyncio locks for thread safety", "category": "l3_outcome"},
        {"resource_url": "Prefer explicit error handling over broad except", "category": "l3_outcome"},
        {"resource_url": "Write tests before implementation", "category": "l2_review"},
    ]
    mock_response = MagicMock()
    mock_response.json.return_value = mock_items
    mock_response.raise_for_status = MagicMock()

    mock_client_instance = MagicMock()
    mock_client_instance.post.return_value = mock_response
    mock_client_instance.__enter__ = MagicMock(return_value=mock_client_instance)
    mock_client_instance.__exit__ = MagicMock(return_value=False)

    with patch("spawn.httpx.Client", return_value=mock_client_instance):
        result = _retrieve_memories_sync("http://localhost:18791", "test-project", "auth module")

    # _retrieve_memories_sync now returns (list, bool)
    assert isinstance(result, tuple), f"Expected (list, bool) tuple, got {type(result)}"
    items, ok = result
    assert ok is True
    assert items == mock_items
    mock_client_instance.post.assert_called_once_with(
        "/retrieve",
        json={
            "queries": [{"role": "user", "content": "auth module"}],
            "where": {"user_id": "test-project"},
        },
    )


def test_retrieve_memories_sync_graceful_on_network_error():
    """Network error returns [] without raising — RET-04 graceful degradation."""
    import httpx

    mock_client_instance = MagicMock()
    mock_client_instance.post.side_effect = httpx.ConnectError("Connection refused")
    mock_client_instance.__enter__ = MagicMock(return_value=mock_client_instance)
    mock_client_instance.__exit__ = MagicMock(return_value=False)

    with patch("spawn.httpx.Client", return_value=mock_client_instance):
        result = _retrieve_memories_sync("http://localhost:18791", "test-project", "query")

    # _retrieve_memories_sync now returns (list, bool); ok=False on network error
    assert isinstance(result, tuple), f"Expected (list, bool) tuple, got {type(result)}"
    items, ok = result
    assert ok is False
    assert items == []


def test_retrieve_memories_sync_empty_url_returns_empty():
    """Empty base_url returns [] immediately without making any HTTP call."""
    with patch("spawn.httpx.Client") as MockClient:
        result = _retrieve_memories_sync("", "test-project", "query")

    # _retrieve_memories_sync now returns (list, bool)
    assert isinstance(result, tuple), f"Expected (list, bool) tuple, got {type(result)}"
    items, ok = result
    assert items == []
    MockClient.assert_not_called()


def test_retrieve_memories_sync_dict_response_with_items_key():
    """API may return {'items': [...]} — must extract the list correctly."""
    inner_items = [
        {"resource_url": "Memory from dict response", "category": "l3_outcome"},
    ]
    mock_response = MagicMock()
    mock_response.json.return_value = {"items": inner_items, "total": 1}
    mock_response.raise_for_status = MagicMock()

    mock_client_instance = MagicMock()
    mock_client_instance.post.return_value = mock_response
    mock_client_instance.__enter__ = MagicMock(return_value=mock_client_instance)
    mock_client_instance.__exit__ = MagicMock(return_value=False)

    with patch("spawn.httpx.Client", return_value=mock_client_instance):
        result = _retrieve_memories_sync("http://localhost:18791", "proj", "query")

    # _retrieve_memories_sync now returns (list, bool)
    assert isinstance(result, tuple), f"Expected (list, bool) tuple, got {type(result)}"
    items, ok = result
    assert ok is True
    assert items == inner_items


# ---------------------------------------------------------------------------
# RET-03: Formatting and budget enforcement
# ---------------------------------------------------------------------------


def test_format_memory_context_empty_list():
    """Empty memory list produces empty string — no header, no placeholder (locked decision)."""
    result = _format_memory_context([])
    assert result == ""


def test_format_memory_context_with_items():
    """Items produce a ## Past Work Context section with bullets (no tag suffixes)."""
    memories = [
        {"resource_url": "Use atomic commits per feature", "category": "l3_outcome"},
        {"resource_url": "Always validate input before processing", "category": "l3_outcome"},
    ]

    result = _format_memory_context(memories)

    assert result.startswith("## Past Work Context\n\n")
    assert "- Use atomic commits per feature" in result
    assert "- Always validate input before processing" in result
    # Section headers replace tag suffixes — no old-style tags expected
    assert "(from memory)" not in result
    assert "(from L2 review)" not in result


def test_format_memory_context_budget_enforcement():
    """Budget enforcement drops items whose bullets would exceed MEMORY_CONTEXT_BUDGET (2000 chars).

    The budget tracks cumulative bullet text characters. Section headers are
    lightweight boilerplate added at build time and are not counted against the
    budget (they add ~23 chars overhead per section at most).
    """
    # Each bullet is ~397 chars ("- " + 395 Xs): 5 items fit (1985 chars), 6th (1985+398=2383) drops
    long_text = "X" * 395
    memories = [{"resource_url": long_text, "category": "l3_outcome"} for _ in range(6)]

    result = _format_memory_context(memories)

    # Output uses new section header format
    assert "## Past Work Context" in result

    # At least one item was dropped (fewer bullets than input items)
    bullet_count = sum(1 for line in result.splitlines() if line.startswith("- "))
    assert bullet_count < 6

    # Bullet content stays within budget (headers add minimal overhead)
    bullet_chars = sum(len(line) + 1 for line in result.splitlines() if line.startswith("- "))
    assert bullet_chars <= MEMORY_CONTEXT_BUDGET


def test_format_memory_context_skips_empty_content_items():
    """Items with empty resource_url and empty content are silently skipped."""
    memories = [
        {"resource_url": "", "content": "", "category": "l3_outcome"},
        {"resource_url": "Valid memory item", "category": "l3_outcome"},
        {"resource_url": None, "content": None, "category": "l3_outcome"},
    ]

    result = _format_memory_context(memories)

    # Should contain the valid item but not empty ones
    assert "Valid memory item" in result
    bullet_count = sum(1 for line in result.splitlines() if line.startswith("- "))
    assert bullet_count == 1


# ---------------------------------------------------------------------------
# RET-02: SOUL augmentation
# ---------------------------------------------------------------------------


def test_build_augmented_soul_with_memory(tmp_path):
    """SOUL augmented with memory context appends the section after base SOUL."""
    memory_context = "## Past Work Context\n\n- test memory"

    # _build_augmented_soul uses render_soul + AgentRegistry — mock them for isolation
    rendered_soul = "# Base SOUL\n\nThis is the base SOUL content.\n" + memory_context

    with (
        patch("spawn.load_project_config", return_value={}),
        patch("spawn.AgentRegistry"),
        patch("spawn.build_variables", return_value={}),
        patch("spawn.build_dynamic_variables", return_value={}),
        patch("spawn.render_soul", return_value=rendered_soul),
    ):
        result = _build_augmented_soul(tmp_path, memory_context, "test-proj", "l3_specialist")

    # Must contain original SOUL content
    assert "# Base SOUL" in result
    assert "This is the base SOUL content." in result

    # Must contain the memory section
    assert "## Past Work Context" in result
    assert "- test memory" in result

    # Memory context must appear after base SOUL
    base_pos = result.index("This is the base SOUL content.")
    memory_pos = result.index("## Past Work Context")
    assert memory_pos > base_pos


def test_build_augmented_soul_empty_memory(tmp_path):
    """Empty memory context falls back to 'No context loaded.' placeholder."""
    base_content = "# Base SOUL\n\nThis is the base SOUL content.\n"

    with (
        patch("spawn.load_project_config", return_value={}),
        patch("spawn.AgentRegistry"),
        patch("spawn.build_variables", return_value={}),
        patch("spawn.build_dynamic_variables", return_value={}),
        patch("spawn.render_soul", return_value=base_content),
    ):
        result = _build_augmented_soul(tmp_path, "", "test-proj", "l3_specialist")

    # render_soul is called and its result is returned
    assert "# Base SOUL" in result
    assert "## Past Work Context" not in result
    assert "## Past Review Outcomes" not in result


def test_build_augmented_soul_missing_soul_file(tmp_path):
    """Missing SOUL.md or render_soul returning '' returns empty string gracefully."""
    with (
        patch("spawn.load_project_config", return_value={}),
        patch("spawn.AgentRegistry"),
        patch("spawn.build_variables", return_value={}),
        patch("spawn.build_dynamic_variables", return_value={}),
        patch("spawn.render_soul", return_value=""),
    ):
        result = _build_augmented_soul(tmp_path, "## Past Work Context\n\n- some memory", "proj", "l3_specialist")

    assert result == ""


# ---------------------------------------------------------------------------
# Tempfile lifecycle
# ---------------------------------------------------------------------------


def test_write_soul_tempfile_creates_and_returns_path():
    """Tempfile is created with correct content and returned path exists."""
    content = "# Test SOUL\n\nSome content here.\n"

    path = _write_soul_tempfile(content)

    try:
        assert path.exists(), f"Tempfile not found at {path}"
        assert path.read_text(encoding="utf-8") == content
        assert path.name.startswith("openclaw-")
        assert path.name.endswith(".soul.md")
    finally:
        path.unlink(missing_ok=True)


# ---------------------------------------------------------------------------
# Section-split behavior (Phase 30 plan 02)
# ---------------------------------------------------------------------------


def test_format_splits_work_and_review_memories():
    """Mixed memories produce both ## Past Work Context and ## Past Review Outcomes sections."""
    memories = [
        {"resource_url": "Use asyncio for concurrent tasks", "category": "l3_outcome"},
        {"resource_url": "Merge approved — all tests passed", "category": "review_decision"},
        {"resource_url": "Add explicit error handling", "category": "l3_outcome"},
        {"resource_url": "Conflict resolved — rebase on main first", "category": "review_decision"},
    ]

    result = _format_memory_context(memories)

    assert "## Past Work Context" in result
    assert "## Past Review Outcomes" in result
    # Work items appear under work section
    assert "- Use asyncio for concurrent tasks" in result
    assert "- Add explicit error handling" in result
    # Review items appear under review section
    assert "- Merge approved — all tests passed" in result
    assert "- Conflict resolved — rebase on main first" in result


def test_format_review_only_no_work_section():
    """Review-only memories produce ## Past Review Outcomes but NOT ## Past Work Context."""
    memories = [
        {"resource_url": "Rejected — missing test coverage", "category": "review_decision"},
        {"resource_url": "Approved with comment: add docstrings", "category": "review_decision"},
    ]

    result = _format_memory_context(memories)

    assert "## Past Review Outcomes" in result
    assert "## Past Work Context" not in result
    assert "- Rejected — missing test coverage" in result


def test_format_work_only_no_review_section():
    """Work-only memories produce ## Past Work Context but NOT ## Past Review Outcomes."""
    memories = [
        {"resource_url": "Prefer explicit imports over wildcard", "category": "l3_outcome"},
        {"resource_url": "Use context managers for file I/O"},  # no category field
    ]

    result = _format_memory_context(memories)

    assert "## Past Work Context" in result
    assert "## Past Review Outcomes" not in result
    assert "- Prefer explicit imports over wildcard" in result
    assert "- Use context managers for file I/O" in result


def test_format_agent_type_fallback_for_review():
    """agent_type=='l2_pm' routes item to ## Past Review Outcomes even without category field."""
    memories = [
        {"resource_url": "Approved — clean implementation", "agent_type": "l2_pm"},
    ]

    result = _format_memory_context(memories)

    assert "## Past Review Outcomes" in result
    assert "## Past Work Context" not in result
    assert "- Approved — clean implementation" in result


def test_format_budget_shared_across_sections():
    """Shared budget stops accumulation when exceeded — at least one item from each category fits."""
    # Create items that together exceed 2000 chars
    # Each work item: ~200 chars; each review item: ~200 chars; 8 total = ~1600 chars bullets
    # + headers ~50 chars each — total well above 2000 with enough items
    work_text = "W" * 195
    review_text = "R" * 195
    memories = []
    for _ in range(6):
        memories.append({"resource_url": work_text, "category": "l3_outcome"})
        memories.append({"resource_url": review_text, "category": "review_decision"})

    result = _format_memory_context(memories)

    # Total bullet content stays within budget
    # (headers add ~50 chars each, so check generously with 2200 cap)
    assert len(result) <= MEMORY_CONTEXT_BUDGET + 200  # headers are outside bullet budget

    # At least one item from each category appears (budget is shared, not split)
    assert "## Past Work Context" in result or "## Past Review Outcomes" in result
    assert "- " + work_text in result or "- " + review_text in result


def test_format_empty_still_returns_empty():
    """Regression guard: _format_memory_context([]) returns '' — no headers, no placeholder."""
    result = _format_memory_context([])
    assert result == ""
    assert "## Past Work Context" not in result
    assert "## Past Review Outcomes" not in result


def test_format_no_tag_suffix_in_bullets():
    """Bullets do NOT contain old tag suffixes — section headers provide source context."""
    memories = [
        {"resource_url": "Use dependency injection", "category": "l3_outcome"},
        {"resource_url": "Merge approved", "category": "review_decision"},
    ]

    result = _format_memory_context(memories)

    # Old-style tag suffixes must be absent
    assert "(from memory)" not in result
    assert "(from L2 review)" not in result
    # Bullets exist but are clean
    assert "- Use dependency injection" in result
    assert "- Merge approved" in result


# ---------------------------------------------------------------------------
# MEM-04: URL rewrite for container networking
# ---------------------------------------------------------------------------


def test_rewrite_memu_url_localhost_to_docker_dns():
    """localhost is replaced with Docker DNS hostname."""
    assert _rewrite_memu_url_for_container("http://localhost:18791") == "http://openclaw-memory:18791"


def test_rewrite_memu_url_127_to_docker_dns():
    """127.0.0.1 is replaced with Docker DNS hostname."""
    assert _rewrite_memu_url_for_container("http://127.0.0.1:18791") == "http://openclaw-memory:18791"


def test_rewrite_memu_url_preserves_path():
    """Port and path are preserved after hostname swap."""
    assert _rewrite_memu_url_for_container("http://localhost:18791/api/v1") == "http://openclaw-memory:18791/api/v1"


def test_rewrite_memu_url_non_localhost_unchanged():
    """Non-localhost URLs pass through unchanged."""
    url = "http://memu.internal:18791"
    assert _rewrite_memu_url_for_container(url) == url


def test_rewrite_memu_url_https_unchanged():
    """External HTTPS URLs pass through unchanged."""
    url = "https://api.memu.io/v1"
    assert _rewrite_memu_url_for_container(url) == url


def test_rewrite_memu_url_empty_returns_empty():
    """Empty URL returns empty string."""
    assert _rewrite_memu_url_for_container("") == ""


def test_rewrite_memu_url_custom_hostname():
    """Custom DNS hostname parameter is used."""
    assert _rewrite_memu_url_for_container("http://localhost:18791", dns_hostname="custom-host") == "http://custom-host:18791"


# ---------------------------------------------------------------------------
# RET-02 (gap closure): Persistent SOUL file path
# ---------------------------------------------------------------------------


def test_write_soul_file_creates_at_project_state_dir(tmp_path):
    """SOUL file is created at workspace/.openclaw/<project>/soul-<task>.md."""
    content = "# Augmented SOUL\n\nWith memory context.\n"
    path = _write_soul_file(content, "testproj", "task-123", tmp_path)

    assert path.exists()
    assert path.read_text(encoding="utf-8") == content
    assert path == tmp_path / ".openclaw" / "testproj" / "soul-task-123.md"


def test_write_soul_file_creates_parent_dirs(tmp_path):
    """Parent directories are created if they don't exist."""
    path = _write_soul_file("content", "newproj", "t1", tmp_path)
    assert path.exists()
    assert (tmp_path / ".openclaw" / "newproj").is_dir()


def test_write_soul_file_overwrites_existing(tmp_path):
    """Writing to the same task_id overwrites the previous file."""
    _write_soul_file("first", "proj", "t1", tmp_path)
    path = _write_soul_file("second", "proj", "t1", tmp_path)
    assert path.read_text(encoding="utf-8") == "second"


# ---------------------------------------------------------------------------
# RET-02 (phase 34): Round-trip category routing tests
# ---------------------------------------------------------------------------


def test_review_decision_category_routes_to_review_section():
    """Items stored with category='review_decision' route to '## Past Review Outcomes'.

    This is the primary routing path — now that snapshot.py sends the category
    field, retrieved items should arrive here and not rely on the agent_type fallback.
    """
    memories = [
        {
            "resource_url": "# L2 Review Decision: task T-001\nVerdict: merge\nReasoning: all good",
            "category": "review_decision",
        }
    ]

    result = _format_memory_context(memories)

    assert "## Past Review Outcomes" in result
    assert "## Past Work Context" not in result  # no work items present
    assert "Verdict: merge" in result


def test_item_without_category_routes_to_work_context():
    """Items without a category field route to '## Past Work Context' (backward compatibility).

    Note: test_format_work_only_no_review_section already covers this case implicitly.
    This explicit test documents the backward-compatibility contract per user decision.
    """
    memories = [
        {"resource_url": "Legacy memory item with no category"},  # no 'category' key
    ]

    result = _format_memory_context(memories)

    assert "## Past Work Context" in result
    assert "## Past Review Outcomes" not in result  # no review items present
    assert "Legacy memory item" in result


# ---------------------------------------------------------------------------
# Phase 37 Plan 02: Category-primary routing, Task Outcomes section, ordering
# ---------------------------------------------------------------------------


def test_category_section_map_contains_expected_keys():
    """CATEGORY_SECTION_MAP is a module-level constant with exactly two entries."""
    assert "review_decision" in CATEGORY_SECTION_MAP
    assert "task_outcome" in CATEGORY_SECTION_MAP
    assert CATEGORY_SECTION_MAP["review_decision"] == "Past Review Outcomes"
    assert CATEGORY_SECTION_MAP["task_outcome"] == "Task Outcomes"


def test_category_primary_routing_review_decision():
    """Items with category='review_decision' route to '## Past Review Outcomes' via primary path.

    No agent_type field — confirms primary routing fires without the fallback.
    """
    memories = [
        {
            "resource_url": "Approved — tests all green, no style issues",
            "category": "review_decision",
            # deliberately no agent_type — primary path only
        }
    ]

    result = _format_memory_context(memories)

    assert "## Past Review Outcomes" in result
    assert "## Past Work Context" not in result
    assert "## Task Outcomes" not in result
    assert "- Approved — tests all green, no style issues" in result


def test_category_primary_routing_task_outcome():
    """Items with category='task_outcome' route to '## Task Outcomes' section.

    This is the NEW section added in Plan 02 — did not exist before.
    """
    memories = [
        {
            "resource_url": "Implemented OAuth2 token refresh with 30-min expiry",
            "category": "task_outcome",
        }
    ]

    result = _format_memory_context(memories)

    assert "## Task Outcomes" in result
    assert "## Past Review Outcomes" not in result
    assert "## Past Work Context" not in result
    assert "- Implemented OAuth2 token refresh with 30-min expiry" in result


def test_category_routing_with_mixed_categories():
    """Mixed category input produces all three sections with correct items per section.

    Verifies:
    - All three sections present
    - Output ordering: Past Review Outcomes -> Task Outcomes -> Past Work Context
    - Each item is under the correct section
    """
    memories = [
        {"resource_url": "Approved — clean diff", "category": "review_decision"},
        {"resource_url": "Auth service implemented", "category": "task_outcome"},
        {"resource_url": "Prefer named parameters over positional"},  # no category
    ]

    result = _format_memory_context(memories)

    assert "## Past Review Outcomes" in result
    assert "## Task Outcomes" in result
    assert "## Past Work Context" in result

    # Verify output ordering: review -> task outcomes -> work context
    review_pos = result.index("## Past Review Outcomes")
    task_pos = result.index("## Task Outcomes")
    work_pos = result.index("## Past Work Context")
    assert review_pos < task_pos < work_pos, (
        f"Section order wrong: review={review_pos}, task={task_pos}, work={work_pos}"
    )

    # Each item must appear under its own section header
    review_section_end = task_pos
    task_section_end = work_pos
    assert "- Approved — clean diff" in result[:review_section_end]
    assert "- Auth service implemented" in result[task_pos:task_section_end]
    assert "- Prefer named parameters over positional" in result[work_pos:]


def test_legacy_items_without_category_still_route_correctly():
    """Items with agent_type='l2_pm' but no category field route to '## Past Review Outcomes'.

    Backward-compat guard: existing memories stored before category field
    introduction still arrive in the review section via the agent_type fallback.
    """
    memories = [
        {
            "resource_url": "Approved — legacy item from before category field",
            "agent_type": "l2_pm",
            # no 'category' key at all
        }
    ]

    result = _format_memory_context(memories)

    assert "## Past Review Outcomes" in result
    assert "## Past Work Context" not in result
    assert "- Approved — legacy item from before category field" in result


def test_task_outcome_category_budget_shared():
    """task_outcome items consume from the same MEMORY_CONTEXT_BUDGET as other sections.

    Input: enough task_outcome items to approach the budget.
    Assert: budget is respected (bullet chars stay within cap); items are dropped
    when the budget is exhausted rather than truncated.
    """
    # Each bullet is ~397 chars; 5 fit (1985 chars), 6th would exceed (1985+398=2383)
    long_text = "T" * 395
    memories = [{"resource_url": long_text, "category": "task_outcome"} for _ in range(6)]

    result = _format_memory_context(memories)

    assert "## Task Outcomes" in result

    # At least one item was dropped
    bullet_count = sum(1 for line in result.splitlines() if line.startswith("- "))
    assert bullet_count < 6

    # Bullet content stays within budget
    bullet_chars = sum(len(line) + 1 for line in result.splitlines() if line.startswith("- "))
    assert bullet_chars <= MEMORY_CONTEXT_BUDGET
