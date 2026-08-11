#!/usr/bin/env bash
# Smoke-test F2 server: API identity + 3 canaries + GPU snapshot.
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"
source .venv/bin/activate 2>/dev/null || true
if [[ -f .env ]]; then set -a; source .env; set +a; fi

export SFB_MODEL="${SFB_F2_EXPECTED_MODEL:-Qwen/Qwen2.5-7B-Instruct}"
BASE="${SFB_BASE_URL:-http://127.0.0.1:8000/v1}"

echo "=== F2 smoke test ==="
echo "expected_model=$SFB_MODEL actual=${SFB_F2_ACTUAL_MODEL:-Qwen/Qwen2-7B-Instruct} base=$BASE"

code=$(curl -s -o /tmp/sfb_models.json -w "%{http_code}" "${BASE}/models")
echo "GET /v1/models -> HTTP $code"
[[ "$code" == "200" ]] || exit 1
python3 -c "import json; d=json.load(open('/tmp/sfb_models.json')); print('model_ids:', [m['id'] for m in d.get('data',[])])"

echo "=== 3-canary dry run ==="
sfb run --condition F2-checkpoint-version --temperature 0 --split core --limit 3 --warmup

if [[ -n "${SFB_RUNPOD_TCP_HOST:-}" ]]; then
  echo "=== GPU snapshot (pod) ==="
  ssh -o BatchMode=yes -o ConnectTimeout=15 -i "${SFB_RUNPOD_KEY:-$HOME/.ssh/sfb_runpod}" \
    -p "${SFB_RUNPOD_TCP_PORT:-22}" "root@${SFB_RUNPOD_TCP_HOST}" \
    "nvidia-smi --query-gpu=name,memory.used,memory.total,utilization.gpu,power.draw --format=csv,noheader; pgrep -af vllm | head -1"
fi
echo "=== F2 smoke OK ==="
