import os

# Lock configuration
LOCK_TIMEOUT = 5  # seconds
LOCK_RETRY_ATTEMPTS = 3

# Polling configuration
POLL_INTERVAL = 1.0  # seconds

# Logging configuration
LOG_LEVEL = os.environ.get("OPENCLAW_LOG_LEVEL", "INFO").upper()
