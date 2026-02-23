import os
from pathlib import Path

# State file location — override with OPENCLAW_STATE_FILE env var
STATE_FILE = Path(os.environ.get(
    'OPENCLAW_STATE_FILE',
    'workspace/.openclaw/workspace-state.json',
))

# Lock configuration
LOCK_TIMEOUT = 5  # seconds
LOCK_RETRY_ATTEMPTS = 3

# Polling configuration
POLL_INTERVAL = 1.0  # seconds

# Snapshot directory — override with OPENCLAW_SNAPSHOT_DIR env var
SNAPSHOT_DIR = Path(os.environ.get(
    'OPENCLAW_SNAPSHOT_DIR',
    'workspace/.openclaw/snapshots/',
))
