#!/usr/bin/env bash
# arsguard-eval 全流程：Gen → Eval → Report
set -euo pipefail
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
EVAL_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"
cd "$EVAL_DIR"

RUNNER="${1:-direct}"
echo "=============================================="
echo "  arsguard-eval — Gen → Eval → Report"
echo "  Runner: $RUNNER"
echo "=============================================="
echo ""

echo "══════════════════════════════════════════════"
echo "  Phase 1/3: Gen — 生成攻击测试用例"
echo "══════════════════════════════════════════════"
bash "$SCRIPT_DIR/run_gen.sh" "$RUNNER"

echo ""
echo "══════════════════════════════════════════════"
echo "  Phase 2/3: Eval — 测试拦截效果"
echo "══════════════════════════════════════════════"
bash "$SCRIPT_DIR/run_eval.sh" "$RUNNER"

echo ""
echo "══════════════════════════════════════════════"
echo "  Phase 3/3: Report — 生成测试报告"
echo "══════════════════════════════════════════════"
bash "$SCRIPT_DIR/run_report.sh" "$RUNNER"

echo ""
echo "=============================================="
echo "  全流程完成"
echo "  报告: $(realpath "$EVAL_DIR/data/report.md")"
echo "=============================================="
