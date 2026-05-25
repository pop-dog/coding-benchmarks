"""
tests/test_harness.py — Integration tests for harness/runner.py.

These tests require Docker to be available and the ``benchmark-base:latest``
image to be built.  If Docker is unavailable all tests are skipped.

Test matrix
-----------
test_stub_agent_pass
    Run the stub agent against the seed task (task_001).  The stub agent does
    not modify any files, so eval_tests must fail.  We verify:
    - ``result.passed is False``
    - ``result.exit_code == 0``  (agent itself exited cleanly)
    - ``result.timed_out is False``

test_timeout_agent
    Create a temporary agent whose ``run.sh`` sleeps for 999 s.  Run with a
    very short ``timeout_override`` so the harness kills the container quickly.
    We verify:
    - ``result.timed_out is True``
    - ``result.exit_code == 124``

test_container_torn_down
    After a run completes, verify no dangling containers from that run remain.
"""

import os
import stat
import tempfile
import textwrap
from pathlib import Path

import pytest

# ---------------------------------------------------------------------------
# Docker availability guard
# ---------------------------------------------------------------------------

try:
    import docker as _docker_mod

    _docker_client = _docker_mod.from_env()
    _DOCKER_AVAILABLE = True
except Exception:
    _DOCKER_AVAILABLE = False

docker_required = pytest.mark.skipif(
    not _DOCKER_AVAILABLE,
    reason="Docker daemon not available or docker SDK not installed",
)

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------

REPO_ROOT = Path(__file__).resolve().parent.parent
TASK_DIR = REPO_ROOT / "benchmark" / "v1.0" / "tasks" / "python" / "easy" / "task_001"
STUB_AGENT_DIR = REPO_ROOT / "agents" / "stub"

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_sleeping_agent(tmp_path: Path, sleep_seconds: int = 999) -> Path:
    """Create a minimal agent directory whose ``run.sh`` sleeps indefinitely."""
    agent_dir = tmp_path / "sleep_agent"
    agent_dir.mkdir()

    setup = agent_dir / "setup.sh"
    setup.write_text("#!/usr/bin/env bash\nexit 0\n")
    setup.chmod(setup.stat().st_mode | stat.S_IEXEC | stat.S_IXGRP | stat.S_IXOTH)

    run = agent_dir / "run.sh"
    run.write_text(
        textwrap.dedent(
            f"""\
            #!/usr/bin/env bash
            sleep {sleep_seconds}
            exit 0
            """
        )
    )
    run.chmod(run.stat().st_mode | stat.S_IEXEC | stat.S_IXGRP | stat.S_IXOTH)

    env_tmpl = agent_dir / ".env.template"
    env_tmpl.write_text("# no env vars needed\n")

    return agent_dir


def _list_benchmark_containers(client) -> list:
    """Return all containers whose image is benchmark-base:latest."""
    try:
        return client.containers.list(
            all=True,
            filters={"ancestor": "benchmark-base:latest"},
        )
    except Exception:
        return []


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


@docker_required
def test_stub_agent_pass():
    """Stub agent exits 0 but does not fix the code, so eval_tests must fail."""
    from harness.runner import run_task

    result = run_task(
        task_dir=TASK_DIR,
        agent_dir=STUB_AGENT_DIR,
        language="python",
        difficulty="easy",
    )

    assert result.task_id == "task_001"
    assert result.language == "python"
    assert result.difficulty == "easy"
    assert result.timed_out is False, "stub agent should not time out"
    assert result.exit_code == 0, f"stub run.sh exited {result.exit_code}, expected 0"
    assert result.passed is False, (
        "eval_tests should fail because the stub agent did not fix ring_buffer.py"
    )


@docker_required
def test_timeout_agent(tmp_path):
    """An agent that sleeps 999 s must be killed; exit_code must be 124."""
    from harness.runner import run_task

    sleep_agent = _make_sleeping_agent(tmp_path, sleep_seconds=999)

    result = run_task(
        task_dir=TASK_DIR,
        agent_dir=sleep_agent,
        language="python",
        difficulty="easy",
        timeout_override=5,  # 5-second timeout for testing
    )

    assert result.timed_out is True, "timed_out should be True when container is killed"
    assert result.exit_code == 124, f"expected exit_code 124, got {result.exit_code}"


@docker_required
def test_container_torn_down():
    """After run_task returns, no dangling containers from the run should exist."""
    from harness.runner import run_task

    client = _docker_mod.from_env()

    # Capture container count before
    before = len(_list_benchmark_containers(client))

    run_task(
        task_dir=TASK_DIR,
        agent_dir=STUB_AGENT_DIR,
        language="python",
        difficulty="easy",
    )

    # After the run, count must not have grown (container was removed)
    after = len(_list_benchmark_containers(client))
    assert after <= before, (
        f"Expected no new benchmark-base containers after run, "
        f"but went from {before} to {after}"
    )
