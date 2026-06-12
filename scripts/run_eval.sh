#!/usr/bin/env bash
# Eval Phase: Run tests against arsguard
set -euo pipefail
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
EVAL_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"
cd "$EVAL_DIR"

RUNNER="${1:-direct}"
echo "[eval] Eval Phase — runner: $RUNNER"
python3 scripts/run.py --runner "$RUNNER" --phase eval --verbose
