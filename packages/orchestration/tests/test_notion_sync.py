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
from notion_sync import (
    SyncResult,
    _evaluate_meaningful_rule,
    _should_write_status,
    _is_openclaw_linked,
    _safe_set_status,
    handle_event_sync,
)
from unittest.mock import patch


# ---------------------------------------------------------------------------
# SyncResult tests
# ---------------------------------------------------------------------------

class TestSyncResult:
    """Tests for the SyncResult tracking class."""

    def test_record_mutation_created(self):
        result = SyncResult("test_sync")
        result.record_mutation("created", "cards_db", "page-1", "dedupe-1")
        assert result.created == 1
        assert result.updated == 0
        assert len(result.mutations) == 1
        assert result.mutations[0]["action"] == "created"
        assert result.mutations[0]["target"] == "cards_db"
        assert result.mutations[0]["notion_page_id"] == "page-1"
        assert result.mutations[0]["dedupe_key"] == "dedupe-1"

    def test_record_mutation_updated(self):
        result = SyncResult("test_sync")
        result.record_mutation("updated", "projects_db", "page-2", "dedupe-2")
        assert result.created == 0
        assert result.updated == 1
        assert len(result.mutations) == 1
        assert result.mutations[0]["action"] == "updated"

    def test_record_skip_and_error(self):
        result = SyncResult("test_sync")
        result.record_skip()
        result.record_skip()
        result.record_error("Test error")
        assert result.skipped == 2
        assert len(result.errors) == 1
        assert result.errors[0] == "Test error"

    def test_to_dict(self):
        result = SyncResult("test_sync")
        result.record_mutation("created", "cards_db", "page-1", "dedupe-1")
        result.record_skip()
        result.record_error("Bad things happened")
        result.extra = {"drift_count": 5}
        
        data = result.to_dict()
        assert data["request_type"] == "test_sync"
        assert data["result"]["created"] == 1
        assert data["result"]["updated"] == 0
        assert data["result"]["skipped"] == 1
        assert data["result"]["errors"] == ["Bad things happened"]
        assert len(data["result"]["mutations"]) == 1
        assert data["result"]["mutations"][0]["action"] == "created"
        assert data["result"]["extra"]["drift_count"] == 5


# ---------------------------------------------------------------------------
# Event Routing tests
# ---------------------------------------------------------------------------

class TestHandleEventSyncRouting:
    """Tests for the handle_event_sync routing function."""

    @patch("notion_sync._sync_project_registered")
    def test_routes_project_registered(self, mock_handler):
        payload = {
            "request_type": "event_sync",
            "event": {"event_type": "project_registered", "project_id": "pumplai"}
        }
        res = handle_event_sync(payload)
        mock_handler.assert_called_once()
        assert res["request_type"] == "event_sync"
        assert res["result"]["skipped"] == 0

    @patch("notion_sync._sync_phase_started")
    def test_routes_phase_started(self, mock_handler):
        payload = {
            "request_type": "event_sync",
            "event": {"event_type": "phase_started", "project_id": "pumplai", "phase_id": "45"}
        }
        handle_event_sync(payload)
        mock_handler.assert_called_once()

    @patch("notion_sync._sync_container_completed")
    def test_routes_container_completed(self, mock_handler):
        payload = {
            "request_type": "event_sync",
            "event": {"event_type": "container_completed"}
        }
        handle_event_sync(payload)
        mock_handler.assert_called_once()

    def test_routes_unknown_event_skips(self):
        payload = {
            "request_type": "event_sync",
            "event": {"event_type": "some_future_event"}
        }
        res = handle_event_sync(payload)
        assert res["result"]["skipped"] == 1


