#!/usr/bin/env bash
# From the Mac: inject F5 (wrong server generation defaults only) on RunPod.
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
if [[ -f "$ROOT/.env" ]]; then set -a; source "$ROOT/.env"; set +a; fi
export SFB_RUNPOD_SSH="${SFB_RUNPOD_SSH:-2pr0ssumaq3ue4-64411ab9@ssh.runpod.io}"
export SFB_RUNPOD_KEY="${SFB_RUNPOD_KEY:-$HOME/.ssh/sfb_runpod}"
export SFB_F5_MODEL="${SFB_F5_MODEL:-Qwen/Qwen2.5-7B-Instruct}"
export SFB_F5_MODEL_REVISION="${SFB_F5_MODEL_REVISION:-${SFB_HEALTHY_REVISION:-a09a35458c702b33eeacc393d103063234e8bc28}}"
export SFB_F5_OVERRIDE_FILE="${SFB_F5_OVERRIDE_FILE:-$ROOT/configs/f5_wrong_generation_config.json}"
export SFB_F5_SERVED_MODEL_NAME="${SFB_F5_SERVED_MODEL_NAME:-Qwen/Qwen2.5-7B-Instruct}"
export SFB_HEALTHY_REVISION="${SFB_HEALTHY_REVISION:-a09a35458c702b33eeacc393d103063234e8bc28}"
PUBKEY="$(cat "${SFB_RUNPOD_KEY}.pub")"
REMOTE="$ROOT/scripts/gpu/remote_bootstrap_f5.sh"
TCP_HOST="${SFB_RUNPOD_TCP_HOST:-}"
TCP_PORT="${SFB_RUNPOD_TCP_PORT:-22}"
POD_WORKDIR="${SFB_POD_WORKDIR:-/workspace/semafailbench}"
if [[ -n "$TCP_HOST" ]]; then
  scp -o BatchMode=yes -o ConnectTimeout=20 -i "$SFB_RUNPOD_KEY" -P "$TCP_PORT" \
    "$ROOT/scripts/serving_artifact_probe.py" "root@${TCP_HOST}:${POD_WORKDIR}/serving_artifact_probe.py"
  scp -o BatchMode=yes -o ConnectTimeout=20 -i "$SFB_RUNPOD_KEY" -P "$TCP_PORT" \
    "$SFB_F5_OVERRIDE_FILE" "root@${TCP_HOST}:${POD_WORKDIR}/f5_generation_override.json"
fi
echo "Injecting isolated F5 (generation config drift, matched weights+tokenizer) via PTY SSH ($SFB_RUNPOD_SSH)"
echo "  model=$SFB_F5_MODEL revision=$SFB_F5_MODEL_REVISION"
echo "  override=$SFB_F5_OVERRIDE_FILE"
echo "  served_model_name=$SFB_F5_SERVED_MODEL_NAME"
{
  printf 'export SFB_PUBKEY=%q\n' "$PUBKEY"
  printf 'export SFB_F5_MODEL=%q\n' "$SFB_F5_MODEL"
  printf 'export SFB_F5_MODEL_REVISION=%q\n' "$SFB_F5_MODEL_REVISION"
  printf 'export F5_OVERRIDE_FILE=%q\n' "${SFB_POD_WORKDIR:-/workspace/semafailbench}/f5_generation_override.json"
  printf 'export SFB_F5_SERVED_MODEL_NAME=%q\n' "$SFB_F5_SERVED_MODEL_NAME"
  printf 'export SFB_HEALTHY_REVISION=%q\n' "$SFB_HEALTHY_REVISION"
  printf 'export MODEL=%q\n' "$SFB_F5_MODEL"
  printf 'export REV=%q\n' "$SFB_F5_MODEL_REVISION"
  printf 'export SERVED_NAME=%q\n' "$SFB_F5_SERVED_MODEL_NAME"
  printf 'export SFB_PORT=%q\n' "${SFB_PORT:-8000}"
  printf 'export SFB_HEALTHY_GPU=%q\n' "${SFB_HEALTHY_GPU:-0}"
  printf 'export SFB_POD_WORKDIR=%q\n' "${SFB_POD_WORKDIR:-/workspace/semafailbench}"
  cat "$REMOTE"
} | python3 "$ROOT/scripts/gpu/ssh_run.py" --timeout "${SFB_BOOTSTRAP_TIMEOUT:-2400}"
