"""
SwarmQuery Implementation

Read-only state aggregation for L1 orchestrator visibility.
Safe for concurrent use with L2/L3 write operations (uses LOCK_SH).
"""

import json
import time
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

# Import from orchestration package
from openclaw.state_engine import JarvisState
from openclaw.config import get_project_root, get_state_path, CACHE_TTL_SECONDS
from openclaw.project_config import load_and_validate_openclaw_config
from openclaw.logging import get_logger

logger = get_logger("swarm_query")


@dataclass
class TaskInfo:
    """Summary of a single task."""
    task_id: str
    status: str
    skill_hint: str
    created_at: float
    updated_at: float
    last_entry: str = ""
    activity_count: int = 0
    
    @property
    def is_active(self) -> bool:
        return self.status in ("in_progress", "starting", "testing")
    
    @property
    def is_terminal(self) -> bool:
        return self.status in ("completed", "failed", "rejected")
    
    @property
    def minutes_since_update(self) -> float:
        return (time.time() - self.updated_at) / 60.0


@dataclass
class ProjectSnapshot:
    """Real-time snapshot of a single project's state."""
    project_id: str
    tasks: Dict[str, TaskInfo] = field(default_factory=dict)
    active_tasks: int = 0
    queued_tasks: int = 0
    completed_tasks: int = 0
    failed_tasks: int = 0
    last_activity: Optional[float] = None
    l3_containers_running: int = 0
    health_score: float = 1.0
    
    def get_stalled_tasks(self, threshold_minutes: float = 30.0) -> List[TaskInfo]:
        """Return tasks with no activity for threshold_minutes."""
        stalled = []
        for task in self.tasks.values():
            if task.is_active and task.minutes_since_update > threshold_minutes:
                stalled.append(task)
        return stalled


@dataclass
class SwarmOverview:
    """Aggregate view across all managed projects."""
    projects: List[ProjectSnapshot] = field(default_factory=list)
    total_active: int = 0
    total_queued: int = 0
    total_completed: int = 0
    total_failed: int = 0
    bottleneck_projects: List[str] = field(default_factory=list)
    
    @property
    def total_tasks(self) -> int:
        return self.total_active + self.total_queued + self.total_completed + self.total_failed


