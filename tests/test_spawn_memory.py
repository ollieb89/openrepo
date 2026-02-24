"""
Tests for pre-spawn memory retrieval and SOUL injection helpers in spawn.py.

Validates all four requirements:
  RET-01: Memory retrieval from memU /retrieve endpoint
  RET-02: SOUL augmentation with Memory Context section
  RET-03: Budget enforcement (2000 char hard cap)
  RET-04: Graceful degradation on network failure
"""

import sys
import os
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent))

from skills.spawn_specialist.spawn import (
    _retrieve_memories_sync,
    _format_memory_context,
    _build_augmented_soul,
    _write_soul_tempfile,
    MEMORY_CONTEXT_BUDGET,
)


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

    with patch("skills.spawn_specialist.spawn.httpx.Client", return_value=mock_client_instance):
        result = _retrieve_memories_sync("http://localhost:18791", "test-project", "auth module")

    assert result == mock_items
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

    with patch("skills.spawn_specialist.spawn.httpx.Client", return_value=mock_client_instance):
        result = _retrieve_memories_sync("http://localhost:18791", "test-project", "query")

    assert result == []


def test_retrieve_memories_sync_empty_url_returns_empty():
    """Empty base_url returns [] immediately without making any HTTP call."""
    with patch("skills.spawn_specialist.spawn.httpx.Client") as MockClient:
        result = _retrieve_memories_sync("", "test-project", "query")

    assert result == []
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

    with patch("skills.spawn_specialist.spawn.httpx.Client", return_value=mock_client_instance):
        result = _retrieve_memories_sync("http://localhost:18791", "proj", "query")

    assert result == inner_items


# ---------------------------------------------------------------------------
# RET-03: Formatting and budget enforcement
# ---------------------------------------------------------------------------


def test_format_memory_context_empty_list():
    """Empty memory list produces empty string — no header, no placeholder (locked decision)."""
    result = _format_memory_context([])
    assert result == ""


def test_format_memory_context_with_items():
    """Items produce a ## Memory Context section with correct bullet format and source tags."""
    memories = [
        {"resource_url": "Use atomic commits per feature", "category": "l3_outcome"},
        {"resource_url": "Always validate input before processing", "category": "l3_outcome"},
        {"resource_url": "Add retry logic on HTTP calls", "category": "l2_review"},
    ]

    result = _format_memory_context(memories)

    assert result.startswith("## Memory Context\n\n")
    assert "- Use atomic commits per feature (from memory)" in result
    assert "- Always validate input before processing (from memory)" in result
    assert "- Add retry logic on HTTP calls (from L2 review)" in result


def test_format_memory_context_budget_enforcement():
    """Budget enforcement drops items that would exceed MEMORY_CONTEXT_BUDGET (2000 chars)."""
    # Each item is ~400 chars — 6 items = ~2400 chars total, must be cut
    long_text = "X" * 395
    memories = [{"resource_url": long_text, "category": "l3_outcome"} for _ in range(6)]

    result = _format_memory_context(memories)

    # Total length must respect the budget
    assert len(result) <= MEMORY_CONTEXT_BUDGET

    # At least one item was dropped (fewer bullets than input items)
    bullet_count = sum(1 for line in result.splitlines() if line.startswith("- "))
    assert bullet_count < 6


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
    """SOUL augmented with memory context ends with Memory Context section."""
    # Create a mock project structure
    soul_dir = tmp_path / "agents" / "l3_specialist" / "agent"
    soul_dir.mkdir(parents=True)
    soul_file = soul_dir / "SOUL.md"
    base_content = "# Base SOUL\n\nThis is the base SOUL content.\n"
    soul_file.write_text(base_content)

    memory_context = "## Memory Context\n\n- test memory (from memory)"

    result = _build_augmented_soul(tmp_path, memory_context)

    # Must contain original SOUL content
    assert "# Base SOUL" in result
    assert "This is the base SOUL content." in result

    # Must contain the Memory Context section
    assert "## Memory Context" in result
    assert "- test memory (from memory)" in result

    # Memory context must appear after base SOUL
    base_pos = result.index("This is the base SOUL content.")
    memory_pos = result.index("## Memory Context")
    assert memory_pos > base_pos


def test_build_augmented_soul_empty_memory(tmp_path):
    """Empty memory context returns base SOUL unchanged — no Memory Context appended."""
    soul_dir = tmp_path / "agents" / "l3_specialist" / "agent"
    soul_dir.mkdir(parents=True)
    soul_file = soul_dir / "SOUL.md"
    base_content = "# Base SOUL\n\nThis is the base SOUL content.\n"
    soul_file.write_text(base_content)

    result = _build_augmented_soul(tmp_path, "")

    assert result == base_content
    assert "## Memory Context" not in result


def test_build_augmented_soul_missing_soul_file(tmp_path):
    """Missing SOUL.md returns empty string gracefully."""
    # No soul file created — project root exists but SOUL.md does not
    result = _build_augmented_soul(tmp_path, "## Memory Context\n\n- some memory")

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
