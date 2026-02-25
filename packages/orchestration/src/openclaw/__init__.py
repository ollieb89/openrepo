"""
OpenClaw Orchestration Package

Public API for the Jarvis Protocol state engine, project configuration,
git snapshot workflow, SOUL renderer, and workspace initialization.

External consumers (L3 containers, CLI tools, dashboard) should import
from this package root. Internal cross-module code should use direct
submodule imports (e.g., `from openclaw.config import X`).
"""

from .state_engine import JarvisState
from .config import LOCK_TIMEOUT, POLL_INTERVAL, get_state_path, get_snapshot_dir
from .init import initialize_workspace, verify_workspace
from .project_config import (
    load_project_config,
    load_and_validate_openclaw_config,
    get_workspace_path,
    get_tech_stack,
    get_agent_mapping,
    get_active_project_id,
    get_pool_config,
    ProjectNotFoundError,
)
from .config_validator import validate_project_config, validate_agent_hierarchy, ConfigValidationError
from .snapshot import (
    create_staging_branch,
    capture_semantic_snapshot,
    l2_review_diff,
    l2_merge_staging,
    l2_reject_staging,
    cleanup_old_snapshots,
    GitOperationError,
)
from .soul_renderer import render_soul, write_soul
from .logging import get_logger
from .autonomy import (
    AutonomyState,
    AutonomyContext,
    StateMachine,
    AutonomyReporter,
)

__all__ = [
    # State engine
    'JarvisState',

    # Config constants
    'LOCK_TIMEOUT', 'POLL_INTERVAL',

    # Logging
    'get_logger',

    # Autonomy framework
    'AutonomyState', 'AutonomyContext', 'StateMachine', 'AutonomyReporter',

    # Workspace lifecycle
    'initialize_workspace', 'verify_workspace',

    # Project configuration
    'load_project_config', 'load_and_validate_openclaw_config',
    'get_workspace_path', 'get_tech_stack',
    'get_agent_mapping', 'get_active_project_id',
    'get_state_path', 'get_snapshot_dir', 'get_pool_config', 'ProjectNotFoundError',

    # Config validation
    'validate_project_config', 'validate_agent_hierarchy', 'ConfigValidationError',

    # Git snapshot workflow
    'create_staging_branch', 'capture_semantic_snapshot',
    'l2_review_diff', 'l2_merge_staging', 'l2_reject_staging',
    'cleanup_old_snapshots', 'GitOperationError',

    # SOUL renderer
    'render_soul', 'write_soul',
]
