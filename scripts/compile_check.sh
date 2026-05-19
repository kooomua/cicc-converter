#!/usr/bin/env bash
set -euo pipefail

# Usage: compile_check.sh <path/to/manuscript.tex>
# Runs pdflatex twice, summarises errors/warnings, saves log to run_log/.

if [[ $# -ne 1 ]]; then
    echo "Usage: $0 <path/to/manuscript.tex>"
    exit 1
fi

TEX_FILE="$(realpath "$1")"
if [[ ! -f "$TEX_FILE" ]]; then
    echo "Error: file not found: $TEX_FILE"
    exit 1
fi

TEX_DIR="$(dirname "$TEX_FILE")"
TEX_BASE="$(basename "$TEX_FILE" .tex)"
TIMESTAMP="$(date +%Y%m%d_%H%M%S)"

# Resolve run_log/ relative to this script's location (project root)
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"
RUN_LOG_DIR="$PROJECT_ROOT/run_log/$TIMESTAMP"
mkdir -p "$RUN_LOG_DIR"

LOG_FILE="$RUN_LOG_DIR/compile.log"
COMBINED_LOG=""

echo "Compiling: $TEX_FILE"
echo "Log:       $LOG_FILE"
echo ""

run_pdflatex() {
    local pass="$1"
    echo "--- pdflatex pass $pass ---"
    local out
    out=$(cd "$TEX_DIR" && pdflatex \
        -interaction=nonstopmode \
        -halt-on-error \
        "$TEX_BASE.tex" 2>&1 || true)
    COMBINED_LOG+="$out"$'\n'
    echo "$out"
}

run_pdflatex 1
run_pdflatex 2

# Save full combined log
printf '%s' "$COMBINED_LOG" > "$LOG_FILE"

# Parse errors and warnings
ERROR_COUNT=$(printf '%s' "$COMBINED_LOG" | grep -c '^!' || true)
WARNING_COUNT=$(printf '%s' "$COMBINED_LOG" | grep -cE '^(LaTeX Warning|Package warning|Overfull|Underfull)' || true)

echo ""
echo "=================================================="
if [[ "$ERROR_COUNT" -gt 0 ]]; then
    echo "RESULT: FAIL"
    echo "Errors:   $ERROR_COUNT"
    echo "Warnings: $WARNING_COUNT"
    echo "Full log: $LOG_FILE"
    echo "=================================================="
    exit 1
else
    echo "RESULT: PASS"
    echo "Errors:   0"
    echo "Warnings: $WARNING_COUNT"
    echo "Full log: $LOG_FILE"
    echo "=================================================="
    exit 0
fi
