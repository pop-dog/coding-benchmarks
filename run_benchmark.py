#!/usr/bin/env python3
"""
run_benchmark.py — Main CLI entry point for the coding-benchmarks harness.

Usage
-----
python run_benchmark.py \\
  --benchmark-dir ./benchmark/v1.0 \\
  --agent-config ./agents/stub \\
  --tasks python/easy,rust/medium \\
  --output results/run_001.json \\
  --parallel 3 \\
  --benchmark-version v1.0 \\
  --agent-version stub-v1
"""

from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Run the coding-benchmark harness against an agent.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument(
        "--benchmark-dir",
        required=True,
        help="Path to the versioned benchmark directory (e.g. ./benchmark/v1.0).",
    )
    parser.add_argument(
        "--agent-config",
        required=True,
        help="Path to the agent repo directory (must contain run.sh and setup.sh).",
    )
    parser.add_argument(
        "--tasks",
        default=None,
        help=(
            "Comma-separated task filter, e.g. 'python/easy,go/hard'. "
            "Omit to run all tasks."
        ),
    )
    parser.add_argument(
        "--output",
        required=True,
        help="Destination path for the JSON results file (e.g. results/run_001.json).",
    )
    parser.add_argument(
        "--parallel",
        type=int,
        default=3,
        help="Maximum number of tasks to run concurrently (default: 3).",
    )
    parser.add_argument(
        "--benchmark-version",
        default="v1.0",
        help="Version string for the benchmark suite (default: v1.0).",
    )
    parser.add_argument(
        "--agent-version",
        default="unknown",
        help="Version string for the agent under test (default: unknown).",
    )
    return parser.parse_args()


def main() -> int:
    args = _parse_args()

    # ------------------------------------------------------------------
    # Resolve paths
    # ------------------------------------------------------------------
    benchmark_dir = str(Path(args.benchmark_dir).resolve())
    agent_dir = str(Path(args.agent_config).resolve())
    output_path = str(Path(args.output).resolve())

    # Ensure the output directory exists.
    output_dir = os.path.dirname(output_path)
    if output_dir:
        os.makedirs(output_dir, exist_ok=True)

    # ------------------------------------------------------------------
    # Parse task filter
    # ------------------------------------------------------------------
    task_filter = None
    if args.tasks:
        task_filter = [t.strip() for t in args.tasks.split(",") if t.strip()]

    # ------------------------------------------------------------------
    # Discover tasks
    # ------------------------------------------------------------------
    from harness.task_runner import discover_tasks, run_all

    tasks = discover_tasks(benchmark_dir, task_filter=task_filter)

    if not tasks:
        print("No tasks found matching the given filter. Exiting.", file=sys.stderr)
        return 1

    print(f"Discovered {len(tasks)} task(s). Running with --parallel {args.parallel}.")

    # ------------------------------------------------------------------
    # Run tasks
    # ------------------------------------------------------------------
    results = run_all(tasks, agent_dir=agent_dir, parallel=args.parallel)

    # ------------------------------------------------------------------
    # Write outputs
    # ------------------------------------------------------------------
    from harness.reporter import write_json, write_markdown

    write_json(
        results,
        output_path=output_path,
        benchmark_version=args.benchmark_version,
        agent_version=args.agent_version,
    )

    md_path = str(Path(output_path).with_suffix(".md"))
    write_markdown(
        results,
        output_path=md_path,
        benchmark_version=args.benchmark_version,
        agent_version=args.agent_version,
    )

    print(f"Results written to {output_path} and {md_path}")

    # ------------------------------------------------------------------
    # Final summary
    # ------------------------------------------------------------------
    total = len(results)
    passed = sum(1 for r in results if r.passed)
    pass_rate = passed / total if total > 0 else 0.0
    print(f"Summary: {passed}/{total} passed ({pass_rate:.1%})")

    return 0


if __name__ == "__main__":
    sys.exit(main())
