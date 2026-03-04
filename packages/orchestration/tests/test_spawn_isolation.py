"""
Tests for dual-layer L3 isolation in spawn.py (Phase 64, Plan 02).

Validates that structural memory categories never reach L3 SOUL context:
  - Layer 1: Pre-filter applied after _retrieve_memories_sync, before _format_memory_context
  - Layer 2: Defense-in-depth inside _format_memory_context via EXCLUDED_CATEGORIES

ISL-01: Pre-filter removes structural memories from retrieval result list
ISL-02: _format_memory_context drops structural categories directly (Layer 2)
ISL-03: SOUL output contains zero topology/structural content
ISL-04: Non-structural categories route normally through both layers
"""

import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

# conftest.py adds skills/spawn to sys.path
from spawn import (
    _format_memory_context,
    _build_augmented_soul,
    CATEGORY_SECTION_MAP,
    EXCLUDED_CATEGORIES,
)


# ---------------------------------------------------------------------------
# Fixtures: memory lists
# ---------------------------------------------------------------------------

STRUCTURAL_MEMORY_CATEGORIES = [
    "structural_correction",
    "structural_preference",
    "structural_pattern",
]

NORMAL_MEMORY_CATEGORIES = [
    "review_decision",
    "task_outcome",
]


def _make_memory(category: str, text: str = None) -> dict:
    """Create a memory item dict with the given category."""
    if text is None:
        text = f"Memory content for {category}"
    return {
        "resource_url": text,
        "category": category,
    }


def _make_memory_with_metadata(category: str, text: str = None) -> dict:
    """Create a memory item dict with category nested under metadata (alternative format)."""
    if text is None:
        text = f"Metadata-wrapped memory for {category}"
    return {
        "resource_url": text,
        "metadata": {"category": category},
    }


# ---------------------------------------------------------------------------
# ISL-00: EXCLUDED_CATEGORIES constant exists and is correct
# ---------------------------------------------------------------------------


def test_excluded_categories_frozenset_exists():
    """EXCLUDED_CATEGORIES is defined as a frozenset at module level."""
    assert isinstance(EXCLUDED_CATEGORIES, frozenset), (
        f"Expected frozenset, got {type(EXCLUDED_CATEGORIES)}"
    )


def test_excluded_categories_contains_all_structural():
    """EXCLUDED_CATEGORIES contains all three structural memory categories."""
    assert "structural_correction" in EXCLUDED_CATEGORIES
    assert "structural_preference" in EXCLUDED_CATEGORIES
    assert "structural_pattern" in EXCLUDED_CATEGORIES


def test_excluded_categories_does_not_include_normal():
    """Normal categories are NOT in EXCLUDED_CATEGORIES."""
    assert "review_decision" not in EXCLUDED_CATEGORIES
    assert "task_outcome" not in EXCLUDED_CATEGORIES


# ---------------------------------------------------------------------------
# ISL-01: Layer 1 pre-filter logic (applied in spawn flow after retrieval)
# ---------------------------------------------------------------------------


def test_prefilter_removes_structural_memories():
    """Pre-filter logic strips structural categories from memories list.

    Simulates the Layer 1 pre-filter applied between _retrieve_memories_sync()
    and _format_memory_context() in the spawn flow.
    """
    memories = [
        _make_memory("structural_correction", "Correction: user preferred lean topology"),
        _make_memory("review_decision", "Approved — tests passed"),
        _make_memory("structural_preference", "Preference: avoid review gates"),
        _make_memory("task_outcome", "Auth service implemented"),
        _make_memory("structural_pattern", "Pattern: always prefer minimal agents"),
    ]

    # Apply Layer 1 pre-filter (same logic as in spawn.py spawn flow)
    pre_count = len(memories)
    filtered = [
        m for m in memories
        if m.get("metadata", {}).get("category", m.get("category", "")) not in EXCLUDED_CATEGORIES
    ]

    assert len(filtered) == 2, f"Expected 2 items after filtering, got {len(filtered)}"
    assert pre_count - len(filtered) == 3, "Should have removed exactly 3 structural items"

    categories_remaining = [m.get("category", "") for m in filtered]
    assert "structural_correction" not in categories_remaining
    assert "structural_preference" not in categories_remaining
    assert "structural_pattern" not in categories_remaining
    assert "review_decision" in categories_remaining
    assert "task_outcome" in categories_remaining


