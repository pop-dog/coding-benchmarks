"""
models.py — Data classes for harness results.
"""

from dataclasses import dataclass


@dataclass
class TaskResult:
    """Result of running one benchmark task through the harness."""

    task_id: str
    """Derived from the task directory name, e.g. 'task_001'."""

    language: str
    """Programming language, e.g. 'python'."""

    difficulty: str
    """Difficulty tier: 'easy', 'medium', or 'hard'."""

    passed: bool
    """True if all eval_tests passed after the agent ran."""

    exit_code: int
    """Agent's exit code (0, 1, or 124 for timeout)."""

    timed_out: bool
    """True if the timeout was hit and the container was killed."""

    agent_stdout: str
    """Captured stdout from run.sh."""

    agent_stderr: str
    """Captured stderr from run.sh."""
