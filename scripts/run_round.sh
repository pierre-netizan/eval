#!/usr/bin/env bash
# arsguard-eval Manual Round Runner
# 固定任务: 用户发命令就跑，支持多轮次 + 结果分析
#
# 用法:
#   bash run_round.sh                          # 跑 1 轮
#   bash run_round.sh --rounds 5               # 跑 5 轮
#   bash run_round.sh --rounds 3 --n 500       # 3 轮，每周期 500 攻击
#   bash run_round.sh --rounds 2 --seed 42     # 2 轮，固定种子
#   bash run_round.sh --analyze                # 仅分析最后一轮，不跑测试
#   bash run_round.sh --rounds 1 --no-analyze  # 跑 1 轮，不分析
#
# 流程:
#   1. 运行 run.sh (4 周期: promptfoo → asb → hackmyagent → joint)
#   2. 自动检测轮次编号
#   3. 运行 round_analyzer.py 分析绕过和误报
#   4. 输出结果并建议修复

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
EVAL_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"
PROJ_DIR="$(cd "$EVAL_DIR/.." && pwd)"

# --- 默认值 ---
ROUNDS=1
N=1000
SEED=""
MODEL="qwen3-0.6b"
DO_ANALYZE=true
ANALYZE_ONLY=false

# --- 参数解析 ---
while [[ $# -gt 0 ]]; do
    case "$1" in
        --rounds)   ROUNDS="$2";   shift 2 ;;
        --n)        N="$2";        shift 2 ;;
        --seed)     SEED="--seed $2"; shift 2 ;;
        --model)    MODEL="$2";    shift 2 ;;
        --no-analyze) DO_ANALYZE=false; shift ;;
        --analyze)  ANALYZE_ONLY=true;   shift ;;
        *)
            echo "Unknown: $1"
            echo "Usage: bash $0 [--rounds N] [--n 1000] [--seed N] [--model qwen3-0.6b] [--no-analyze] [--analyze]"
            exit 1
            ;;
    esac
done

# --- 分析模式: 只分析最后一轮 ---
if $ANALYZE_ONLY; then
    RESULTS_DIR="$PROJ_DIR/data-results"
    LAST=$(ls -d "$RESULTS_DIR"/round[0-9]* 2>/dev/null | grep -oP 'round\K\d+' | sort -n | tail -1)
    if [ -z "$LAST" ]; then
        echo "No previous rounds found in $RESULTS_DIR/"
        exit 1
    fi
    echo "=== Analyzing round $LAST ==="
    python3 "$EVAL_DIR/scripts/round_analyzer.py" --round "$LAST"
    exit 0
fi

# --- 逐轮运行 ---
for ((i = 1; i <= ROUNDS; i++)); do
    echo ""
    echo "╔══════════════════════════════════════════════╗"
    echo "║  Running round $i of $ROUNDS"
    echo "╚══════════════════════════════════════════════╝"
    echo ""

    bash "$EVAL_DIR/scripts/run.sh" --mode all --n "$N" $SEED --model "$MODEL"
done

# --- 分析最后一轮的绕过/误报 ---
if $DO_ANALYZE; then
    RESULTS_DIR="$PROJ_DIR/data-results"
    LAST=$(ls -d "$RESULTS_DIR"/round[0-9]* 2>/dev/null | grep -oP 'round\K\d+' | sort -n | tail -1)

    if [ -n "$LAST" ]; then
        echo ""
        echo "=== Analyzing round $LAST ==="
        python3 "$EVAL_DIR/scripts/round_analyzer.py" --round "$LAST"
    fi
fi

echo ""
echo "Done — $ROUNDS round(s) completed."