class TestHandleCaptureRouting:
    """Tests for the handle_capture routing function."""

    @patch("capture_handler._process_single_capture")
    def test_routes_single_capture(self, mock_process):
        from capture_handler import handle_capture
        from notion_sync import SyncResult
        
        payload = {
            "request_type": "capture",
            "capture": {"title": "renew gym", "area": "Health"}
        }
        res = SyncResult("capture")
        handle_capture(payload, res)
        
        mock_process.assert_called_once()
        args = mock_process.call_args[0]
        assert args[0]["title"] == "renew gym"
        assert args[0]["area"] == "Health"
        assert args[1] == res

    @patch("capture_handler._process_single_capture")
    def test_routes_batch_capture(self, mock_process):
        from capture_handler import handle_capture
        from notion_sync import SyncResult
        
        payload = {
            "request_type": "capture",
            "capture": {"title": "gym, taxes, call mom", "area": "Health"} # Area inherited by all
        }
        res = SyncResult("capture")
        handle_capture(payload, res)
        
        assert mock_process.call_count == 3
        
        # Verify first call
        args1 = mock_process.call_args_list[0][0]
        assert args1[0]["title"] == "gym"
        assert args1[0]["area"] == "Health"


class TestProcessSingleCapture:
    """Tests for _process_single_capture."""

    def setup_method(self):
        import notion_sync
        notion_sync._project_page_id_cache.clear()

    @patch("capture_handler._load_config")
    @patch("notion_client.NotionClient")
    def test_process_single_capture_create(self, mock_client_class, mock_load_config):
        mock_load_config.return_value = {"area_keywords": _make_area_keywords()}
        
        mock_client = mock_client_class.return_value
        mock_client._get_db_ids.return_value = ("proj_db", "proj_ds", "cards_db", "cards_ds")
        
        # Mock not finding existing capture
        mock_client.query_database.return_value = []
        
        mock_client.create_page.return_value = {"id": "capture-page-1"}
        
        from capture_handler import _process_single_capture
        from notion_sync import SyncResult
        
        capture = {
            "title": "renew gym",
            "notes": "check prices"
        }
        res = SyncResult("capture")
        
        _process_single_capture(capture, res)
        
        # Verify area was inferred and card created
        mock_client.create_page.assert_called_once()
        create_args = mock_client.create_page.call_args[0]
        assert create_args[0] == "cards_db"
        
        props = create_args[1]
        assert props["Name"]["title"][0]["text"]["content"] == "renew gym"
        assert props["Area"]["select"]["name"] == "Health"
        assert props["Status"]["select"]["name"] == "Backlog"
        assert props["Notes"]["rich_text"][0]["text"]["content"] == "check prices (area inferred)"
        
        assert res.created == 1
        assert res.mutations[0]["area_inferred"] is True

    @patch("capture_handler._load_config")
    @patch("notion_client.NotionClient")
    def test_process_single_capture_update(self, mock_client_class, mock_load_config):
        mock_load_config.return_value = {"area_keywords": _make_area_keywords()}
        
        mock_client = mock_client_class.return_value
        mock_client._get_db_ids.return_value = ("proj_db", "proj_ds", "cards_db", "cards_ds")
        
        # Mock finding existing capture
        existing_card = {
            "id": "capture-page-1",
            "properties": {
                "Notes": {"rich_text": [{"plain_text": "existing notes"}]}
            }
        }
        mock_client.query_database.return_value = [existing_card]
        
        from capture_handler import _process_single_capture
        from notion_sync import SyncResult
        
        capture = {
            "title": "renew gym",
            "notes": "new notes",
            "status": "This Week"
        }
        res = SyncResult("capture")
        
        _process_single_capture(capture, res)
        
        mock_client.update_page.assert_called_once()
        update_args = mock_client.update_page.call_args[0]
        assert update_args[0] == "capture-page-1"
        
        props = update_args[1]
        assert "Last Synced" in props
        assert props["Notes"]["rich_text"][0]["text"]["content"] == "existing notes\nnew notes"
        assert props["Status"]["select"]["name"] == "This Week"
        
        assert res.updated == 1


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


class TestIsOpenClawLinked:
    """test_is_openclaw_linked — delegates to _should_write_status."""

    def test_delegates_to_should_write_status(self):
        """_is_openclaw_linked behaves exactly like _should_write_status."""
        linked_card = _make_card(openclaw_phase_id="pumplai:45")
        unlinked_card = _make_card()
        
        assert _is_openclaw_linked(linked_card) is True
        assert _is_openclaw_linked(unlinked_card) is False


