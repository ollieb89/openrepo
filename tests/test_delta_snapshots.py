"""
Tests for Phase 42: Delta Snapshots.

Validates all four PERF requirements:
  PERF-05: Per-project memory_cursors tracked in state.json metadata
  PERF-06: Pre-spawn retrieval fetches only memories newer than cursor
  PERF-07: New created_after filter parameter on memU /retrieve endpoint
  PERF-08: Configurable max_snapshots per project with automatic pruning
"""

import json
import sys
import time
import tempfile
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

# Project root on path — matches pattern in test_spawn_memory.py and test_health_scan.py
sys.path.insert(0, "/home/ollie/.openclaw")

# Docker memory service router on path — needed for _filter_after import
sys.path.insert(0, "/home/ollie/.openclaw/docker/memory/memory_service")

from orchestration.state_engine import JarvisState


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_jarvis_state(tmp_path: Path) -> JarvisState:
    """Create a minimal workspace-state.json and return a JarvisState instance."""
    state_file = tmp_path / "workspace-state.json"
    state = {
        "version": "1.0.0",
        "protocol": "jarvis",
        "tasks": {},
        "metadata": {
            "created_at": time.time(),
            "last_updated": time.time(),
        },
    }
    state_file.write_text(json.dumps(state))
    return JarvisState(state_file)


# ---------------------------------------------------------------------------
# PERF-05: JarvisState cursor helpers
# ---------------------------------------------------------------------------


def test_get_memory_cursor_absent(tmp_path):
    """get_memory_cursor returns None when memory_cursors key is absent from metadata."""
    jarvis = _make_jarvis_state(tmp_path)
    result = jarvis.get_memory_cursor("testproj")
    assert result is None


def test_update_memory_cursor_writes(tmp_path):
    """update_memory_cursor writes the ISO timestamp under metadata.memory_cursors[project_id]."""
    jarvis = _make_jarvis_state(tmp_path)
    cursor_value = "2026-02-24T10:00:00+00:00"
    jarvis.update_memory_cursor("testproj", cursor_value)

    # Read raw state JSON from disk and verify
    state_file = tmp_path / "workspace-state.json"
    state = json.loads(state_file.read_text())
    assert state["metadata"]["memory_cursors"]["testproj"] == cursor_value


def test_get_memory_cursor_corrupt(tmp_path):
    """get_memory_cursor returns None when the stored value is not a valid ISO timestamp."""
    state_file = tmp_path / "workspace-state.json"
    state = {
        "version": "1.0.0",
        "protocol": "jarvis",
        "tasks": {},
        "metadata": {
            "created_at": time.time(),
            "last_updated": time.time(),
            "memory_cursors": {
                "testproj": "not-a-date",
            },
        },
    }
    state_file.write_text(json.dumps(state))
    jarvis = JarvisState(state_file)
    result = jarvis.get_memory_cursor("testproj")
    assert result is None


# ---------------------------------------------------------------------------
# PERF-06: Spawn retrieval with cursor — (list, bool) return type
# ---------------------------------------------------------------------------


def test_retrieve_sends_created_after():
    """_retrieve_memories_sync sends created_after in the JSON payload when provided.

    Also verifies the function accepts a created_after keyword parameter.
    The function must return a (list, bool) tuple — this test checks BOTH conditions.
    """
    from skills.spawn_specialist.spawn import _retrieve_memories_sync

    mock_response = MagicMock()
    mock_response.json.return_value = []
    mock_response.raise_for_status = MagicMock()

    mock_client_instance = MagicMock()
    mock_client_instance.post.return_value = mock_response
    mock_client_instance.__enter__ = MagicMock(return_value=mock_client_instance)
    mock_client_instance.__exit__ = MagicMock(return_value=False)

    cursor = "2026-02-24T10:00:00+00:00"

    with patch("skills.spawn_specialist.spawn.httpx.Client", return_value=mock_client_instance):
        result = _retrieve_memories_sync(
            "http://fake-memu:18791",
            "testproj",
            "some query",
            created_after=cursor,
        )

    # Return type must be (list, bool) — not a bare list
    assert isinstance(result, tuple), f"Expected tuple, got {type(result)}"
    assert len(result) == 2, f"Expected 2-element tuple, got len={len(result)}"
    items, ok = result

    # Payload must include created_after
    call_kwargs = mock_client_instance.post.call_args
    sent_payload = call_kwargs[1]["json"] if call_kwargs[1] else call_kwargs[0][1]
    assert "created_after" in sent_payload, "created_after not found in sent payload"
    assert sent_payload["created_after"] == cursor


