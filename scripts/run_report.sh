#!/usr/bin/env bash
# Report Phase: Generate test report in all formats (Markdown, HTML, LaTeX, PDF).
# 输出到 data/report.{md,html,tex,pdf}，依赖 TeXLive (xelatex) 生成 PDF。
#
# Usage: bash eval/scripts/run_report.sh [direct|promptfoo]
set -euo pipefail
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
EVAL_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"
cd "$EVAL_DIR"

RUNNER="${1:-direct}"
echo "[report] Report Phase — runner: $RUNNER"
echo "[report] Formats: report.md, report.html, report.tex, report.pdf"
python3 scripts/run.py --runner "$RUNNER" --phase report --verbose

echo ""
echo "[report] Output files:"
ls -lh data/report.* 2>/dev/null || echo "  (no report files found)"
