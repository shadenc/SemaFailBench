#!/usr/bin/env bash
# Runs ON the RunPod pod. Stops prior vLLM, starts F2 wrong-version server.
set +e
ACTUAL_MODEL="${SFB_F2_ACTUAL_MODEL:-Qwen/Qwen2-7B-Instruct}"
REV="${SFB_F2_REVISION:-f2826a00ceef68f0f2b946d945ecc0477ce4450c}"
EXPECTED_MODEL="${SFB_F2_EXPECTED_MODEL:-Qwen/Qwen2.5-7B-Instruct}"
SERVED_NAME="${SFB_F2_SERVED_MODEL_NAME:-Qwen/Qwen2.5-7B-Instruct}"
PORT="${SFB_PORT:-8000}"
GPU="${SFB_HEALTHY_GPU:-0}"
WORKDIR="${SFB_POD_WORKDIR:-/workspace/semafailbench}"
HEALTHY_REV="${SFB_HEALTHY_REVISION:-a09a35458c702b33eeacc393d103063234e8bc28}"
export WORKDIR ACTUAL_MODEL REV EXPECTED_MODEL SERVED_NAME PORT GPU HEALTHY_REV

mkdir -p "$WORKDIR" /root/.ssh
chmod 700 /root/.ssh

if [[ -n "${SFB_PUBKEY:-}" ]]; then
  touch /root/.ssh/authorized_keys
  chmod 600 /root/.ssh/authorized_keys
  grep -qxF "$SFB_PUBKEY" /root/.ssh/authorized_keys || echo "$SFB_PUBKEY" >> /root/.ssh/authorized_keys
fi

unset NVIDIA_VISIBLE_DEVICES
export NVIDIA_VISIBLE_DEVICES="$GPU"
export CUDA_VISIBLE_DEVICES="$GPU"
export HF_HOME="${HF_HOME:-/workspace/.cache/huggingface}"
export PIP_PROGRESS_BAR=off
export PYTHONUNBUFFERED=1
export VLLM_USE_FLASHINFER_SAMPLER=0

python3 -m pip install -U pip huggingface_hub
if ! python3 -c "import vllm" 2>/dev/null; then
  python3 -m pip install vllm
fi

for pidfile in "$WORKDIR/vllm_healthy.pid" "$WORKDIR/vllm_f1.pid" "$WORKDIR/vllm_f2.pid"; do
  if [[ -f "$pidfile" ]]; then
    pid="$(cat "$pidfile")"
    kill "$pid" 2>/dev/null; sleep 2; kill -9 "$pid" 2>/dev/null || true
    rm -f "$pidfile"
  fi
done
pkill -f 'vllm.entrypoints.openai.api_server' 2>/dev/null || true
sleep 3

python3 - <<PY
import json, os, subprocess, sys
from datetime import datetime, timezone
from pathlib import Path

work = Path(os.environ.get("WORKDIR", "/workspace/semafailbench"))
actual = os.environ.get("ACTUAL_MODEL", "Qwen/Qwen2-7B-Instruct")
expected = os.environ.get("EXPECTED_MODEL", "Qwen/Qwen2.5-7B-Instruct")
served = os.environ.get("SERVED_NAME", expected)
rev = os.environ.get("REV", "")
healthy_rev = os.environ.get("HEALTHY_REV", "")

pins = {
    "timestamp_utc": datetime.now(timezone.utc).isoformat(),
    "fault_id": "F2",
    "fault_name": "Model / checkpoint version regression",
    "deployment_kind": "wrong_model_version_artifact",
    "expected_model": expected,
    "actual_model": actual,
    "served_model_name": served,
    "actual_model_revision": rev,
    "healthy_reference_revision": healthy_rev,
    "python": sys.version,
    "port": os.environ.get("PORT", "8000"),
    "healthy_gpu": os.environ.get("GPU", "0"),
    "hf_home": os.environ.get("HF_HOME", "/workspace/.cache/huggingface"),
}
try:
    smi = subprocess.check_output(
        ["nvidia-smi", "--query-gpu=index,name,memory.used,memory.total,driver_version", "--format=csv,noheader"],
        text=True,
    ).strip()
    pins["nvidia_smi_before_load"] = smi
