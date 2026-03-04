ARG BASE_IMAGE=openclaw-base:bookworm-slim
FROM ${BASE_IMAGE}

# Switch to root for package installation (sandbox base runs as non-root)
USER root

# Install L3-specific dependencies not in the sandbox base
RUN apt-get update && apt-get install -y --no-install-recommends \
    python3-pip \
    && rm -rf /var/lib/apt/lists/*

# Install Python dependencies required by the openclaw package (volume-mounted at runtime)
RUN pip3 install --no-cache-dir --break-system-packages \
    jsonschema>=4.26.0

# Create L3 worker user (UID 1000 to match host volume permissions).
# The sandbox base already creates a 'sandbox' user at UID 1000, so we
# rename it to 'l3worker' for L3 identity consistency.
RUN usermod -l l3worker -d /home/l3worker -m sandbox \
    && groupmod -n l3worker sandbox

# Set working directory
WORKDIR /workspace

# Copy entrypoint
COPY entrypoint.sh /entrypoint.sh
RUN chmod +x /entrypoint.sh

# Labels for tracking
LABEL openclaw.tier="l3"
LABEL openclaw.component="specialist"
LABEL openclaw.base="openclaw-base:bookworm-slim"

# Health check — verifies container entrypoint has completed initialization.
# Sentinel file /tmp/openclaw-healthy is written by entrypoint.sh after startup.
# cap_drop ALL safe: uses /bin/sh -c "test ..." (shell builtin, no capabilities needed).
# start_period=30s gives the entrypoint time to configure git, checkout branch, and write the sentinel.
HEALTHCHECK --interval=30s --timeout=5s --retries=3 --start-period=30s \
    CMD test -f /tmp/openclaw-healthy || exit 1

# Switch to non-root user
USER l3worker

ENTRYPOINT ["bash", "/entrypoint.sh"]
