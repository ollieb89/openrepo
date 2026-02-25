"""
Notion HTTP client wrapper for the notion-kanban-sync skill.

Handles:
- Authenticated API calls with Notion-Version: 2025-09-03
- Retry with exponential backoff on 429 and 5xx
- Discover-or-create bootstrap for Projects DB and Cards DB
- Config.json caching of both database_id and data_source_id for each DB
- Thread-safe config reads/writes
- Activity field append (read-before-write, 2 API calls)
- Upsert by dedupe key

IMPORTANT — API 2025-09-03 ID distinction:
  database_id   → page creation (POST /v1/pages with parent.database_id)
  data_source_id → queries (POST /v1/data_sources/{data_source_id}/query)
  Both are cached separately in config.json.
"""

import json
import os
import time
import threading
import logging
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import httpx

logger = logging.getLogger(__name__)

_NOTION_API_BASE = "https://api.notion.com"
_NOTION_VERSION = "2025-09-03"

# Module-level lock for config reads/writes (prevents concurrent bootstrap races)
_config_lock = threading.Lock()


class NotionClient:
    """HTTP wrapper for the Notion API (version 2025-09-03).

    Usage:
        client = NotionClient()
        client.bootstrap()           # discovers/creates Projects DB and Cards DB
        pages = client.query_database(ds_id, filter_)
        result = client.upsert_by_dedupe(db_id, ds_id, "OpenClaw Phase ID", "pumplai:45", props)
    """

    def __init__(self, config_path: Optional[str] = None) -> None:
        token = os.environ.get("NOTION_TOKEN")
        if not token:
            raise RuntimeError("NOTION_TOKEN not set")

        self._headers = {
            "Authorization": f"Bearer {token}",
            "Notion-Version": _NOTION_VERSION,
            "Content-Type": "application/json",
        }

        if config_path is None:
            self._config_path = Path(__file__).parent / "config.json"
        else:
            self._config_path = Path(config_path)

        self._bulk_mode: bool = False  # enable for reconcile to add inter-request delays

    # ------------------------------------------------------------------
    # Config persistence (thread-safe)
    # ------------------------------------------------------------------

    def _load_config(self) -> Dict[str, Any]:
        with _config_lock:
            with open(self._config_path, "r", encoding="utf-8") as f:
                return json.load(f)

    def _save_config(self, config: Dict[str, Any]) -> None:
        with _config_lock:
            with open(self._config_path, "w", encoding="utf-8") as f:
                json.dump(config, f, indent=2)
                f.write("\n")

    # ------------------------------------------------------------------
    # Core HTTP request with retry/backoff
    # ------------------------------------------------------------------

    def _request(self, method: str, path: str, **kwargs) -> Dict[str, Any]:
        """Make an authenticated Notion API request with retry on 429/5xx.

        Retry policy:
          - 429 (rate limit): exponential backoff — base_delay * 2^attempt, max retry_max_attempts
          - 5xx (server error): retry once after 2s
          - 400 (bad request): do NOT retry, raise immediately
          - 404: raise (caller handles cache invalidation)
        """
        config = self._load_config()
        max_retries = int(config.get("retry_max_attempts", 3))
        base_delay = float(config.get("retry_base_delay_seconds", 1.0))

        url = f"{_NOTION_API_BASE}{path}"

        for attempt in range(max_retries + 1):
            if self._bulk_mode and attempt == 0:
                # Rate-limit throttle for bulk operations (reconcile)
                time.sleep(0.35)

            try:
                resp = httpx.request(method, url, headers=self._headers, **kwargs)
            except httpx.RequestError as exc:
                if attempt >= max_retries:
                    raise RuntimeError(f"Notion request network error: {exc}") from exc
                logger.warning(f"Notion network error (attempt {attempt + 1}): {exc}")
                time.sleep(base_delay * (2 ** attempt))
                continue

            if resp.status_code == 429:
                if attempt < max_retries:
                    delay = base_delay * (2 ** attempt)
                    logger.warning(f"Notion 429 rate limit, backing off {delay}s (attempt {attempt + 1})")
                    time.sleep(delay)
                    continue
                raise RuntimeError(f"Notion rate limit exceeded after {max_retries} retries (429)")

            if resp.status_code >= 500:
                if attempt < max_retries:
                    logger.warning(f"Notion {resp.status_code} server error, retrying after 2s (attempt {attempt + 1})")
                    time.sleep(2.0)
                    continue
                raise RuntimeError(f"Notion server error after retries: {resp.status_code} {resp.text}")

            if resp.status_code == 400:
                raise RuntimeError(f"Notion bad request (400): {resp.text}")

            if resp.status_code == 404:
                raise RuntimeError(f"Notion not found (404): {path}")

            resp.raise_for_status()
            return resp.json()

        raise RuntimeError("Notion request failed after all retry attempts")

    # ------------------------------------------------------------------
    # Typed helpers
    # ------------------------------------------------------------------

    def search_database(self, name: str, signature_property: str) -> Optional[Dict[str, str]]:
        """Search for a Notion database by title and verify it has a signature property.

        Returns {"database_id": ..., "data_source_id": ...} or None.

        Note: API 2025-09-03 returns object type "data_source" (not "database").
        """
        result = self._request("POST", "/v1/search", json={
            "query": name,
            "filter": {"value": "database", "property": "object"},
        })
        for obj in result.get("results", []):
            # API 2025-09-03: object type is "data_source"
            if obj.get("object") not in ("database", "data_source"):
                continue
            # Match title
            title_parts = obj.get("title", [])
            obj_title = "".join(t.get("plain_text", "") for t in title_parts)
            if obj_title.strip().lower() != name.strip().lower():
                continue
            # Verify signature property exists
            properties = obj.get("properties", {})
            if signature_property not in properties:
                continue
            # Return both IDs
            database_id = obj.get("id")
            data_source_id = obj.get("data_source_id", database_id)
            return {"database_id": database_id, "data_source_id": data_source_id}
        return None

    def create_database(self, parent_page_id: str, title: str, properties: Dict[str, Any]) -> Dict[str, str]:
        """Create a Notion database (data source) with the given schema.

        Returns {"database_id": ..., "data_source_id": ...}.
        """
        result = self._request("POST", "/v1/data_sources", json={
            "parent": {"page_id": parent_page_id},
            "title": [{"text": {"content": title}}],
            "properties": properties,
            "is_inline": True,
        })
        database_id = result.get("id")
        data_source_id = result.get("data_source_id", database_id)
        return {"database_id": database_id, "data_source_id": data_source_id}

    def query_database(self, data_source_id: str, filter_: Optional[Dict[str, Any]] = None) -> List[Dict[str, Any]]:
        """Query a Notion database using data_source_id (API 2025-09-03 requirement).

        Uses /v1/data_sources/{data_source_id}/query — NOT database_id.
        """
        payload: Dict[str, Any] = {}
        if filter_:
            payload["filter"] = filter_
        result = self._request("POST", f"/v1/data_sources/{data_source_id}/query", json=payload)
        return result.get("results", [])

    def create_page(self, database_id: str, properties: Dict[str, Any]) -> Dict[str, Any]:
        """Create a page in a Notion database using database_id (for page creation)."""
        return self._request("POST", "/v1/pages", json={
            "parent": {"database_id": database_id},
            "properties": properties,
        })

    def update_page(self, page_id: str, properties: Dict[str, Any]) -> Dict[str, Any]:
        """Update a Notion page's properties."""
        return self._request("PATCH", f"/v1/pages/{page_id}", json={
            "properties": properties,
        })

    def get_page(self, page_id: str) -> Dict[str, Any]:
        """Get a Notion page (used for read-before-write on Activity field)."""
        return self._request("GET", f"/v1/pages/{page_id}")

    def upsert_by_dedupe(
        self,
        db_id: str,
        ds_id: str,
        dedupe_property: str,
        dedupe_value: str,
        properties: Dict[str, Any],
    ) -> Dict[str, Any]:
        """Search for a page by dedupe property, create or update.

        Returns {"action": "created"|"updated", "page_id": ..., "properties": ...}
        """
        # Search by dedupe property
        results = self.query_database(ds_id, filter_={
            "property": dedupe_property,
            "rich_text": {"equals": dedupe_value},
        })

        if results:
            page_id = results[0]["id"]
            page = self.update_page(page_id, properties)
            return {
                "action": "updated",
                "page_id": page_id,
                "properties": page.get("properties", {}),
            }
        else:
            page = self.create_page(db_id, properties)
            return {
                "action": "created",
                "page_id": page["id"],
                "properties": page.get("properties", {}),
            }

    # ------------------------------------------------------------------
    # Activity append helper (read-before-write)
    # ------------------------------------------------------------------

    def append_activity(self, page_id: str, new_line: str) -> Dict[str, Any]:
        """Append a line to the Activity rich_text field of a page.

        This is 2 API calls:
          1. GET page to read current Activity text
          2. PATCH page with prepended new line + existing content

        Also updates Last Activity At and Last Synced timestamps.
        """
        page = self.get_page(page_id)
        props = page.get("properties", {})

        # Extract existing Activity text
        activity_prop = props.get("Activity", {})
        existing_parts = activity_prop.get("rich_text", [])
        existing_text = "".join(p.get("plain_text", "") for p in existing_parts)

        # Prepend new line with timestamp
        now = datetime.now(timezone.utc)
        timestamp = now.strftime("%Y-%m-%d %H:%M")
        new_text = f"[{timestamp}] {new_line}\n{existing_text}".rstrip()

        now_iso = now.isoformat()

        return self.update_page(page_id, {
            "Activity": {
                "rich_text": [{"text": {"content": new_text[:2000]}}]  # Notion rich_text limit
            },
            "Last Activity At": {"date": {"start": now_iso}},
            "Last Synced": {"date": {"start": now_iso}},
        })

    # ------------------------------------------------------------------
    # Bootstrap — discover or create Projects DB and Cards DB
    # ------------------------------------------------------------------

    def _get_db_ids(self) -> Tuple[Optional[str], Optional[str], Optional[str], Optional[str]]:
        """Return (projects_db_id, projects_ds_id, cards_db_id, cards_ds_id).

        Calls bootstrap() if any are None.
        """
        config = self._load_config()
        proj_db = config.get("notion_projects_db_id")
        proj_ds = config.get("notion_projects_ds_id")
        cards_db = config.get("notion_cards_db_id")
        cards_ds = config.get("notion_cards_ds_id")

        if not all([proj_db, proj_ds, cards_db, cards_ds]):
            self.bootstrap()
            config = self._load_config()
            proj_db = config.get("notion_projects_db_id")
            proj_ds = config.get("notion_projects_ds_id")
            cards_db = config.get("notion_cards_db_id")
            cards_ds = config.get("notion_cards_ds_id")

        return proj_db, proj_ds, cards_db, cards_ds

    def bootstrap(self) -> None:
        """Discover or create the Projects DB and Cards DB, caching all 4 IDs.

        First invocation: searches for DBs by name + signature property.
        If not found and auto_create_dbs: creates with full schema.
        Subsequent invocations: reads from config.json cache.
        On 404 for cached IDs: clears and re-discovers.
        """
        config = self._load_config()

        # --- Projects DB ---
        proj_db_id, proj_ds_id = self._bootstrap_single_db(
            config=config,
            db_id_key="notion_projects_db_id",
            ds_id_key="notion_projects_ds_id",
            name="Projects",
            signature_property="OpenClaw ID",
            schema=_PROJECTS_DB_SCHEMA,
        )

        # --- Cards DB ---
        cards_db_id, cards_ds_id = self._bootstrap_single_db(
            config=config,
            db_id_key="notion_cards_db_id",
            ds_id_key="notion_cards_ds_id",
            name="Cards",
            signature_property="OpenClaw Phase ID",
            schema=_CARDS_DB_SCHEMA,
        )

        # Persist all 4 IDs atomically
        config["notion_projects_db_id"] = proj_db_id
        config["notion_projects_ds_id"] = proj_ds_id
        config["notion_cards_db_id"] = cards_db_id
        config["notion_cards_ds_id"] = cards_ds_id
        self._save_config(config)

        logger.info(
            f"Bootstrap complete. Projects: db={proj_db_id}, ds={proj_ds_id}. "
            f"Cards: db={cards_db_id}, ds={cards_ds_id}"
        )

    def _bootstrap_single_db(
        self,
        config: Dict[str, Any],
        db_id_key: str,
        ds_id_key: str,
        name: str,
        signature_property: str,
        schema: Dict[str, Any],
    ) -> Tuple[str, str]:
        """Bootstrap a single Notion DB — validate cache, discover, or create.

        Returns (database_id, data_source_id).
        """
        cached_db_id = config.get(db_id_key)
        cached_ds_id = config.get(ds_id_key)

        # Validate cached IDs
        if cached_db_id:
            try:
                self._request("GET", f"/v1/databases/{cached_db_id}")
                logger.debug(f"{name} DB cached ID valid: {cached_db_id}")
                return cached_db_id, cached_ds_id or cached_db_id
            except RuntimeError as e:
                if "404" in str(e):
                    logger.warning(f"{name} DB cached ID returned 404, re-discovering")
                    cached_db_id = None
                    cached_ds_id = None
                else:
                    raise

        # Search for existing DB
        ids = self.search_database(name, signature_property)
        if ids:
            logger.info(f"Found existing {name} DB: {ids}")
            return ids["database_id"], ids["data_source_id"]

        # Create if allowed
        auto_create = config.get("auto_create_dbs", True)
        if not auto_create:
            raise RuntimeError(
                f"{name} DB not found. Set notion_{name.lower()}_db_id in config.json "
                f"or enable auto_create_dbs."
            )

        parent_page_id = config.get("notion_parent_page_id")
        if not parent_page_id:
            raise RuntimeError(
                f"Set notion_parent_page_id in config.json to enable auto-creation of {name} DB. "
                f"This is the Notion page ID under which the database will be created."
            )

        logger.info(f"Creating {name} DB under parent page {parent_page_id}")
        ids = self.create_database(parent_page_id, name, schema)
        logger.info(f"Created {name} DB: {ids}")
        return ids["database_id"], ids["data_source_id"]