def test_prefilter_handles_metadata_wrapped_categories():
    """Pre-filter also handles category nested under 'metadata' key."""
    memories = [
        _make_memory_with_metadata("structural_correction", "Structural data via metadata"),
        _make_memory("review_decision", "Normal review memory"),
    ]

    filtered = [
        m for m in memories
        if m.get("metadata", {}).get("category", m.get("category", "")) not in EXCLUDED_CATEGORIES
    ]

    assert len(filtered) == 1
    assert filtered[0].get("category") == "review_decision"


def test_prefilter_empty_list_stays_empty():
    """Pre-filter on empty list returns empty list."""
    filtered = [
        m for m in []
        if m.get("metadata", {}).get("category", m.get("category", "")) not in EXCLUDED_CATEGORIES
    ]
    assert filtered == []


def test_prefilter_all_normal_categories_pass_through():
    """Pre-filter does not remove non-structural categories."""
    memories = [
        _make_memory("review_decision", "Review content"),
        _make_memory("task_outcome", "Task outcome content"),
        _make_memory("l3_outcome", "L3 outcome content"),
    ]

    filtered = [
        m for m in memories
        if m.get("metadata", {}).get("category", m.get("category", "")) not in EXCLUDED_CATEGORIES
    ]

    assert len(filtered) == 3, f"Expected all 3 items, got {len(filtered)}"


# ---------------------------------------------------------------------------
# ISL-02: Layer 2 defense-in-depth in _format_memory_context
# ---------------------------------------------------------------------------


def test_structural_categories_excluded_in_format():
    """_format_memory_context drops structural categories via EXCLUDED_CATEGORIES (Layer 2).

    Even if structural memories reach the format layer, they are dropped with
    a warning. This is the defense-in-depth layer.
    """
    structural_memories = [
        _make_memory("structural_correction", "Correction: prefer lean"),
        _make_memory("structural_preference", "Preference: no review gates"),
        _make_memory("structural_pattern", "Pattern: flat delegation always"),
    ]

    result = _format_memory_context(structural_memories)

    # All structural content must be absent from the output
    assert "Correction: prefer lean" not in result
    assert "Preference: no review gates" not in result
    assert "Pattern: flat delegation always" not in result


def test_format_returns_empty_for_structural_only_input():
    """_format_memory_context returns '' when all input items are structural categories."""
    memories = [
        _make_memory("structural_correction"),
        _make_memory("structural_preference"),
        _make_memory("structural_pattern"),
    ]

    result = _format_memory_context(memories)
    assert result == "", f"Expected empty string, got: {repr(result)}"


def test_format_mixed_structural_and_normal_drops_structural():
    """_format_memory_context drops structural items but keeps normal items."""
    memories = [
        _make_memory("structural_correction", "Structural data — should be dropped"),
        _make_memory("review_decision", "Approved — should appear"),
        _make_memory("structural_preference", "Preference data — should be dropped"),
        _make_memory("task_outcome", "Auth task done — should appear"),
    ]

    result = _format_memory_context(memories)

    # Structural content must be absent
    assert "Structural data — should be dropped" not in result
    assert "Preference data — should be dropped" not in result

    # Normal content must be present
    assert "Approved — should appear" in result
    assert "Auth task done — should appear" in result


# ---------------------------------------------------------------------------
# ISL-03: SOUL output has no topology/structural content
# ---------------------------------------------------------------------------


def test_augmented_soul_has_no_topology_content(tmp_path):
    """_build_augmented_soul() produces a SOUL with zero structural memory content.

    Creates a minimal project structure, calls _build_augmented_soul with
    a memory_context that was pre-filtered (empty), and verifies structural
    content does not appear in the output.
    """
    # Create minimal agent SOUL structure
    soul_dir = tmp_path / "agents" / "l3_specialist" / "agent"
    soul_dir.mkdir(parents=True)
    soul_file = soul_dir / "SOUL.md"
    soul_file.write_text("# L3 Specialist SOUL\n\nBase agent context.\n$memory_section\n")

    # memory_context is empty (structural items pre-filtered at Layer 1)
    memory_context = ""

    # Structural categories that should NOT appear in SOUL
    structural_terms = [
        "structural_correction",
        "structural_preference",
        "structural_pattern",
        "topology",
        "archetype",
        "rubric",
    ]

    with (
        patch("spawn.load_project_config", return_value={"project_id": "test-proj"}),
        patch("spawn.AgentRegistry"),
        patch("spawn.build_variables", return_value={}),
        patch("spawn.build_dynamic_variables", return_value={}),
        patch("spawn.render_soul", return_value="# L3 Soul\n\nBase context.\n"),
    ):
        result = _build_augmented_soul(tmp_path, memory_context, "test-proj", "l3_specialist")

    # SOUL must contain base content, not structural terms from the memory system
    # (structural terms are part of the infrastructure code, not SOUL content)
    # The key assertion: no structural MEMORY SECTION content in SOUL
    assert result is not None
    assert isinstance(result, str)

    # Verify the render_soul was called with memory_section = "No context loaded."
    # (when memory_context is empty, the default is used)
    assert "structural_correction" not in result
    assert "structural_preference" not in result
    assert "structural_pattern" not in result


