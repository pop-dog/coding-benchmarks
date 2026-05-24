# PRD: AI Coding Agent Benchmark Suite

## Problem Statement

As a developer building custom AI coding agents, I have no reliable way to measure whether my agents are improving over time or how they perform across different programming languages and task complexities. Existing benchmarks (SWE-bench, HumanEval) are either too large to run locally, test the wrong capabilities (code completion rather than agentic edit-run-debug loops), or cannot be targeted at a specific agent's skill set. I need a self-contained, reproducible benchmark I control and can run against any agent I build.

## Solution

A self-hosted benchmark suite that evaluates custom AI coding agents on multi-step agentic tasks across three programming languages and three difficulty tiers. Each task is a self-contained repository with a natural language prompt, an example test suite the agent can use as feedback during its work, and a hidden evaluation suite the harness uses to score the result. A Python harness orchestrates Docker containers, enforces per-task timeouts, and produces structured results in JSON and Markdown.

## User Stories

1. As a benchmark operator, I want to run the full 27-task suite against an agent with a single CLI command, so that I can get a complete picture of agent performance without manual steps.
2. As a benchmark operator, I want tasks isolated in fresh Docker containers, so that one task's side effects cannot influence another task's result.
3. As a benchmark operator, I want configurable parallelism (`--parallel N`), so that I can tune throughput against my API rate limits and host resources.
4. As a benchmark operator, I want tiered timeouts per difficulty (easy: 5 min, medium: 10 min, hard: 20 min), so that hard tasks get adequate time without letting stuck agents run indefinitely.
5. As a benchmark operator, I want binary pass/fail scoring as the primary metric, so that results are unambiguous and comparable across runs.
6. As a benchmark operator, I want secondary metrics (agent completion time, solution runtime, steps taken, tokens consumed) recorded per task, so that I can distinguish efficient agents from brute-force ones that happen to pass.
7. As a benchmark operator, I want results saved as JSON (source of truth) and auto-generated as a Markdown scorecard, so that I can read results at a glance and diff them programmatically.
8. As a benchmark operator, I want the benchmark versioned (`v1.0`, `v1.1`), so that I can track whether agent improvements are real or reflect overfitting to a known task set.
9. As a benchmark operator, I want `eval_tests/` never exposed to the agent, so that agents cannot game the benchmark by targeting the evaluation criteria directly.
10. As an agent author, I want a strict, documented CLI contract (`setup.sh` + `run.sh`), so that I can benchmark any agent that implements the interface without modifying the harness.
11. As an agent author, I want to control my own agent setup (`setup.sh`), so that I can install dependencies, configure Claude Code, and inject secrets without the harness needing to know my agent's internals.
12. As an agent author, I want my agent config (CLAUDE.md, skills) to live in a separate repo from the benchmark, so that I can benchmark multiple agent versions against the same stable task suite.
13. As a task author, I want a clear difficulty rubric (files touched + conceptual complexity), so that I can generate and calibrate tasks consistently across Python, Go, and Rust.
14. As a task author, I want tasks to be LLM-generated and human-reviewed, so that I can produce a large task corpus quickly without sacrificing quality.
15. As a task author, I want each task to include a small example test suite visible to the agent, so that the agent has a runnable feedback signal during its edit-run-debug loop.
16. As a task author, I want each task to include a separate hidden evaluation suite, so that scoring is independent of the feedback signal the agent used during the loop.
17. As a task author, I want tasks organized in a versioned directory tree (`tasks/<language>/<difficulty>/task_NNN/`), so that the benchmark suite is self-contained and navigable.
18. As a task author, I want task repos to contain realistic source code with language-appropriate bugs and features, so that agents are tested on real coding patterns rather than toy problems.
19. As a benchmark operator, I want the Docker base image to include Python + pytest, Go, and Rust/Cargo toolchains plus the Claude Code CLI, so that any task can run without per-task image builds.
20. As a benchmark operator, I want the harness to copy task files into a writable sandbox inside the container (not modify the benchmark source), so that the original task files remain pristine across runs.
21. As a benchmark operator, I want the harness to mount the agent repo into the container and run `setup.sh` before the task starts, so that agent installation is reproducible and the harness stays agent-agnostic.
22. As a benchmark operator, I want the agent's outbound network restricted to `api.anthropic.com`, so that agents cannot fetch solutions from the internet during a task.
23. As a benchmark operator, I want a task manifest that specifies which tasks to include in a run, so that I can run subsets (e.g., `--tasks python/easy`) without running the full suite.
24. As a benchmark operator, I want each run to record the benchmark version and agent version alongside results, so that I can attribute score changes to the right variable when comparing runs.

## Implementation Decisions

### Module: Benchmark Task Store
The task corpus is a versioned directory tree within the benchmark repo:
```
benchmark/
  v1.0/
    tasks/
      python/
        easy/task_001/ ... task_003/
        medium/task_001/ ... task_003/
        hard/task_001/ ... task_003/
      go/
        easy/ ... hard/
      rust/
        easy/ ... hard/
```
Each task directory contains: `repo/` (source code), `prompt.md` (natural language description), `tests/` (example suite visible to agent), `eval_tests/` (hidden evaluation suite). `eval_tests/` is never mounted into agent containers and should not be committed to any public remote.

### Module: Docker Harness
The harness is a Python module using the `docker` SDK. It is responsible for:
- Building/pulling the shared base image (Python + pytest, Go, Rust/Cargo, Node, Claude Code CLI)
- Spinning up a fresh container per task
- Copying `repo/`, `prompt.md`, and `tests/` into `/sandbox/` inside the container
- Mounting the agent repo at `/agent/` inside the container
- Injecting environment variables declared in the agent's `.env.template`
- Running `/agent/setup.sh` (agent self-installation)
- Running `/agent/run.sh --task-dir /sandbox --timeout N --language L --difficulty D`
- Enforcing the tiered timeout; recording exit code
- Running `eval_tests/` against `/sandbox/repo/` after agent exit
- Tearing down the container

