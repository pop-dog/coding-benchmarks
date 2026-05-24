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

---

## Generating New Tasks

`tools/generate_task.py` is a standalone utility that calls the Claude API to
draft a complete benchmark task directory.  It is not part of the runtime
harness and is intended for use by task authors.

### Setup

```bash
pip install -r tools/requirements.txt
export ANTHROPIC_API_KEY=sk-...
```

### Usage

```bash
python tools/generate_task.py \
  --language python \
  --difficulty easy \
  --category "off-by-one bug" \
  --output benchmark/v1.0/tasks/python/easy/task_002
```

| Flag | Required | Description |
|------|----------|-------------|
| `--language` | yes | `python`, `go`, or `rust` |
| `--difficulty` | yes | `easy`, `medium`, or `hard` |
| `--category` | yes | Bug category (see rubrics below) |
| `--output` | yes | Path to the new task directory (must not exist) |
| `--dry-run` | no | Print the LLM prompt and exit without calling the API |

### Difficulty rubrics

| Tier | Files changed | Typical bug types |
|------|--------------|-------------------|
| easy | 1 | off-by-one, wrong conditional, missing return |
| medium | 1–3 | non-obvious boundary condition, partially-implemented feature |
| hard | 3+ | cross-cutting concern, integration bug, interacting defects |

### Language-appropriate bug categories

| Language | Categories |
|----------|-----------|
| python | off-by-one, wrong conditional, missing return, incorrect slice, type error |
| go | concurrency bug (race condition), wrong error handling, nil pointer, goroutine leak |
| rust | borrow checker violation, wrong lifetime, off-by-one, incorrect iterator usage |

### Output layout

The script creates the following files under `--output`:

```
<output>/
  repo/<module>.py          # source with the seeded bug
  repo/README.md            # module documentation (no spoilers)
  prompt.md                 # problem description shown to the agent
  tests/test_<module>.py    # example tests (fail on buggy repo, visible to agent)
  eval_tests/test_<module>_eval.py  # thorough eval tests (hidden from agent)
```

### Human review checklist

After generating a task, verify the following before committing:

- [ ] `pytest <output>/tests/` **fails** against the unmodified repo
- [ ] `pytest <output>/eval_tests/` **fails** against the unmodified repo
- [ ] Both test suites **pass** after applying the correct fix
- [ ] The problem is solvable within the tiered timeout for its difficulty
- [ ] The difficulty rubric is met (number of files changed, bug complexity)
- [ ] `prompt.md` clearly describes the observed failure symptom without revealing the fix or the affected line
