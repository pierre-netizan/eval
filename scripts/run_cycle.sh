#!/usr/bin/env bash
# 4-Cycle test runner.
# Runs one or all of: promptfoo-only, asb-only, hackmyagent-only, joint
#
# Usage:
#   bash scripts/run_cycle.sh                    # All 4 cycles
#   bash scripts/run_cycle.sh --cycle asb        # Single cycle
#   bash scripts/run_cycle.sh --n 500            # 500 attacks per cycle
#   bash scripts/run_cycle.sh --seed 42          # Deterministic
set -euo pipefail
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
EVAL_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"
cd "$EVAL_DIR"

N=1000
CYCLE="all"
SEED=""

while [[ $# -gt 0 ]]; do
    case "$1" in
        --n) N="$2"; shift 2 ;;
        --cycle) CYCLE="$2"; shift 2 ;;
        --seed) SEED="--seed $2"; shift 2 ;;
        *) echo "Usage: $0 [--n N] [--cycle promptfoo|asb|hackmyagent|joint|all] [--seed N]"; exit 1 ;;
    esac
done

echo "=============================================="
echo "  arsguard 4-Cycle Test"
echo "  Attacks/cycle: $N"
echo "  Cycles: $CYCLE"
echo "=============================================="
echo ""

python3 scripts/test_cycle.py --n "$N" --cycle "$CYCLE" $SEED

echo ""
echo "=============================================="
echo "  Done. Data in data/<cycle>/{gen,eval,report}/"
echo "=============================================="

# Show file listing
for d in "$EVAL_DIR/data"/promptfoo "$EVAL_DIR/data"/asb "$EVAL_DIR/data"/hackmyagent "$EVAL_DIR/data"/joint; do
    if [ -d "$d" ]; then
        echo "  $(basename $d)/:"
        for sub in gen eval report; do
            count=$(ls "$d/$sub" 2>/dev/null | wc -l)
            echo "    $sub/: $count files"
        done
    fi
done
