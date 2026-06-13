#!/usr/bin/env bash
# arsguard-eval: run Gen → Eval → Report for ALL tools (original pipeline).
#
# 此脚本调用 test_comprehensive.py 分 5 阶段执行，每阶段 grep 过滤关键输出。
# 如需新的 4 周期模式（promptfoo-only/asb-only/hackmyagent-only/joint），
# 请使用 run.sh：
#   bash eval/scripts/run.sh --mode all
#
# Usage: bash eval/scripts/run_all.sh [--tool <tool_name>]
set -euo pipefail
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
EVAL_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"
cd "$EVAL_DIR"

TOOL_FLAG=""
if [ "${1:-}" = "--tool" ] && [ -n "${2:-}" ]; then
    TOOL_FLAG="--tool $2"
    echo "  Single tool mode: $2"
fi

echo "=============================================="
echo "  arsguard-eval — Gen → Eval → Report"
echo "=============================================="
echo ""

echo "══════════════════════════════════════════════"
echo "  Phase 1/5: Gen — 生成攻击测试用例"
echo "══════════════════════════════════════════════"
python3 "$SCRIPT_DIR/test_comprehensive.py" $TOOL_FLAG 2>&1 | grep -E "(Phase 1|attacks ->|^  [a-z])"
echo ""

echo "══════════════════════════════════════════════"
echo "  Phase 2/5: Eval — 测试拦截效果"
echo "══════════════════════════════════════════════"
python3 "$SCRIPT_DIR/test_comprehensive.py" $TOOL_FLAG 2>&1 | grep -E "(Phase 2|intercept|BLOCKED|BYPASSED|^  [a-z])"
echo ""

echo "══════════════════════════════════════════════"
echo "  Phase 3/5: 合并统计"
echo "══════════════════════════════════════════════"
python3 "$SCRIPT_DIR/test_comprehensive.py" $TOOL_FLAG 2>&1 | grep -E "(Phase 3|summary|^    [a-z])"
echo ""

echo "══════════════════════════════════════════════"
echo "  Phase 4/5: Report — 按工具生成"
echo "══════════════════════════════════════════════"
python3 "$SCRIPT_DIR/test_comprehensive.py" $TOOL_FLAG 2>&1 | grep -E "(Phase 4|Phase 5|\[md\]|\[html\]|\[tex\]|\[pdf\])"
echo ""

echo "══════════════════════════════════════════════"
echo "  Phase 5/5: 输出文件"
echo "══════════════════════════════════════════════"
ls -lh data/gen_attacks_*.json data/gen_report_*.json data/eval_results_*.json data/eval_report_*.json data/report_*.md 2>/dev/null
echo ""

echo "=============================================="
echo "  全流程完成"
echo "=============================================="
