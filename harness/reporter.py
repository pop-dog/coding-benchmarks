"""
reporter.py — Results reporting for the benchmark harness.

Provides two public functions:

- ``write_json``     — writes a JSON file with run metadata and per-task records.
- ``write_markdown`` — writes a Markdown scorecard with a pass-rate table and a
                       per-task metrics summary.
"""

from __future__ import annotations

import json
from datetime import datetime, timezone
from typing import List

from .models import TaskResult

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

LANGUAGES = ["python", "go", "rust"]
DIFFICULTIES = ["easy", "medium", "hard"]

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _now_iso() -> str:
    """Return the current UTC time as an ISO 8601 string."""
    return datetime.now(tz=timezone.utc).isoformat()


def _result_to_record(result: TaskResult) -> dict:
    """Flatten a TaskResult (including its TaskMetrics) into a plain dict."""
    return {
        "task_id": result.task_id,
        "language": result.language,
        "difficulty": result.difficulty,
        "passed": result.passed,
        "exit_code": result.exit_code,
        "timed_out": result.timed_out,
        "agent_stdout": result.agent_stdout,
        "agent_stderr": result.agent_stderr,
        "agent_completion_time_s": result.metrics.agent_completion_time_s,
        "eval_runtime_s": result.metrics.eval_runtime_s,
        "steps": result.metrics.steps,
        "tokens": result.metrics.tokens,
    }


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def write_json(
    results: List[TaskResult],
    output_path: str,
    benchmark_version: str,
    agent_version: str,
) -> None:
    """Write a JSON results file.

    The file contains:
    - ``timestamp``         — ISO 8601 UTC timestamp of the run.
    - ``benchmark_version`` — caller-supplied benchmark version string.
    - ``agent_version``     — caller-supplied agent version string.
    - ``tasks``             — list of per-task records with all TaskResult and
                              TaskMetrics fields flattened into a single object.

    Parameters
    ----------
    results:
        List of TaskResult objects from the harness.
    output_path:
        Destination file path (will be created or overwritten).
    benchmark_version:
        Version string for the benchmark suite (e.g. ``"v1.0"``).
    agent_version:
        Version string for the agent under test (e.g. ``"stub-0.1"``).
    """
    payload = {
        "timestamp": _now_iso(),
        "benchmark_version": benchmark_version,
        "agent_version": agent_version,
        "tasks": [_result_to_record(r) for r in results],
    }
    with open(output_path, "w", encoding="utf-8") as fh:
        json.dump(payload, fh, indent=2)


def write_markdown(
    results: List[TaskResult],
    output_path: str,
    benchmark_version: str,
    agent_version: str,
) -> None:
    """Write a Markdown scorecard.

    The scorecard contains:
    1. Run metadata (timestamp, benchmark_version, agent_version, overall pass rate).
    2. A 3×3 pass-rate table (rows = language, cols = difficulty) showing
       "X/N passed" for each cell.
    3. A per-task metrics summary table.

    Parameters
    ----------
    results:
        List of TaskResult objects from the harness.
    output_path:
        Destination file path (will be created or overwritten).
    benchmark_version:
        Version string for the benchmark suite (e.g. ``"v1.0"``).
    agent_version:
        Version string for the agent under test (e.g. ``"stub-0.1"``).
    """
    timestamp = _now_iso()

    total = len(results)
    total_passed = sum(1 for r in results if r.passed)
    overall = f"{total_passed}/{total}" if total > 0 else "0/0"

    lines: list[str] = []

    # ------------------------------------------------------------------
    # Run metadata
    # ------------------------------------------------------------------
    lines.append("# Benchmark Results\n")
    lines.append(f"| Key | Value |")
    lines.append(f"|-----|-------|")
    lines.append(f"| Timestamp | {timestamp} |")
    lines.append(f"| Benchmark Version | {benchmark_version} |")
    lines.append(f"| Agent Version | {agent_version} |")
    lines.append(f"| Overall Pass Rate | {overall} |")
    lines.append("")

    # ------------------------------------------------------------------
    # 3×3 pass-rate table
    # ------------------------------------------------------------------
    lines.append("## Pass Rate by Language and Difficulty\n")

    # Build header row
    header_cells = ["Language"] + [d.capitalize() for d in DIFFICULTIES]
    lines.append("| " + " | ".join(header_cells) + " |")
    lines.append("| " + " | ".join(["---"] * len(header_cells)) + " |")

    for lang in LANGUAGES:
        row_cells = [lang]
        for diff in DIFFICULTIES:
            matching = [r for r in results if r.language == lang and r.difficulty == diff]
            n = len(matching)
            p = sum(1 for r in matching if r.passed)
            row_cells.append(f"{p}/{n} passed")
        lines.append("| " + " | ".join(row_cells) + " |")

    lines.append("")

    # ------------------------------------------------------------------
    # Per-task metrics summary table
    # ------------------------------------------------------------------
    lines.append("## Per-Task Metrics\n")

    metric_headers = [
        "Task ID",
        "Language",
        "Difficulty",
        "Passed",
        "agent_completion_time_s",
        "eval_runtime_s",
        "Steps",
        "Tokens",
    ]
    lines.append("| " + " | ".join(metric_headers) + " |")
    lines.append("| " + " | ".join(["---"] * len(metric_headers)) + " |")

    for r in results:
        steps_str = str(r.metrics.steps) if r.metrics.steps is not None else "N/A"
        tokens_str = str(r.metrics.tokens) if r.metrics.tokens is not None else "N/A"
        passed_str = "yes" if r.passed else "no"
        row = [
            r.task_id,
            r.language,
            r.difficulty,
            passed_str,
            f"{r.metrics.agent_completion_time_s:.3f}",
            f"{r.metrics.eval_runtime_s:.3f}",
            steps_str,
            tokens_str,
        ]
        lines.append("| " + " | ".join(row) + " |")

    lines.append("")

    with open(output_path, "w", encoding="utf-8") as fh:
        fh.write("\n".join(lines))
