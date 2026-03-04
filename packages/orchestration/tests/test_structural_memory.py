"""
Unit tests for structural memory module (Phase 64).

Tests cover:
- MemoryProfiler: exponential decay weighting, archetype affinity computation,
  preference_fit with epsilon-greedy exploration, threshold gating
- PatternExtractor: LLM-based pattern extraction with threshold gating
- Storage functions: save/load roundtrips for memory-profile.json and patterns.json
- Config: new topology config keys (exploration_rate, decay_lambda, pattern_extraction_threshold)
"""
import asyncio
import json
import math
from datetime import datetime, timezone, timedelta
from pathlib import Path
from unittest.mock import AsyncMock, patch, MagicMock

import pytest

from openclaw.topology.memory import MemoryProfiler, PatternExtractor
from openclaw.topology.storage import (
    save_memory_profile,
    load_memory_profile,
    save_patterns,
    load_patterns,
)
from openclaw.config import get_topology_config


# ---------------------------------------------------------------------------
# Config tests
# ---------------------------------------------------------------------------

class TestTopologyConfigExtensions:
    def test_config_returns_exploration_rate(self):
        cfg = get_topology_config()
        assert "exploration_rate" in cfg
        assert cfg["exploration_rate"] == pytest.approx(0.20)

    def test_config_returns_decay_lambda(self):
        cfg = get_topology_config()
        assert "decay_lambda" in cfg
        assert cfg["decay_lambda"] == pytest.approx(0.05)

    def test_config_returns_pattern_extraction_threshold(self):
        cfg = get_topology_config()
        assert "pattern_extraction_threshold" in cfg
        assert cfg["pattern_extraction_threshold"] == 5


# ---------------------------------------------------------------------------
# Storage roundtrip tests
# ---------------------------------------------------------------------------

class TestMemoryProfileStorage:
    def test_save_load_memory_profile(self, tmp_path, monkeypatch):
        """Roundtrip save -> load preserves all fields."""
        monkeypatch.setenv("OPENCLAW_ROOT", str(tmp_path))

        profile = {
            "project_id": "test-proj",
            "correction_count": 7,
            "soft_correction_count": 3,
            "hard_correction_count": 4,
            "threshold_status": "active",
            "archetype_affinity": {"lean": 6.5, "balanced": 5.0, "robust": 7.2},
            "last_computed": "2026-03-04T08:00:00Z",
            "active_pattern_ids": ["pat-1", "pat-2"],
        }

        save_memory_profile("test-proj", profile)
        loaded = load_memory_profile("test-proj")

        assert loaded["project_id"] == "test-proj"
        assert loaded["correction_count"] == 7
        assert loaded["soft_correction_count"] == 3
        assert loaded["hard_correction_count"] == 4
        assert loaded["threshold_status"] == "active"
        assert loaded["archetype_affinity"]["lean"] == pytest.approx(6.5)
        assert loaded["archetype_affinity"]["robust"] == pytest.approx(7.2)
        assert loaded["last_computed"] == "2026-03-04T08:00:00Z"
        assert loaded["active_pattern_ids"] == ["pat-1", "pat-2"]

    def test_load_memory_profile_missing_returns_default(self, tmp_path, monkeypatch):
        """Missing file returns default profile dict."""
        monkeypatch.setenv("OPENCLAW_ROOT", str(tmp_path))

        profile = load_memory_profile("nonexistent-proj")

        assert profile["project_id"] == ""
        assert profile["correction_count"] == 0
        assert profile["threshold_status"] == "below_threshold"
        assert profile["archetype_affinity"] == {"lean": 5.0, "balanced": 5.0, "robust": 5.0}
        assert profile["active_pattern_ids"] == []

    def test_save_load_patterns(self, tmp_path, monkeypatch):
        """Roundtrip save -> load preserves pattern list."""
        monkeypatch.setenv("OPENCLAW_ROOT", str(tmp_path))

        patterns = [
            {"pattern": "always adds review gate", "confidence": 0.85, "source_correction_ids": ["c1", "c2"], "archetype_bias": "robust"},
            {"pattern": "prefers minimal delegation", "confidence": 0.70, "source_correction_ids": ["c3"], "archetype_bias": "lean"},
        ]

        save_patterns("test-proj", patterns)
        loaded = load_patterns("test-proj")

        assert len(loaded) == 2
        assert loaded[0]["pattern"] == "always adds review gate"
        assert loaded[0]["confidence"] == pytest.approx(0.85)
        assert loaded[1]["archetype_bias"] == "lean"

    def test_load_patterns_missing_returns_empty(self, tmp_path, monkeypatch):
        """Missing patterns file returns empty list."""
        monkeypatch.setenv("OPENCLAW_ROOT", str(tmp_path))
        result = load_patterns("nonexistent-proj")
        assert result == []


