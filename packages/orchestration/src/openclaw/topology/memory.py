"""
Structural Memory Module (Phase 64)

Provides MemoryProfiler and PatternExtractor for adaptive preference scoring
based on historical correction data.

MemoryProfiler:
    Computes archetype affinity scores using exponential decay weighting.
    Supports epsilon-greedy exploration for diversity in proposals.

PatternExtractor:
    Uses LLM to extract recurring structural patterns from correction diffs.
    Only activates when correction count meets the configured threshold.
"""
import asyncio
import json
import logging
import math
from datetime import datetime, timezone
from typing import Optional

from openclaw.config import get_topology_config
from openclaw.topology.llm_client import call_llm, strip_markdown_fences
from openclaw.topology.storage import (
    load_changelog,
    save_memory_profile,
    load_memory_profile,
    save_patterns,
    load_patterns,
)

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# LLM prompt constants
# ---------------------------------------------------------------------------

PATTERN_EXTRACTION_SYSTEM = """You are an expert at analyzing AI agent orchestration topology corrections.
Your task is to identify recurring structural patterns from a series of correction diffs.

Return a JSON array of pattern objects. Each pattern object must have exactly these fields:
- pattern: (string) A concise description of the structural preference or anti-pattern observed
- confidence: (float 0.0–1.0) How confident you are this is a real recurring pattern
- source_correction_ids: (array of strings) Correction identifiers that evidence this pattern
- archetype_bias: (string) One of "lean", "balanced", "robust" — the archetype this pattern favors

Return ONLY the JSON array with no markdown fences or explanation.
Discard patterns where confidence < 0.4.
If no clear patterns exist, return an empty array [].
"""

PATTERN_EXTRACTION_USER = """Analyze the following {n} correction diffs for project '{project_id}'.

Existing patterns (for deduplication — do not re-extract these):
{existing_patterns}

Correction diffs to analyze:
{correction_diffs}

Extract recurring structural preferences. Return JSON array of pattern objects.
"""


