#!/usr/bin/env bash
# Eval Phase: Run attack tests against arsguard security hooks.
# 此阶段连接 Squid + OpenClaw（需先启动 docker-compose），
# 或使用 direct runner 在本地直接调用 arsguard 钩子。
#
# Usage: bash eval/scripts/run_eval.sh [direct|promptfoo]
set -euo pipefail
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
EVAL_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"
cd "$EVAL_DIR"

RUNNER="${1:-direct}"
echo "[eval] Eval Phase — runner: $RUNNER"
python3 scripts/run.py --runner "$RUNNER" --phase eval --verbose
