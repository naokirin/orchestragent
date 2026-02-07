#!/usr/bin/env bash
# Format edited Python files with Ruff (or Black) when available.
# Receives JSON on stdin from Claude Code's PostToolUse hook; extracts file_path and runs formatter.
set -euo pipefail
input=$(cat)

# Extract file_path from JSON using jq (preferred) or python3 as fallback
if command -v jq &>/dev/null; then
  file_path=$(printf '%s' "$input" | jq -r '.file_path // empty' 2>/dev/null) || exit 0
elif command -v python3 &>/dev/null; then
  file_path=$(printf '%s' "$input" | python3 -c "import sys,json; d=json.load(sys.stdin); print(d.get('file_path',''))" 2>/dev/null) || exit 0
else
  exit 0
fi

if [[ -z "$file_path" ]]; then
  exit 0
fi
case "$file_path" in
  *.py) ;;
  *) exit 0 ;;
esac
[[ -f "$file_path" ]] || exit 0

root="${CLAUDE_PROJECT_DIR:-.}"
if command -v ruff &>/dev/null; then
  (cd "$root" && ruff format "$file_path" 2>/dev/null) || true
elif command -v black &>/dev/null; then
  (cd "$root" && black "$file_path" 2>/dev/null) || true
fi
exit 0
