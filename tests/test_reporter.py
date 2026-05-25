"""
tests/test_reporter.py — Fixture-based tests for harness/reporter.py.

No Docker is required; all tests operate on in-memory TaskResult fixtures
and temporary files.
"""

from __future__ import annotations

import json
import tempfile
from pathlib import Path

import pytest

from harness.models import TaskMetrics, TaskResult
from harness.reporter import write_json, write_markdown

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


def _make_result(
    task_id: str,
    language: str,
    difficulty: str,
    passed: bool,
    agent_completion_time_s: float = 1.5,
    eval_runtime_s: float = 0.3,
    steps: int | None = 10,
    tokens: int | None = 500,
    exit_code: int = 0,
    timed_out: bool = False,
    agent_stdout: str = "",
    agent_stderr: str = "",
) -> TaskResult:
    return TaskResult(
        task_id=task_id,
        language=language,
        difficulty=difficulty,
        passed=passed,
        exit_code=exit_code,
        timed_out=timed_out,
        agent_stdout=agent_stdout,
        agent_stderr=agent_stderr,
        metrics=TaskMetrics(
            agent_completion_time_s=agent_completion_time_s,
            eval_runtime_s=eval_runtime_s,
            steps=steps,
            tokens=tokens,
        ),
    )


@pytest.fixture()
def two_results() -> list[TaskResult]:
    """Two known TaskResult fixtures: one passing, one failing."""
    return [
        _make_result(
            task_id="task_001",
            language="python",
            difficulty="easy",
            passed=True,
            steps=12,
            tokens=4821,
        ),
        _make_result(
            task_id="task_002",
            language="go",
            difficulty="medium",
            passed=False,
            steps=7,
            tokens=1200,
        ),
    ]


@pytest.fixture()
def pass_rate_results() -> list[TaskResult]:
    """Fixtures with known pass/fail spread across the 3×3 language/difficulty grid."""
    return [
        # python / easy: 1 pass, 1 fail  → "1/2 passed"
        _make_result("t01", "python", "easy", passed=True),
        _make_result("t02", "python", "easy", passed=False),
        # python / medium: 0 tasks       → "0/0 passed"
        # go / hard: 2 passes            → "2/2 passed"
        _make_result("t03", "go", "hard", passed=True),
        _make_result("t04", "go", "hard", passed=True),
        # rust / easy: 1 fail            → "0/1 passed"
        _make_result("t05", "rust", "easy", passed=False),
    ]


@pytest.fixture()
def null_metrics_result() -> list[TaskResult]:
    """A single TaskResult with steps=None and tokens=None."""
    return [
        _make_result(
            task_id="task_003",
            language="rust",
            difficulty="hard",
            passed=False,
            steps=None,
            tokens=None,
        )
    ]


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


class TestWriteJsonSchema:
    """test_write_json_schema — verify top-level and per-task keys in JSON output."""

    def test_top_level_keys(self, two_results, tmp_path):
        out = str(tmp_path / "results.json")
        write_json(two_results, out, benchmark_version="v1.0", agent_version="stub-0.1")

        with open(out) as fh:
            data = json.load(fh)

        assert set(data.keys()) == {"timestamp", "benchmark_version", "agent_version", "tasks"}

    def test_benchmark_and_agent_version(self, two_results, tmp_path):
        out = str(tmp_path / "results.json")
        write_json(two_results, out, benchmark_version="v1.0", agent_version="stub-0.1")

        with open(out) as fh:
            data = json.load(fh)

        assert data["benchmark_version"] == "v1.0"
        assert data["agent_version"] == "stub-0.1"

    def test_task_count(self, two_results, tmp_path):
        out = str(tmp_path / "results.json")
        write_json(two_results, out, benchmark_version="v1.0", agent_version="stub-0.1")

        with open(out) as fh:
            data = json.load(fh)

        assert len(data["tasks"]) == 2

    def test_per_task_keys(self, two_results, tmp_path):
        out = str(tmp_path / "results.json")
        write_json(two_results, out, benchmark_version="v1.0", agent_version="stub-0.1")

        with open(out) as fh:
            data = json.load(fh)

        expected_keys = {
            "task_id",
            "language",
            "difficulty",
            "passed",
            "exit_code",
            "timed_out",
            "agent_stdout",
            "agent_stderr",
            "agent_completion_time_s",
            "eval_runtime_s",
            "steps",
            "tokens",
        }
        for task_record in data["tasks"]:
            assert set(task_record.keys()) == expected_keys

    def test_per_task_values(self, two_results, tmp_path):
        out = str(tmp_path / "results.json")
        write_json(two_results, out, benchmark_version="v1.0", agent_version="stub-0.1")

        with open(out) as fh:
            data = json.load(fh)

        first = data["tasks"][0]
        assert first["task_id"] == "task_001"
        assert first["language"] == "python"
        assert first["difficulty"] == "easy"
        assert first["passed"] is True
        assert first["steps"] == 12
        assert first["tokens"] == 4821


