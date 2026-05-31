#!/usr/bin/env bash
set -euo pipefail

TASK_DIR=""
TIMEOUT=""
LANGUAGE=""
DIFFICULTY=""

while [[ $# -gt 0 ]]; do
    case "$1" in
        --task-dir)   TASK_DIR="$2";   shift 2 ;;
        --timeout)    TIMEOUT="$2";    shift 2 ;;
        --language)   LANGUAGE="$2";   shift 2 ;;
        --difficulty) DIFFICULTY="$2"; shift 2 ;;
        *) echo "Unknown argument: $1" >&2; exit 1 ;;
    esac
done

PROMPT_FILE="${TASK_DIR}/prompt.md"
REPO_DIR="${TASK_DIR}/repo"
TMP_OUT=$(mktemp)

cd "$REPO_DIR"

EXIT_CODE=0
timeout "$TIMEOUT" claude \
    -p "$(cat "$PROMPT_FILE")" \
    --allowedTools "Edit,Write,Read,Bash,Glob,Grep,MultiEdit" \
    --output-format json \
    >"$TMP_OUT" \
    || EXIT_CODE=$?

if [[ $EXIT_CODE -eq 124 ]]; then
    echo '{"steps": 0, "tokens": 0}'
    exit 124
fi

STEPS=$(jq '.num_turns // 0' "$TMP_OUT" 2>/dev/null || echo 0)
TOKENS=$(jq '(.usage.input_tokens // 0) + (.usage.output_tokens // 0)' "$TMP_OUT" 2>/dev/null || echo 0)

echo "{\"steps\": ${STEPS}, \"tokens\": ${TOKENS}}"
exit "$EXIT_CODE"