### Module: Task Runner
Orchestrates parallel execution of tasks using a configurable worker pool (`--parallel N`, default 3). Dispatches tasks to the Docker Harness, collects results, and feeds them to the Metrics Collector. Handles timeout enforcement at the orchestration level as a backstop in addition to the per-container timeout.

### Module: Metrics Collector
Captures per-task secondary metrics:
- **Agent completion time**: wall-clock time from container start to agent exit
- **Solution runtime**: harness times the `eval_tests/` execution as a proxy for solution efficiency
- **Steps taken**: parsed from structured JSON the agent emits to stdout
- **Tokens consumed**: parsed from structured JSON the agent emits to stdout

Agents emit metrics as a single JSON object on stdout at exit:
```json
{"steps": 12, "tokens": 4821}
```
The harness captures stdout and merges this with its own timing measurements.

### Module: Results Reporter
Consumes the collected metrics and produces two artifacts:
- `results/run_<timestamp>.json`: complete machine-readable record (task id, language, difficulty, pass/fail, all secondary metrics, benchmark version, agent version, run timestamp)
- `results/run_<timestamp>.md`: human-readable scorecard with pass rate per language/difficulty cell and secondary metric summaries

### Module: Task Generator (tooling, not runtime)
A standalone utility (not part of the harness) for generating new tasks using an LLM. Takes a language, difficulty tier, and problem category as input; produces a draft task directory for human review. Human reviewer validates: example tests fail against the original repo, eval tests are non-trivial, the problem is solvable, and difficulty rubric is met.

### Agent CLI Contract
Any agent that implements the following interface can be benchmarked:

**Agent repo layout:**
```
<agent-repo>/
  setup.sh        # installs agent into container; receives no arguments
  run.sh          # implements benchmark run; receives CLI args below
  .env.template   # lists required env var names (values injected by harness)
```

**run.sh CLI signature:**
```
./run.sh --task-dir <path> --timeout <seconds> --language <python|go|rust> --difficulty <easy|medium|hard>
```

**Exit codes:** `0` = agent believes task is complete, `1` = agent gave up, `124` = timeout.

**Stdout:** single JSON object with steps and tokens at exit (see Metrics Collector above).

The contract is strict. Agents that do not conform are not benchmarkable. The harness makes no accommodations for non-conforming agents.

### Difficulty Rubric
- **Easy**: 1 file changed, clear bug with an obvious failure mode (off-by-one, wrong conditional, missing return)
- **Medium**: 1–3 files changed, non-obvious bug or missing feature implementation (cross-function logic, edge case, error handling)
- **Hard**: 3+ files changed, cross-cutting concern or multi-component integration bug (concurrency bugs in Go, borrow checker violations in Rust, architectural misuse)

### Task Grid (v1.0)
3 languages × 3 difficulty tiers × 3 tasks per cell = **27 tasks total**.

### Versioning
Benchmark task sets are versioned directories (`v1.0/`, `v1.1/`). New versions add tasks; existing tasks are not modified. The harness records which benchmark version was used in every results file. `eval_tests/` directories are never published to public remotes.

### Network Policy
Agent containers are allowed outbound access to `api.anthropic.com` only. No other outbound access is permitted.

## Testing Decisions

A good test for this system verifies observable external behavior — what the harness produces — not internal implementation details like which Docker API calls were made. Tests should be deterministic and not require a live Anthropic API key.

**Modules to test:**

- **Docker Harness**: Use a stub agent (`setup.sh` is a no-op, `run.sh` writes a known file and exits 0) and a stub task (repo with a trivially passing eval test). Verify the harness correctly records pass, measures timing, and tears down the container. Test timeout enforcement with a `run.sh` that sleeps past the timeout.
- **Task Runner**: Test that `--parallel N` dispatches N tasks concurrently and that all results are collected correctly.
- **Metrics Collector**: Test JSON parsing from agent stdout, including missing/malformed fields (should degrade gracefully, not crash).
- **Results Reporter**: Given a fixture of known task results, verify the JSON output schema and Markdown scorecard content.
- **Task Generator**: Not tested automatically — human review is the validation step.

## Out of Scope

- Public leaderboard or web UI for results
- Support for languages beyond Python, Go, and Rust in v1.0
- Per-task Docker images (all tasks share the base image in v1.0)
- LLM-as-judge or human evaluation as a scoring mechanism
- Partial credit scoring
- Tasks that require internet access during the agent's edit-run-debug loop
- Integration with external CI systems
- Automatic task rotation or procedural generation

## Further Notes

- The benchmark is intentionally personal and private. `eval_tests/` should never be committed to a public remote. Consider a `.gitignore` rule and a separate private store (e.g., private S3 bucket or private git submodule) for eval tests.
- The 3×3 grid conflates language difficulty with task complexity (Go = Hard, Rust = Medium, Python = Easy by language choice). This is acceptable for v1.0 but means you cannot independently attribute performance differences to language vs. task complexity. Consider adding cross-tier tasks in v2.0 to decouple this.
- Claude Code requires `ANTHROPIC_API_KEY` and outbound network access to `api.anthropic.com`. Running many parallel agents simultaneously may hit Anthropic rate limits — start with `--parallel 3` and tune from there.
- Worst-case full-suite runtime at `--parallel 3`: approximately 105 minutes (9 easy × 5 min + 9 medium × 10 min + 9 hard × 20 min, divided by 3 parallel workers).
- The Task Generator utility is separate from the benchmark runtime and is not on the critical path for v1.0. Tasks can be hand-crafted initially and the generator added later.
