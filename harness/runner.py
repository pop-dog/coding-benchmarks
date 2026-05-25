"""
runner.py — Core harness module.

Runs a single benchmark task end-to-end inside a fresh Docker container
spawned from the `benchmark-base:latest` image.

Harness flow
============
1. Spin up a fresh container from ``benchmark-base:latest``.
2. Copy ``repo/``, ``prompt.md``, and ``tests/`` into ``/sandbox/`` inside
   the container.
3. Mount the agent repo at ``/agent/`` inside the container (read-only bind
   mount).
4. Inject environment variables declared in the agent's ``.env.template``
   (vars not set in the host environment are silently skipped).
5. Run ``/agent/setup.sh`` inside the container.
6. Run ``/agent/run.sh --task-dir /sandbox --timeout N --language L
   --difficulty D`` inside the container.
7. Enforce the tiered timeout (easy: 300 s, medium: 600 s, hard: 1200 s);
   kill the container if breached.
8. Copy ``eval_tests/`` into the container's ``/sandbox/eval_tests/``, then
   run ``pytest /sandbox/eval_tests/`` inside the container.  Capture the
   exit code to determine pass/fail.
9. Record exit code and pass/fail.
10. Tear down the container (always, including on error and timeout).

Network policy
==============
Containers are created without ``--network host`` so they do not inherit the
host network.  Full outbound restriction to ``api.anthropic.com`` only is a
TODO for v2 — for now we rely on Docker's default bridge network.

TODO (v2): Create a custom Docker network with ``internal=True`` and add a
transparent proxy or ``--add-host`` entry so only ``api.anthropic.com`` is
reachable from the container.
"""

import io
import os
import tarfile
import time
from pathlib import Path
from typing import Optional

import docker
import docker.errors

from .models import TaskResult

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

IMAGE = "benchmark-base:latest"

TIMEOUTS = {
    "easy": 300,
    "medium": 600,
    "hard": 1200,
}

SANDBOX_DIR = "/sandbox"
AGENT_DIR = "/agent"

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _parse_env_template(env_template_path: Path) -> dict:
    """Read an ``.env.template`` file and return vars present in the host env.

    Lines that are blank or start with ``#`` are ignored.  For each
    ``KEY=...`` line the key is looked up in the host environment; if it is
    not set the variable is silently skipped.
    """
    env = {}
    if not env_template_path.exists():
        return env
    for line in env_template_path.read_text().splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        key = line.split("=", 1)[0].strip()
        if key and key in os.environ:
            env[key] = os.environ[key]
    return env


def _make_tar_from_path(src: Path) -> bytes:
    """Return a tar archive (as bytes) whose root contains ``src``.

    If ``src`` is a directory the archive root is the directory itself
    (i.e. the archive contains ``<dirname>/file``, … ).  If ``src`` is a
    file the archive root contains just that file.
    """
    buf = io.BytesIO()
    with tarfile.open(fileobj=buf, mode="w") as tf:
        tf.add(str(src), arcname=src.name)
    buf.seek(0)
    return buf.read()


def _put_path(container, src: Path, dest_parent: str) -> None:
    """Copy *src* (file or directory) into *dest_parent* inside *container*.

    Uses the Docker ``put_archive`` API so no bind mounts are needed.
    """
    data = _make_tar_from_path(src)
    container.put_archive(dest_parent, data)


