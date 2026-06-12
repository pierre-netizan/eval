#!/usr/bin/env bash
# Gen Phase: Generate test cases
set -euo pipefail
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
EVAL_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"
cd "$EVAL_DIR"

RUNNER="${1:-direct}"
echo "[gen] Gen Phase — runner: $RUNNER"
python3 scripts/run.py --runner "$RUNNER" --phase gen --verbose
