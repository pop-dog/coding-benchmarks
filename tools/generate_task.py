#!/usr/bin/env python3
"""
generate_task.py — LLM-based benchmark task generator.

Calls the Claude API to produce a complete draft task directory containing:
  repo/<module>.py
  repo/README.md
  prompt.md
  tests/test_<module>.py
  eval_tests/test_<module>_eval.py

Usage:
    python tools/generate_task.py \
        --language python \
        --difficulty easy \
        --category "off-by-one bug" \
        --output benchmark/v1.0/tasks/python/easy/task_002

    # Print the prompt without calling the API:
    python tools/generate_task.py \
        --language python \
        --difficulty easy \
        --category "off-by-one bug" \
        --output benchmark/v1.0/tasks/python/easy/task_002 \
        --dry-run
"""

import argparse
import json
import os
import sys
import textwrap


# ---------------------------------------------------------------------------
# Difficulty and category rubrics
# ---------------------------------------------------------------------------

DIFFICULTY_RUBRICS = {
    "easy": (
        "1 file changed. The bug should be immediately clear once the reader "
        "inspects the relevant function. Typical bugs: off-by-one error, wrong "
        "conditional (e.g. `<` instead of `<=`), missing return statement."
    ),
    "medium": (
        "1–3 files changed. The bug is non-obvious and may require tracing "
        "through multiple code paths to locate. Typical bugs: incorrect boundary "
        "condition in a helper function, partially-implemented feature with a "
        "subtle contract violation, wrong assumption about data layout."
    ),
    "hard": (
        "3+ files changed. The defect is a cross-cutting concern or integration "
        "bug — it cannot be fixed by editing a single isolated function. Typical "
        "bugs: concurrency / synchronisation problem, architectural mismatch "
        "between components, a series of related off-by-one errors that interact."
    ),
}

LANGUAGE_CATEGORIES = {
    "python": [
        "off-by-one",
        "wrong conditional",
        "missing return",
        "incorrect slice",
        "type error",
    ],
    "go": [
        "concurrency bug (race condition)",
        "wrong error handling",
        "nil pointer",
        "goroutine leak",
    ],
    "rust": [
        "borrow checker violation",
        "wrong lifetime",
        "off-by-one",
        "incorrect iterator usage",
    ],
}

# ---------------------------------------------------------------------------
# Prompt construction
# ---------------------------------------------------------------------------

SYSTEM_PROMPT = textwrap.dedent("""\
    You are an expert software engineer who creates benchmark tasks for AI coding
    agents.  Your job is to produce a realistic, self-contained code repository
    with a deliberate bug that an AI agent must find and fix.

    You MUST respond with a single, valid JSON object and nothing else — no
    markdown fences, no prose before or after the JSON.  The object must have
    exactly these keys:

      "repo_filename"   : string — the bare filename of the main source file
                          (e.g. "ring_buffer.py", "stack.py").  No path prefix.
      "repo_code"       : string — full source of the main module, including the
                          seeded bug.  Use \\n for newlines inside the string.
      "repo_readme"     : string — README.md for the repo/ directory.  Describes
                          what the module does and its public API.  Does NOT
                          mention the bug or how to fix it.
      "prompt_md"       : string — prompt.md shown to the AI agent.  Describes
                          the observed failure symptom and what needs to be fixed,
                          but does NOT reveal which line is wrong or what the
                          correct value is.
      "tests_code"      : string — pytest file (tests/test_<module>.py).  A small
                          set of example tests that exercise the public API.
                          These tests FAIL against the buggy repo and PASS after
                          the correct fix.  The agent can see these.
      "eval_tests_code" : string — pytest file (eval_tests/test_<module>_eval.py).
                          A more thorough test suite not shown to the agent.
                          Every test FAILS against the buggy repo and PASSES after
                          the correct fix.

    Guidelines for the generated content:
    - The module should implement a recognisable data structure or algorithm.
    - The bug must be exactly of the requested category and difficulty.
    - The repo_code must be syntactically valid for the target language; the ONLY
      defect is the seeded bug.
    - prompt.md must describe the failure symptom clearly without revealing the fix.
    - Both test files must include a sys.path / import preamble appropriate for the
      target language's test runner so they can be executed from the task root.
    - Use idiomatic style for the target language throughout.
""")


