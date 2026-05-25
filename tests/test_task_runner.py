"""
tests/test_task_runner.py — Unit tests for harness/task_runner.py.

No Docker is required; run_task is mocked for the parallel-execution test.
"""

from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from harness.models import TaskMetrics, TaskResult

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------

REPO_ROOT = Path(__file__).resolve().parent.parent
BENCHMARK_DIR = str(REPO_ROOT / "benchmark" / "v1.0")

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _fake_run_task(task_dir: str, agent_dir: str, language: str, difficulty: str) -> TaskResult:
    """Fake run_task that returns a minimal TaskResult without touching Docker."""
    task_id = Path(task_dir).name
    return TaskResult(
        task_id=task_id,
        language=language,
        difficulty=difficulty,
        passed=True,
        exit_code=0,
        timed_out=False,
        agent_stdout="",
        agent_stderr="",
        metrics=TaskMetrics(
            agent_completion_time_s=1.0,
            eval_runtime_s=0.1,
            steps=None,
            tokens=None,
        ),
    )


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


class TestDiscoverTasks:
    """Tests for discover_tasks()."""

    def test_discover_tasks_all(self):
        """Given the real benchmark dir, at least 1 task (the seed task) is found."""
        from harness.task_runner import discover_tasks

        tasks = discover_tasks(BENCHMARK_DIR)

        assert len(tasks) >= 1, "Expected at least 1 task in benchmark/v1.0"
        # Each descriptor must have the required keys.
        required_keys = {"task_dir", "language", "difficulty", "task_id"}
        for t in tasks:
            assert required_keys.issubset(t.keys()), f"Missing keys in task descriptor: {t}"

    def test_discover_tasks_filter(self):
        """With filter ['python/easy'], only python/easy tasks are returned."""
        from harness.task_runner import discover_tasks

        tasks = discover_tasks(BENCHMARK_DIR, task_filter=["python/easy"])

        assert len(tasks) >= 1, "Expected at least 1 python/easy task"
        for t in tasks:
            assert t["language"] == "python", f"Unexpected language: {t['language']}"
            assert t["difficulty"] == "easy", f"Unexpected difficulty: {t['difficulty']}"

    def test_discover_tasks_nonexistent_filter(self):
        """Filter ['go/easy'] returns an empty list (no go tasks exist yet)."""
        from harness.task_runner import discover_tasks

        tasks = discover_tasks(BENCHMARK_DIR, task_filter=["go/easy"])

        assert tasks == [], f"Expected empty list, got: {tasks}"


class TestRunAllParallel:
    """Tests for run_all() — run_task is mocked so Docker is not needed."""

    def test_run_all_parallel(self, tmp_path):
        """All 3 submitted tasks must be collected; run_task must not be called for real."""
        from harness.task_runner import run_all

        # Build 3 minimal stub task descriptors pointing to the real task_001 dir
        # (the path is passed through to run_task which is mocked, so the dir
        # does not actually need to be valid for this test).
        task_001_dir = str(
            REPO_ROOT / "benchmark" / "v1.0" / "tasks" / "python" / "easy" / "task_001"
        )
        stub_tasks = [
            {
                "task_dir": task_001_dir,
                "language": "python",
                "difficulty": "easy",
                "task_id": f"task_{i:03d}",
            }
            for i in range(1, 4)
        ]

        with patch("harness.task_runner.run_task", side_effect=_fake_run_task) as mock_run:
            results = run_all(stub_tasks, agent_dir=str(tmp_path), parallel=3)

        # All 3 results must be collected.
        assert len(results) == 3, f"Expected 3 results, got {len(results)}"

        # run_task must have been called exactly once per task.
        assert mock_run.call_count == 3, (
            f"run_task should be called 3 times, was called {mock_run.call_count} time(s)"
        )

        # Every result should be a TaskResult.
        for r in results:
            assert isinstance(r, TaskResult), f"Expected TaskResult, got {type(r)}"
