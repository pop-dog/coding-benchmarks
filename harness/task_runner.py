"""
task_runner.py — Parallel task discovery and execution for the benchmark harness.

Public API
----------
- ``discover_tasks`` — walk a benchmark directory and return task descriptors.
- ``run_all``        — execute a list of tasks in parallel with a thread pool.
"""

from __future__ import annotations

import sys
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
from typing import List, Optional

from .models import TaskResult
from .runner import run_task

# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def discover_tasks(
    benchmark_dir: str,
    task_filter: Optional[List[str]] = None,
) -> List[dict]:
    """Walk *benchmark_dir* and return one descriptor dict per task found.

    The expected directory layout is::

        <benchmark_dir>/tasks/<language>/<difficulty>/task_NNN/

    Parameters
    ----------
    benchmark_dir:
        Path to a versioned benchmark directory (e.g. ``benchmark/v1.0``).
    task_filter:
        Optional list of ``"<language>/<difficulty>"`` strings.  When provided
        only tasks whose language *and* difficulty match one of the entries are
        returned.  Example: ``["python/easy", "rust/medium"]``.

    Returns
    -------
    list[dict]
        Each element has keys: ``task_dir``, ``language``, ``difficulty``,
        ``task_id``.
    """
    tasks_root = Path(benchmark_dir) / "tasks"
    if not tasks_root.is_dir():
        return []

    # Normalise the filter into a set for O(1) lookup.
    filter_set: Optional[set[str]] = (
        {f.strip() for f in task_filter} if task_filter is not None else None
    )

    results: List[dict] = []

    for lang_dir in sorted(tasks_root.iterdir()):
        if not lang_dir.is_dir():
            continue
        language = lang_dir.name

        for diff_dir in sorted(lang_dir.iterdir()):
            if not diff_dir.is_dir():
                continue
            difficulty = diff_dir.name

            if filter_set is not None and f"{language}/{difficulty}" not in filter_set:
                continue

            for task_dir in sorted(diff_dir.iterdir()):
                if not task_dir.is_dir():
                    continue
                results.append(
                    {
                        "task_dir": str(task_dir),
                        "language": language,
                        "difficulty": difficulty,
                        "task_id": task_dir.name,
                    }
                )

    return results


def run_all(
    tasks: List[dict],
    agent_dir: str,
    parallel: int = 3,
) -> List[TaskResult]:
    """Run *tasks* in parallel using a thread pool and return all results.

    Prints a one-line progress update to stderr as each task finishes::

        [PASS] python/easy/task_001 (12.3s)
        [FAIL] rust/medium/task_002 (45.1s)

    Parameters
    ----------
    tasks:
        List of task descriptor dicts as returned by :func:`discover_tasks`.
    agent_dir:
        Path to the agent directory passed through to :func:`~harness.runner.run_task`.
    parallel:
        Maximum number of tasks to run concurrently (default: 3).

    Returns
    -------
    list[TaskResult]
        All results collected; order is completion order, not input order.
    """
    results: List[TaskResult] = []

    with ThreadPoolExecutor(max_workers=parallel) as executor:
        future_to_task = {
            executor.submit(
                run_task,
                task["task_dir"],
                agent_dir,
                task["language"],
                task["difficulty"],
            ): task
            for task in tasks
        }

        for future in as_completed(future_to_task):
            task = future_to_task[future]
            result: TaskResult = future.result()
            status = "PASS" if result.passed else "FAIL"
            elapsed = result.metrics.agent_completion_time_s
            label = f"{task['language']}/{task['difficulty']}/{task['task_id']}"
            print(f"[{status}] {label} ({elapsed:.1f}s)", file=sys.stderr, flush=True)
            results.append(result)

    return results
