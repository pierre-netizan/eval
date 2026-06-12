#!/usr/bin/env bash
# Setup test environment: Docker + Ollama models
set -euo pipefail
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
EVAL_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"
cd "$EVAL_DIR"

echo "[setup] Starting test environment ..."

# 1. Pull Ollama models
echo "[setup] Pulling Ollama models ..."
ollama pull qwen3-0.6b 2>/dev/null || echo "  qwen3-0.6b: skip (already exists or Ollama not available)"
ollama pull Qwen/Qwen3-4B-Instruct-2507 2>/dev/null || echo "  Qwen3-4B: skip (already exists or Ollama not available)"

# 2. Start Docker Compose
echo "[setup] Starting Docker services (Ollama + Squid + OpenClaw) ..."
docker compose -f docker/docker-compose.yml up -d

# 3. Wait for services
echo "[setup] Waiting for services ..."
echo "  → Ollama: http://localhost:11434"
for i in $(seq 1 30); do
    if curl -sf http://localhost:11434/api/tags >/dev/null 2>&1; then
        echo "    Ollama ready"
        break
    fi
    sleep 2
done
echo "  → Squid: http://localhost:3128"
for i in $(seq 1 20); do
    if curl -sf -x http://localhost:3128 http://openclaw:8080/health >/dev/null 2>&1; then
        echo "    Squid/OpenClaw ready"
        break
    fi
    sleep 2
done

echo "[setup] Done. Test environment is ready."
