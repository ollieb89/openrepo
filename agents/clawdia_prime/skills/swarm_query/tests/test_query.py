"""
Tests for SwarmQuery skill.

Tests cover:
- Read-only safety (no write operations)
- Cache behavior
- Health score computation
- Stalled task detection
"""

import json
import tempfile
import time
import threading
from pathlib import Path
from unittest.mock import patch, MagicMock

import pytest

from ..query import (
    SwarmQuery,
    ProjectSnapshot,
    TaskInfo,
    SwarmOverview,
)


class TestTaskInfo:
    """Test TaskInfo dataclass."""
    
    def test_is_active(self):
        """Test active status detection."""
        assert TaskInfo("t1", "in_progress", "code", 0, 0).is_active is True
        assert TaskInfo("t1", "starting", "code", 0, 0).is_active is True
        assert TaskInfo("t1", "testing", "code", 0, 0).is_active is True
        assert TaskInfo("t1", "completed", "code", 0, 0).is_active is False
        assert TaskInfo("t1", "failed", "code", 0, 0).is_active is False
        assert TaskInfo("t1", "pending", "code", 0, 0).is_active is False
    
    def test_is_terminal(self):
        """Test terminal status detection."""
        assert TaskInfo("t1", "completed", "code", 0, 0).is_terminal is True
        assert TaskInfo("t1", "failed", "code", 0, 0).is_terminal is True
        assert TaskInfo("t1", "rejected", "code", 0, 0).is_terminal is True
        assert TaskInfo("t1", "in_progress", "code", 0, 0).is_terminal is False
    
    def test_minutes_since_update(self):
        """Test time since update calculation."""
        now = time.time()
        task = TaskInfo("t1", "in_progress", "code", now - 3600, now - 1800)
        assert task.minutes_since_update == pytest.approx(30.0, rel=0.1)


class TestProjectSnapshot:
    """Test ProjectSnapshot dataclass."""
    
    def test_get_stalled_tasks(self):
        """Test stalled task detection."""
        now = time.time()
        snapshot = ProjectSnapshot(
            project_id="test",
            tasks={
                "active_recent": TaskInfo("t1", "in_progress", "code", now - 3600, now - 60),
                "active_old": TaskInfo("t2", "in_progress", "code", now - 3600, now - 3600),
                "completed": TaskInfo("t3", "completed", "code", now - 3600, now - 3600),
            }
        )
        
        stalled = snapshot.get_stalled_tasks(threshold_minutes=30)
        assert len(stalled) == 1
        assert stalled[0].task_id == "active_old"


class TestSwarmQueryInit:
    """Test SwarmQuery initialization."""
    
    def test_explicit_project_ids(self):
        """Test initialization with explicit project list."""
        query = SwarmQuery(project_ids=["p1", "p2", "p3"])
        assert query._project_ids == ["p1", "p2", "p3"]
    
    def test_load_from_config(self, tmp_path):
        """Test loading projects from clawdia_prime config."""
        with patch('agents.clawdia_prime.skills.swarm_query.query.get_project_root') as mock_root:
            mock_root.return_value = tmp_path
            
            # Create config
            config_dir = tmp_path / "agents" / "clawdia_prime" / "agent"
            config_dir.mkdir(parents=True)
            config = {"projects": ["proj-a", "proj-b"]}
            (config_dir / "config.json").write_text(json.dumps(config))
            
            query = SwarmQuery()
            assert query._project_ids == ["proj-a", "proj-b"]
    
    def test_discover_from_directory(self, tmp_path):
        """Test discovering projects from projects/ directory."""
        with patch('agents.clawdia_prime.skills.swarm_query.query.get_project_root') as mock_root:
            mock_root.return_value = tmp_path
            
            # Create projects directory
            projects_dir = tmp_path / "projects"
            projects_dir.mkdir()
            (projects_dir / "proj-x").mkdir()
            (projects_dir / "proj-y").mkdir()
            (projects_dir / "_ignored").mkdir()  # Should be ignored
            
            query = SwarmQuery()
            assert query._project_ids == ["proj-x", "proj-y"]


