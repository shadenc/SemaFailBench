#!/usr/bin/env bash
# Runs ON the RunPod pod. Stops prior vLLM, starts isolated F5 (wrong generation defaults only).
set -euo pipefail
MODEL="${SFB_F5_MODEL:-google/gemma-2-9b-it}"
REV="${SFB_F5_MODEL_REVISION:-${SFB_HEALTHY_REVISION:-11c9b309abf73637e4b6f9a3fa1e92e615547819}}"
SERVED_NAME="${SFB_F5_SERVED_MODEL_NAME:-google/gemma-2-9b-it}"
PORT="${SFB_PORT:-8000}"
GPU="${SFB_HEALTHY_GPU:-0}"
WORKDIR="${SFB_POD_WORKDIR:-/workspace/semafailbench}"
F5_OVERRIDE_FILE="${F5_OVERRIDE_FILE:-$WORKDIR/f5_generation_override.json}"
export MODEL REV SERVED_NAME PORT GPU WORKDIR F5_OVERRIDE_FILE

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

for pidfile in "$WORKDIR/vllm_healthy.pid" "$WORKDIR/vllm_f1.pid" "$WORKDIR/vllm_f2.pid" "$WORKDIR/vllm_f3.pid" "$WORKDIR/vllm_f4.pid" "$WORKDIR/vllm_f5.pid" "$WORKDIR/vllm_f6.pid"; do
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
rm -f "$WORKDIR/pins_f5.json"

python3 - <<PY
import hashlib
import json
import os
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

work = Path(os.environ.get("WORKDIR", "/workspace/semafailbench"))
model = os.environ.get("MODEL", "google/gemma-2-9b-it")
rev = os.environ.get("REV", "")
served = os.environ.get("SERVED_NAME", model)
override_file = Path(os.environ.get("F5_OVERRIDE_FILE", str(work / "f5_generation_override.json")))

pins = {
    "timestamp_utc": datetime.now(timezone.utc).isoformat(),
    "fault_id": "F5",
    "fault_name": "Decoding / generation configuration drift",
    "deployment_kind": "decoding_config_drift_isolated",
    "model_repo": model,
    "model_revision_requested": rev,
    "tokenizer_repo": model,
    "tokenizer_revision_requested": rev,
    "served_model_name": served,
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

model_path = snapshot_download(model, revision=rev or None, local_files_only=False)
pins["model_local_path"] = model_path
pins["tokenizer_local_path"] = model_path

healthy_gen_path = Path(model_path) / "generation_config.json"
healthy_gen = json.loads(healthy_gen_path.read_text(encoding="utf-8")) if healthy_gen_path.is_file() else {}
pins["healthy_generation_config_path"] = str(healthy_gen_path)
pins["healthy_generation_config"] = healthy_gen
pins["healthy_generation_config_hash"] = hashlib.sha256(
    json.dumps(healthy_gen, sort_keys=True).encode("utf-8")
).hexdigest()

if override_file.is_file():
    wrong_gen = json.loads(override_file.read_text(encoding="utf-8"))
else:
    wrong_gen = {"temperature": 1.4, "top_p": 0.95, "do_sample": True}
override_file.write_text(json.dumps(wrong_gen, indent=2), encoding="utf-8")
pins["wrong_generation_override_path"] = str(override_file)
pins["wrong_generation_override"] = wrong_gen
pins["wrong_generation_override_hash"] = hashlib.sha256(
    json.dumps(wrong_gen, sort_keys=True).encode("utf-8")
).hexdigest()

merged = dict(healthy_gen)
merged.update(wrong_gen)
pins["effective_server_generation_config"] = merged
pins["generation_config_differs_from_healthy_files"] = wrong_gen != {}

try:
    info = HfApi().model_info(model, revision=rev or None)
    pins["model_revision_pinned"] = info.sha
    pins["tokenizer_revision_pinned"] = info.sha
except Exception as exc:
    pins["model_revision_error"] = str(exc)

(work / "pins_f5.json").write_text(json.dumps(pins, indent=2), encoding="utf-8")
print(json.dumps(pins, indent=2))
PY

PIN_MODEL_REV=$(python3 -c "import json; print(json.load(open('$WORKDIR/pins_f5.json')).get('model_revision_pinned') or json.load(open('$WORKDIR/pins_f5.json')).get('model_revision_requested') or '')")
OVERRIDE_JSON=$(python3 -c "import json; print(json.dumps(json.load(open('$WORKDIR/pins_f5.json'))['wrong_generation_override']))")
echo "f5_model_revision=${PIN_MODEL_REV:-unpinned}"
echo "f5_generation_override=${OVERRIDE_JSON}"

echo "Starting isolated F5 vLLM on GPU $GPU port $PORT"
echo "  model=$MODEL revision=$REV"
echo "  override-generation-config=$OVERRIDE_JSON"

nohup env \
  NVIDIA_VISIBLE_DEVICES="$GPU" \
  CUDA_VISIBLE_DEVICES="$GPU" \
  VLLM_USE_FLASHINFER_SAMPLER=0 \
  PYTHONUNBUFFERED=1 \
  python3 -m vllm.entrypoints.openai.api_server \
  --model "$MODEL" \
  --revision "$PIN_MODEL_REV" \
  --served-model-name "$SERVED_NAME" \
  --host 127.0.0.1 \
  --port "$PORT" \
  --tensor-parallel-size 1 \
  --dtype bfloat16 \
  --max-model-len 8192 \
  --gpu-memory-utilization 0.90 \
  --enforce-eager \
  --override-generation-config "$OVERRIDE_JSON" \
  > "$WORKDIR/vllm_f5.log" 2>&1 &
echo $! > "$WORKDIR/vllm_f5.pid"

echo "Waiting for F5 vLLM to load..."
for i in $(seq 1 90); do
  if curl -sf "http://127.0.0.1:${PORT}/v1/models" >/dev/null 2>&1; then
    echo "F5 API ready after ${i}0s"
    curl -s "http://127.0.0.1:${PORT}/v1/models" | head -c 400
    echo
    break
  fi
  sleep 10
  if ! kill -0 "$(cat "$WORKDIR/vllm_f5.pid")" 2>/dev/null; then
    echo "F5 vLLM exited early"
    tail -60 "$WORKDIR/vllm_f5.log"
    exit 1
  fi
done

python3 - <<PY
import json, subprocess
from pathlib import Path
work = Path("$WORKDIR")
pins = json.loads((work / "pins_f5.json").read_text())
try:
    smi = subprocess.check_output(
        ["nvidia-smi", "--query-gpu=index,name,memory.used,memory.total,utilization.gpu", "--format=csv,noheader"],
        text=True,
    ).strip()
    pins["nvidia_smi_after_load"] = smi
except Exception as exc:
    pins["nvidia_smi_after_error"] = str(exc)
pid = int((work / "vllm_f5.pid").read_text().strip())
pins["vllm_command"] = open(f"/proc/{pid}/cmdline", "rb").read().replace(b"\\x00", b" ").decode("utf-8", "replace")
(work / "pins_f5.json").write_text(json.dumps(pins, indent=2), encoding="utf-8")
print("Updated pins_f5.json with post-load GPU snapshot + vLLM cmdline")
PY

echo "=== vllm_f5 pid ==="
cat "$WORKDIR/vllm_f5.pid"
echo "=== vllm_f5 log tail ==="
tail -40 "$WORKDIR/vllm_f5.log"