# ------------------------------------------------------------------
# DB Schema definitions (from SPEC.md)
# ------------------------------------------------------------------

_PROJECTS_DB_SCHEMA: Dict[str, Any] = {
    "Name": {"title": {}},
    "OpenClaw ID": {"rich_text": {}},
    "Type": {
        "select": {
            "options": [
                {"name": "Dev Project", "color": "blue"},
                {"name": "Life Initiative", "color": "green"},
            ]
        }
    },
    "Status": {
        "select": {
            "options": [
                {"name": "Active", "color": "green"},
                {"name": "Paused", "color": "yellow"},
                {"name": "Completed", "color": "blue"},
                {"name": "Archived", "color": "gray"},
            ]
        }
    },
    "Repo/Path": {"url": {}},
    "Current Phase": {"rich_text": {}},
    "Milestone": {"rich_text": {}},
    "Sync Status": {"rich_text": {}},
    "Sync Error": {"rich_text": {}},
    "Notes": {"rich_text": {}},
    "Priority": {
        "select": {
            "options": [
                {"name": "High", "color": "red"},
                {"name": "Medium", "color": "yellow"},
                {"name": "Low", "color": "gray"},
            ]
        }
    },
}

_CARDS_DB_SCHEMA: Dict[str, Any] = {
    "Name": {"title": {}},
    "Status": {
        "select": {
            "options": [
                {"name": "Backlog", "color": "gray"},
                {"name": "This Week", "color": "blue"},
                {"name": "In Progress", "color": "yellow"},
                {"name": "Waiting", "color": "orange"},
                {"name": "Done", "color": "green"},
                {"name": "Archived", "color": "default"},
            ]
        }
    },
    "Area": {
        "select": {
            "options": [
                {"name": "Dev", "color": "blue"},
                {"name": "Health", "color": "green"},
                {"name": "Finance", "color": "yellow"},
                {"name": "Learning", "color": "purple"},
                {"name": "Relationships", "color": "pink"},
                {"name": "Admin", "color": "gray"},
            ]
        }
    },
    "Card Type": {
        "select": {
            "options": [
                {"name": "Phase", "color": "blue"},
                {"name": "Task", "color": "gray"},
                {"name": "Life Task", "color": "green"},
                {"name": "Initiative", "color": "purple"},
                {"name": "Bug", "color": "red"},
                {"name": "Incident", "color": "orange"},
            ]
        }
    },
    "Capture Source": {
        "select": {
            "options": [
                {"name": "OpenClaw Event", "color": "blue"},
                {"name": "Conversation", "color": "green"},
                {"name": "Manual", "color": "gray"},
            ]
        }
    },
    "OpenClaw Phase ID": {"rich_text": {}},
    "OpenClaw Event Anchor": {"rich_text": {}},
    "Capture Hash": {"rich_text": {}},
    "Priority": {
        "select": {
            "options": [
                {"name": "High", "color": "red"},
                {"name": "Medium", "color": "yellow"},
                {"name": "Low", "color": "gray"},
            ]
        }
    },
    "Target Week": {"date": {}},
    "Notes": {"rich_text": {}},
    "Activity": {"rich_text": {}},
    "Last Activity At": {"date": {}},
    "Last Synced": {"date": {}},
}