except Exception as exc:
    pins["nvidia_smi_error"] = str(exc)

for name in ("torch", "vllm", "transformers"):
    try:
        m = __import__(name)
        pins[f"{name}_version"] = getattr(m, "__version__", None)
    except Exception as exc:
        pins[f"{name}_error"] = str(exc)

from huggingface_hub import snapshot_download, HfApi
path = snapshot_download(actual, revision=rev, local_files_only=False)
pins["model_local_path"] = path
try:
    info = HfApi().model_info(actual, revision=rev)
    pins["actual_model_revision_pinned"] = info.sha
    pins["actual_model_id"] = info.id
except Exception as exc:
    pins["model_revision_error"] = str(exc)

(work / "pins_f2.json").write_text(json.dumps(pins, indent=2), encoding="utf-8")
print(json.dumps(pins, indent=2))
PY

PIN_REV=$(python3 -c "import json; print(json.load(open('$WORKDIR/pins_f2.json')).get('actual_model_revision_pinned') or json.load(open('$WORKDIR/pins_f2.json')).get('actual_model_revision') or '')")
echo "f2_actual_model_revision=${PIN_REV:-unpinned}"

echo "Starting F2 vLLM wrong-version artifact on GPU $GPU port $PORT"
echo "  actual_model=$ACTUAL_MODEL revision=$REV"
echo "  served_model_name=$SERVED_NAME (expected logical id)"

nohup env \
  NVIDIA_VISIBLE_DEVICES="$GPU" \
  CUDA_VISIBLE_DEVICES="$GPU" \
  VLLM_USE_FLASHINFER_SAMPLER=0 \
  PYTHONUNBUFFERED=1 \
  python3 -m vllm.entrypoints.openai.api_server \
  --model "$ACTUAL_MODEL" \
  --revision "$REV" \
  --served-model-name "$SERVED_NAME" \
  --host 127.0.0.1 \
  --port "$PORT" \
  --tensor-parallel-size 1 \
  --dtype bfloat16 \
  --max-model-len 8192 \
  --gpu-memory-utilization 0.90 \
  --enforce-eager \
  > "$WORKDIR/vllm_f2.log" 2>&1 &
echo $! > "$WORKDIR/vllm_f2.pid"

echo "Waiting for F2 vLLM to load..."
for i in $(seq 1 90); do
  if curl -sf "http://127.0.0.1:${PORT}/v1/models" >/dev/null 2>&1; then
    echo "F2 API ready after ${i}0s"
    curl -s "http://127.0.0.1:${PORT}/v1/models" | head -c 400
    echo
    break
  fi
  sleep 10
  if ! kill -0 "$(cat "$WORKDIR/vllm_f2.pid")" 2>/dev/null; then
    echo "F2 vLLM exited early"
    tail -60 "$WORKDIR/vllm_f2.log"
    exit 1
  fi
done

python3 - <<PY
import json, subprocess
from pathlib import Path
work = Path("$WORKDIR")
pins = json.loads((work / "pins_f2.json").read_text())
try:
    smi = subprocess.check_output(
        ["nvidia-smi", "--query-gpu=index,name,memory.used,memory.total,utilization.gpu", "--format=csv,noheader"],
        text=True,
    ).strip()
    pins["nvidia_smi_after_load"] = smi
except Exception as exc:
    pins["nvidia_smi_after_error"] = str(exc)
(work / "pins_f2.json").write_text(json.dumps(pins, indent=2), encoding="utf-8")
print("Updated pins_f2.json with post-load GPU snapshot")
PY

echo "=== vllm_f2 pid ==="
cat "$WORKDIR/vllm_f2.pid"
echo "=== vllm_f2 log tail ==="
tail -40 "$WORKDIR/vllm_f2.log"
