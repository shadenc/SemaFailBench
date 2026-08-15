#!/usr/bin/env bash
# Wait for RunPod SSH + bootstrap Mistral v0.3 healthy vLLM on GPU.
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"
if [[ -f .env ]]; then set -a; source .env; set +a; fi

echo "Waiting for pod SSH (${SFB_RUNPOD_SSH:-unset})..."
for i in $(seq 1 60); do
  if bash "$ROOT/scripts/gpu/probe.sh" >/dev/null 2>&1; then
    echo "Pod reachable after attempt $i"
    break
  fi
  if [[ "$i" -eq 60 ]]; then
    echo "Pod not reachable after 60 attempts. Update .env SSH/TCP from RunPod Connect tab." >&2
    exit 1
  fi
  echo "  attempt $i/60 — sleeping 15s"
  sleep 15
done

echo "Starting Mistral download + vLLM bootstrap (may take 5–15 min on first download)..."
bash "$ROOT/scripts/gpu/bootstrap_mistral_healthy.sh"

echo ""
echo "Next: in a separate terminal run: bash scripts/gpu/tunnel.sh"
echo "Then verify: curl -s http://127.0.0.1:8000/v1/models"
