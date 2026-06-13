#!/usr/bin/env bash
# Run gen/eval/report for a single tool.
# Usage: bash scripts/run_tool.sh <tool_name>
#   tool_name: hackmyagent, asb, promptfoo
set -euo pipefail
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
EVAL_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"
cd "$EVAL_DIR"

TOOL="${1:?Usage: $0 <tool_name> (hackmyagent|asb|promptfoo)}"

echo "=============================================="
echo "  Tool: $TOOL — Gen → Eval → Report"
echo "=============================================="

echo ""
echo "══════════════════════════════════════════════"
echo "  Phase 1/3: Gen ($TOOL)"
echo "══════════════════════════════════════════════"
python3 "$SCRIPT_DIR/test_comprehensive.py" --tool "$TOOL" 2>&1 | head -20
echo ""

echo "══════════════════════════════════════════════"
echo "  Phase 2/3: Eval ($TOOL)"
echo "══════════════════════════════════════════════"
python3 "$SCRIPT_DIR/test_comprehensive.py" --tool "$TOOL" 2>&1 | grep -E "(Phase|intercept|BLOCKED|BYPASSED|Total|拦截)"
echo ""

echo "══════════════════════════════════════════════"
echo "  Phase 3/3: Report ($TOOL)"
echo "══════════════════════════════════════════════"
ls -lh data/gen_attacks_${TOOL}.json data/gen_report_${TOOL}.json data/eval_results_${TOOL}.json data/eval_report_${TOOL}.json data/report_${TOOL}.* 2>/dev/null
echo ""

echo "=============================================="
echo "  $TOOL done. See data/ directory for files."
echo "=============================================="
