#!/usr/bin/env bash
# From the Mac: inject F1 (AWQ quantization) on RunPod — stops healthy vLLM, starts F1.
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
if [[ -f "$ROOT/.env" ]]; then set -a; source "$ROOT/.env"; set +a; fi
export SFB_RUNPOD_SSH="${SFB_RUNPOD_SSH:-tk036kllrbagyq-64411c49@ssh.runpod.io}"
export SFB_RUNPOD_KEY="${SFB_RUNPOD_KEY:-$HOME/.ssh/sfb_runpod}"
export SFB_F1_MODEL="${SFB_F1_MODEL:-Qwen/Qwen2.5-7B-Instruct-AWQ}"
export SFB_F1_QUANTIZATION="${SFB_F1_QUANTIZATION:-awq}"
PUBKEY="$(cat "${SFB_RUNPOD_KEY}.pub")"
REMOTE="$ROOT/scripts/gpu/remote_bootstrap_f1.sh"
echo "Injecting F1 quantization fault via PTY SSH ($SFB_RUNPOD_SSH)"
echo "  model=$SFB_F1_MODEL quantization=$SFB_F1_QUANTIZATION"
{
  printf 'export SFB_PUBKEY=%q\n' "$PUBKEY"
  printf 'export SFB_F1_MODEL=%q\n' "$SFB_F1_MODEL"
  printf 'export SFB_F1_QUANTIZATION=%q\n' "$SFB_F1_QUANTIZATION"
  printf 'export SFB_MODEL=%q\n' "${SFB_MODEL:-Qwen/Qwen2.5-7B-Instruct}"
  printf 'export SFB_PORT=%q\n' "${SFB_PORT:-8000}"
  printf 'export SFB_HEALTHY_GPU=%q\n' "${SFB_HEALTHY_GPU:-0}"
  printf 'export SFB_POD_WORKDIR=%q\n' "${SFB_POD_WORKDIR:-/workspace/semafailbench}"
  printf 'export MODEL=%q\n' "$SFB_F1_MODEL"
  printf 'export QUANT=%q\n' "$SFB_F1_QUANTIZATION"
  cat "$REMOTE"
} | python3 "$ROOT/scripts/gpu/ssh_run.py" --timeout "${SFB_BOOTSTRAP_TIMEOUT:-2400}"