class TestWriteMarkdownPassRateTable:
    """test_write_markdown_pass_rate_table — verify correct pass counts in 3×3 table."""

    def _read(self, path: str) -> str:
        with open(path) as fh:
            return fh.read()

    def test_markdown_file_created(self, pass_rate_results, tmp_path):
        out = str(tmp_path / "report.md")
        write_markdown(pass_rate_results, out, benchmark_version="v1.0", agent_version="stub-0.1")
        assert Path(out).exists()

    def test_python_easy_pass_rate(self, pass_rate_results, tmp_path):
        out = str(tmp_path / "report.md")
        write_markdown(pass_rate_results, out, benchmark_version="v1.0", agent_version="stub-0.1")
        content = self._read(out)
        # python / easy: 1 pass out of 2
        assert "1/2 passed" in content

    def test_go_hard_pass_rate(self, pass_rate_results, tmp_path):
        out = str(tmp_path / "report.md")
        write_markdown(pass_rate_results, out, benchmark_version="v1.0", agent_version="stub-0.1")
        content = self._read(out)
        # go / hard: 2 passes out of 2
        assert "2/2 passed" in content

    def test_rust_easy_pass_rate(self, pass_rate_results, tmp_path):
        out = str(tmp_path / "report.md")
        write_markdown(pass_rate_results, out, benchmark_version="v1.0", agent_version="stub-0.1")
        content = self._read(out)
        # rust / easy: 0 passes out of 1
        assert "0/1 passed" in content

    def test_empty_cell_shows_zero(self, pass_rate_results, tmp_path):
        out = str(tmp_path / "report.md")
        write_markdown(pass_rate_results, out, benchmark_version="v1.0", agent_version="stub-0.1")
        content = self._read(out)
        # python / medium: no tasks → "0/0 passed"
        assert "0/0 passed" in content

    def test_metadata_present(self, pass_rate_results, tmp_path):
        out = str(tmp_path / "report.md")
        write_markdown(
            pass_rate_results, out, benchmark_version="v2.0", agent_version="my-agent-1.0"
        )
        content = self._read(out)
        assert "v2.0" in content
        assert "my-agent-1.0" in content

    def test_overall_pass_rate(self, pass_rate_results, tmp_path):
        out = str(tmp_path / "report.md")
        write_markdown(pass_rate_results, out, benchmark_version="v1.0", agent_version="stub-0.1")
        content = self._read(out)
        # t01 (python/easy, pass), t03 (go/hard, pass), t04 (go/hard, pass)
        # = 3 passes out of 5 total tasks
        assert "3/5" in content


class TestMissingMetricsGraceful:
    """test_missing_metrics_graceful — steps=None and tokens=None produce null in JSON."""

    def test_null_steps_in_json(self, null_metrics_result, tmp_path):
        out = str(tmp_path / "results.json")
        write_json(null_metrics_result, out, benchmark_version="v1.0", agent_version="stub-0.1")

        with open(out) as fh:
            data = json.load(fh)

        assert data["tasks"][0]["steps"] is None

    def test_null_tokens_in_json(self, null_metrics_result, tmp_path):
        out = str(tmp_path / "results.json")
        write_json(null_metrics_result, out, benchmark_version="v1.0", agent_version="stub-0.1")

        with open(out) as fh:
            data = json.load(fh)

        assert data["tasks"][0]["tokens"] is None

    def test_no_crash_on_null_metrics(self, null_metrics_result, tmp_path):
        """write_json and write_markdown must not raise with None steps/tokens."""
        json_out = str(tmp_path / "results.json")
        md_out = str(tmp_path / "report.md")

        write_json(null_metrics_result, json_out, benchmark_version="v1.0", agent_version="stub-0.1")
        write_markdown(null_metrics_result, md_out, benchmark_version="v1.0", agent_version="stub-0.1")

        assert Path(json_out).exists()
        assert Path(md_out).exists()

    def test_null_metrics_markdown_shows_na(self, null_metrics_result, tmp_path):
        """Markdown table should show N/A for absent steps and tokens."""
        out = str(tmp_path / "report.md")
        write_markdown(null_metrics_result, out, benchmark_version="v1.0", agent_version="stub-0.1")

        with open(out) as fh:
            content = fh.read()

        assert "N/A" in content