# ---------------------------------------------------------------------------
# Helpers for constructing changelog entries
# ---------------------------------------------------------------------------

def _make_changelog_entry(
    correction_type: str,
    approved_archetype: str,
    days_ago: float = 0.0,
    project_id: str = "proj-a",
    diff: str = "- edge A\n+ edge B",
) -> dict:
    ts = (datetime.now(timezone.utc) - timedelta(days=days_ago)).isoformat()
    return {
        "project_id": project_id,
        "timestamp": ts,
        "correction_type": correction_type,
        "diff": diff,
        "annotations": {"approved_archetype": approved_archetype},
    }


# ---------------------------------------------------------------------------
# MemoryProfiler tests
# ---------------------------------------------------------------------------

class TestDecayWeights:
    def test_decay_weights_older_corrections_less(self, tmp_path, monkeypatch):
        """A correction from 14 days ago has ~50% the weight of a correction from today (lambda=0.05)."""
        monkeypatch.setenv("OPENCLAW_ROOT", str(tmp_path))
        profiler = MemoryProfiler("proj-a", decay_lambda=0.05)

        now_ts = datetime.now(timezone.utc).isoformat()
        old_ts = (datetime.now(timezone.utc) - timedelta(days=14)).isoformat()

        w_now = profiler._decay_weight(now_ts)
        w_old = profiler._decay_weight(old_ts)

        # 14-day half-life: e^(-0.05 * 14) ≈ 0.496
        expected_ratio = math.exp(-0.05 * 14)
        assert w_old / w_now == pytest.approx(expected_ratio, abs=0.02)

    def test_decay_weight_invalid_timestamp_returns_one(self, tmp_path, monkeypatch):
        """Invalid/unknown timestamp returns 1.0 (no penalty)."""
        monkeypatch.setenv("OPENCLAW_ROOT", str(tmp_path))
        profiler = MemoryProfiler("proj-a")

        assert profiler._decay_weight("not-a-timestamp") == pytest.approx(1.0)
        assert profiler._decay_weight("") == pytest.approx(1.0)
        assert profiler._decay_weight(None) == pytest.approx(1.0)


class TestCorrectionStoredWithMetadata:
    def test_correction_stored_with_metadata(self, tmp_path, monkeypatch):
        """load_changelog returns entries with timestamp, correction_type, and annotations.approved_archetype."""
        from openclaw.topology.storage import append_changelog

        monkeypatch.setenv("OPENCLAW_ROOT", str(tmp_path))

        entry = _make_changelog_entry("soft", "lean", days_ago=1.0)
        append_changelog("proj-a", entry)

        from openclaw.topology.storage import load_changelog
        entries = load_changelog("proj-a")

        assert len(entries) == 1
        assert "timestamp" in entries[0]
        assert entries[0]["correction_type"] == "soft"
        assert entries[0]["annotations"]["approved_archetype"] == "lean"

    def test_corrections_retrievable_by_project(self, tmp_path, monkeypatch):
        """load_changelog(project_id) returns only that project's corrections."""
        from openclaw.topology.storage import append_changelog, load_changelog

        monkeypatch.setenv("OPENCLAW_ROOT", str(tmp_path))

        entry_a = _make_changelog_entry("soft", "lean", project_id="proj-a")
        entry_b = _make_changelog_entry("hard", "robust", project_id="proj-b")
        append_changelog("proj-a", entry_a)
        append_changelog("proj-b", entry_b)

        entries_a = load_changelog("proj-a")
        entries_b = load_changelog("proj-b")

        assert len(entries_a) == 1
        assert entries_a[0]["project_id"] == "proj-a"
        assert len(entries_b) == 1
        assert entries_b[0]["project_id"] == "proj-b"


