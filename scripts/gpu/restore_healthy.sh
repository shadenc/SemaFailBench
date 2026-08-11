#!/usr/bin/env bash
# From the Mac: stop F1 and restore healthy bf16 vLLM on RunPod.
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
if [[ -f "$ROOT/.env" ]]; then set -a; source "$ROOT/.env"; set +a; fi
export SFB_RUNPOD_SSH="${SFB_RUNPOD_SSH:-tk036kllrbagyq-64411c49@ssh.runpod.io}"
export SFB_RUNPOD_KEY="${SFB_RUNPOD_KEY:-$HOME/.ssh/sfb_runpod}"
PUBKEY="$(cat "${SFB_RUNPOD_KEY}.pub")"
echo "Restoring healthy vLLM ($SFB_RUNPOD_SSH)"
{
  printf 'export SFB_PUBKEY=%q\n' "$PUBKEY"
  cat "$ROOT/scripts/gpu/remote_stop_vllm.sh"
  cat "$ROOT/scripts/gpu/remote_bootstrap_healthy.sh"
} | python3 "$ROOT/scripts/gpu/ssh_run.py" --timeout "${SFB_BOOTSTRAP_TIMEOUT:-1800}"
