#!/usr/bin/env bash
# Runs ON the RunPod pod. Stops healthy vLLM, starts F1 AWQ-quantized server.
set +e
MODEL="${SFB_F1_MODEL:-hugging-quants/gemma-2-9b-it-AWQ-INT4}"
REV="${SFB_F1_REVISION:-6e62725da8e92309167814dad7aacc0ed8cb2484}"
QUANT="${SFB_F1_QUANTIZATION:-awq_marlin}"
PORT="${SFB_PORT:-8000}"
GPU="${SFB_HEALTHY_GPU:-0}"
WORKDIR="${SFB_POD_WORKDIR:-/workspace/semafailbench}"
HEALTHY_MODEL="${SFB_MODEL:-google/gemma-2-9b-it}"
HEALTHY_REV="${SFB_HEALTHY_REVISION:-11c9b309abf73637e4b6f9a3fa1e92e615547819}"
export WORKDIR MODEL REV QUANT PORT GPU HEALTHY_MODEL HEALTHY_REV

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
if [[ -z "${HF_TOKEN:-}" && -f "$HF_HOME/token" ]]; then export HF_TOKEN="$(cat "$HF_HOME/token")"; fi
export HUGGING_FACE_HUB_TOKEN="${HUGGING_FACE_HUB_TOKEN:-${HF_TOKEN:-}}"
export PIP_PROGRESS_BAR=off
export PYTHONUNBUFFERED=1
export VLLM_USE_FLASHINFER_SAMPLER=0

if ! python3 -c "import huggingface_hub" 2>/dev/null; then
  python3 -m pip install --break-system-packages huggingface_hub
fi
if ! python3 -c "import vllm" 2>/dev/null; then
  python3 -m pip install --break-system-packages vllm
fi

# Stop healthy / prior vLLM
for pidfile in "$WORKDIR/vllm_healthy.pid" "$WORKDIR/vllm_f1.pid" "$WORKDIR/vllm_f2.pid" "$WORKDIR/vllm_f4.pid" "$WORKDIR/vllm_f5.pid" "$WORKDIR/vllm_f6.pid"; do
  if [[ -f "$pidfile" ]]; then
    pid="$(cat "$pidfile")"
    kill "$pid" 2>/dev/null || true
    sleep 2
    kill -9 "$pid" 2>/dev/null || true
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
model = os.environ.get("MODEL", "hugging-quants/gemma-2-9b-it-AWQ-INT4")
requested_rev = os.environ.get("REV") or None
quant = os.environ.get("QUANT", "awq_marlin")
healthy = os.environ.get("HEALTHY_MODEL", "google/gemma-2-9b-it")

pins = {
    "timestamp_utc": datetime.now(timezone.utc).isoformat(),
    "fault_id": "F1",
    "fault_name": "Quantization regression",
    "python": sys.version,
    "model_repo": model,
    "quantization": quant,
    "healthy_reference_repo": healthy,
    "healthy_reference_revision": os.environ.get("HEALTHY_REV"),
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
path = snapshot_download(model, revision=requested_rev, local_files_only=False)
pins["model_local_path"] = path
healthy_rev = os.environ.get("HEALTHY_REV") or None
healthy_path = snapshot_download(
    healthy,
    revision=healthy_rev,
    allow_patterns=[
        "tokenizer*",
        "special_tokens_map.json",
        "generation_config.json",
        "config.json",
    ],
    local_files_only=False,
)
pins["tokenizer_repo"] = healthy
pins["tokenizer_revision"] = healthy_rev
pins["tokenizer_local_path"] = healthy_path
try:
    info = HfApi().model_info(model, revision=requested_rev)
    pins["model_revision"] = info.sha
    pins["model_id"] = info.id
except Exception as exc:
    pins["model_revision_error"] = str(exc)

(work / "pins_f1.json").write_text(json.dumps(pins, indent=2), encoding="utf-8")
print(json.dumps(pins, indent=2))
PY

REV=$(python3 -c "import json; print(json.load(open('$WORKDIR/pins_f1.json')).get('model_revision') or '')")
TOKENIZER_PATH=$(python3 -c "import json; print(json.load(open('$WORKDIR/pins_f1.json')).get('tokenizer_local_path') or '')")
echo "f1_model_revision=${REV:-unpinned}"
echo "f1_tokenizer_path=${TOKENIZER_PATH}"

echo "Starting F1 vLLM AWQ on GPU $GPU port $PORT"
nohup env \
  NVIDIA_VISIBLE_DEVICES="$GPU" \
  CUDA_VISIBLE_DEVICES="$GPU" \
  VLLM_USE_FLASHINFER_SAMPLER=0 \
  PYTHONUNBUFFERED=1 \
  python3 -m vllm.entrypoints.openai.api_server \
  --model "$MODEL" \
  ${REV:+--revision "$REV"} \
  --tokenizer "$TOKENIZER_PATH" \
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