class TestSwarmQueryCache:
    """Test caching behavior."""
    
    def test_cache_hit(self):
        """Test that cached results are returned within TTL."""
        query = SwarmQuery(project_ids=["test"])
        
        # Manually populate cache
        snapshot = ProjectSnapshot(project_id="test")
        query._cache["test"] = (snapshot, time.time())
        
        # Should return cached value without reading state
        with patch.object(query, '_read_project_state') as mock_read:
            result = query.get_project_status("test")
            assert result is snapshot
            mock_read.assert_not_called()
    
    def test_cache_expired(self):
        """Test that expired cache triggers re-read."""
        query = SwarmQuery(project_ids=["test"])
        query._cache_ttl = 0.1  # Short TTL for testing
        
        # Populate cache with old timestamp
        snapshot = ProjectSnapshot(project_id="test")
        query._cache["test"] = (snapshot, time.time() - 1.0)
        
        # Cache should be expired
        assert query._get_cached_snapshot("test") is None
    
    def test_invalidate_cache_single(self):
        """Test invalidating cache for single project."""
        query = SwarmQuery(project_ids=["p1", "p2"])
        query._cache["p1"] = (ProjectSnapshot("p1"), time.time())
        query._cache["p2"] = (ProjectSnapshot("p2"), time.time())
        
        query.invalidate_cache("p1")
        
        assert "p1" not in query._cache
        assert "p2" in query._cache
    
    def test_invalidate_cache_all(self):
        """Test invalidating all cache."""
        query = SwarmQuery(project_ids=["p1", "p2"])
        query._cache["p1"] = (ProjectSnapshot("p1"), time.time())
        query._cache["p2"] = (ProjectSnapshot("p2"), time.time())
        
        query.invalidate_cache()
        
        assert len(query._cache) == 0


class TestHealthScoring:
    """Test health score computation."""
    
    def test_perfect_health(self):
        """Test health score for healthy project."""
        query = SwarmQuery()
        snapshot = ProjectSnapshot(
            project_id="test",
            active_tasks=1,
            queued_tasks=2,
            failed_tasks=0
        )
        score = query._compute_health_score(snapshot)
        assert score == 1.0
    
    def test_at_capacity(self):
        """Test health penalty for at-capacity."""
        query = SwarmQuery()
        snapshot = ProjectSnapshot(
            project_id="test",
            active_tasks=3,  # At typical max_concurrent
            queued_tasks=0,
            failed_tasks=0
        )
        score = query._compute_health_score(snapshot)
        assert score == 0.7  # 1.0 - 0.3
    
    def test_high_backlog(self):
        """Test health penalty for high backlog."""
        query = SwarmQuery()
        snapshot = ProjectSnapshot(
            project_id="test",
            active_tasks=0,
            queued_tasks=6,  # > 5
            failed_tasks=0
        )
        score = query._compute_health_score(snapshot)
        assert score == 0.7  # 1.0 - 0.3
    
    def test_failures(self):
        """Test health penalty for failures."""
        query = SwarmQuery()
        snapshot = ProjectSnapshot(
            project_id="test",
            active_tasks=0,
            queued_tasks=0,
            failed_tasks=1
        )
        score = query._compute_health_score(snapshot)
        assert score == 0.7  # 1.0 - 0.3
    
    def test_multiple_penalties(self):
        """Test health penalties stack."""
        query = SwarmQuery()
        snapshot = ProjectSnapshot(
            project_id="test",
            active_tasks=3,   # -0.3
            queued_tasks=6,   # -0.3
            failed_tasks=1    # -0.3
        )
        score = query._compute_health_score(snapshot)
        assert score == 0.1  # 1.0 - 0.3 - 0.3 - 0.3
    
    def test_health_floor(self):
        """Test health score cannot go below 0."""
        query = SwarmQuery()
        snapshot = ProjectSnapshot(
            project_id="test",
            active_tasks=10,
            queued_tasks=20,
            failed_tasks=5
        )
        score = query._compute_health_score(snapshot)
        assert score == 0.0


class TestReadOnlySafety:
    """Test that SwarmQuery is truly read-only."""
    
    def test_no_write_methods(self):
        """Verify SwarmQuery has no write methods."""
        query = SwarmQuery()
        
        # Get all public methods
        methods = [m for m in dir(query) if not m.startswith('_')]
        
        # Should only have read/query methods
        read_methods = {
            'get_project_status',
            'get_swarm_overview',
            'find_stalled_tasks',
            'get_health_score',
            'invalidate_cache',
        }
        
        # Check no write-sounding methods exist
        write_sounding = {'write', 'update', 'create', 'delete', 'modify', 'set', 'add', 'remove'}
        for method in methods:
            for ws in write_sounding:
                assert ws not in method.lower(), f"Method '{method}' sounds like a write operation"