class TestSafeSetStatus:
    """test_safe_set_status — applies status ownership rules."""

    def test_writes_status_when_linked(self):
        """OpenClaw-linked card gets Status added to properties dict."""
        card = _make_card(openclaw_phase_id="pumplai:45")
        props = {"Name": {"title": [{"text": {"content": "Test"}}]}}
        
        result_props = _safe_set_status(props, card, "Done")
        
        assert "Status" in result_props
        assert result_props["Status"]["select"]["name"] == "Done"
        assert result_props["Name"]["title"][0]["text"]["content"] == "Test"

    @patch("notion_sync.logger.info")
    def test_skips_status_when_unlinked_and_logs(self, mock_logger):
        """Notion-owned card (unlinked) does not get Status added; logs skip message."""
        card = _make_card()
        card["id"] = "page-unlinked-123"
        props = {"Name": {"title": [{"text": {"content": "Test"}}]}}
        
        result_props = _safe_set_status(props, card, "Done")
        
        assert "Status" not in result_props
        assert result_props["Name"]["title"][0]["text"]["content"] == "Test"
        
        mock_logger.assert_called_once()
        log_args = mock_logger.call_args[0]
        assert "Skipping Status write" in log_args[0]
        assert "page-unlinked-123" in log_args


# ---------------------------------------------------------------------------
# Project Handlers tests
# ---------------------------------------------------------------------------

class TestProjectHandlers:
    """Tests for project_registered and project_removed handlers."""

    @patch("notion_client.NotionClient")
    def test_sync_project_registered(self, mock_client_class):
        # Setup mock client
        mock_client = mock_client_class.return_value
        mock_client._get_db_ids.return_value = ("proj_db", "proj_ds", "cards_db", "cards_ds")
        
        # Mock upsert returns
        mock_client.upsert_by_dedupe.side_effect = [
            {"action": "created", "page_id": "proj-page-1"},   # Projects DB upsert
            {"action": "created", "page_id": "triage-page-1"}  # Triage card upsert
        ]
        
        from notion_sync import _sync_project_registered, SyncResult
        
        event = {
            "project_id": "pumplai",
            "payload": {"name": "PumpLAI", "workspace_path": "/home/user/pumplai"}
        }
        result = SyncResult("event_sync")
        
        _sync_project_registered(event, result)
        
        # Verify Projects DB upsert call
        call_args = mock_client.upsert_by_dedupe.call_args_list[0]
        assert call_args[0][0] == "proj_db"
        assert call_args[0][2] == "OpenClaw ID"
        assert call_args[0][3] == "pumplai"
        assert "Name" in call_args[0][4]
        assert "Repo/Path" in call_args[0][4]
        
        # Verify Triage Card upsert call
        call_args2 = mock_client.upsert_by_dedupe.call_args_list[1]
        assert call_args2[0][0] == "cards_db"
        assert call_args2[0][2] == "OpenClaw Phase ID"
        assert call_args2[0][3] == "pumplai:triage"
        assert "Project" in call_args2[0][4]
        
        assert result.created == 2
        assert len(result.mutations) == 2
        assert result.mutations[0]["target"] == "projects_db"
        assert result.mutations[1]["target"] == "cards_db"

    @patch("notion_client.NotionClient")
    def test_sync_project_removed(self, mock_client_class):
        mock_client = mock_client_class.return_value
        mock_client._get_db_ids.return_value = ("proj_db", "proj_ds", "cards_db", "cards_ds")
        
        # Mock finding the project
        mock_client.query_database.return_value = [{"id": "proj-page-1"}]
        
        from notion_sync import _sync_project_removed, SyncResult
        
        event = {"project_id": "pumplai"}
        result = SyncResult("event_sync")
        
        _sync_project_removed(event, result)
        
        mock_client.query_database.assert_called_once()
        mock_client.update_page.assert_called_once()
        update_args = mock_client.update_page.call_args[0]
        assert update_args[0] == "proj-page-1"
        assert update_args[1]["Status"]["select"]["name"] == "Archived"
        
        assert result.updated == 1
        assert len(result.mutations) == 1
        assert result.mutations[0]["action"] == "updated"

    @patch("notion_client.NotionClient")
    def test_sync_project_removed_not_found(self, mock_client_class):
        mock_client = mock_client_class.return_value
        mock_client._get_db_ids.return_value = ("proj_db", "proj_ds", "cards_db", "cards_ds")
        
        # Mock project NOT found
        mock_client.query_database.return_value = []
        
        from notion_sync import _sync_project_removed, SyncResult
        
        event = {"project_id": "pumplai"}
        result = SyncResult("event_sync")
        
        _sync_project_removed(event, result)
        
        mock_client.query_database.assert_called_once()
        mock_client.update_page.assert_not_called()
        
        assert result.skipped == 1
        assert result.updated == 0


