"""
Unit tests for the notion-kanban-sync skill core behaviors.

Tests cover:
- capture_hash: determinism and normalization
- _infer_area: keyword matching and fallback
- _infer_status: urgency signals
- _evaluate_meaningful_rule: 3-condition pure function
- _parse_batch: comma/newline/semicolon splitting
- _should_write_status: status ownership guard

No live Notion API calls — all Notion client interaction is mocked.

Run from project root:
    uv run pytest packages/orchestration/tests/test_notion_sync.py -v
"""

from __future__ import annotations

import sys
import os

# Add skills/notion-kanban-sync to sys.path for imports
_skill_dir = os.path.join(os.path.dirname(__file__), "../../../skills/notion-kanban-sync")
if _skill_dir not in sys.path:
    sys.path.insert(0, _skill_dir)

import pytest

from capture_handler import _compute_capture_hash, _infer_area, _infer_status, _parse_batch
from notion_sync import _evaluate_meaningful_rule, _should_write_status


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_area_keywords():
    """Sample area_keywords config matching the skill's defaults."""
    return {
        "Health": ["gym", "fitness", "health", "doctor", "dentist", "workout", "diet"],
        "Finance": ["tax", "taxes", "invoice", "payment", "budget", "money", "bank", "finance"],
        "Learning": ["course", "book", "study", "read", "learn", "tutorial", "workshop"],
        "Relationships": ["call", "friend", "family", "mom", "dad", "birthday", "wedding"],
        "Admin": ["admin", "paperwork", "form", "renew", "apply", "register"],
    }


def _make_card(openclaw_phase_id: str = "", openclaw_event_anchor: str = "") -> dict:
    """Helper to build a minimal Cards DB page dict."""
    props = {
        "OpenClaw Phase ID": {
            "rich_text": [{"plain_text": openclaw_phase_id}] if openclaw_phase_id else []
        },
        "OpenClaw Event Anchor": {
            "rich_text": [{"plain_text": openclaw_event_anchor}] if openclaw_event_anchor else []
        },
    }
    return {"id": "page-123", "properties": props}


# ---------------------------------------------------------------------------
# capture hash tests
# ---------------------------------------------------------------------------

class TestCaptureHashDeterministic:
    """test_capture_hash_deterministic — same inputs produce same hash; different inputs differ."""

    def test_capture_hash_deterministic(self):
        """Same inputs always produce the same 12-char hash."""
        h1 = _compute_capture_hash("Renew gym membership", "Health")
        h2 = _compute_capture_hash("Renew gym membership", "Health")
        assert h1 == h2, "Same inputs produced different hashes"
        assert len(h1) == 12

    def test_capture_hash_different_inputs(self):
        """Different inputs produce different hashes."""
        h1 = _compute_capture_hash("Renew gym membership", "Health")
        h2 = _compute_capture_hash("Pay taxes", "Finance")
        assert h1 != h2, "Different inputs produced the same hash"

    def test_capture_hash_target_week_differentiates(self):
        """Adding target_week changes the hash."""
        h1 = _compute_capture_hash("Renew gym", "Health")
        h2 = _compute_capture_hash("Renew gym", "Health", target_week="2026-03-01")
        assert h1 != h2


class TestCaptureHashNormalized:
    """test_capture_hash_normalized — case-insensitive normalization."""

    def test_capture_hash_case_insensitive(self):
        """'Renew Gym' and 'renew gym' produce the same hash."""
        h1 = _compute_capture_hash("Renew Gym", "Health")
        h2 = _compute_capture_hash("renew gym", "health")
        assert h1 == h2, "Hashes differ despite same content (different case)"

    def test_capture_hash_whitespace_stripped(self):
        """Leading/trailing whitespace does not affect the hash."""
        h1 = _compute_capture_hash("  Renew Gym  ", " Health ")
        h2 = _compute_capture_hash("Renew Gym", "Health")
        assert h1 == h2


# ---------------------------------------------------------------------------
# Area inference tests
# ---------------------------------------------------------------------------

class TestInferAreaKeywordMatch:
    """test_infer_area_keyword_match — keyword matching for known areas."""

    def test_gym_is_health(self):
        """'gym membership' → Health area."""
        kws = _make_area_keywords()
        area, inferred = _infer_area("gym membership", kws)
        assert area == "Health"
        assert inferred is True

    def test_taxes_is_finance(self):
        """'pay taxes' → Finance area."""
        kws = _make_area_keywords()
        area, inferred = _infer_area("pay taxes", kws)
        assert area == "Finance"
        assert inferred is True

    def test_book_is_learning(self):
        """'read a book' → Learning area."""
        kws = _make_area_keywords()
        area, inferred = _infer_area("read a book", kws)
        assert area == "Learning"
        assert inferred is True

    def test_call_mom_is_relationships(self):
        """'call mom' → Relationships area."""
        kws = _make_area_keywords()
        area, inferred = _infer_area("call mom", kws)
        assert area == "Relationships"
        assert inferred is True


