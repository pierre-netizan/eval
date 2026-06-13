#!/usr/bin/env bash
# Auto-test watch script.
# Watches arsguard hook files and eval project for changes, auto-runs tests.
# Usage:
#   bash scripts/run_watch.sh              # watch + run all tests on change
#   bash scripts/run_watch.sh --once        # run all tests once, no watch
#   bash scripts/run_watch.sh --tool asb    # watch + run only asb tests
#
# Requires: inotifywait (from inotify-tools) for watch mode
# Falls back to: polling mode if inotifywait not available
set -euo pipefail
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
EVAL_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"
PROJECT_DIR="$(cd "$EVAL_DIR/.." && pwd)"

cd "$EVAL_DIR"

ONCE=false
TOOL_FLAG=""

for arg in "$@"; do
    case "$arg" in
        --once) ONCE=true ;;
        --tool=*) TOOL_FLAG="--tool ${arg#*=}" ;;
        --help|-h)
            echo "Usage: $0 [--once] [--tool=<name>]"
            echo "  --once        Run tests once and exit (no watch)"
            echo "  --tool=<name> Run only a specific tool (hackmyagent|asb|promptfoo)"
            exit 0
            ;;
    esac
done

run_tests() {
    echo ""
    echo "=============================================="
    echo "  $(date '+%Y-%m-%d %H:%M:%S') — Running tests..."
    echo "=============================================="
    python3 "$SCRIPT_DIR/test_comprehensive.py" $TOOL_FLAG 2>&1 | \
        grep -E "(Phase|intercept|Total|attacks ->|summary|Rate|\[md\]|\[html\]|\[tex\]|\[pdf\])"
    echo ""
    echo "  $(date '+%Y-%m-%d %H:%M:%S') — Tests complete"
    echo "=============================================="
}

# Run once if --once flag
if $ONCE; then
    run_tests
    exit $?
fi

echo "=============================================="
echo "  Auto-Test Watch Script"
echo "  Watching:"
echo "    - $EVAL_DIR/runners/"
echo "    - $EVAL_DIR/lib/"
echo "    - $EVAL_DIR/report/"
echo "    - $PROJECT_DIR/arsguard/src/plugins/hooks/"
echo ""
echo "  Test run: tests all tools on file change"
echo "  Press Ctrl+C to stop"
echo "=============================================="

# Initial test run
run_tests

# Determine watch method
if command -v inotifywait &>/dev/null; then
    echo "  Using inotifywait for file watching..."
    echo ""
    while true; do
        inotifywait -q -e modify -e create -e delete \
            "$EVAL_DIR/runners" \
            "$EVAL_DIR/lib" \
            "$EVAL_DIR/report" \
            "$EVAL_DIR/scripts" \
            "$PROJECT_DIR/arsguard/src/plugins/hooks" \
            "$PROJECT_DIR/arsguard/src/plugins" \
            "$PROJECT_DIR/arsguard/src" \
            2>/dev/null
        sleep 1
        run_tests
    done
else
    echo "  inotifywait not found."
    echo "  Install inotify-tools for efficient file watching:"
    echo "    apt install inotify-tools   # Debian/Ubuntu"
    echo "    yum install inotify-tools   # RHEL/CentOS"
    echo ""
    echo "  Falling back to polling mode (check every 5 seconds)..."
    echo ""
    # Polling mode: use find -newer to detect changes
    LAST_RUN=$(date +%s)
    while true; do
        sleep 5
        CHANGED=$(find \
            "$EVAL_DIR/runners/" \
            "$EVAL_DIR/lib/" \
            "$EVAL_DIR/report/" \
            "$EVAL_DIR/scripts/" \
            "$PROJECT_DIR/arsguard/src/plugins/hooks/" \
            "$PROJECT_DIR/arsguard/src/plugins/" \
            "$PROJECT_DIR/arsguard/src/arsguard.py" \
            -type f -newer "$EVAL_DIR/.watch_timestamp" 2>/dev/null || true)
        if [ -n "$CHANGED" ]; then
            run_tests
            touch "$EVAL_DIR/.watch_timestamp"
        fi
    done
fi