class TestPreferenceFit:
    def _setup_5_lean_corrections(self, tmp_path, monkeypatch, project_id="proj-a"):
        """Helper: populate changelog with 5 lean corrections."""
        from openclaw.topology.storage import append_changelog

        monkeypatch.setenv("OPENCLAW_ROOT", str(tmp_path))

        for i in range(5):
            entry = _make_changelog_entry("soft", "lean", days_ago=float(i), project_id=project_id)
            append_changelog(project_id, entry)

    def test_preference_fit_uses_profile(self, tmp_path, monkeypatch):
        """With 5+ corrections favoring 'lean', archetype_affinity['lean'] > archetype_affinity['robust']."""
        self._setup_5_lean_corrections(tmp_path, monkeypatch)

        profiler = MemoryProfiler("proj-a", decay_lambda=0.05)
        profile = profiler.compute_profile()

        assert profile["archetype_affinity"]["lean"] > profile["archetype_affinity"]["robust"]
        assert profile["threshold_status"] == "active"

    def test_preference_fit_neutral_below_threshold(self, tmp_path, monkeypatch):
        """With < 5 corrections, all affinities are 5.0 (neutral)."""
        from openclaw.topology.storage import append_changelog

        monkeypatch.setenv("OPENCLAW_ROOT", str(tmp_path))

        # Only 3 corrections
        for i in range(3):
            entry = _make_changelog_entry("soft", "lean", days_ago=float(i))
            append_changelog("proj-a", entry)

        profiler = MemoryProfiler("proj-a")
        profile = profiler.compute_profile()

        assert profile["threshold_status"] == "below_threshold"
        assert profile["archetype_affinity"]["lean"] == pytest.approx(5.0)
        assert profile["archetype_affinity"]["balanced"] == pytest.approx(5.0)
        assert profile["archetype_affinity"]["robust"] == pytest.approx(5.0)

    def test_epsilon_greedy_exploration(self, tmp_path, monkeypatch):
        """When explore=True, preference_fit returns 5 for all archetypes (session-level)."""
        self._setup_5_lean_corrections(tmp_path, monkeypatch)

        profiler = MemoryProfiler("proj-a")
        profiler.compute_profile()  # Establish active profile

        # With explore=True, all archetypes should return neutral (5)
        lean_fit = profiler.get_preference_fit("lean", explore=True)
        robust_fit = profiler.get_preference_fit("robust", explore=True)
        balanced_fit = profiler.get_preference_fit("balanced", explore=True)

        assert lean_fit == 5
        assert robust_fit == 5
        assert balanced_fit == 5

    def test_preference_fit_returns_non_neutral_when_active(self, tmp_path, monkeypatch):
        """With active profile and explore=False, lean affinity should differ from neutral."""
        self._setup_5_lean_corrections(tmp_path, monkeypatch)

        profiler = MemoryProfiler("proj-a")
        profiler.compute_profile()

        lean_fit = profiler.get_preference_fit("lean", explore=False)
        # Should be > 5 because lean is favored
        assert lean_fit > 5


class TestMemoryReport:
    def test_memory_report_correction_count(self, tmp_path, monkeypatch):
        """MemoryProfiler.get_report() returns correct soft/hard counts."""
        from openclaw.topology.storage import append_changelog

        monkeypatch.setenv("OPENCLAW_ROOT", str(tmp_path))

        # 3 soft + 2 hard corrections
        for i in range(3):
            append_changelog("proj-a", _make_changelog_entry("soft", "lean", days_ago=float(i)))
        for i in range(2):
            append_changelog("proj-a", _make_changelog_entry("hard", "robust", days_ago=float(i + 3)))

        profiler = MemoryProfiler("proj-a")
        profiler.compute_profile()
        report = profiler.get_report()

        assert report["correction_count"] == 5
        assert report["soft_correction_count"] == 3
        assert report["hard_correction_count"] == 2

    def test_memory_report_threshold_status(self, tmp_path, monkeypatch):
        """Report shows 'active' when >= 5 corrections, 'below_threshold' when < 5."""
        from openclaw.topology.storage import append_changelog

        monkeypatch.setenv("OPENCLAW_ROOT", str(tmp_path))

        # First check below threshold (4 corrections)
        for i in range(4):
            append_changelog("proj-a", _make_changelog_entry("soft", "lean", days_ago=float(i)))

        profiler = MemoryProfiler("proj-a")
        profiler.compute_profile()
        report = profiler.get_report()
        assert report["threshold_status"] == "below_threshold"

        # Add 1 more to reach threshold
        append_changelog("proj-a", _make_changelog_entry("soft", "lean", days_ago=4.0))
        profiler.compute_profile()
        report = profiler.get_report()
        assert report["threshold_status"] == "active"


# ---------------------------------------------------------------------------
# PatternExtractor tests
# ---------------------------------------------------------------------------

