#!/usr/bin/env bash
# Compile LaTeX report to PDF using xelatex with CJK support
set -euo pipefail
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
EVAL_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"

TEX_FILE="${1:-$EVAL_DIR/data/report.tex}"
PDF_DIR="$(dirname "$TEX_FILE")"
PDF_FILE="${PDF_DIR}/report.pdf"

if [ ! -f "$TEX_FILE" ]; then
    echo "[pdf] ERROR: $TEX_FILE not found"
    echo "[pdf] Run 'bash scripts/run_report.sh' to generate .tex first"
    exit 1
fi

if ! command -v xelatex &>/dev/null; then
    echo "[pdf] xelatex not found. Installing TeX Live..."
    if command -v apt-get &>/dev/null; then
        sudo apt-get update && sudo apt-get install -y texlive-xetex texlive-lang-chinese texlive-fonts-extra
    elif command -v brew &>/dev/null; then
        brew install texlive
    else
        echo "Please install TeX Live manually: https://www.tug.org/texlive/"
        exit 1
    fi
fi

echo "[pdf] Compiling $TEX_FILE → $PDF_DIR/report.pdf"
cp "$TEX_FILE" "$PDF_DIR/report.tex"
cd "$PDF_DIR"

xelatex -interaction=nonstopmode -output-directory="$PDF_DIR" report.tex 2>&1 || true

# Remove auxiliary files
rm -f report.aux report.log report.out

echo "[pdf] Done: $PDF_FILE"
ls -lh "$PDF_FILE"
