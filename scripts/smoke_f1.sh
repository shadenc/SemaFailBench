#!/usr/bin/env bash
# Smoke-test F1 server: API + 3 canaries + GPU snapshot. Run from Mac with tunnel up.
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"
source .venv/bin/activate 2>/dev/null || true

export SFB_MODEL="${SFB_F1_MODEL:-hugging-quants/gemma-2-9b-it-AWQ-INT4}"
BASE="${SFB_BASE_URL:-http://127.0.0.1:8000/v1}"

echo "=== F1 smoke test ==="
echo "model=$SFB_MODEL base=$BASE"

code=$(curl -s -o /tmp/sfb_models.json -w "%{http_code}" "${BASE}/models")
echo "GET /v1/models -> HTTP $code"
if [[ "$code" != "200" ]]; then
  echo "FAIL: API not reachable. Start tunnel: bash scripts/gpu/tunnel.sh"
  exit 1
fi
python3 -c "import json; d=json.load(open('/tmp/sfb_models.json')); print('model_ids:', [m['id'] for m in d.get('data',[])])"

echo "=== 3-canary dry run ==="
sfb run --condition F1-quantization --temperature 0 --split core --limit 3 --warmup

if [[ -n "${SFB_RUNPOD_TCP_HOST:-}" ]] || [[ -f .env ]]; then
  set -a; [[ -f .env ]] && source .env; set +a
  if [[ -n "${SFB_RUNPOD_TCP_HOST:-}" ]]; then
    echo "=== GPU snapshot (pod) ==="
    ssh -o BatchMode=yes -o ConnectTimeout=15 -i "${SFB_RUNPOD_KEY:-$HOME/.ssh/sfb_runpod}" \
      -p "${SFB_RUNPOD_TCP_PORT:-22}" "root@${SFB_RUNPOD_TCP_HOST}" \
      "nvidia-smi --query-gpu=name,memory.used,memory.total,utilization.gpu,power.draw --format=csv,noheader; pgrep -af vllm | head -1"
  fi
fi

echo "=== F1 smoke OK ==="
