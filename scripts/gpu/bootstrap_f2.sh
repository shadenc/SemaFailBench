#!/usr/bin/env bash
# From the Mac: inject F2 (stale checkpoint revision) on RunPod.
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
if [[ -f "$ROOT/.env" ]]; then set -a; source "$ROOT/.env"; set +a; fi
export SFB_RUNPOD_SSH="${SFB_RUNPOD_SSH:-g0uutfrnf83h9v-64410f64@ssh.runpod.io}"
export SFB_RUNPOD_KEY="${SFB_RUNPOD_KEY:-$HOME/.ssh/sfb_runpod}"
export SFB_F2_MODEL="${SFB_F2_MODEL:-Qwen/Qwen2.5-7B-Instruct}"
export SFB_F2_REVISION="${SFB_F2_REVISION:-52e20a6f5f475e5c8f6a8ebda4ae5fa6b1ea22ac}"
export SFB_HEALTHY_REVISION="${SFB_HEALTHY_REVISION:-a09a35458c702b33eeacc393d103063234e8bc28}"
PUBKEY="$(cat "${SFB_RUNPOD_KEY}.pub")"
REMOTE="$ROOT/scripts/gpu/remote_bootstrap_f2.sh"
echo "Injecting F2 checkpoint-version fault via PTY SSH ($SFB_RUNPOD_SSH)"
echo "  model=$SFB_F2_MODEL revision=$SFB_F2_REVISION (healthy=$SFB_HEALTHY_REVISION)"
{
  printf 'export SFB_PUBKEY=%q\n' "$PUBKEY"
  printf 'export SFB_F2_MODEL=%q\n' "$SFB_F2_MODEL"
  printf 'export SFB_F2_REVISION=%q\n' "$SFB_F2_REVISION"
  printf 'export SFB_HEALTHY_REVISION=%q\n' "$SFB_HEALTHY_REVISION"
  printf 'export SFB_PORT=%q\n' "${SFB_PORT:-8000}"
  printf 'export SFB_HEALTHY_GPU=%q\n' "${SFB_HEALTHY_GPU:-0}"
  printf 'export SFB_POD_WORKDIR=%q\n' "${SFB_POD_WORKDIR:-/workspace/semafailbench}"
  printf 'export MODEL=%q\n' "$SFB_F2_MODEL"
  printf 'export REV=%q\n' "$SFB_F2_REVISION"
  printf 'export HEALTHY_REV=%q\n' "$SFB_HEALTHY_REVISION"
  cat "$REMOTE"
} | python3 "$ROOT/scripts/gpu/ssh_run.py" --timeout "${SFB_BOOTSTRAP_TIMEOUT:-2400}"