# ---------------------------------------------------------------------------
# Phase Handlers tests
# ---------------------------------------------------------------------------

class TestPhaseHandlers:
    """Tests for phase_started, phase_completed, and phase_blocked handlers."""

    def setup_method(self):
        import notion_sync
        notion_sync._project_page_id_cache.clear()

    @patch("notion_client.NotionClient")
    def test_sync_phase_started_new(self, mock_client_class):
        mock_client = mock_client_class.return_value
        mock_client._get_db_ids.return_value = ("proj_db", "proj_ds", "cards_db", "cards_ds")
        
        # Mock project lookup
        mock_client.query_database.side_effect = [
            [{"id": "proj-page-1"}], # Project lookup
            [],                      # Phase card existing check (not found -> create)
            [{"id": "proj-page-1"}]  # Projects DB lookup for Current Phase update
        ]
        
        mock_client.create_page.return_value = {"id": "phase-page-1"}
        
        from notion_sync import _sync_phase_started, SyncResult
        
        event = {
            "project_id": "pumplai",
            "phase_id": "45",
            "payload": {"phase_name": "Test Phase"}
        }
        result = SyncResult("event_sync")
        
        _sync_phase_started(event, result)
        
        # Assert create_page was called with right props
        mock_client.create_page.assert_called_once()
        create_args = mock_client.create_page.call_args[0]
        assert create_args[0] == "cards_db"
        assert create_args[1]["Status"]["select"]["name"] == "In Progress"
        assert create_args[1]["Name"]["title"][0]["text"]["content"] == "Phase 45: Test Phase"
        
        # Assert Projects DB Current Phase updated
        mock_client.update_page.assert_called_once()
        update_args = mock_client.update_page.call_args[0]
        assert update_args[0] == "proj-page-1"
        assert update_args[1]["Current Phase"]["rich_text"][0]["text"]["content"] == "Phase 45: Test Phase"
        
        # Assert activity appended
        mock_client.append_activity.assert_called_once_with("phase-page-1", "phase_started: Phase 45")
        
        assert result.created == 1
        assert len(result.mutations) == 1

    @patch("notion_client.NotionClient")
    def test_sync_phase_completed(self, mock_client_class):
        mock_client = mock_client_class.return_value
        mock_client._get_db_ids.return_value = ("proj_db", "proj_ds", "cards_db", "cards_ds")
        
        # Mock finding the phase card
        # Also need to mock the card having OpenClaw Phase ID so it passes _should_write_status guard
        phase_card = _make_card(openclaw_phase_id="pumplai:45")
        phase_card["id"] = "phase-page-1"
        
        mock_client.query_database.side_effect = [
            [phase_card],            # Phase card lookup
            [{"id": "proj-page-1"}]  # Projects DB lookup for Current Phase update
        ]
        
        from notion_sync import _sync_phase_completed, SyncResult
        
        event = {
            "project_id": "pumplai",
            "phase_id": "45",
            "payload": {"phase_name": "Test Phase"}
        }
        result = SyncResult("event_sync")
        
        _sync_phase_completed(event, result)
        
        assert mock_client.update_page.call_count == 2
        # First update is phase card
        update_card_args = mock_client.update_page.call_args_list[0][0]
        assert update_card_args[0] == "phase-page-1"
        assert update_card_args[1]["Status"]["select"]["name"] == "Done"
        
        # Second update is Projects DB Current Phase
        update_proj_args = mock_client.update_page.call_args_list[1][0]
        assert update_proj_args[0] == "proj-page-1"
        assert update_proj_args[1]["Current Phase"]["rich_text"][0]["text"]["content"] == "Completed: Phase 45: Test Phase"
        
        # Assert activity appended
        mock_client.append_activity.assert_called_once_with("phase-page-1", "phase_completed: Phase 45")
        
        assert result.updated == 1
        assert len(result.mutations) == 1

    @patch("notion_client.NotionClient")
    def test_sync_phase_blocked(self, mock_client_class):
        mock_client = mock_client_class.return_value
        mock_client._get_db_ids.return_value = ("proj_db", "proj_ds", "cards_db", "cards_ds")
        
        # Mock finding the phase card
        phase_card = _make_card(openclaw_phase_id="pumplai:45")
        phase_card["id"] = "phase-page-1"
        mock_client.query_database.return_value = [phase_card]
        
        from notion_sync import _sync_phase_blocked, SyncResult
        
        event = {
            "project_id": "pumplai",
            "phase_id": "45",
            "payload": {"blocker": "Waiting on API key"}
        }
        result = SyncResult("event_sync")
        
        _sync_phase_blocked(event, result)
        
        mock_client.update_page.assert_called_once()
        update_args = mock_client.update_page.call_args[0]
        assert update_args[0] == "phase-page-1"
        assert update_args[1]["Status"]["select"]["name"] == "Waiting"
        
        # Assert activity appended
        mock_client.append_activity.assert_called_once_with("phase-page-1", "phase_blocked: Waiting on API key")
        
        assert result.updated == 1
        assert len(result.mutations) == 1


