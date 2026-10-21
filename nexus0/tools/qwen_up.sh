#!/usr/bin/env bash
# Start llama-server for Qwen-0. Nav runs this; CI never does.
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/../../.." && pwd)"
MODEL="${NAVI_QWEN_MODEL:-$HOME/models/qwen3-4b-instruct-2507/Qwen_Qwen3-4B-Instruct-2507-Q4_K_M.gguf}"
GBNF="${NAVI_QWEN_GBNF:-$ROOT/echoai/nexus0/cortex.gbnf}"
HOST="${NAVI_QWEN_HOST:-127.0.0.1}"
PORT="${NAVI_QWEN_PORT:-8080}"
BIN="${NAVI_QWEN_SERVER:-$HOME/src/llama.cpp/build/bin/llama-server}"

if [[ ! -f "$MODEL" ]]; then
  echo "missing GGUF: $MODEL" >&2
  exit 1
fi
if [[ ! -x "$BIN" ]]; then
  echo "missing llama-server: $BIN" >&2
  exit 1
fi

echo "model  $MODEL"
echo "gbnf   $GBNF  (el wrapper la manda por request; no al arrancar)"
echo "bind   $HOST:$PORT"
echo
echo "export NAVI_CORTEX_CMD=\"python3 $ROOT/echoai/nexus0/tools/qwen_cortex.py\""
echo "export NAVI_CORTEX_TIMEOUT=120"
echo "export NAVI_QWEN_URL=http://$HOST:$PORT"
echo "export NAVI_QWEN_MODEL=$MODEL"
echo "export NAVI_QWEN_GBNF=$GBNF"
echo

exec "$BIN" -m "$MODEL" --host "$HOST" --port "$PORT" -c 2048 -ngl 0