class TestInferAreaNoMatchFallback:
    """test_infer_area_no_match_fallback — unknown title falls back to Admin."""

    def test_no_match_returns_admin(self):
        """A title with no keywords falls back to 'Admin'."""
        kws = _make_area_keywords()
        area, inferred = _infer_area("random task xyz", kws)
        assert area == "Admin"
        assert inferred is True

    def test_empty_keywords_returns_admin(self):
        """Empty keyword config falls back to Admin."""
        area, inferred = _infer_area("anything", {})
        assert area == "Admin"
        assert inferred is True


# ---------------------------------------------------------------------------
# Status inference tests
# ---------------------------------------------------------------------------

class TestInferStatusUrgent:
    """test_infer_status_urgent — urgency signals map to 'This Week'."""

    def test_urgent_prefix(self):
        """'urgent: file taxes' → This Week."""
        status = _infer_status("urgent: file taxes")
        assert status == "This Week"

    def test_today_keyword(self):
        """'submit today' → This Week."""
        status = _infer_status("submit today")
        assert status == "This Week"

    def test_asap_keyword(self):
        """'fix this asap' → This Week."""
        status = _infer_status("fix this asap")
        assert status == "This Week"

    def test_deadline_keyword(self):
        """'project deadline approaching' → This Week."""
        status = _infer_status("project deadline approaching")
        assert status == "This Week"


class TestInferStatusDefault:
    """test_infer_status_default — non-urgent titles → Backlog."""

    def test_organize_bookshelf(self):
        """'organize bookshelf' → Backlog (no urgency signal)."""
        status = _infer_status("organize bookshelf")
        assert status == "Backlog"

    def test_renew_gym(self):
        """'renew gym membership' → Backlog."""
        status = _infer_status("renew gym membership")
        assert status == "Backlog"

    def test_empty_title(self):
        """Empty title → Backlog (no urgency)."""
        status = _infer_status("")
        assert status == "Backlog"


# ---------------------------------------------------------------------------
# Meaningful rule tests
# ---------------------------------------------------------------------------

def _make_container_event(
    runtime_seconds: float = 0,
    requires_human_review: bool = False,
    failure_category: str | None = None,
) -> dict:
    """Build a minimal container event dict."""
    return {
        "event_type": "container_completed",
        "project_id": "pumplai",
        "payload": {
            "runtime_seconds": runtime_seconds,
            "requires_human_review": requires_human_review,
            "failure_category": failure_category,
        },
    }


class TestMeaningfulRuleRuntime:
    """test_meaningful_rule_runtime — containers with runtime > 600s are meaningful."""

    def test_long_runtime_is_meaningful(self):
        """Container with runtime > 600s (10 min) → meaningful=True."""
        event = _make_container_event(runtime_seconds=700)
        assert _evaluate_meaningful_rule(event, {}) is True

    def test_exact_threshold_not_meaningful(self):
        """Container with runtime exactly 600s is NOT meaningful (> not >=)."""
        event = _make_container_event(runtime_seconds=600)
        assert _evaluate_meaningful_rule(event, {}) is False

    def test_custom_threshold(self):
        """Config can override meaningful_container_runtime_min."""
        event = _make_container_event(runtime_seconds=120)
        config = {"meaningful_container_runtime_min": 1}  # 1 minute threshold
        assert _evaluate_meaningful_rule(event, config) is True


class TestMeaningfulRuleShortRuntime:
    """test_meaningful_rule_short_runtime — short containers are NOT meaningful."""

    def test_short_runtime_not_meaningful(self):
        """Container with 30s runtime → meaningful=False."""
        event = _make_container_event(runtime_seconds=30)
        assert _evaluate_meaningful_rule(event, {}) is False


class TestMeaningfulRuleHumanReview:
    """test_meaningful_rule_human_review — requires_human_review=True forces meaningful."""

    def test_human_review_required(self):
        """requires_human_review=True → meaningful=True regardless of runtime."""
        event = _make_container_event(runtime_seconds=5, requires_human_review=True)
        assert _evaluate_meaningful_rule(event, {}) is True

    def test_no_human_review_and_short_runtime(self):
        """requires_human_review=False and short runtime → meaningful=False."""
        event = _make_container_event(runtime_seconds=10, requires_human_review=False)
        assert _evaluate_meaningful_rule(event, {}) is False


