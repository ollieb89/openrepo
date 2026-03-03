"""
Topology File Storage

Provides fcntl-based read/write operations for topology files.
Stores topology data under:
  <project_root>/workspace/.openclaw/<project_id>/topology/

Files:
  current.json   — Latest topology snapshot (atomic write with .bak backup)
  changelog.json — Append-only list of change entries

Follows the Jarvis Protocol pattern from state_engine.py:
  - LOCK_EX for writes, LOCK_SH for reads
  - .tmp + rename for atomic writes (crash-safe)
  - .bak backup before overwriting current.json
  - Graceful .bak recovery on corruption
"""

import fcntl
import json
import logging
import shutil
from pathlib import Path
from typing import Dict, List, Optional

from openclaw.config import get_project_root
from openclaw.topology.models import TopologyGraph

logger = logging.getLogger(__name__)


def _topology_dir(project_id: str) -> Path:
    """Return the topology directory for a project, creating it if needed.

    Path: <project_root>/workspace/.openclaw/<project_id>/topology/
    """
    topo_dir = get_project_root() / "workspace" / ".openclaw" / project_id / "topology"
    topo_dir.mkdir(parents=True, exist_ok=True)
    return topo_dir


def save_topology(project_id: str, graph: TopologyGraph) -> None:
    """Persist a TopologyGraph to current.json using atomic write.

    Protocol:
    1. If current.json exists, copy to current.json.bak
    2. Write graph JSON to current.json.tmp with LOCK_EX held
    3. Rename .tmp → current.json (atomic on POSIX systems)

    Args:
        project_id: The project identifier.
        graph: The topology graph to persist.
    """
    topo_dir = _topology_dir(project_id)
    current_path = topo_dir / "current.json"
    tmp_path = topo_dir / "current.json.tmp"
    bak_path = topo_dir / "current.json.bak"

    # Backup existing file before overwrite
    if current_path.exists():
        shutil.copy2(str(current_path), str(bak_path))

    # Write to .tmp with exclusive lock, then rename atomically
    with open(tmp_path, "w", encoding="utf-8") as f:
        fcntl.flock(f.fileno(), fcntl.LOCK_EX)
        try:
            f.write(graph.to_json())
            f.flush()
        finally:
            fcntl.flock(f.fileno(), fcntl.LOCK_UN)

    tmp_path.rename(current_path)


def load_topology(project_id: str) -> Optional[TopologyGraph]:
    """Load the current topology snapshot from disk.

    Returns None if no topology file exists for the given project.
    Falls back to .bak if current.json is corrupted.

    Args:
        project_id: The project identifier.

    Returns:
        TopologyGraph or None if not found.
    """
    topo_dir = _topology_dir(project_id)
    current_path = topo_dir / "current.json"

    if not current_path.exists():
        return None

    # Try primary file first
    try:
        with open(current_path, "r", encoding="utf-8") as f:
            fcntl.flock(f.fileno(), fcntl.LOCK_SH)
            try:
                raw = f.read()
            finally:
                fcntl.flock(f.fileno(), fcntl.LOCK_UN)
        return TopologyGraph.from_json(raw)
    except (json.JSONDecodeError, KeyError, ValueError) as exc:
        logger.warning(
            "topology current.json corrupted for project %s: %s — attempting .bak recovery",
            project_id,
            exc,
        )

    # Fall back to .bak
    bak_path = topo_dir / "current.json.bak"
    if bak_path.exists():
        try:
            with open(bak_path, "r", encoding="utf-8") as f:
                fcntl.flock(f.fileno(), fcntl.LOCK_SH)
                try:
                    raw = f.read()
                finally:
                    fcntl.flock(f.fileno(), fcntl.LOCK_UN)
            logger.warning("topology recovered from .bak for project %s", project_id)
            return TopologyGraph.from_json(raw)
        except Exception as bak_exc:
            logger.error("topology .bak recovery also failed for project %s: %s", project_id, bak_exc)

    return None


