"""
Tests for write_python_metrics_snapshot() in openclaw.metrics.

These tests cover:
- Atomic write (temp file + os.replace)
- Throttle behavior (750ms window)
- Failure isolation (errors swallowed, never raised to caller)
- Lock-safety (no JarvisState or read_state() called internally)
"""

import json
import time
from pathlib import Path

import pytest

import openclaw.metrics as m
from openclaw.metrics import write_python_metrics_snapshot


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture(autouse=True)
def reset_throttle():
    """Clear per-project throttle state before each test so tests are isolated."""
    m._last_snapshot_times.clear()
    yield
    m._last_snapshot_times.clear()


def _make_state_file(tmp_path: Path) -> Path:
    """Write a minimal workspace-state.json and return its path."""
    state_file = tmp_path / "workspace-state.json"
    state_file.write_text(
        json.dumps(
            {
                "version": "1.0.0",
                "tasks": {
                    "t1": {"status": "pending"},
                    "t2": {"status": "in_progress"},
                    "t3": {"status": "completed"},
                },
                "metadata": {},
            }
        )
    )
    return state_file


def _minimal_state_dict() -> dict:
    return {
        "version": "1.0.0",
        "tasks": {
            "t1": {"status": "pending"},
            "t2": {"status": "in_progress"},
            "t3": {"status": "completed"},
        },
        "metadata": {},
    }


# ---------------------------------------------------------------------------
# Test: writes valid JSON with expected keys
# ---------------------------------------------------------------------------


def test_writes_valid_json(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """write_python_metrics_snapshot writes python-metrics.json with required keys."""
    # Disable throttle so write always proceeds
    monkeypatch.setattr("openclaw.metrics._SNAPSHOT_THROTTLE_S", 0.0)

    state_file = _make_state_file(tmp_path)
    project_id = "test-project"
    state_dict = _minimal_state_dict()

    write_python_metrics_snapshot(project_id, state_file, state_dict)

    snapshot_path = tmp_path / "python-metrics.json"
    assert snapshot_path.exists(), "python-metrics.json should be written"

    data = json.loads(snapshot_path.read_text())

    # Top-level namespaces
    assert "python" in data, "response must have 'python' key"
    assert "meta" in data, "response must have 'meta' key"

    # python.* sub-keys (from collect_metrics_from_state shape)
    assert "tasks" in data["python"], "python.tasks must be present"
    assert "pool" in data["python"], "python.pool must be present"

    # meta.* sub-keys
    assert "generated_at" in data["meta"], "meta.generated_at must be present"
    assert "source_state_mtime" in data["meta"], "meta.source_state_mtime must be present"


# ---------------------------------------------------------------------------
# Test: atomic write via temp file + os.replace
# ---------------------------------------------------------------------------


def test_atomic_write(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """python-metrics.json is always complete — no partial writes visible to readers."""
    monkeypatch.setattr("openclaw.metrics._SNAPSHOT_THROTTLE_S", 0.0)

    state_file = _make_state_file(tmp_path)
    project_id = "test-project"
    state_dict = _minimal_state_dict()

    # Track os.replace calls to confirm atomic swap was used
    replace_calls = []
    original_replace = __import__("os").replace

    def patched_replace(src: str, dst: str) -> None:
        replace_calls.append((src, dst))
        original_replace(src, dst)

    monkeypatch.setattr("os.replace", patched_replace)

    write_python_metrics_snapshot(project_id, state_file, state_dict)

    assert len(replace_calls) == 1, "os.replace must be called exactly once (atomic swap)"
    src, dst = replace_calls[0]
    assert dst == str(tmp_path / "python-metrics.json"), "destination must be python-metrics.json"
    assert src != dst, "source (temp file) must differ from destination"


# ---------------------------------------------------------------------------
# Test: throttle — second call within window is skipped
# ---------------------------------------------------------------------------


def test_throttle_skips_second_write(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """When called twice within the throttle window, the file is written exactly once."""
    # Use a large throttle window so the second call is definitely inside it
    monkeypatch.setattr("openclaw.metrics._SNAPSHOT_THROTTLE_S", 60.0)

    state_file = _make_state_file(tmp_path)
    project_id = "test-project"
    state_dict = _minimal_state_dict()

    write_calls = []
    original_replace = __import__("os").replace

    def patched_replace(src: str, dst: str) -> None:
        if "python-metrics" in dst:
            write_calls.append(dst)
        original_replace(src, dst)

    monkeypatch.setattr("os.replace", patched_replace)

    write_python_metrics_snapshot(project_id, state_file, state_dict)
    write_python_metrics_snapshot(project_id, state_file, state_dict)

    assert len(write_calls) == 1, "throttle must prevent second write within the window"


# ---------------------------------------------------------------------------
# Test: failure swallowed — os.replace raises OSError, no exception propagated
# ---------------------------------------------------------------------------


def test_failure_swallowed(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """All exceptions inside write_python_metrics_snapshot are swallowed — callers never see them."""
    monkeypatch.setattr("openclaw.metrics._SNAPSHOT_THROTTLE_S", 0.0)

    state_file = _make_state_file(tmp_path)
    project_id = "test-project"
    state_dict = _minimal_state_dict()

    def raise_os_error(src: str, dst: str) -> None:
        raise OSError("simulated disk full error")

    monkeypatch.setattr("os.replace", raise_os_error)

    # Must NOT raise — errors must be swallowed internally
    write_python_metrics_snapshot(project_id, state_file, state_dict)


# ---------------------------------------------------------------------------
# Test: lock-safety — function does NOT call JarvisState or read_state() internally
# ---------------------------------------------------------------------------


def test_no_reentrant_lock(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """write_python_metrics_snapshot must not instantiate JarvisState or call read_state().

    The function receives state_dict as a parameter — calling read_state() inside
    would create a re-entrant lock deadlock when invoked from _write_state_locked.
    """
    monkeypatch.setattr("openclaw.metrics._SNAPSHOT_THROTTLE_S", 0.0)

    state_file = _make_state_file(tmp_path)
    project_id = "test-project"
    state_dict = _minimal_state_dict()

    jarvis_instantiated = []

    # Patch JarvisState in the metrics module to detect instantiation
    class MockJarvisState:
        def __init__(self, *args, **kwargs):
            jarvis_instantiated.append(args)

        def read_state(self):
            jarvis_instantiated.append("read_state called")
            return {}

    monkeypatch.setattr("openclaw.metrics.JarvisState", MockJarvisState, raising=False)

    write_python_metrics_snapshot(project_id, state_file, state_dict)

    assert len(jarvis_instantiated) == 0, (
        "write_python_metrics_snapshot must NOT instantiate JarvisState — "
        "it should use the state_dict parameter directly to avoid re-entrant lock deadlock"
    )
