"""
Test configuration for orchestration tests.

Adds the project root to sys.path so that imports from skills/spawn/
work (since skills/ is not a proper package yet).

Also adds the docker/memory path for scan_engine imports.
"""
import sys
from pathlib import Path

# Project root: /home/ollie/.openclaw
PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent.parent

# Allow imports from skills/spawn/ (e.g., `from spawn import ...`, `from pool import ...`)
_skills_spawn_dir = PROJECT_ROOT / "skills" / "spawn"
if str(_skills_spawn_dir) not in sys.path:
    sys.path.insert(0, str(_skills_spawn_dir))

# Allow imports from docker/memory/ (e.g., `from memory_service.scan_engine import ...`)
_docker_memory_dir = PROJECT_ROOT / "docker" / "memory"
_packages_memory_dir = PROJECT_ROOT / "packages" / "memory"
for _d in (_docker_memory_dir, _packages_memory_dir):
    if _d.exists() and str(_d) not in sys.path:
        sys.path.insert(0, str(_d))

# Allow imports from docker/memory/memory_service/ or packages/memory equivalent
_docker_memory_service_dir = PROJECT_ROOT / "docker" / "memory" / "memory_service"
_packages_memory_service_dir = PROJECT_ROOT / "packages" / "memory" / "memory_service"
for _d in (_docker_memory_service_dir, _packages_memory_service_dir):
    if _d.exists() and str(_d) not in sys.path:
        sys.path.insert(0, str(_d))

import pytest


@pytest.fixture
def valid_openclaw_config():
    """Minimal valid openclaw.json dict matching OPENCLAW_JSON_SCHEMA. Tests copy and modify."""
    return {
        "gateway": {"port": 18789},
        "agents": {"list": []},
    }
