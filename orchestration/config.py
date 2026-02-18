from pathlib import Path

# State file location (relative to project root)
STATE_FILE = Path('workspace/.openclaw/workspace-state.json')

# Lock configuration
LOCK_TIMEOUT = 5  # seconds
LOCK_RETRY_ATTEMPTS = 3

# Polling configuration
POLL_INTERVAL = 1.0  # seconds

# Snapshot directory
SNAPSHOT_DIR = Path('workspace/.openclaw/snapshots/')