def append_changelog(project_id: str, entry: dict) -> None:
    """Append an entry to changelog.json using an atomic read-modify-write.

    Acquires LOCK_EX for the entire read-modify-write cycle to prevent
    concurrent corruption.

    Args:
        project_id: The project identifier.
        entry: A dict describing the change event.
    """
    topo_dir = _topology_dir(project_id)
    changelog_path = topo_dir / "changelog.json"
    tmp_path = topo_dir / "changelog.json.tmp"

    # Read-modify-write under exclusive lock
    with open(str(changelog_path) + ".lock", "w", encoding="utf-8") as lock_f:
        fcntl.flock(lock_f.fileno(), fcntl.LOCK_EX)
        try:
            if changelog_path.exists():
                with open(changelog_path, "r", encoding="utf-8") as f:
                    entries: List[dict] = json.load(f)
            else:
                entries = []

            entries.append(entry)

            with open(tmp_path, "w", encoding="utf-8") as f:
                json.dump(entries, f, indent=2)
            tmp_path.rename(changelog_path)
        finally:
            fcntl.flock(lock_f.fileno(), fcntl.LOCK_UN)


def load_changelog(project_id: str) -> List[Dict]:
    """Load the changelog entries from changelog.json.

    Returns an empty list if the changelog file does not exist.

    Args:
        project_id: The project identifier.

    Returns:
        List of changelog entry dicts.
    """
    topo_dir = _topology_dir(project_id)
    changelog_path = topo_dir / "changelog.json"

    if not changelog_path.exists():
        return []

    with open(changelog_path, "r", encoding="utf-8") as f:
        fcntl.flock(f.fileno(), fcntl.LOCK_SH)
        try:
            return json.load(f)
        finally:
            fcntl.flock(f.fileno(), fcntl.LOCK_UN)


# ---------------------------------------------------------------------------
# Pending proposals persistence
# ---------------------------------------------------------------------------

def save_pending_proposals(project_id: str, data: dict) -> None:
    """Persist pending proposal data to pending-proposals.json using atomic write.

    Uses the same tmp+rename+fcntl pattern as save_topology for crash safety.

    Args:
        project_id: The project identifier.
        data: The pending proposal data dict to persist.
    """
    topo_dir = _topology_dir(project_id)
    pending_path = topo_dir / "pending-proposals.json"
    tmp_path = topo_dir / "pending-proposals.json.tmp"

    with open(tmp_path, "w", encoding="utf-8") as f:
        fcntl.flock(f.fileno(), fcntl.LOCK_EX)
        try:
            json.dump(data, f, indent=2)
            f.flush()
        finally:
            fcntl.flock(f.fileno(), fcntl.LOCK_UN)

    tmp_path.rename(pending_path)


def load_pending_proposals(project_id: str) -> Optional[dict]:
    """Load pending proposal data from pending-proposals.json.

    Returns None if the file does not exist.

    Args:
        project_id: The project identifier.

    Returns:
        Loaded dict or None if no pending proposals file exists.
    """
    topo_dir = _topology_dir(project_id)
    pending_path = topo_dir / "pending-proposals.json"

    if not pending_path.exists():
        return None

    with open(pending_path, "r", encoding="utf-8") as f:
        fcntl.flock(f.fileno(), fcntl.LOCK_SH)
        try:
            return json.load(f)
        finally:
            fcntl.flock(f.fileno(), fcntl.LOCK_UN)


def delete_pending_proposals(project_id: str) -> None:
    """Delete pending-proposals.json if it exists.

    Silently does nothing if the file is not present.

    Args:
        project_id: The project identifier.
    """
    topo_dir = _topology_dir(project_id)
    pending_path = topo_dir / "pending-proposals.json"

    if pending_path.exists():
        pending_path.unlink()
        logger.debug("Deleted pending-proposals.json for project=%s", project_id)