def build_user_prompt(language: str, difficulty: str, category: str) -> str:
    rubric = DIFFICULTY_RUBRICS.get(difficulty, "")
    known_categories = LANGUAGE_CATEGORIES.get(language, [])
    category_note = (
        f"Known categories for {language}: {', '.join(known_categories)}."
        if known_categories
        else ""
    )

    return textwrap.dedent(f"""\
        Generate a benchmark task with the following parameters:

        Language   : {language}
        Difficulty : {difficulty}
        Bug category: {category}

        Difficulty rubric:
        {rubric}

        {category_note}

        Requirements:
        1. Choose a module name that is a short, descriptive snake_case identifier
           (e.g. "lru_cache", "min_heap", "token_bucket").
        2. Implement the module correctly first, then introduce exactly one bug of
           the requested category.
        3. The example tests (tests_code) should contain 3–6 focused tests that
           clearly demonstrate the failure.
        4. The eval tests (eval_tests_code) should be thorough — cover edge cases,
           wrap-around, empty / full states, and any other scenarios that make the
           bug unambiguously detectable.  Aim for 10–20 test cases.
        5. prompt.md must NOT contain the word "bug", the specific line number, or
           the corrected code.  Describe only what the user observes going wrong.

        Respond with a single JSON object as described in the system prompt.
    """)


# ---------------------------------------------------------------------------
# API call
# ---------------------------------------------------------------------------

def call_claude(language: str, difficulty: str, category: str) -> dict:
    """Call the Claude API and return the parsed JSON response."""
    try:
        import anthropic
    except ImportError:
        sys.exit(
            "Error: the 'anthropic' package is not installed.\n"
            "Run:  pip install anthropic"
        )

    api_key = os.environ.get("ANTHROPIC_API_KEY")
    if not api_key:
        sys.exit(
            "Error: ANTHROPIC_API_KEY environment variable is not set."
        )

    client = anthropic.Anthropic(api_key=api_key)
    user_prompt = build_user_prompt(language, difficulty, category)

    message = client.messages.create(
        model="claude-sonnet-4-6",
        max_tokens=8192,
        system=SYSTEM_PROMPT,
        messages=[{"role": "user", "content": user_prompt}],
    )

    raw_text = message.content[0].text.strip()

    # Strip markdown code fences if the model wrapped the JSON anyway.
    if raw_text.startswith("```"):
        lines = raw_text.splitlines()
        # Drop opening fence (e.g. ```json) and closing fence.
        inner_lines = []
        in_fence = False
        for line in lines:
            if line.startswith("```") and not in_fence:
                in_fence = True
                continue
            if line.startswith("```") and in_fence:
                break
            if in_fence:
                inner_lines.append(line)
        raw_text = "\n".join(inner_lines)

    try:
        data = json.loads(raw_text)
    except json.JSONDecodeError as exc:
        sys.exit(
            f"Error: Claude returned content that could not be parsed as JSON.\n"
            f"Parse error: {exc}\n\n"
            f"Raw response:\n{raw_text[:2000]}"
        )

    required_keys = {
        "repo_filename",
        "repo_code",
        "repo_readme",
        "prompt_md",
        "tests_code",
        "eval_tests_code",
    }
    missing = required_keys - set(data.keys())
    if missing:
        sys.exit(
            f"Error: Claude's JSON response is missing required keys: "
            f"{', '.join(sorted(missing))}"
        )

    return data


# ---------------------------------------------------------------------------
# File writing
# ---------------------------------------------------------------------------

