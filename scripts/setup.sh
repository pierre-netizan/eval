#!/usr/bin/env bash
# Setup script: install dependencies for the eval project
set -euo pipefail
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
EVAL_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"

cd "$EVAL_DIR"

echo "=============================================="
echo "  arsguard-eval Setup"
echo "=============================================="

# Python deps
if [ -f pyproject.toml ]; then
    echo "  Installing Python dependencies..."
    pip install -e . 2>/dev/null || pip install pyyaml jsonschema 2>/dev/null || true
fi

# Check for inotifywait
if ! command -v inotifywait &>/dev/null; then
    echo ""
    echo "  [WARNING] inotifywait not found."
    echo "  Install inotify-tools for auto-test watch mode:"
    echo "    sudo apt install inotify-tools   # Debian/Ubuntu"
    echo "    sudo yum install inotify-tools   # RHEL/CentOS"
    echo ""
fi

# Check for xelatex
if ! command -v xelatex &>/dev/null; then
    echo "  [WARNING] xelatex not found."
    echo "  Install texlive for PDF report generation:"
    echo "    sudo apt install texlive-xetex texlive-lang-chinese"
    echo ""
fi

echo ""
echo "  Setup complete."
echo ""
echo "  Available commands:"
echo "    python3 scripts/test_comprehensive.py         # Run all tests"
echo "    python3 scripts/test_comprehensive.py --tool asb  # Single tool"
echo "    bash scripts/run_all.sh                       # Full pipeline"
echo "    bash scripts/run_tool.sh asb                  # Single tool pipeline"
echo "    bash scripts/run_watch.sh                     # Auto-test on changes"
echo "    bash scripts/run_watch.sh --once              # Single test run"
echo "=============================================="
