# Agent CLI Contract

## Overview

This document defines the interface every agent must implement to participate in the coding benchmark harness. The contract is strict: the harness makes no accommodations for non-conforming agents. An agent that deviates from any requirement below will produce incorrect results or cause the benchmark run to fail.

---

## Agent Repo Layout

Each agent lives in its own directory (or repository) with the following required files:

```
<agent-repo>/
  setup.sh        # installs the agent into the container; receives no arguments
  run.sh          # implements the benchmark run
  .env.template   # lists required env var names (one per line, values injected by harness)
```

All three files must be present. The harness will not proceed if any are missing.

---

## setup.sh

`setup.sh` is called once before any task starts. It installs the agent — dependencies, binaries, configuration — into the container.

Requirements:

- Receives **no arguments**
- Must **exit 0** on success
- Any non-zero exit code causes the harness to abort the entire run

---

## run.sh CLI Signature

```
./run.sh --task-dir <path> --timeout <seconds> --language <python|go|rust> --difficulty <easy|medium|hard>
```

| Argument | Description |
|---|---|
| `--task-dir <path>` | Absolute path to the task directory inside the sandbox. The agent uses this to locate `/sandbox/repo/`, `/sandbox/tests/`, and `/sandbox/prompt.md`. |
| `--timeout <seconds>` | Maximum wall-clock seconds the agent should run before giving up. The harness enforces a hard kill at this boundary; the agent should respect it voluntarily and exit before being killed. |
| `--language <python\|go\|rust>` | Programming language of the task source code. |
| `--difficulty <easy\|medium\|hard>` | Difficulty tier of the task, which corresponds directly to the timeout value (see Tiered Timeouts below). |

---

## Exit Codes

| Code | Meaning |
|---|---|
| `0` | Agent believes the task is complete |
| `1` | Agent gave up or encountered an unrecoverable error |
| `124` | Agent timed out (the harness also enforces a hard kill at the timeout boundary) |

Any exit code other than `0`, `1`, or `124` is treated as an error.

---

## Stdout — Metrics JSON

The agent must emit a single JSON object on **stdout** at exit:

```json
{"steps": 12, "tokens": 4821}
```

| Field | Description |
|---|---|
| `steps` | Number of edit/action steps the agent took |
| `tokens` | Total tokens consumed during the run |

Both fields are optional. Missing fields are recorded as `null` by the harness.

**No other output should be written to stdout.** Use stderr for all logging, debugging, and diagnostic output. Extraneous stdout content will corrupt metrics parsing.

---

## Sandbox Environment

When `run.sh` executes, the agent is inside a container with the following layout:

| Path | Description |
|---|---|
| `/sandbox/repo/` | Writable copy of the task source code. The agent makes all edits here. |
| `/sandbox/tests/` | Example test suite the agent can run to get feedback on its solution. |
| `/sandbox/prompt.md` | Natural language description of the task. |
| `/agent/` | The agent repo itself (read-only). |

**Network:** Outbound access is restricted to `api.anthropic.com` only. All other outbound connections will be blocked.

---

## Tiered Timeouts

The `--timeout` argument passed to `run.sh` reflects the difficulty tier:

| Difficulty | Timeout |
|---|---|
| `easy` | 300 seconds |
| `medium` | 600 seconds |
| `hard` | 1200 seconds |

The harness enforces a hard kill at the timeout boundary regardless of what the agent does. Agents should monitor elapsed time and exit cleanly (with an appropriate exit code and metrics JSON) before the deadline.

---

## Reference Implementation

`agents/stub/` is the minimal conforming agent. It implements all three required files:

- `setup.sh` — no-op, exits 0
- `run.sh` — emits `{"steps": 0, "tokens": 0}` and exits 0 without modifying any files
- `.env.template` — empty (the stub requires no environment variables)

Use the stub to verify harness plumbing before integrating a real agent.
