#!/usr/bin/env bash
# Launch plan for the healthy Qwen2.5-7B-Instruct server (GPU host).
# Do not invent CUDA/vLLM point releases. Pin at install time on the 5090.

set -euo pipefail

MODEL="${SFB_MODEL:-Qwen/Qwen2.5-7B-Instruct}"
PORT="${SFB_PORT:-8000}"
TP="${SFB_TP:-1}"
DTYPE="${SFB_DTYPE:-bfloat16}"
MAX_LEN="${SFB_MAX_MODEL_LEN:-8192}"
GPU_UTIL="${SFB_GPU_UTIL:-0.90}"
REVISION="${SFB_MODEL_REVISION:-}"

ARGS=(
  --model "$MODEL"
  --host 0.0.0.0
  --port "$PORT"
  --tensor-parallel-size "$TP"
  --dtype "$DTYPE"
  --max-model-len "$MAX_LEN"
  --gpu-memory-utilization "$GPU_UTIL"
  --enforce-eager
)

if [[ -n "$REVISION" ]]; then
  ARGS+=(--revision "$REVISION")
fi

echo "Starting vLLM OpenAI server:"
echo "  model=$MODEL revision=${REVISION:-default} port=$PORT tp=$TP dtype=$DTYPE"
exec python -m vllm.entrypoints.openai.api_server "${ARGS[@]}"