def test_cursor_not_updated_on_fetch_failure():
    """_retrieve_memories_sync returns ok=False on network failure.

    The caller uses ok to decide whether to advance the cursor — False means
    the cursor must NOT be advanced so the next spawn retries the same window.
    """
    from skills.spawn_specialist.spawn import _retrieve_memories_sync
    import httpx

    mock_client_instance = MagicMock()
    mock_client_instance.post.side_effect = httpx.ConnectError("Connection refused")
    mock_client_instance.__enter__ = MagicMock(return_value=mock_client_instance)
    mock_client_instance.__exit__ = MagicMock(return_value=False)

    with patch("skills.spawn_specialist.spawn.httpx.Client", return_value=mock_client_instance):
        result = _retrieve_memories_sync("http://bad-host:9999", "proj", "query")

    assert isinstance(result, tuple), f"Expected tuple, got {type(result)}"
    items, ok = result
    assert ok is False, f"Expected ok=False on failure, got ok={ok}"


def test_cursor_updated_after_success():
    """_retrieve_memories_sync returns ok=True on a successful HTTP 200 response.

    The caller uses ok=True to advance the cursor after the fetch.
    """
    from skills.spawn_specialist.spawn import _retrieve_memories_sync

    mock_response = MagicMock()
    mock_response.json.return_value = []
    mock_response.raise_for_status = MagicMock()

    mock_client_instance = MagicMock()
    mock_client_instance.post.return_value = mock_response
    mock_client_instance.__enter__ = MagicMock(return_value=mock_client_instance)
    mock_client_instance.__exit__ = MagicMock(return_value=False)

    with patch("skills.spawn_specialist.spawn.httpx.Client", return_value=mock_client_instance):
        result = _retrieve_memories_sync("http://memu:18791", "proj", "query")

    assert isinstance(result, tuple), f"Expected tuple, got {type(result)}"
    items, ok = result
    assert ok is True, f"Expected ok=True on success, got ok={ok}"


# ---------------------------------------------------------------------------
# PERF-07: FastAPI _filter_after helper
# ---------------------------------------------------------------------------


def test_filter_after_timestamp():
    """_filter_after returns only items whose created_at is strictly after the cutoff.

    Items exactly at the cutoff are excluded (strictly after).
    """
    from routers.retrieve import _filter_after

    cutoff = "2026-02-24T10:00:00+00:00"
    items = [
        {"id": "before", "created_at": "2026-02-24T09:00:00+00:00"},   # before — exclude
        {"id": "after",  "created_at": "2026-02-24T11:00:00+00:00"},   # after — include
        {"id": "exact",  "created_at": "2026-02-24T10:00:00+00:00"},   # at cutoff — exclude
    ]

    result = _filter_after(items, cutoff)

    ids = [item["id"] for item in result]
    assert "after" in ids
    assert "before" not in ids
    assert "exact" not in ids


def test_filter_after_missing_created_at():
    """_filter_after passes through items with no created_at key (conservative)."""
    from routers.retrieve import _filter_after

    cutoff = "2026-02-24T10:00:00+00:00"
    items = [
        {"id": "no_ts"},               # no created_at — should pass through
        {"id": "null_ts", "created_at": None},  # None — should pass through
    ]

    result = _filter_after(items, cutoff)

    ids = [item["id"] for item in result]
    assert "no_ts" in ids
    assert "null_ts" in ids


def test_filter_after_unix_float():
    """_filter_after handles Unix float timestamps in created_at correctly."""
    from routers.retrieve import _filter_after

    # Use a far-future Unix timestamp to ensure it's "after" any reasonable cutoff
    future_float = time.time() + 1_000_000   # ~11 days in the future
    past_float = 0.0  # 1970-01-01 — clearly before any modern cutoff

    cutoff = "2026-02-24T10:00:00+00:00"
    items = [
        {"id": "future", "created_at": future_float},
        {"id": "past",   "created_at": past_float},
    ]

    result = _filter_after(items, cutoff)

    ids = [item["id"] for item in result]
    assert "future" in ids
    assert "past" not in ids


def test_filter_after_bad_cursor_passthrough():
    """_filter_after returns all items unchanged when created_after is not a valid ISO date."""
    from routers.retrieve import _filter_after

    items = [
        {"id": "a", "created_at": "2026-02-24T09:00:00+00:00"},
        {"id": "b", "created_at": "2026-02-24T11:00:00+00:00"},
    ]

    result = _filter_after(items, "not-a-date")

    assert len(result) == 2
    ids = [item["id"] for item in result]
    assert "a" in ids
    assert "b" in ids


# ---------------------------------------------------------------------------
# PERF-08: Snapshot pruning
# ---------------------------------------------------------------------------


