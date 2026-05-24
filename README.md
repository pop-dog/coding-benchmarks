# AI Coding Agent Benchmark Suite

A self-hosted benchmark that evaluates custom AI coding agents on multi-step agentic tasks across Python, Go, and Rust at three difficulty tiers.

---

## Getting Started

### Prerequisites

- [Docker](https://docs.docker.com/get-docker/) installed and running on your host machine.

### Build the base image

All benchmark task containers share a single base image (`benchmark-base:latest`) that bundles every required toolchain. Build it once before running any benchmark tasks.

```bash
bash docker/build.sh
```

`build.sh` performs two steps:

1. Runs `docker build` and tags the resulting image as `benchmark-base:latest`.
2. Spins up a temporary container and runs `docker/verify.sh` inside it, which checks that every toolchain (python3, pytest, go, rustc, cargo, node, npm, claude) is functional. The script exits 0 on success and prints a per-tool pass/fail table.

### Verify the image manually

If you want to re-run the toolchain checks without rebuilding:

```bash
docker run --rm \
  --volume "$(pwd)/docker/verify.sh:/verify.sh:ro" \
  benchmark-base:latest \
  /bin/bash /verify.sh
```

### What the image contains

| Tool | Source |
|------|--------|
| Python 3 + pip + pytest | Ubuntu 22.04 apt + pip |
| Go (stable) | Official tarball from go.dev/dl |
| Rust + Cargo | rustup (stable toolchain) |
| Node.js v20.x + npm | NodeSource apt repository |
| Claude Code CLI | `npm install -g @anthropic-ai/claude-code` |

---

## Repository layout

```
coding-benchmarks/
  docker/
    Dockerfile     # defines benchmark-base:latest
    build.sh       # build + verify convenience script
    verify.sh      # toolchain health checks (runs inside the image)
  benchmark/
    v1.0/
      tasks/
        python/easy|medium|hard/task_NNN/
        go/easy|medium|hard/task_NNN/
        rust/easy|medium|hard/task_NNN/
  results/         # gitignored — written by the harness at runtime
  PRD.md           # full product requirements and design decisions
```

---

## Running the benchmark

Full harness usage will be documented once the harness module is implemented. See `PRD.md` for the complete design.
