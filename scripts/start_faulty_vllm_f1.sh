#!/usr/bin/env bash
# Launch F1 faulty server: AWQ-quantized Qwen2.5-7B-Instruct (GPU host).
set -euo pipefail

MODEL="${SFB_F1_MODEL:-Qwen/Qwen2.5-7B-Instruct-AWQ}"
PORT="${SFB_PORT:-8000}"
TP="${SFB_TP:-1}"
MAX_LEN="${SFB_MAX_MODEL_LEN:-8192}"
GPU_UTIL="${SFB_GPU_UTIL:-0.90}"
QUANT="${SFB_F1_QUANTIZATION:-awq}"
REVISION="${SFB_F1_MODEL_REVISION:-}"

ARGS=(
  --model "$MODEL"
  --host 0.0.0.0
  --port "$PORT"
  --tensor-parallel-size "$TP"
  --max-model-len "$MAX_LEN"
  --gpu-memory-utilization "$GPU_UTIL"
  --quantization "$QUANT"
  --enforce-eager
)

if [[ -n "$REVISION" ]]; then
  ARGS+=(--revision "$REVISION")
fi

echo "Starting F1 vLLM (quantization regression):"
echo "  model=$MODEL quantization=$QUANT port=$PORT tp=$TP max_len=$MAX_LEN"
exec python -m vllm.entrypoints.openai.api_server "${ARGS[@]}"
