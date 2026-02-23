import os
from pathlib import Path

# DEPRECATED: Use orchestration.project_config.get_state_path() instead.
# Retained for backward compatibility. Will be removed in Phase 13.
STATE_FILE = Path(os.environ.get(
    'OPENCLAW_STATE_FILE',
    'workspace/.openclaw/workspace-state.json',
))

# Lock configuration
LOCK_TIMEOUT = 5  # seconds
LOCK_RETRY_ATTEMPTS = 3

# Polling configuration
POLL_INTERVAL = 1.0  # seconds

# DEPRECATED: Use orchestration.project_config.get_snapshot_dir() instead.
# Retained for backward compatibility. Will be removed in Phase 13.
SNAPSHOT_DIR = Path(os.environ.get(
    'OPENCLAW_SNAPSHOT_DIR',
    'workspace/.openclaw/snapshots/',
))
