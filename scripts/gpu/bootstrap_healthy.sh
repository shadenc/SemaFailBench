#!/usr/bin/env bash
# From the Mac: PTY-SSH into RunPod and bootstrap the healthy vLLM server.
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
if [[ -f "$ROOT/.env" ]]; then set -a; source "$ROOT/.env"; set +a; fi
export SFB_RUNPOD_SSH="${SFB_RUNPOD_SSH:-qp386qvf6p72gg-64411ac1@ssh.runpod.io}"
export SFB_RUNPOD_KEY="${SFB_RUNPOD_KEY:-$HOME/.ssh/sfb_runpod}"
PUBKEY="$(cat "${SFB_RUNPOD_KEY}.pub")"
REMOTE="$ROOT/scripts/gpu/remote_bootstrap_healthy.sh"
echo "Bootstrapping healthy vLLM via PTY SSH ($SFB_RUNPOD_SSH)"
# Prepend pubkey + env for the remote script.
{
  printf 'export SFB_PUBKEY=%q\n' "$PUBKEY"
  printf 'export SFB_MODEL=%q\n' "${SFB_MODEL:-Qwen/Qwen2.5-7B-Instruct}"
  printf 'export SFB_HEALTHY_REVISION=%q\n' "${SFB_HEALTHY_REVISION:-a09a35458c702b33eeacc393d103063234e8bc28}"
  printf 'export SFB_PORT=%q\n' "${SFB_PORT:-8000}"
  printf 'export SFB_HEALTHY_GPU=%q\n' "${SFB_HEALTHY_GPU:-0}"
  printf 'export SFB_POD_WORKDIR=%q\n' "${SFB_POD_WORKDIR:-/workspace/semafailbench}"
  cat "$REMOTE"
} | python3 "$ROOT/scripts/gpu/ssh_run.py" --timeout "${SFB_BOOTSTRAP_TIMEOUT:-1800}"