class MemoryProfiler:
    """Computes and persists archetype affinity profiles from correction history.

    Uses exponential decay to weight recent corrections more heavily than older ones.
    Supports epsilon-greedy exploration: when explore=True, returns neutral preference_fit=5
    for all archetypes regardless of learned profile (20% exploration rate by default).

    Args:
        project_id: The OpenClaw project identifier.
        decay_lambda: Decay rate for exponential weighting. Default 0.05 (~14-day half-life).
        exploration_rate: Fraction of scoring sessions that use neutral preference. Default 0.20.
        min_threshold: Minimum corrections before profile becomes active. Default 5.
    """

    def __init__(
        self,
        project_id: str,
        decay_lambda: Optional[float] = None,
        exploration_rate: Optional[float] = None,
        min_threshold: Optional[int] = None,
    ) -> None:
        self.project_id = project_id

        # Load defaults from config, allow override via constructor args
        cfg = get_topology_config()
        self.decay_lambda = decay_lambda if decay_lambda is not None else cfg["decay_lambda"]
        self.exploration_rate = exploration_rate if exploration_rate is not None else cfg["exploration_rate"]
        self.min_threshold = min_threshold if min_threshold is not None else cfg["pattern_extraction_threshold"]

    def _decay_weight(self, timestamp_iso) -> float:
        """Compute exponential decay weight for a correction at the given timestamp.

        Returns exp(-lambda * age_days) where age_days is the number of days since
        the correction was made. Corrections from today return ~1.0; older corrections
        return progressively smaller weights.

        Args:
            timestamp_iso: ISO 8601 timestamp string (or None/invalid).

        Returns:
            Float in (0, 1] — 1.0 for unknown/invalid timestamps (no penalty).
        """
        if not timestamp_iso:
            return 1.0

        try:
            if isinstance(timestamp_iso, str):
                # Handle both timezone-aware and naive timestamps
                ts = datetime.fromisoformat(timestamp_iso)
            else:
                return 1.0

            # Ensure both datetimes are comparable
            if ts.tzinfo is None:
                now = datetime.now()
            else:
                now = datetime.now(timezone.utc)

            age_days = max(0.0, (now - ts).total_seconds() / 86400.0)
            return math.exp(-self.decay_lambda * age_days)

        except (ValueError, TypeError, OverflowError):
            return 1.0

    def compute_profile(self) -> dict:
        """Compute and persist the archetype affinity profile from correction history.

        Loads the changelog and applies exponential decay weighting to build affinity
        scores for each archetype. If correction count is below the minimum threshold,
        returns a default profile with all affinities at neutral (5.0).

        Signal mapping per correction:
          - "initial" correction → +1.0 to approved archetype
          - "soft" correction → +0.5 to approved archetype
          - "hard" correction → +1.0 to approved archetype

        Final affinities are normalized to [0, 10] scale.

        Returns:
            Profile dict with archetype_affinity, threshold_status, correction counts, etc.
        """
        changelog = load_changelog(self.project_id)
        total = len(changelog)
        soft_count = sum(1 for e in changelog if e.get("correction_type") == "soft")
        hard_count = sum(1 for e in changelog if e.get("correction_type") == "hard")

        if total < self.min_threshold:
            profile = {
                "project_id": self.project_id,
                "correction_count": total,
                "soft_correction_count": soft_count,
                "hard_correction_count": hard_count,
                "threshold_status": "below_threshold",
                "archetype_affinity": {"lean": 5.0, "balanced": 5.0, "robust": 5.0},
                "last_computed": datetime.now(timezone.utc).isoformat(),
                "active_pattern_ids": [],
            }
            save_memory_profile(self.project_id, profile)
            return profile

        # Build weighted affinity scores
        signal_map = {
            "initial": 1.0,
            "soft": 0.5,
            "hard": 1.0,
        }
        archetypes = ["lean", "balanced", "robust"]
        raw_scores = {a: 0.0 for a in archetypes}
        total_weight = 0.0

        for entry in changelog:
            correction_type = entry.get("correction_type", "soft")
            approved_archetype = (
                entry.get("annotations", {}).get("approved_archetype") or ""
            ).lower()

            if approved_archetype not in archetypes:
                continue

            signal = signal_map.get(correction_type, 0.5)
            weight = self._decay_weight(entry.get("timestamp", ""))
            raw_scores[approved_archetype] += signal * weight
            total_weight += weight

        # Normalize to [0, 10] scale
        # All neutral = 5.0 base. Scores above mean → higher, below → lower.
        if total_weight > 0:
            # Compute weighted fractions for each archetype
            total_raw = sum(raw_scores.values())
            if total_raw > 0:
                # Map fractions to [0, 10] scale
                # Equal distribution = 1/3 each → 5.0 each
                equal_share = 1.0 / len(archetypes)
                affinity = {}
                for a in archetypes:
                    fraction = raw_scores[a] / total_raw
                    # Deviation from equal: positive → above 5.0, negative → below
                    deviation = (fraction - equal_share) / equal_share  # normalized
                    # Scale to [0, 10] range: neutral = 5.0, max deviation = ±5.0
                    affinity[a] = max(0.0, min(10.0, 5.0 + deviation * 5.0))
            else:
                affinity = {a: 5.0 for a in archetypes}
        else:
            affinity = {a: 5.0 for a in archetypes}

        # Load existing patterns for active_pattern_ids
        existing_patterns = load_patterns(self.project_id)
        active_pattern_ids = [
            p.get("pattern", "")[:40] for p in existing_patterns[:10]
        ]

        profile = {
            "project_id": self.project_id,
            "correction_count": total,
            "soft_correction_count": soft_count,
            "hard_correction_count": hard_count,
            "threshold_status": "active",
            "archetype_affinity": affinity,
            "last_computed": datetime.now(timezone.utc).isoformat(),
            "active_pattern_ids": active_pattern_ids,
        }
        save_memory_profile(self.project_id, profile)
        return profile

    def get_preference_fit(self, archetype: str, explore: bool = False) -> int:
        """Return preference fit score for an archetype (0–10 scale).

        If the profile is below threshold OR explore=True, returns 5 (neutral).
        Otherwise returns the clamped, rounded archetype affinity score.

        The `explore` parameter is determined by the caller drawing a SINGLE
        random number per scoring session (epsilon-greedy at the session level,
        not per-archetype).

        Args:
            archetype: One of "lean", "balanced", "robust".
            explore: If True, return neutral regardless of learned profile.

        Returns:
            Integer in [0, 10]. Returns 5 (neutral) when exploring or below threshold.
        """
        profile = load_memory_profile(self.project_id)

        if explore or profile.get("threshold_status") != "active":
            return 5

        affinity = profile.get("archetype_affinity", {})
        score = affinity.get(archetype, 5.0)
        return max(0, min(10, round(score)))

    def get_report(self, detail: bool = False) -> dict:
        """Return a summary report of the memory profile state.

        Args:
            detail: If True, include full pattern list and decay-weighted timeline.

        Returns:
            Dict with project_id, correction counts, threshold_status, archetype_affinity,
            and top 3 patterns. If detail=True, adds full patterns and timeline.
        """
        profile = load_memory_profile(self.project_id)
        patterns = load_patterns(self.project_id)

        report = {
            "project_id": self.project_id,
            "correction_count": profile.get("correction_count", 0),
            "soft_correction_count": profile.get("soft_correction_count", 0),
            "hard_correction_count": profile.get("hard_correction_count", 0),
            "threshold_status": profile.get("threshold_status", "below_threshold"),
            "archetype_affinity": profile.get("archetype_affinity", {"lean": 5.0, "balanced": 5.0, "robust": 5.0}),
            "top_patterns": sorted(patterns, key=lambda p: p.get("confidence", 0), reverse=True)[:3],
        }

        if detail:
            changelog = load_changelog(self.project_id)
            timeline = []
            for entry in changelog:
                timeline.append({
                    "timestamp": entry.get("timestamp", ""),
                    "correction_type": entry.get("correction_type", ""),
                    "approved_archetype": entry.get("annotations", {}).get("approved_archetype", ""),
                    "decay_weight": self._decay_weight(entry.get("timestamp", "")),
                })
            report["timeline"] = timeline
            report["all_patterns"] = patterns

        return report


