#!/usr/bin/env bash
# arsguard-eval Cron Job Setup
# 定时任务: 在固定时间自动运行测试
#
# 用法:
#   bash setup_cron.sh                          # 交互式设置
#   bash setup_cron.sh --daily                  # 每天 02:00 运行
#   bash setup_cron.sh --weekly                 # 每周一 02:00 运行
#   bash setup_cron.sh --hourly                 # 每小时运行
#   bash setup_cron.sh --custom "0 3 * * 1-5"   # 自定义 cron 表达式
#   bash setup_cron.sh --remove                 # 删除已安装的 cron 任务
#   bash setup_cron.sh --status                 # 查看当前安装状态
#
# 定时任务执行:
#   1. 运行 4 周期测试 (n=1000, 自动种子)
#   2. 运行分析器生成报告
#   3. 日志输出到 data-results/round<X>/logs/
#   4. 结果可通过 data-results/round<X>/report/ 查看

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
EVAL_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"
PROJ_DIR="$(cd "$EVAL_DIR/.." && pwd)"
CRON_LABEL="# arsguard-eval-cron"

# --- 构建 cron 命令 ---
RUN_CMD="cd $PROJ_DIR && bash $EVAL_DIR/scripts/run_round.sh --rounds 1 --no-analyze >> $PROJ_DIR/data-results/cron.log 2>&1 && bash $EVAL_DIR/scripts/round_analyzer.py --round \$(ls -d $PROJ_DIR/data-results/round[0-9]* | grep -oP 'round\\K\\d+' | sort -n | tail -1) >> $PROJ_DIR/data-results/cron.log 2>&1"

# --- 参数解析 ---
MODE="${1:-interactive}"

case "$MODE" in
    --daily)
        CRON_EXPR="0 2 * * *"
        ;;
    --weekly)
        CRON_EXPR="0 2 * * 1"
        ;;
    --hourly)
        CRON_EXPR="0 * * * *"
        ;;
    --custom)
        CRON_EXPR="$2"
        ;;
    --remove)
        echo "Removing cron job..."
        (crontab -l 2>/dev/null | grep -v "$CRON_LABEL") | crontab - || true
        echo "Done. Cron job removed."
        exit 0
        ;;
    --status)
        echo "Current arsguard cron jobs:"
        crontab -l 2>/dev/null | grep "$CRON_LABEL" || echo "  (none installed)"
        exit 0
        ;;
    interactive|*)
        echo "Arsguard-eval Cron Setup"
        echo "========================"
        echo "1) Daily (02:00)"
        echo "2) Weekly (Monday 02:00)"
        echo "3) Hourly"
        echo "4) Custom cron expression"
        echo "5) Remove existing"
        echo "6) Show status"
        echo ""
        read -rp "Choose [1-6]: " choice
        case "$choice" in
            1) CRON_EXPR="0 2 * * *" ;;
            2) CRON_EXPR="0 2 * * 1" ;;
            3) CRON_EXPR="0 * * * *" ;;
            4) read -rp "Enter cron expression (e.g. '0 3 * * 1-5'): " CRON_EXPR ;;
            5) exec bash "$0" --remove ;;
            6) exec bash "$0" --status ;;
            *) echo "Invalid"; exit 1 ;;
        esac
        ;;
esac

if [ -z "${CRON_EXPR:-}" ]; then
    echo "Error: no cron expression provided"
    exit 1
fi

# --- 安装 cron 任务 ---
CRON_LINE="$CRON_EXPR $CRON_LABEL $RUN_CMD"

# 检查是否已存在，替换或追加
if crontab -l 2>/dev/null | grep -q "$CRON_LABEL"; then
    (crontab -l 2>/dev/null | sed "\|$CRON_LABEL|d") > /tmp/cron_new.txt
    echo "$CRON_LINE" >> /tmp/cron_new.txt
    crontab /tmp/cron_new.txt
    echo "Updated existing cron job."
else
    (crontab -l 2>/dev/null; echo "$CRON_LINE") | crontab -
    echo "Installed new cron job."
fi

echo ""
echo "Cron expression: $CRON_EXPR"
echo "Command:"
echo "  $RUN_CMD"
echo ""
echo "Logs: $PROJ_DIR/data-results/cron.log"
echo ""
echo "To view: crontab -l"
echo "To remove: bash $0 --remove"
