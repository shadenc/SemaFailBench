#!/usr/bin/env bash
# Runs ON the RunPod pod. Stops healthy vLLM, starts F1 AWQ-quantized server.
set +e
MODEL="${SFB_F1_MODEL:-Qwen/Qwen2.5-7B-Instruct-AWQ}"
QUANT="${SFB_F1_QUANTIZATION:-awq}"
PORT="${SFB_PORT:-8000}"
GPU="${SFB_HEALTHY_GPU:-0}"
WORKDIR="${SFB_POD_WORKDIR:-/workspace/semafailbench}"
HEALTHY_MODEL="${SFB_MODEL:-Qwen/Qwen2.5-7B-Instruct}"
export WORKDIR MODEL QUANT PORT GPU HEALTHY_MODEL

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

# Stop healthy / prior vLLM
for pidfile in "$WORKDIR/vllm_healthy.pid" "$WORKDIR/vllm_f1.pid"; do
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
model = os.environ.get("MODEL", "Qwen/Qwen2.5-7B-Instruct-AWQ")
quant = os.environ.get("QUANT", "awq")
healthy = os.environ.get("HEALTHY_MODEL", "Qwen/Qwen2.5-7B-Instruct")

pins = {
    "timestamp_utc": datetime.now(timezone.utc).isoformat(),
    "fault_id": "F1",
    "fault_name": "Quantization regression",
    "python": sys.version,
    "model_repo": model,
    "quantization": quant,
    "healthy_reference_repo": healthy,
    "port": os.environ.get("PORT", "8000"),
    "healthy_gpu": os.environ.get("GPU", "0"),
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
path = snapshot_download(model, local_files_only=False)
pins["model_local_path"] = path
try:
    info = HfApi().model_info(model)
    pins["model_revision"] = info.sha
    pins["model_id"] = info.id
except Exception as exc:
    pins["model_revision_error"] = str(exc)

(work / "pins_f1.json").write_text(json.dumps(pins, indent=2), encoding="utf-8")
print(json.dumps(pins, indent=2))
PY

REV=$(python3 -c "import json; print(json.load(open('$WORKDIR/pins_f1.json')).get('model_revision') or '')")
echo "f1_model_revision=${REV:-unpinned}"

echo "Starting F1 vLLM AWQ on GPU $GPU port $PORT"
nohup env \
  NVIDIA_VISIBLE_DEVICES="$GPU" \
  CUDA_VISIBLE_DEVICES="$GPU" \
  VLLM_USE_FLASHINFER_SAMPLER=0 \
  PYTHONUNBUFFERED=1 \
  python3 -m vllm.entrypoints.openai.api_server \
  --model "$MODEL" \
  ${REV:+--revision "$REV"} \
  --quantization "$QUANT" \
  --host 127.0.0.1 \
  --port "$PORT" \
  --tensor-parallel-size 1 \
  --max-model-len 8192 \
  --gpu-memory-utilization 0.90 \
  --enforce-eager \
  > "$WORKDIR/vllm_f1.log" 2>&1 &
echo $! > "$WORKDIR/vllm_f1.pid"

echo "Waiting for F1 vLLM to load (AWQ download + init)..."
for i in $(seq 1 90); do
  if curl -sf "http://127.0.0.1:${PORT}/v1/models" >/dev/null 2>&1; then
    echo "F1 API ready after ${i}0s"
    curl -s "http://127.0.0.1:${PORT}/v1/models" | head -c 400
    echo
    break
  fi
  sleep 10
  if ! kill -0 "$(cat "$WORKDIR/vllm_f1.pid")" 2>/dev/null; then
    echo "F1 vLLM exited early"
    tail -60 "$WORKDIR/vllm_f1.log"
    exit 1
  fi
done

python3 - <<PY
import json, subprocess
from pathlib import Path
work = Path("$WORKDIR")
pins = json.loads((work / "pins_f1.json").read_text())
try:
    smi = subprocess.check_output(
        ["nvidia-smi", "--query-gpu=index,name,memory.used,memory.total,utilization.gpu", "--format=csv,noheader"],
        text=True,
    ).strip()
    pins["nvidia_smi_after_load"] = smi
except Exception as exc:
    pins["nvidia_smi_after_error"] = str(exc)
(work / "pins_f1.json").write_text(json.dumps(pins, indent=2), encoding="utf-8")
print("Updated pins_f1.json with post-load GPU snapshot")
PY

echo "=== vllm_f1 pid ==="
cat "$WORKDIR/vllm_f1.pid"
echo "=== vllm_f1 log tail ==="
tail -40 "$WORKDIR/vllm_f1.log"
