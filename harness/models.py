"""
models.py — Data classes for harness results.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional


@dataclass
class TaskMetrics:
    """Timing and token metrics collected during a single task run."""

    agent_completion_time_s: float
    """Wall-clock seconds from container start to agent exit."""

    eval_runtime_s: float
    """Wall-clock seconds to run eval_tests (proxy for solution efficiency)."""

    steps: Optional[int]
    """Number of agent steps parsed from agent stdout JSON; None if absent/malformed."""

    tokens: Optional[int]
    """Number of tokens parsed from agent stdout JSON; None if absent/malformed."""


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

    metrics: TaskMetrics = field(
        default_factory=lambda: TaskMetrics(
            agent_completion_time_s=0.0,
            eval_runtime_s=0.0,
            steps=None,
            tokens=None,
        )
    )
    """Timing and token metrics for this task run."""