# ---------------------------------------------------------------------------
# Container Handlers tests
# ---------------------------------------------------------------------------

class TestContainerHandlers:
    """Tests for container_completed and container_failed handlers."""

    def setup_method(self):
        import notion_sync
        notion_sync._project_page_id_cache.clear()

    @patch("notion_sync._load_config")
    @patch("notion_client.NotionClient")
    def test_sync_container_completed_routine(self, mock_client_class, mock_load_config):
        """Routine container -> only appends to Activity, no card created."""
        mock_load_config.return_value = {"meaningful_container_runtime_min": 10}
        
        mock_client = mock_client_class.return_value
        mock_client._get_db_ids.return_value = ("proj_db", "proj_ds", "cards_db", "cards_ds")
        
        # Mock finding the parent phase card
        parent_card = _make_card(openclaw_phase_id="pumplai:45")
        parent_card["id"] = "parent-phase-1"
        mock_client.query_database.return_value = [parent_card]
        
        from notion_sync import _sync_container_completed, SyncResult
        
        event = {
            "project_id": "pumplai",
            "phase_id": "45",
            "container_id": "l3-abc",
            "payload": {
                "runtime_seconds": 30, # < 600s, so not meaningful
                "requires_human_review": False
            }
        }
        result = SyncResult("event_sync")
        
        _sync_container_completed(event, result)
        
        # Verify no card was created
        mock_client.upsert_by_dedupe.assert_not_called()
        
        # Verify activity was appended to parent
        mock_client.append_activity.assert_called_once_with(
            "parent-phase-1", 
            "container_completed: l3-abc (30s)"
        )
        
        assert result.skipped == 1
        assert result.created == 0

    @patch("notion_sync._load_config")
    @patch("notion_client.NotionClient")
    def test_sync_container_completed_meaningful(self, mock_client_class, mock_load_config):
        """Meaningful container -> creates card and appends to Activity."""
        mock_load_config.return_value = {"meaningful_container_runtime_min": 10}
        
        mock_client = mock_client_class.return_value
        mock_client._get_db_ids.return_value = ("proj_db", "proj_ds", "cards_db", "cards_ds")
        
        # Mock finding the parent phase card AND the project page
        parent_card = _make_card(openclaw_phase_id="pumplai:45")
        parent_card["id"] = "parent-phase-1"
        
        mock_client.query_database.side_effect = [
            [parent_card],           # 1. find parent phase card
            [{"id": "proj-page-1"}]  # 2. find project page id
        ]
        
        mock_client.upsert_by_dedupe.return_value = {"action": "created", "page_id": "child-card-1"}
        
        from notion_sync import _sync_container_completed, SyncResult
        
        event = {
            "project_id": "pumplai",
            "phase_id": "45",
            "container_id": "l3-abc",
            "payload": {
                "runtime_seconds": 700, # > 600s, so meaningful!
                "requires_human_review": False
            }
        }
        result = SyncResult("event_sync")
        
        _sync_container_completed(event, result)
        
        # Verify child card was created
        mock_client.upsert_by_dedupe.assert_called_once()
        upsert_args = mock_client.upsert_by_dedupe.call_args[0]
        assert upsert_args[0] == "cards_db"
        assert upsert_args[2] == "OpenClaw Event Anchor"
        assert upsert_args[3] == "pumplai:l3-abc:container_completed"
        assert upsert_args[4]["Status"]["select"]["name"] == "Done"
        
        # Verify activity was appended to parent
        mock_client.append_activity.assert_called_once_with(
            "parent-phase-1", 
            "container_completed: l3-abc (700s)"
        )
        
        assert result.created == 1
        assert result.skipped == 0
        assert len(result.mutations) == 1

    @patch("notion_sync._load_config")
    @patch("notion_client.NotionClient")
    def test_sync_container_failed_routine_retries_remaining(self, mock_client_class, mock_load_config):
        """Routine failure, retries remaining -> append activity only."""
        mock_load_config.return_value = {"meaningful_container_runtime_min": 10, "retry_max_attempts": 3}
        
        mock_client = mock_client_class.return_value
        mock_client._get_db_ids.return_value = ("proj_db", "proj_ds", "cards_db", "cards_ds")
        
        parent_card = _make_card(openclaw_phase_id="pumplai:45")
        parent_card["id"] = "parent-phase-1"
        mock_client.query_database.return_value = [parent_card]
        
        from notion_sync import _sync_container_failed, SyncResult
        
        event = {
            "project_id": "pumplai",
            "phase_id": "45",
            "container_id": "l3-abc",
            "payload": {
                "exit_code": 1,
                "retry_count": 1, # < 3, retries remaining
                "runtime_seconds": 30,
                "failure_category": "network_error" # not actionable
            }
        }
        result = SyncResult("event_sync")
        
        _sync_container_failed(event, result)
        
        mock_client.upsert_by_dedupe.assert_not_called()
        mock_client.update_page.assert_not_called() # parent not updated
        
        mock_client.append_activity.assert_called_once_with(
            "parent-phase-1", 
            "container_failed: l3-abc (exit 1)"
        )
        
        assert result.skipped == 1

    @patch("notion_sync._load_config")
    @patch("notion_client.NotionClient")
    def test_sync_container_failed_retries_exhausted(self, mock_client_class, mock_load_config):
        """Retries exhausted -> update parent phase to Waiting."""
        mock_load_config.return_value = {"meaningful_container_runtime_min": 10, "retry_max_attempts": 3}
        
        mock_client = mock_client_class.return_value
        mock_client._get_db_ids.return_value = ("proj_db", "proj_ds", "cards_db", "cards_ds")
        
        parent_card = _make_card(openclaw_phase_id="pumplai:45")
        parent_card["id"] = "parent-phase-1"
        mock_client.query_database.return_value = [parent_card]
        
        from notion_sync import _sync_container_failed, SyncResult
        
        event = {
            "project_id": "pumplai",
            "phase_id": "45",
            "container_id": "l3-abc",
            "payload": {
                "exit_code": 1,
                "retry_count": 3, # >= 3, retries exhausted
                "runtime_seconds": 30,
                "failure_category": "network_error"
            }
        }
        result = SyncResult("event_sync")
        
        _sync_container_failed(event, result)
        
        mock_client.upsert_by_dedupe.assert_not_called()
        
        # Verify parent status was updated to Waiting
        mock_client.update_page.assert_called_once()
        update_args = mock_client.update_page.call_args[0]
        assert update_args[0] == "parent-phase-1"
        assert update_args[1]["Status"]["select"]["name"] == "Waiting"
        
        # Verify both activities appended
        assert mock_client.append_activity.call_count == 2
        mock_client.append_activity.assert_any_call("parent-phase-1", "container_failed: l3-abc (exit 1)")
        mock_client.append_activity.assert_any_call("parent-phase-1", "retries exhausted — phase blocked")
        
        assert result.updated == 1

    @patch("notion_sync._load_config")
    @patch("notion_client.NotionClient")
    def test_sync_container_failed_meaningful(self, mock_client_class, mock_load_config):
        """Meaningful failure (tests failed) -> create bug card."""
        mock_load_config.return_value = {"meaningful_container_runtime_min": 10, "retry_max_attempts": 3}
        
        mock_client = mock_client_class.return_value
        mock_client._get_db_ids.return_value = ("proj_db", "proj_ds", "cards_db", "cards_ds")
        
        parent_card = _make_card(openclaw_phase_id="pumplai:45")
        parent_card["id"] = "parent-phase-1"
        
        mock_client.query_database.side_effect = [
            [parent_card],           # 1. find parent phase card
            [{"id": "proj-page-1"}]  # 2. find project page id
        ]
        
        mock_client.upsert_by_dedupe.return_value = {"action": "created", "page_id": "bug-card-1"}
        
        from notion_sync import _sync_container_failed, SyncResult
        
        event = {
            "project_id": "pumplai",
            "phase_id": "45",
            "container_id": "l3-abc",
            "payload": {
                "exit_code": 1,
                "retry_count": 0,
                "runtime_seconds": 30,
                "failure_category": "tests_failed" # Actionable!
            }
        }
        result = SyncResult("event_sync")
        
        _sync_container_failed(event, result)
        
        # Verify bug card was created
        mock_client.upsert_by_dedupe.assert_called_once()
        upsert_args = mock_client.upsert_by_dedupe.call_args[0]
        assert upsert_args[0] == "cards_db"
        assert upsert_args[4]["Status"]["select"]["name"] == "Waiting"
        assert upsert_args[4]["Card Type"]["select"]["name"] == "Bug"
        
        assert result.created == 1


