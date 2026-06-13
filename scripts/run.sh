#!/usr/bin/env bash
# arsguard-eval Unified Test Entry Point
# 输出到 data-results/round<X>/，支持自动轮次递增
#
# 用法:
#   bash run.sh                                                 # 自动下一轮，运行全部 4 周期
#   bash run.sh --mode promptfoo                                # 仅 promptfoo
#   bash run.sh --mode asb --n 500                              # ASB 500 轮
#   bash run.sh --mode joint --seed 42                          # 混合模式固定种子
#   bash run.sh --round 3                                       # 指定轮次编号
#
# 输出结构:
#   data-results/round<X>/
#     logs/
#     promptfoo/  (gen/  eval/  report/)
#     asb/        (gen/  eval/  report/)
#     hackmyagent/ (gen/  eval/  report/)
#     joint/      (gen/  eval/  report/)

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
EVAL_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"
PROJ_DIR="$(cd "$EVAL_DIR/.." && pwd)"

# --- 默认值 ---
MODE="all"
N=1000
SEED=""
MODEL="qwen3-0.6b"
ROUND=""       # 空 = 自动递增

# --- 参数解析 ---
while [[ $# -gt 0 ]]; do
    case "$1" in
        --mode)   MODE="$2";   shift 2 ;;
        --n)      N="$2";      shift 2 ;;
        --seed)   SEED="--seed $2"; shift 2 ;;
        --model)  MODEL="$2";  shift 2 ;;
        --round)  ROUND="$2";  shift 2 ;;
        *)
            echo "Unknown: $1"
            echo "Usage: bash $0 [--mode all|promptfoo|asb|hackmyagent|joint] [--n 1000] [--seed N] [--model qwen3-0.6b] [--round X]"
            exit 1
            ;;
    esac
done

# --- 确定轮次编号 ---
RESULTS_DIR="$PROJ_DIR/data-results"
mkdir -p "$RESULTS_DIR"

if [ -z "$ROUND" ]; then
    # 自动递增: 找最大 round<数字>，+1
    LAST=$(ls -d "$RESULTS_DIR"/round[0-9]* 2>/dev/null | grep -oP 'round\K\d+' | sort -n | tail -1)
    ROUND=$((LAST + 1))
fi

OUTPUT_DIR="$RESULTS_DIR/round$ROUND"
LOG_DIR="$OUTPUT_DIR/logs"
mkdir -p "$OUTPUT_DIR" "$LOG_DIR"

echo "=============================================="
echo "  arsguard-eval — Round $ROUND"
echo "=============================================="
echo "  mode:   $MODE"
echo "  n:      $N"
echo "  seed:   ${SEED:-<random>}"
echo "  model:  $MODEL"
echo "  output: $OUTPUT_DIR/"
echo "  logs:   $LOG_DIR/"
echo "=============================================="
echo ""

# --- 执行 test_cycle.py ---
cd "$PROJ_DIR"
python3 "$EVAL_DIR/scripts/test_cycle.py" \
    --cycle "$MODE" \
    --n "$N" \
    $SEED \
    --model "$MODEL" \
    --output "$OUTPUT_DIR" 2>&1 | tee -a "$LOG_DIR/cycle_combined.log"

echo ""
echo "=============================================="
echo "  Round $ROUND Complete"
echo "=============================================="
echo "  Output: $OUTPUT_DIR/"
ls -1 "$OUTPUT_DIR"/*/ 2>/dev/null | while read -r d; do
    echo "    $(basename "$(dirname "$d")")/  (gen/  eval/  report/)"
done
echo "  Logs:   $LOG_DIR/"