class SwarmQuery:
    """
    Read-only query interface for L1 swarm visibility.
    
    Thread-safe for concurrent reads. Uses 5-second TTL cache to prevent
    state file thrashing when querying multiple projects.
    """
    
    def __init__(self, project_ids: Optional[List[str]] = None):
        """
        Initialize SwarmQuery.
        
        Args:
            project_ids: List of project IDs to query. If None, reads from
                        clawdia_prime config or discovers from projects/ dir.
        """
        self._project_ids = project_ids or self._load_managed_projects()
        self._cache: Dict[str, Tuple[ProjectSnapshot, float]] = {}
        self._cache_ttl = CACHE_TTL_SECONDS
        
    def _load_managed_projects(self) -> List[str]:
        """Load project list from clawdia_prime config or discover from projects/."""
        try:
            # Try to read from clawdia_prime config
            root = get_project_root()
            config_path = root / "agents" / "clawdia_prime" / "agent" / "config.json"
            if config_path.exists():
                with open(config_path) as f:
                    config = json.load(f)
                projects = config.get("projects", [])
                if projects:
                    logger.debug(f"Loaded projects from clawdia_prime config: {projects}")
                    return projects
        except Exception as e:
            logger.warning(f"Failed to load clawdia_prime config: {e}")
        
        # Fallback: discover from projects/ directory
        try:
            root = get_project_root()
            projects_dir = root / "projects"
            if projects_dir.exists():
                projects = [
                    p.name for p in projects_dir.iterdir()
                    if p.is_dir() and not p.name.startswith("_")
                ]
                logger.debug(f"Discovered projects from directory: {projects}")
                return sorted(projects)
        except Exception as e:
            logger.warning(f"Failed to discover projects: {e}")
        
        # Last resort: try active_project from openclaw.json
        try:
            config = load_and_validate_openclaw_config()
            active = config.get("active_project")
            if active:
                return [active]
        except Exception:
            pass
        
        return []
    
    def _get_cached_snapshot(self, project_id: str) -> Optional[ProjectSnapshot]:
        """Get cached snapshot if still valid."""
        if project_id in self._cache:
            snapshot, cached_at = self._cache[project_id]
            if time.monotonic() - cached_at < self._cache_ttl:
                logger.debug(f"Cache hit for project {project_id}")
                return snapshot
            else:
                logger.debug(f"Cache expired for project {project_id}")
        return None
    
    def _cache_snapshot(self, project_id: str, snapshot: ProjectSnapshot) -> None:
        """Cache a snapshot with current timestamp."""
        self._cache[project_id] = (snapshot, time.monotonic())
    
    def get_project_status(self, project_id: str, use_cache: bool = True) -> Optional[ProjectSnapshot]:
        """
        Get detailed status for a single project.
        
        Args:
            project_id: The project to query
            use_cache: If True, may return cached result within TTL
            
        Returns:
            ProjectSnapshot or None if project not found/error
        """
        # Check cache first
        if use_cache:
            cached = self._get_cached_snapshot(project_id)
            if cached:
                return cached
        
        try:
            state_path = get_state_path(project_id)
            if not state_path.exists():
                logger.debug(f"No state file for project {project_id}")
                return None
            
            # Read state (uses LOCK_SH - shared lock, safe with writers)
            jarvis = JarvisState(state_path)
            state = jarvis.read_state()
            tasks = state.get("tasks", {})
            
            # Build snapshot
            snapshot = ProjectSnapshot(project_id=project_id)
            latest_activity = 0.0
            
            for task_id, task_data in tasks.items():
                status = task_data.get("status", "unknown")
                created = task_data.get("created_at", 0.0)
                updated = task_data.get("updated_at", created)
                activity_log = task_data.get("activity_log", [])
                
                # Get last entry text
                last_entry = ""
                if activity_log:
                    last_entry = activity_log[-1].get("entry", "")
                    last_entry_time = activity_log[-1].get("timestamp", updated)
                    latest_activity = max(latest_activity, last_entry_time)
                
                task_info = TaskInfo(
                    task_id=task_id,
                    status=status,
                    skill_hint=task_data.get("skill_hint", "unknown"),
                    created_at=created,
                    updated_at=updated,
                    last_entry=last_entry,
                    activity_count=len(activity_log)
                )
                
                snapshot.tasks[task_id] = task_info
                
                # Categorize by status
                if status in ("in_progress", "starting", "testing"):
                    snapshot.active_tasks += 1
                elif status == "pending":
                    snapshot.queued_tasks += 1
                elif status == "completed":
                    snapshot.completed_tasks += 1
                elif status in ("failed", "rejected"):
                    snapshot.failed_tasks += 1
            
            snapshot.last_activity = latest_activity if latest_activity > 0 else None
            
            # Query Docker for running L3 containers (optional, non-blocking)
            snapshot.l3_containers_running = self._count_project_containers(project_id)
            
            # Compute health score
            snapshot.health_score = self._compute_health_score(snapshot)
            
            # Cache and return
            self._cache_snapshot(project_id, snapshot)
            return snapshot
            
        except Exception as e:
            logger.error(f"Failed to query project {project_id}: {e}")
            return None
    
    def get_swarm_overview(self) -> SwarmOverview:
        """
        Get aggregate view across all managed projects.
        
        Returns:
            SwarmOverview with totals and bottleneck detection
        """
        overview = SwarmOverview()
        
        for project_id in self._project_ids:
            snapshot = self.get_project_status(project_id)
            if snapshot:
                overview.projects.append(snapshot)
                overview.total_active += snapshot.active_tasks
                overview.total_queued += snapshot.queued_tasks
                overview.total_completed += snapshot.completed_tasks
                overview.total_failed += snapshot.failed_tasks
                
                # Detect bottlenecks (health < 0.5)
                if snapshot.health_score < 0.5:
                    overview.bottleneck_projects.append(project_id)
        
        return overview
    
    def find_stalled_tasks(self, threshold_minutes: float = 30.0) -> Dict[str, List[TaskInfo]]:
        """
        Find stalled tasks across all projects.
        
        Args:
            threshold_minutes: Tasks with no activity for this long are stalled
            
        Returns:
            Dict mapping project_id -> list of stalled TaskInfo
        """
        stalled_by_project: Dict[str, List[TaskInfo]] = {}
        
        for project_id in self._project_ids:
            snapshot = self.get_project_status(project_id)
            if snapshot:
                stalled = snapshot.get_stalled_tasks(threshold_minutes)
                if stalled:
                    stalled_by_project[project_id] = stalled
        
        return stalled_by_project
    
    def get_health_score(self, project_id: str) -> float:
        """
        Get health score for a single project (0.0-1.0).
        
        Args:
            project_id: Project to check
            
        Returns:
            Health score, or 0.0 if project not found
        """
        snapshot = self.get_project_status(project_id)
        return snapshot.health_score if snapshot else 0.0
    
    def _compute_health_score(self, snapshot: ProjectSnapshot) -> float:
        """
        Compute project health score (0.0-1.0).
        
        Algorithm:
        - Start at 1.0 (perfect health)
        - -0.3 if at capacity (active >= 3, typical max_concurrent)
        - -0.3 if backlog is high (queued > 5)
        - -0.3 if there are recent failures
        - -0.1 per stalled task
        """
        score = 1.0
        
        # Capacity pressure
        if snapshot.active_tasks >= 3:
            score -= 0.3
        
        # Backlog pressure
        if snapshot.queued_tasks > 5:
            score -= 0.3
        
        # Failure pressure
        if snapshot.failed_tasks > 0:
            score -= 0.3
        
        # Stalled task penalty
        stalled = len(snapshot.get_stalled_tasks())
        score -= 0.1 * stalled
        
        return max(0.0, score)
    
    def _count_project_containers(self, project_id: str) -> int:
        """
        Count running L3 containers for a project.
        
        This is optional - failures are logged but not raised.
        """
        try:
            import docker
            client = docker.from_env()
            containers = client.containers.list(
                filters={
                    "label": "openclaw.managed=true",
                    "label": f"openclaw.project={project_id}",
                    "status": "running"
                }
            )
            return len(containers)
        except Exception as e:
            logger.debug(f"Docker query failed for project {project_id}: {e}")
            return 0
    
    def invalidate_cache(self, project_id: Optional[str] = None) -> None:
        """
        Invalidate cache for a project or all projects.
        
        Args:
            project_id: If provided, invalidate only this project. Otherwise all.
        """
        if project_id:
            self._cache.pop(project_id, None)
        else:
            self._cache.clear()
        logger.debug(f"Cache invalidated for {project_id or 'all projects'}")
