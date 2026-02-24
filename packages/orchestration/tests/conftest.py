"""
Test configuration for orchestration tests.

Adds the project root to sys.path so that imports from skills/spawn_specialist/
work (since skills/ is not a proper package yet).

Also adds the docker/memory path for scan_engine imports.
"""
import sys
from pathlib import Path

# Project root: /home/ollie/.openclaw
PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent.parent

# Allow imports from skills/spawn_specialist/ (e.g., `from spawn import ...`, `from pool import ...`)
_skills_spawn_dir = PROJECT_ROOT / "skills" / "spawn_specialist"
if str(_skills_spawn_dir) not in sys.path:
    sys.path.insert(0, str(_skills_spawn_dir))

# Allow imports from docker/memory/ (e.g., `from memory_service.scan_engine import ...`)
_docker_memory_dir = PROJECT_ROOT / "docker" / "memory"
if str(_docker_memory_dir) not in sys.path:
    sys.path.insert(0, str(_docker_memory_dir))

# Allow imports from docker/memory/memory_service/ (e.g., `from routers.retrieve import _filter_after`)
_docker_memory_service_dir = PROJECT_ROOT / "docker" / "memory" / "memory_service"
if str(_docker_memory_service_dir) not in sys.path:
    sys.path.insert(0, str(_docker_memory_service_dir))