class TestConcurrency:
    """Test concurrent read safety."""
    
    def test_concurrent_reads(self, tmp_path):
        """Test multiple threads can read simultaneously."""
        # Create a state file
        state_file = tmp_path / "workspace-state.json"
        state = {
            "version": "1.0.0",
            "protocol": "jarvis",
            "tasks": {
                f"task-{i}": {
                    "status": "in_progress",
                    "skill_hint": "code",
                    "activity_log": [{"timestamp": time.time(), "status": "in_progress", "entry": "Test"}],
                    "created_at": time.time(),
                    "updated_at": time.time()
                }
                for i in range(10)
            },
            "metadata": {"created_at": time.time(), "last_updated": time.time()}
        }
        state_file.write_text(json.dumps(state))
        
        query = SwarmQuery(project_ids=["test"])
        results = []
        
        def reader():
            with patch('agents.clawdia_prime.skills.swarm_query.query.get_state_path') as mock_path:
                mock_path.return_value = state_file
                snapshot = query.get_project_status("test", use_cache=False)
                results.append(snapshot)
        
        # Spawn multiple readers
        threads = [threading.Thread(target=reader) for _ in range(5)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()
        
        # All should succeed
        assert len(results) == 5
        for snapshot in results:
            assert snapshot is not None
            assert snapshot.project_id == "test"
            assert len(snapshot.tasks) == 10


class TestStalledDetection:
    """Test stalled task detection."""
    
    def test_find_stalled_tasks(self):
        """Test finding stalled tasks across projects."""
        now = time.time()
        
        # Create mock snapshots
        snapshot1 = ProjectSnapshot(project_id="p1")
        snapshot1.tasks = {
            "active": TaskInfo("active", "in_progress", "code", now - 3600, now - 60),
            "stalled": TaskInfo("stalled", "in_progress", "code", now - 3600, now - 3600),
        }
        
        snapshot2 = ProjectSnapshot(project_id="p2")
        snapshot2.tasks = {
            "also_stalled": TaskInfo("also_stalled", "starting", "test", now - 3600, now - 7200),
        }
        
        query = SwarmQuery(project_ids=["p1", "p2"])
        
        with patch.object(query, 'get_project_status') as mock_get:
            mock_get.side_effect = lambda pid, **kw: {
                "p1": snapshot1,
                "p2": snapshot2,
            }.get(pid)
            
            stalled = query.find_stalled_tasks(threshold_minutes=30)
            
            assert "p1" in stalled
            assert "p2" in stalled
            assert len(stalled["p1"]) == 1
            assert stalled["p1"][0].task_id == "stalled"
            assert len(stalled["p2"]) == 1
            assert stalled["p2"][0].task_id == "also_stalled"


class TestSwarmOverview:
    """Test swarm overview aggregation."""
    
    def test_overview_aggregation(self):
        """Test that overview aggregates correctly."""
        query = SwarmQuery(project_ids=["p1", "p2"])
        
        # Create mock snapshots
        snapshot1 = ProjectSnapshot(
            project_id="p1",
            active_tasks=2,
            queued_tasks=1,
            completed_tasks=5,
            failed_tasks=0,
            health_score=0.7
        )
        snapshot2 = ProjectSnapshot(
            project_id="p2",
            active_tasks=3,
            queued_tasks=6,  # High backlog
            completed_tasks=2,
            failed_tasks=1,
            health_score=0.4
        )
        
        with patch.object(query, 'get_project_status') as mock_get:
            mock_get.side_effect = lambda pid, **kw: {
                "p1": snapshot1,
                "p2": snapshot2,
            }.get(pid)
            
            overview = query.get_swarm_overview()
            
            assert overview.total_active == 5
            assert overview.total_queued == 7
            assert overview.total_completed == 7
            assert overview.total_failed == 1
            assert overview.total_tasks == 20
            assert "p2" in overview.bottleneck_projects
            assert "p1" not in overview.bottleneck_projects
