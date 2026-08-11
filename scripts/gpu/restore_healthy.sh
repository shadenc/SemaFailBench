#!/usr/bin/env bash
# From the Mac: stop F1 and restore healthy bf16 vLLM on RunPod.
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
if [[ -f "$ROOT/.env" ]]; then set -a; source "$ROOT/.env"; set +a; fi
export SFB_RUNPOD_SSH="${SFB_RUNPOD_SSH:-tk036kllrbagyq-64411c49@ssh.runpod.io}"
export SFB_RUNPOD_KEY="${SFB_RUNPOD_KEY:-$HOME/.ssh/sfb_runpod}"
export SFB_MODEL="${SFB_MODEL:-Qwen/Qwen2.5-7B-Instruct}"
export SFB_HEALTHY_REVISION="${SFB_HEALTHY_REVISION:-a09a35458c702b33eeacc393d103063234e8bc28}"
PUBKEY="$(cat "${SFB_RUNPOD_KEY}.pub")"
TCP_HOST="${SFB_RUNPOD_TCP_HOST:-}"
TCP_PORT="${SFB_RUNPOD_TCP_PORT:-22}"
POD_WORKDIR="${SFB_POD_WORKDIR:-/workspace/semafailbench}"
if [[ -n "$TCP_HOST" ]]; then
  scp -o BatchMode=yes -o ConnectTimeout=20 -i "$SFB_RUNPOD_KEY" -P "$TCP_PORT" \
    "$ROOT/scripts/serving_artifact_probe.py" "root@${TCP_HOST}:${POD_WORKDIR}/serving_artifact_probe.py"
fi
echo "Restoring healthy vLLM ($SFB_RUNPOD_SSH)"
{
  printf 'export SFB_PUBKEY=%q\n' "$PUBKEY"
  printf 'export SFB_MODEL=%q\n' "$SFB_MODEL"
  printf 'export SFB_HEALTHY_REVISION=%q\n' "$SFB_HEALTHY_REVISION"
  printf 'export REV=%q\n' "$SFB_HEALTHY_REVISION"
  cat "$ROOT/scripts/gpu/remote_stop_vllm.sh"
  cat "$ROOT/scripts/gpu/remote_bootstrap_healthy.sh"
} | python3 "$ROOT/scripts/gpu/ssh_run.py" --timeout "${SFB_BOOTSTRAP_TIMEOUT:-1800}"