class PatternExtractor:
    """Extracts recurring structural patterns from correction history using LLM.

    Only activates when the correction count meets the configured threshold.
    Handles LLM failures gracefully by returning existing patterns unchanged.

    Args:
        project_id: The OpenClaw project identifier.
        min_threshold: Minimum corrections before extraction is attempted. Default 5.
    """

    def __init__(self, project_id: str, min_threshold: Optional[int] = None) -> None:
        self.project_id = project_id

        cfg = get_topology_config()
        self.min_threshold = (
            min_threshold if min_threshold is not None
            else cfg["pattern_extraction_threshold"]
        )

    def extract(self) -> list:
        """Extract structural patterns from correction history via LLM.

        If the changelog has fewer entries than min_threshold, returns [] immediately
        without calling the LLM.

        On LLM success: parses JSON response, filters patterns with confidence < 0.4,
        prunes to top 10 by confidence if total > 20, saves to storage.

        On LLM failure: logs a warning and returns existing patterns unchanged (never raises).

        Returns:
            List of pattern dicts. Each dict has: pattern, confidence,
            source_correction_ids, archetype_bias.
        """
        changelog = load_changelog(self.project_id)

        if len(changelog) < self.min_threshold:
            return []

        existing_patterns = load_patterns(self.project_id)

        # Build diffs summary for LLM
        correction_diffs = []
        for i, entry in enumerate(changelog):
            diff_text = entry.get("diff", "")
            correction_type = entry.get("correction_type", "unknown")
            approved_arch = entry.get("annotations", {}).get("approved_archetype", "unknown")
            correction_diffs.append(
                f"[{i}] type={correction_type} approved={approved_arch}\n{diff_text}"
            )

        existing_summary = (
            json.dumps(existing_patterns, indent=2) if existing_patterns else "[]"
        )

        user_message = PATTERN_EXTRACTION_USER.format(
            n=len(changelog),
            project_id=self.project_id,
            existing_patterns=existing_summary,
            correction_diffs="\n\n".join(correction_diffs),
        )

        try:
            raw_response = asyncio.run(
                call_llm(PATTERN_EXTRACTION_SYSTEM, user_message)
            )
            clean_json = strip_markdown_fences(raw_response)
            new_patterns = json.loads(clean_json)

            if not isinstance(new_patterns, list):
                raise ValueError(f"Expected list, got {type(new_patterns)}")

            # Filter low-confidence patterns
            filtered = [p for p in new_patterns if p.get("confidence", 0) >= 0.4]

            # Prune to top 10 if over 20
            if len(filtered) > 20:
                filtered = sorted(filtered, key=lambda p: p.get("confidence", 0), reverse=True)[:10]

            save_patterns(self.project_id, filtered)
            return filtered

        except Exception as exc:
            logger.warning(
                "PatternExtractor LLM call failed for project %s: %s — returning existing patterns",
                self.project_id,
                exc,
            )
            return existing_patterns
