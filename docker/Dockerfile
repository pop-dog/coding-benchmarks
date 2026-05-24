FROM ubuntu:22.04

# Prevent interactive prompts during package installation
ENV DEBIAN_FRONTEND=noninteractive

# ── System packages ─────────────────────────────────────────────────────────
RUN apt-get update && apt-get install -y --no-install-recommends \
    ca-certificates \
    curl \
    wget \
    git \
    build-essential \
    python3 \
    python3-pip \
    python3-venv \
    && rm -rf /var/lib/apt/lists/*

# ── Python / pytest ──────────────────────────────────────────────────────────
RUN pip3 install --no-cache-dir pytest

# ── Go (latest stable from official tarball) ─────────────────────────────────
ENV GO_VERSION=1.23.4
RUN wget -q "https://go.dev/dl/go${GO_VERSION}.linux-amd64.tar.gz" -O /tmp/go.tar.gz \
    && tar -C /usr/local -xzf /tmp/go.tar.gz \
    && rm /tmp/go.tar.gz

ENV PATH="/usr/local/go/bin:${PATH}"
ENV GOPATH="/go"
ENV PATH="${GOPATH}/bin:${PATH}"

# ── Rust / Cargo (via rustup, non-interactive) ───────────────────────────────
ENV RUSTUP_HOME=/usr/local/rustup
ENV CARGO_HOME=/usr/local/cargo
ENV PATH="/usr/local/cargo/bin:${PATH}"

RUN curl --proto '=https' --tlsv1.2 -sSf https://sh.rustup.rs \
    | sh -s -- -y --no-modify-path --default-toolchain stable \
    && rustup component add rustfmt clippy

# ── Node.js v20.x (via NodeSource) ───────────────────────────────────────────
RUN curl -fsSL https://deb.nodesource.com/setup_20.x | bash - \
    && apt-get install -y --no-install-recommends nodejs \
    && rm -rf /var/lib/apt/lists/*

# ── Claude Code CLI ───────────────────────────────────────────────────────────
RUN npm install -g @anthropic-ai/claude-code

# ── Default working directory ─────────────────────────────────────────────────
WORKDIR /sandbox

CMD ["/bin/bash"]
