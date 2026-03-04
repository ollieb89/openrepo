FROM debian:bookworm-slim

LABEL openclaw.component="base"
LABEL openclaw.variant="bookworm-slim"

ENV DEBIAN_FRONTEND=noninteractive

RUN apt-get update \
  && apt-get install -y --no-install-recommends \
    bash \
    ca-certificates \
    curl \
    git \
    jq \
    python3 \
    ripgrep \
  && rm -rf /var/lib/apt/lists/*

RUN useradd --uid 1000 --create-home --shell /bin/bash sandbox
USER sandbox
WORKDIR /home/sandbox