def derive_module_name(repo_filename: str) -> str:
    """Return the bare module name without extension (e.g. 'ring_buffer')."""
    return os.path.splitext(os.path.basename(repo_filename))[0]


def write_task(output_dir: str, data: dict) -> None:
    """Write all task files to output_dir."""
    repo_filename = data["repo_filename"]
    module_name = derive_module_name(repo_filename)

    files = {
        os.path.join("repo", repo_filename): data["repo_code"],
        os.path.join("repo", "README.md"): data["repo_readme"],
        "prompt.md": data["prompt_md"],
        os.path.join("tests", f"test_{module_name}.py"): data["tests_code"],
        os.path.join("eval_tests", f"test_{module_name}_eval.py"): data["eval_tests_code"],
    }

    for rel_path, content in files.items():
        abs_path = os.path.join(output_dir, rel_path)
        os.makedirs(os.path.dirname(abs_path), exist_ok=True)
        with open(abs_path, "w", encoding="utf-8") as fh:
            # Ensure file ends with a newline.
            fh.write(content if content.endswith("\n") else content + "\n")
        print(f"  wrote  {os.path.join(output_dir, rel_path)}")


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Generate a new benchmark task using the Claude API.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=textwrap.dedent("""\
            Examples:
              python tools/generate_task.py \\
                  --language python \\
                  --difficulty easy \\
                  --category "off-by-one bug" \\
                  --output benchmark/v1.0/tasks/python/easy/task_002

              # Print the LLM prompt without calling the API:
              python tools/generate_task.py \\
                  --language python \\
                  --difficulty easy \\
                  --category "off-by-one bug" \\
                  --output benchmark/v1.0/tasks/python/easy/task_002 \\
                  --dry-run
        """),
    )
    parser.add_argument(
        "--language",
        required=True,
        choices=list(LANGUAGE_CATEGORIES.keys()),
        help="Target programming language.",
    )
    parser.add_argument(
        "--difficulty",
        required=True,
        choices=list(DIFFICULTY_RUBRICS.keys()),
        help="Task difficulty tier.",
    )
    parser.add_argument(
        "--category",
        required=True,
        help="Bug category (e.g. 'off-by-one bug', 'wrong conditional').",
    )
    parser.add_argument(
        "--output",
        required=True,
        help="Path to the output task directory (will be created).",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help=(
            "Print the system prompt and user prompt that would be sent to "
            "Claude, then exit without calling the API or writing any files."
        ),
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()

    if args.dry_run:
        user_prompt = build_user_prompt(args.language, args.difficulty, args.category)
        separator = "=" * 72
        print(separator)
        print("SYSTEM PROMPT")
        print(separator)
        print(SYSTEM_PROMPT)
        print()
        print(separator)
        print("USER PROMPT")
        print(separator)
        print(user_prompt)
        print()
        print(separator)
        print(
            f"[dry-run] Would call claude-sonnet-4-6 and write files to: {args.output}"
        )
        return

    if os.path.exists(args.output):
        sys.exit(
            f"Error: output directory already exists: {args.output}\n"
            "Choose a different --output path or remove the existing directory."
        )

    print(
        f"Generating {args.difficulty} {args.language} task "
        f"(category: {args.category}) …"
    )

    data = call_claude(args.language, args.difficulty, args.category)

    print(f"Writing task files to: {args.output}")
    write_task(args.output, data)

    module_name = derive_module_name(data["repo_filename"])
    print()
    print("Done.  Before committing, verify:")
    print(f"  1. pytest {args.output}/tests/          FAILS on the unmodified repo")
    print(f"  2. pytest {args.output}/eval_tests/     FAILS on the unmodified repo")
    print(f"  3. After applying the correct fix, both test suites pass")
    print(f"  4. The fix respects the '{args.difficulty}' difficulty rubric")
    print(f"  5. prompt.md describes the symptom without revealing the fix")


if __name__ == "__main__":
    main()