# ---------------------------------------------------------------------------
# Reconcile Handler tests
# ---------------------------------------------------------------------------

class TestReconcileHandler:
    """Tests for reconcile handler and its 4 correction types."""

    def setup_method(self):
        import notion_sync
        notion_sync._project_page_id_cache.clear()

    @patch("reconcile_handler._read_openclaw_projects")
    @patch("notion_client.NotionClient")
    def test_reconcile_missing_projects(self, mock_client_class, mock_read_projects):
        """OpenClaw projects not in Notion -> create Projects DB rows."""
        mock_client = mock_client_class.return_value
        mock_client._get_db_ids.return_value = ("proj_db", "proj_ds", "cards_db", "cards_ds")
        
        # Mock OpenClaw projects
        mock_read_projects.return_value = [
            {"project_id": "newproj", "name": "New Project", "workspace": "/path/new"}
        ]
        
        # Mock Notion query (empty - no existing projects)
        mock_client._request.return_value = {"results": [], "has_more": False}
        
        mock_client.create_page.return_value = {"id": "new-proj-page-1"}
        
        from reconcile_handler import _reconcile_missing_projects
        from notion_sync import SyncResult
        
        result = SyncResult("reconcile")
        notion_project_ids = set()  # Empty - no projects exist
        
        _reconcile_missing_projects(
            mock_read_projects.return_value,
            notion_project_ids,
            mock_client,
            "proj_db",
            "proj_ds",
            result
        )
        
        mock_client.create_page.assert_called_once()
        create_args = mock_client.create_page.call_args[0]
        assert create_args[0] == "proj_db"
        assert create_args[1]["OpenClaw ID"]["rich_text"][0]["text"]["content"] == "newproj"
        
        assert result.created == 1
        assert result.mutations[0]["dedupe_key"] == "newproj"

    @patch("reconcile_handler._get_workspace_phase_statuses")
    @patch("notion_client.NotionClient")
    def test_reconcile_status_mismatch(self, mock_client_class, mock_get_statuses):
        """Status mismatch on OpenClaw-linked cards -> correct to match OpenClaw."""
        mock_client = mock_client_class.return_value
        
        # OpenClaw says phase should be "In Progress"
        mock_get_statuses.return_value = {"pumplai:45": "In Progress"}
        
        # Notion card with wrong status
        notion_card = _make_card(openclaw_phase_id="pumplai:45")
        notion_card["id"] = "phase-card-1"
        # Add a Status select property
        notion_card["properties"]["Status"] = {"select": {"name": "Backlog"}}
        
        from reconcile_handler import _reconcile_status_mismatch
        from notion_sync import SyncResult
        
        result = SyncResult("reconcile")
        openclaw_projects = [{"project_id": "pumplai", "name": "PumpLAI"}]
        
        _reconcile_status_mismatch(
            openclaw_projects,
            [notion_card],
            mock_client,
            result
        )
        
        mock_client.update_page.assert_called_once()
        update_args = mock_client.update_page.call_args[0]
        assert update_args[0] == "phase-card-1"
        assert update_args[1]["Status"]["select"]["name"] == "In Progress"
        
        assert result.updated == 1

    @patch("notion_client.NotionClient")
    def test_reconcile_missing_relations(self, mock_client_class):
        """Cards with Phase ID but no Project relation -> backfill relation."""
        mock_client = mock_client_class.return_value
        
        # Card with Phase ID but empty relation
        notion_card = _make_card(openclaw_phase_id="pumplai:45")
        notion_card["id"] = "phase-card-1"
        notion_card["properties"]["Project"] = {"relation": []}  # Empty relation
        
        from reconcile_handler import _reconcile_missing_relations
        from notion_sync import SyncResult
        
        result = SyncResult("reconcile")
        notion_projects_by_id = {"pumplai": "proj-page-1"}
        
        _reconcile_missing_relations(
            [notion_card],
            notion_projects_by_id,
            mock_client,
            result
        )
        
        mock_client.update_page.assert_called_once()
        update_args = mock_client.update_page.call_args[0]
        assert update_args[0] == "phase-card-1"
        assert update_args[1]["Project"]["relation"][0]["id"] == "proj-page-1"
        
        assert result.updated == 1

    @patch("notion_client.NotionClient")
    def test_reconcile_dangling_cards(self, mock_client_class):
        """Cards pointing to non-existent phases -> archive (set Status=Archived)."""
        mock_client = mock_client_class.return_value
        
        # Card with Phase ID pointing to deleted phase
        notion_card = _make_card(openclaw_phase_id="oldproj:99")
        notion_card["id"] = "old-phase-card"
        notion_card["properties"]["Status"] = {"select": {"name": "In Progress"}}
        
        from reconcile_handler import _reconcile_dangling_cards
        from notion_sync import SyncResult
        
        result = SyncResult("reconcile")
        openclaw_project_ids = {"pumplai", "smartai"}  # "oldproj" is NOT in this set
        openclaw_phase_keys = {"pumplai:45", "smartai:12"}  # "oldproj:99" is NOT here
        
        _reconcile_dangling_cards(
            [notion_card],
            openclaw_project_ids,
            openclaw_phase_keys,
            mock_client,
            result
        )
        
        mock_client.update_page.assert_called_once()
        update_args = mock_client.update_page.call_args[0]
        assert update_args[0] == "old-phase-card"
        assert update_args[1]["Status"]["select"]["name"] == "Archived"
        
        assert result.updated == 1

    @patch("notion_client.NotionClient")
    def test_reconcile_dangling_cards_already_archived(self, mock_client_class):
        """Dangling cards already Archived -> skip."""
        mock_client = mock_client_class.return_value
        
        # Card already Archived
        notion_card = _make_card(openclaw_phase_id="oldproj:99")
        notion_card["id"] = "old-phase-card"
        notion_card["properties"]["Status"] = {"select": {"name": "Archived"}}
        
        from reconcile_handler import _reconcile_dangling_cards
        from notion_sync import SyncResult
        
        result = SyncResult("reconcile")
        openclaw_project_ids = {"pumplai"}
        openclaw_phase_keys = set()
        
        _reconcile_dangling_cards(
            [notion_card],
            openclaw_project_ids,
            openclaw_phase_keys,
            mock_client,
            result
        )
        
        mock_client.update_page.assert_not_called()
        assert result.skipped == 1


# ---------------------------------------------------------------------------
# End of tests
