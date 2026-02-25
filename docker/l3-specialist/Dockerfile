FROM debian:bookworm-slim

# Install essentials for code/test tasks
RUN apt-get update && apt-get install -y \
    git \
    python3 \
    python3-pip \
    curl \
    jq \
    && rm -rf /var/lib/apt/lists/*

# Create non-root user (UID 1000 to match host)
RUN useradd -m -u 1000 -s /bin/bash l3worker

# Copy orchestration package (will be mounted as volume in practice)
# This is a placeholder - the actual orchestration package is mounted at runtime

# Set working directory
WORKDIR /workspace

# Copy entrypoint
COPY entrypoint.sh /entrypoint.sh
RUN chmod +x /entrypoint.sh

# Labels for tracking
LABEL openclaw.tier="l3"
LABEL openclaw.component="specialist"

# Health check — verifies container entrypoint has completed initialization.
# Sentinel file /tmp/openclaw-healthy is written by entrypoint.sh after startup.
# cap_drop ALL safe: uses /bin/sh -c "test ..." (shell builtin, no capabilities needed).
# start_period=30s gives the entrypoint time to configure git, checkout branch, and write the sentinel.
HEALTHCHECK --interval=30s --timeout=5s --retries=3 --start-period=30s \
    CMD test -f /tmp/openclaw-healthy || exit 1

# Switch to non-root user
USER l3worker

ENTRYPOINT ["bash", "/entrypoint.sh"]