class TestMeaningfulRuleActionableFailure:
    """test_meaningful_rule_actionable_failure — failure categories that warrant action."""

    def test_tests_failed_is_meaningful(self):
        """failure_category='tests_failed' → meaningful=True."""
        event = _make_container_event(failure_category="tests_failed")
        assert _evaluate_meaningful_rule(event, {}) is True

    def test_lint_failed_is_meaningful(self):
        """failure_category='lint_failed' → meaningful=True."""
        event = _make_container_event(failure_category="lint_failed")
        assert _evaluate_meaningful_rule(event, {}) is True

    def test_deploy_failed_is_meaningful(self):
        """failure_category='deploy_failed' → meaningful=True."""
        event = _make_container_event(failure_category="deploy_failed")
        assert _evaluate_meaningful_rule(event, {}) is True

    def test_unknown_failure_category_not_meaningful(self):
        """failure_category='network_error' → meaningful=False (not in actionable set)."""
        event = _make_container_event(failure_category="network_error", runtime_seconds=10)
        assert _evaluate_meaningful_rule(event, {}) is False


# ---------------------------------------------------------------------------
# Batch parsing tests
# ---------------------------------------------------------------------------

class TestBatchParseComma:
    """test_batch_parse_comma — comma-separated list → multiple items."""

    def test_comma_separated_three_items(self):
        """'gym, taxes, call mom' → 3 separate capture items."""
        capture = {"title": "gym, taxes, call mom"}
        items = _parse_batch(capture)
        assert len(items) == 3
        titles = [i["title"] for i in items]
        assert "gym" in titles
        assert "taxes" in titles
        assert "call mom" in titles

    def test_comma_with_shared_area(self):
        """Batch items inherit shared area from the original capture dict."""
        capture = {"title": "gym, dentist", "area": "Health"}
        items = _parse_batch(capture)
        assert len(items) == 2
        assert all(i["area"] == "Health" for i in items)

    def test_comma_sentence_not_split(self):
        """Natural sentence with '. ' is not split on comma."""
        capture = {"title": "Go to the gym. Also, pay taxes."}
        items = _parse_batch(capture)
        assert len(items) == 1, "Sentence should not be split into multiple items"


class TestBatchParseSingle:
    """test_batch_parse_single — single title → list of one item."""

    def test_single_title(self):
        """'renew gym' → list with exactly 1 item."""
        capture = {"title": "renew gym", "area": "Health"}
        items = _parse_batch(capture)
        assert len(items) == 1
        assert items[0]["title"] == "renew gym"

    def test_empty_title(self):
        """Empty title → list with 1 item (empty title — caller handles empty check)."""
        capture = {"title": ""}
        items = _parse_batch(capture)
        assert len(items) == 1
        assert items[0]["title"] == ""

    def test_newline_separated(self):
        """Newline-separated titles → multiple items."""
        capture = {"title": "gym\ntaxes\ncall mom"}
        items = _parse_batch(capture)
        assert len(items) == 3

    def test_semicolon_separated(self):
        """Semicolon-separated titles → multiple items."""
        capture = {"title": "gym; taxes; call mom"}
        items = _parse_batch(capture)
        assert len(items) == 3


# ---------------------------------------------------------------------------
# Status ownership tests
# ---------------------------------------------------------------------------

class TestShouldWriteStatusLinked:
    """test_should_write_status_linked — OpenClaw-linked cards allow status writes."""

    def test_phase_id_present(self):
        """Card with non-empty OpenClaw Phase ID → _should_write_status returns True."""
        card = _make_card(openclaw_phase_id="pumplai:45")
        assert _should_write_status(card) is True

    def test_event_anchor_present(self):
        """Card with non-empty OpenClaw Event Anchor → _should_write_status returns True."""
        card = _make_card(openclaw_event_anchor="pumplai:l3-abc:container_completed")
        assert _should_write_status(card) is True

    def test_both_ids_present(self):
        """Card with both Phase ID and Event Anchor → _should_write_status returns True."""
        card = _make_card(openclaw_phase_id="pumplai:45", openclaw_event_anchor="pumplai:l3-abc:container_completed")
        assert _should_write_status(card) is True


class TestShouldWriteStatusUnlinked:
    """test_should_write_status_unlinked — Notion-owned cards block status writes."""

    def test_no_ids_returns_false(self):
        """Card with no OpenClaw Phase ID and no Event Anchor → _should_write_status returns False."""
        card = _make_card()  # Both IDs empty
        assert _should_write_status(card) is False

    def test_empty_phase_id_returns_false(self):
        """Card with explicitly empty OpenClaw Phase ID → _should_write_status returns False."""
        props = {
            "OpenClaw Phase ID": {"rich_text": []},
            "OpenClaw Event Anchor": {"rich_text": []},
        }
        card = {"id": "page-456", "properties": props}
        assert _should_write_status(card) is False

    def test_missing_properties_returns_false(self):
        """Card with no properties dict → _should_write_status returns False (safe default)."""
        card = {"id": "page-789"}
        assert _should_write_status(card) is False
