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

# Switch to non-root user
USER l3worker

ENTRYPOINT ["bash", "/entrypoint.sh"]