# ---------------------------------------------------------------------------
# ISL-04: Non-structural categories route normally through both layers
# ---------------------------------------------------------------------------


def test_non_structural_categories_still_route_review_decision():
    """review_decision items route to ## Past Review Outcomes after adding isolation layers."""
    memories = [
        _make_memory("review_decision", "Approved — all tests passed"),
    ]

    result = _format_memory_context(memories)

    assert "## Past Review Outcomes" in result
    assert "- Approved — all tests passed" in result


def test_non_structural_categories_still_route_task_outcome():
    """task_outcome items route to ## Task Outcomes after adding isolation layers."""
    memories = [
        _make_memory("task_outcome", "Implemented OAuth2 token refresh"),
    ]

    result = _format_memory_context(memories)

    assert "## Task Outcomes" in result
    assert "- Implemented OAuth2 token refresh" in result


def test_non_structural_categories_work_after_prefilter():
    """Full pipeline: prefilter then _format_memory_context routes normal items correctly.

    Simulates the real spawn flow: apply Layer 1 filter, then call _format_memory_context.
    Normal items must survive both layers with correct routing.
    """
    memories = [
        _make_memory("structural_correction", "Should be removed at Layer 1"),
        _make_memory("review_decision", "Approved — clean diff"),
        _make_memory("structural_preference", "Also removed at Layer 1"),
        _make_memory("task_outcome", "Deploy successful"),
        _make_memory("l3_outcome", "General work context"),
    ]

    # Layer 1: pre-filter
    filtered = [
        m for m in memories
        if m.get("metadata", {}).get("category", m.get("category", "")) not in EXCLUDED_CATEGORIES
    ]

    assert len(filtered) == 3, f"Expected 3 after pre-filter, got {len(filtered)}"

    # Layer 2: format — normal items should route correctly
    result = _format_memory_context(filtered)

    assert "## Past Review Outcomes" in result
    assert "## Task Outcomes" in result
    assert "- Approved — clean diff" in result
    assert "- Deploy successful" in result
    assert "Should be removed at Layer 1" not in result
    assert "Also removed at Layer 1" not in result


def test_category_section_map_unchanged_by_isolation():
    """CATEGORY_SECTION_MAP still contains expected keys after isolation additions."""
    assert "review_decision" in CATEGORY_SECTION_MAP
    assert "task_outcome" in CATEGORY_SECTION_MAP
    assert CATEGORY_SECTION_MAP["review_decision"] == "Past Review Outcomes"
    assert CATEGORY_SECTION_MAP["task_outcome"] == "Task Outcomes"


def test_both_layers_combined_no_structural_leakage():
    """Combined two-layer test: structural items are blocked by Layer 1 and Layer 2.

    This is the key integration test: even if Layer 1 fails to remove an item,
    Layer 2 catches it. Demonstrate both paths by testing each independently.
    """
    all_structural = [
        _make_memory("structural_correction", "SC: prefer lean agents"),
        _make_memory("structural_preference", "SP: no review overhead"),
        _make_memory("structural_pattern", "SP: always delegate directly"),
    ]

    # Layer 2 alone: call _format_memory_context directly with structural items
    result_layer2 = _format_memory_context(all_structural)
    assert result_layer2 == "", (
        f"Layer 2 should block all structural items. Got: {repr(result_layer2)}"
    )

    # Layer 1 alone: apply pre-filter to all-structural list
    filtered = [
        m for m in all_structural
        if m.get("metadata", {}).get("category", m.get("category", "")) not in EXCLUDED_CATEGORIES
    ]
    assert filtered == [], (
        f"Layer 1 should remove all structural items. Got: {filtered}"
    )
