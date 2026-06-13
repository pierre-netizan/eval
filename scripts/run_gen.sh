#!/usr/bin/env bash
# Gen Phase: Generate attack test cases using the specified runner.
# Runner 可扩展：新建 runners/<name>_runner.py 后在此传入 --runner <name>。
#
# Usage: bash eval/scripts/run_gen.sh [direct|promptfoo]
set -euo pipefail
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
EVAL_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"
cd "$EVAL_DIR"

RUNNER="${1:-direct}"
echo "[gen] Gen Phase — runner: $RUNNER"
python3 scripts/run.py --runner "$RUNNER" --phase gen --verbose
