#!/usr/bin/env bash
# Report Phase: Generate test report
set -euo pipefail
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
EVAL_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"
cd "$EVAL_DIR"

RUNNER="${1:-direct}"
echo "[report] Report Phase — runner: $RUNNER"
python3 scripts/run.py --runner "$RUNNER" --phase report --verbose