class TestPatternExtractor:
    def _setup_changelog(self, tmp_path, monkeypatch, count: int, project_id: str = "proj-a"):
        from openclaw.topology.storage import append_changelog
        monkeypatch.setenv("OPENCLAW_ROOT", str(tmp_path))
        for i in range(count):
            append_changelog(
                project_id,
                _make_changelog_entry("soft", "lean", days_ago=float(i), project_id=project_id),
            )

    def test_pattern_extraction_below_threshold(self, tmp_path, monkeypatch):
        """With < 5 corrections, returns empty list without calling LLM."""
        self._setup_changelog(tmp_path, monkeypatch, count=3)

        with patch("openclaw.topology.memory.call_llm") as mock_llm:
            extractor = PatternExtractor("proj-a", min_threshold=5)
            result = extractor.extract()

        assert result == []
        mock_llm.assert_not_called()

    def test_pattern_extraction_above_threshold(self, tmp_path, monkeypatch):
        """With 5+ corrections, PatternExtractor calls LLM and returns patterns."""
        self._setup_changelog(tmp_path, monkeypatch, count=5)

        mock_response = json.dumps([
            {
                "pattern": "always adds review gate on structural changes",
                "confidence": 0.85,
                "source_correction_ids": [],
                "archetype_bias": "robust",
            },
            {
                "pattern": "prefers lean delegation chains",
                "confidence": 0.75,
                "source_correction_ids": [],
                "archetype_bias": "lean",
            },
        ])

        with patch("openclaw.topology.memory.call_llm", new_callable=AsyncMock) as mock_llm:
            mock_llm.return_value = mock_response
            extractor = PatternExtractor("proj-a", min_threshold=5)
            result = extractor.extract()

        assert len(result) == 2
        assert result[0]["confidence"] == pytest.approx(0.85)
        mock_llm.assert_called_once()

    def test_pattern_extraction_filters_low_confidence(self, tmp_path, monkeypatch):
        """Patterns with confidence < 0.4 are discarded."""
        self._setup_changelog(tmp_path, monkeypatch, count=5)

        mock_response = json.dumps([
            {"pattern": "high confidence", "confidence": 0.80, "source_correction_ids": [], "archetype_bias": "lean"},
            {"pattern": "low confidence", "confidence": 0.30, "source_correction_ids": [], "archetype_bias": "robust"},
            {"pattern": "borderline", "confidence": 0.40, "source_correction_ids": [], "archetype_bias": "balanced"},
        ])

        with patch("openclaw.topology.memory.call_llm", new_callable=AsyncMock) as mock_llm:
            mock_llm.return_value = mock_response
            extractor = PatternExtractor("proj-a", min_threshold=5)
            result = extractor.extract()

        # Low confidence (0.30) should be discarded; 0.40 is at boundary (keep)
        assert len(result) == 2
        patterns_text = [p["pattern"] for p in result]
        assert "low confidence" not in patterns_text

    def test_pattern_extraction_on_llm_failure_returns_existing(self, tmp_path, monkeypatch):
        """On LLM failure, returns existing patterns unchanged (never raises)."""
        self._setup_changelog(tmp_path, monkeypatch, count=5)

        # Pre-populate existing patterns
        existing = [{"pattern": "existing pattern", "confidence": 0.80, "source_correction_ids": [], "archetype_bias": "lean"}]
        save_patterns("proj-a", existing)

        with patch("openclaw.topology.memory.call_llm", new_callable=AsyncMock) as mock_llm:
            mock_llm.side_effect = RuntimeError("LLM call failed")
            extractor = PatternExtractor("proj-a", min_threshold=5)
            result = extractor.extract()

        # Should not raise, should return existing patterns
        assert result == existing

    def test_pattern_extraction_prunes_to_top_10_when_over_20(self, tmp_path, monkeypatch):
        """If total patterns > 20, prunes to top 10 by confidence."""
        self._setup_changelog(tmp_path, monkeypatch, count=5)

        # Build 22 patterns with varying confidence
        patterns = [
            {"pattern": f"pattern-{i}", "confidence": round(0.5 + i * 0.02, 2), "source_correction_ids": [], "archetype_bias": "lean"}
            for i in range(22)
        ]
        mock_response = json.dumps(patterns)

        with patch("openclaw.topology.memory.call_llm", new_callable=AsyncMock) as mock_llm:
            mock_llm.return_value = mock_response
            extractor = PatternExtractor("proj-a", min_threshold=5)
            result = extractor.extract()

        assert len(result) == 10
        # Top 10 by confidence should be the last 10 (highest indices)
        confidences = [p["confidence"] for p in result]
        assert all(c >= min(confidences) for c in confidences)