def _exec_run(container, cmd, timeout_s: float) -> tuple[int, str, str]:
    """Run *cmd* inside *container*, enforcing *timeout_s*.

    Returns ``(exit_code, stdout, stderr)``.  If the timeout fires the
    container is killed and ``(124, "", "")`` is returned — the caller is
    responsible for final container cleanup.
    """
    exec_id = container.client.api.exec_create(
        container.id,
        cmd,
        stdout=True,
        stderr=True,
    )
    sock = container.client.api.exec_start(exec_id["Id"], stream=True, demux=True)

    stdout_chunks: list[bytes] = []
    stderr_chunks: list[bytes] = []
    deadline = time.monotonic() + timeout_s
    timed_out = False

    for stdout_data, stderr_data in sock:
        if stdout_data:
            stdout_chunks.append(stdout_data)
        if stderr_data:
            stderr_chunks.append(stderr_data)
        if time.monotonic() > deadline:
            timed_out = True
            break

    if timed_out:
        try:
            container.kill()
        except docker.errors.APIError:
            pass
        return 124, "", ""

    inspect = container.client.api.exec_inspect(exec_id["Id"])
    exit_code = inspect.get("ExitCode", 1)
    stdout = b"".join(stdout_chunks).decode("utf-8", errors="replace")
    stderr = b"".join(stderr_chunks).decode("utf-8", errors="replace")
    return exit_code, stdout, stderr


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def run_task(
    task_dir: str | Path,
    agent_dir: str | Path,
    language: str,
    difficulty: str,
    *,
    timeout_override: Optional[int] = None,
) -> TaskResult:
    """Run one benchmark task end-to-end and return a :class:`TaskResult`.

    Parameters
    ----------
    task_dir:
        Absolute path to the task directory (e.g.
        ``benchmark/v1.0/tasks/python/easy/task_001``).  Must contain
        ``repo/``, ``prompt.md``, ``tests/``, and ``eval_tests/``.
    agent_dir:
        Absolute path to the agent directory (e.g. ``agents/stub``).
        Must contain ``run.sh``, ``setup.sh``, and optionally
        ``.env.template``.
    language:
        Programming language string passed to the agent (e.g. ``"python"``).
    difficulty:
        Difficulty tier: ``"easy"``, ``"medium"``, or ``"hard"``.
    timeout_override:
        If provided, overrides the tiered default timeout (seconds).  Useful
        in tests.
    """
    task_dir = Path(task_dir).resolve()
    agent_dir = Path(agent_dir).resolve()

    task_id = task_dir.name
    timeout_s = timeout_override if timeout_override is not None else TIMEOUTS[difficulty]

    client = docker.from_env()

    # ------------------------------------------------------------------
    # Collect env vars from agent's .env.template
    # ------------------------------------------------------------------
    env = _parse_env_template(agent_dir / ".env.template")

    # ------------------------------------------------------------------
    # Launch container
    # ------------------------------------------------------------------
    # The agent directory is bind-mounted read-only at /agent/.
    # No host-network — containers get Docker's default bridge.
    container = client.containers.run(
        IMAGE,
        command="sleep infinity",
        detach=True,
        remove=False,
        environment=env,
        volumes={
            str(agent_dir): {
                "bind": AGENT_DIR,
                "mode": "ro",
            }
        },
    )

    result = TaskResult(
        task_id=task_id,
        language=language,
        difficulty=difficulty,
        passed=False,
        exit_code=1,
        timed_out=False,
        agent_stdout="",
        agent_stderr="",
    )

    try:
        # ------------------------------------------------------------------
        # Ensure /sandbox exists inside the container
        # ------------------------------------------------------------------
        container.exec_run(["mkdir", "-p", SANDBOX_DIR])

        # ------------------------------------------------------------------
        # Copy task files into /sandbox/
        # ------------------------------------------------------------------
        for item_name in ("repo", "prompt.md", "tests"):
            src = task_dir / item_name
            if src.exists():
                _put_path(container, src, SANDBOX_DIR)

        # ------------------------------------------------------------------
        # Run /agent/setup.sh
        # ------------------------------------------------------------------
        container.exec_run(["bash", f"{AGENT_DIR}/setup.sh"], workdir=SANDBOX_DIR)

        # ------------------------------------------------------------------
        # Run /agent/run.sh with tiered timeout
        # ------------------------------------------------------------------
        agent_cmd = [
            "bash",
            f"{AGENT_DIR}/run.sh",
            "--task-dir", SANDBOX_DIR,
            "--timeout", str(timeout_s),
            "--language", language,
            "--difficulty", difficulty,
        ]

        exit_code, stdout, stderr = _exec_run(container, agent_cmd, timeout_s)

        result.agent_stdout = stdout
        result.agent_stderr = stderr

        if exit_code == 124:
            result.timed_out = True
            result.exit_code = 124
            # Container has already been killed; skip eval.
            return result

        result.exit_code = exit_code

        # ------------------------------------------------------------------
        # Copy eval_tests/ into /sandbox/eval_tests/ and run pytest
        # ------------------------------------------------------------------
        eval_tests_src = task_dir / "eval_tests"
        if eval_tests_src.exists():
            _put_path(container, eval_tests_src, SANDBOX_DIR)
            eval_result = container.exec_run(
                ["python3", "-m", "pytest", "/sandbox/eval_tests/", "-q", "--tb=short"],
                workdir=SANDBOX_DIR,
            )
            result.passed = (eval_result.exit_code == 0)
        else:
            # No eval tests — treat as passed if agent exited cleanly.
            result.passed = (exit_code == 0)

    finally:
        # ------------------------------------------------------------------
        # Always tear down the container
        # ------------------------------------------------------------------
        try:
            container.stop(timeout=5)
        except docker.errors.APIError:
            pass
        try:
            container.remove(force=True)
        except docker.errors.APIError:
            pass

    return result