def test_prune_called_when_configured(tmp_path):
    """capture_semantic_snapshot calls cleanup_old_snapshots when max_snapshots is set."""
    from orchestration.snapshot import capture_semantic_snapshot

    with (
        patch("orchestration.snapshot.load_project_config") as mock_load_cfg,
        patch("orchestration.snapshot.cleanup_old_snapshots") as mock_cleanup,
        patch("orchestration.snapshot.subprocess.run") as mock_run,
        patch("orchestration.snapshot.get_snapshot_dir") as mock_snapdir,
    ):
        # Provide a valid max_snapshots in l3_overrides
        mock_load_cfg.return_value = {"l3_overrides": {"max_snapshots": 5}}

        # Mock snapshot dir to use tmp_path
        snapshots_dir = tmp_path / ".openclaw" / "testproj" / "snapshots"
        snapshots_dir.mkdir(parents=True, exist_ok=True)
        mock_snapdir.return_value = snapshots_dir

        # Mock subprocess.run to return fake diff output
        mock_diff = MagicMock()
        mock_diff.stdout = "diff --git a/foo.py b/foo.py\n+line"
        mock_diff.returncode = 0

        mock_stat = MagicMock()
        mock_stat.stdout = " 1 file changed, 1 insertion(+)"
        mock_stat.returncode = 0

        mock_run.side_effect = [mock_diff, mock_stat]

        capture_semantic_snapshot("task-001", str(tmp_path), "testproj")

        mock_cleanup.assert_called_once()
        call_kwargs = mock_cleanup.call_args[1] if mock_cleanup.call_args[1] else {}
        call_args = mock_cleanup.call_args[0] if mock_cleanup.call_args[0] else ()
        # Verify max_snapshots=5 was passed (either positional or keyword)
        assert 5 in call_args or call_kwargs.get("max_snapshots") == 5


def test_prune_not_called_when_unconfigured(tmp_path):
    """capture_semantic_snapshot does NOT call cleanup_old_snapshots when max_snapshots absent."""
    from orchestration.snapshot import capture_semantic_snapshot

    with (
        patch("orchestration.snapshot.load_project_config") as mock_load_cfg,
        patch("orchestration.snapshot.cleanup_old_snapshots") as mock_cleanup,
        patch("orchestration.snapshot.subprocess.run") as mock_run,
        patch("orchestration.snapshot.get_snapshot_dir") as mock_snapdir,
    ):
        # l3_overrides with no max_snapshots key
        mock_load_cfg.return_value = {"l3_overrides": {}}

        snapshots_dir = tmp_path / ".openclaw" / "testproj" / "snapshots"
        snapshots_dir.mkdir(parents=True, exist_ok=True)
        mock_snapdir.return_value = snapshots_dir

        mock_diff = MagicMock()
        mock_diff.stdout = "diff --git a/bar.py b/bar.py\n+line"
        mock_diff.returncode = 0

        mock_stat = MagicMock()
        mock_stat.stdout = " 1 file changed, 1 insertion(+)"
        mock_stat.returncode = 0

        mock_run.side_effect = [mock_diff, mock_stat]

        capture_semantic_snapshot("task-002", str(tmp_path), "testproj")

        mock_cleanup.assert_not_called()


def test_prune_failure_nonfatal(tmp_path):
    """capture_semantic_snapshot completes without raising when cleanup_old_snapshots raises OSError."""
    from orchestration.snapshot import capture_semantic_snapshot

    with (
        patch("orchestration.snapshot.load_project_config") as mock_load_cfg,
        patch("orchestration.snapshot.cleanup_old_snapshots") as mock_cleanup,
        patch("orchestration.snapshot.subprocess.run") as mock_run,
        patch("orchestration.snapshot.get_snapshot_dir") as mock_snapdir,
    ):
        mock_load_cfg.return_value = {"l3_overrides": {"max_snapshots": 10}}

        snapshots_dir = tmp_path / ".openclaw" / "testproj" / "snapshots"
        snapshots_dir.mkdir(parents=True, exist_ok=True)
        mock_snapdir.return_value = snapshots_dir

        # Pruning raises an OSError — must not propagate
        mock_cleanup.side_effect = OSError("permission denied")

        mock_diff = MagicMock()
        mock_diff.stdout = "diff --git a/baz.py b/baz.py\n+line"
        mock_diff.returncode = 0

        mock_stat = MagicMock()
        mock_stat.stdout = " 1 file changed, 1 insertion(+)"
        mock_stat.returncode = 0

        mock_run.side_effect = [mock_diff, mock_stat]

        # Must NOT raise
        result = capture_semantic_snapshot("task-003", str(tmp_path), "testproj")
        assert result is not None
