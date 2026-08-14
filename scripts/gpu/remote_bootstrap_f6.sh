#!/usr/bin/env bash
# Runs ON the RunPod pod. Stops prior vLLM, starts isolated F6 (wrong LoRA adapter only).
set +e
MODEL="${SFB_F6_MODEL:-Qwen/Qwen2.5-7B-Instruct}"
REV="${SFB_F6_MODEL_REVISION:-${SFB_HEALTHY_REVISION:-a09a35458c702b33eeacc393d103063234e8bc28}}"
SERVED_NAME="${SFB_F6_SERVED_MODEL_NAME:-Qwen/Qwen2.5-7B-Instruct}"
LORA_REPO="${SFB_F6_LORA_REPO:-arvindcr4/tool-call-lora-qwen2.5-7b}"
LORA_MODULE="${SFB_F6_LORA_MODULE:-stale-tool-lora}"
MAX_LORA_RANK="${SFB_F6_MAX_LORA_RANK:-16}"
PORT="${SFB_PORT:-8000}"
GPU="${SFB_HEALTHY_GPU:-0}"
WORKDIR="${SFB_POD_WORKDIR:-/workspace/semafailbench}"
export MODEL REV SERVED_NAME LORA_REPO LORA_MODULE MAX_LORA_RANK PORT GPU WORKDIR

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

python3 -m pip install -U pip huggingface_hub peft
if ! python3 -c "import vllm" 2>/dev/null; then
  python3 -m pip install vllm
fi

for pidfile in "$WORKDIR/vllm_healthy.pid" "$WORKDIR/vllm_f1.pid" "$WORKDIR/vllm_f2.pid" "$WORKDIR/vllm_f3.pid" "$WORKDIR/vllm_f4.pid" "$WORKDIR/vllm_f5.pid" "$WORKDIR/vllm_f6.pid"; do
  if [[ -f "$pidfile" ]]; then
    pid="$(cat "$pidfile")"
    kill "$pid" 2>/dev/null; sleep 2; kill -9 "$pid" 2>/dev/null || true
    rm -f "$pidfile"
  fi
done
pkill -f 'vllm.entrypoints.openai.api_server' 2>/dev/null || true
sleep 3

python3 - <<PY
import hashlib
import json
import os
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

work = Path(os.environ.get("WORKDIR", "/workspace/semafailbench"))
model = os.environ.get("MODEL", "Qwen/Qwen2.5-7B-Instruct")
rev = os.environ.get("REV", "")
served = os.environ.get("SERVED_NAME", model)
lora_repo = os.environ.get("LORA_REPO", "")
lora_module = os.environ.get("LORA_MODULE", "stale-tool-lora")
max_rank = int(os.environ.get("MAX_LORA_RANK", "16"))

pins = {
    "timestamp_utc": datetime.now(timezone.utc).isoformat(),
    "fault_id": "F6",
    "fault_name": "Wrong / stale LoRA adapter",
    "deployment_kind": "lora_adapter_mismatch_isolated",
    "model_repo": model,
    "model_revision_requested": rev,
    "tokenizer_repo": model,
    "tokenizer_revision_requested": rev,
    "served_model_name": served,
    "lora_module_name": lora_module,
    "lora_adapter_repo": lora_repo,
    "max_lora_rank": max_rank,
    "healthy_lora": "none",
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

for name in ("torch", "vllm", "transformers", "peft"):
    try:
        m = __import__(name)
        pins[f"{name}_version"] = getattr(m, "__version__", None)
    except Exception as exc:
        pins[f"{name}_error"] = str(exc)

from huggingface_hub import snapshot_download, HfApi

model_path = snapshot_download(model, revision=rev or None, local_files_only=False)
pins["model_local_path"] = model_path
pins["tokenizer_local_path"] = model_path

lora_path = snapshot_download(lora_repo, local_files_only=False)
pins["lora_local_path"] = lora_path
try:
    adapter_cfg = json.loads((Path(lora_path) / "adapter_config.json").read_text(encoding="utf-8"))
except Exception as exc:
    adapter_cfg = {"error": str(exc)}
pins["lora_adapter_config"] = adapter_cfg
pins["lora_adapter_config_hash"] = hashlib.sha256(
    json.dumps(adapter_cfg, sort_keys=True).encode("utf-8")
).hexdigest()

healthy_gen_path = Path(model_path) / "generation_config.json"
healthy_gen = json.loads(healthy_gen_path.read_text(encoding="utf-8")) if healthy_gen_path.is_file() else {}
pins["healthy_generation_config"] = healthy_gen
pins["healthy_generation_config_hash"] = hashlib.sha256(
    json.dumps(healthy_gen, sort_keys=True).encode("utf-8")
).hexdigest()

try:
    info = HfApi().model_info(model, revision=rev or None)
    pins["model_revision_pinned"] = info.sha
    pins["tokenizer_revision_pinned"] = info.sha
except Exception as exc:
    pins["model_revision_error"] = str(exc)

try:
    lora_info = HfApi().model_info(lora_repo)
    pins["lora_adapter_revision"] = lora_info.sha
except Exception as exc:
    pins["lora_adapter_revision_error"] = str(exc)

(work / "pins_f6.json").write_text(json.dumps(pins, indent=2), encoding="utf-8")
print(json.dumps(pins, indent=2))
PY

PIN_MODEL_REV=$(python3 -c "import json; print(json.load(open('$WORKDIR/pins_f6.json')).get('model_revision_pinned') or json.load(open('$WORKDIR/pins_f6.json')).get('model_revision_requested') or '')")
LORA_MODULES_ARG="${LORA_MODULE}=${LORA_REPO}"
echo "f6_model_revision=${PIN_MODEL_REV:-unpinned}"
echo "f6_lora_modules=${LORA_MODULES_ARG}"

echo "Starting isolated F6 vLLM on GPU $GPU port $PORT"
echo "  base model=$MODEL revision=$REV"
echo "  lora-modules $LORA_MODULES_ARG max-rank=$MAX_LORA_RANK"

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
  --enable-lora \
  --max-lora-rank "$MAX_LORA_RANK" \
  --max-loras 1 \
  --lora-modules "$LORA_MODULES_ARG" \
  > "$WORKDIR/vllm_f6.log" 2>&1 &
echo $! > "$WORKDIR/vllm_f6.pid"

echo "Waiting for F6 vLLM to load..."
for i in $(seq 1 120); do
  if curl -sf "http://127.0.0.1:${PORT}/v1/models" >/dev/null 2>&1; then
    echo "F6 API ready after ${i}0s"
    curl -s "http://127.0.0.1:${PORT}/v1/models" | head -c 600
    echo
    break
  fi
  sleep 10
  if ! kill -0 "$(cat "$WORKDIR/vllm_f6.pid")" 2>/dev/null; then
    echo "F6 vLLM exited early"
    tail -80 "$WORKDIR/vllm_f6.log"
    exit 1
  fi
done

python3 - <<PY
import json, subprocess
from pathlib import Path
work = Path("$WORKDIR")
pins = json.loads((work / "pins_f6.json").read_text())
try:
    smi = subprocess.check_output(
        ["nvidia-smi", "--query-gpu=index,name,memory.used,memory.total,utilization.gpu", "--format=csv,noheader"],
        text=True,
    ).strip()
    pins["nvidia_smi_after_load"] = smi
except Exception as exc:
    pins["nvidia_smi_after_error"] = str(exc)
pid = int((work / "vllm_f6.pid").read_text().strip())
pins["vllm_command"] = open(f"/proc/{pid}/cmdline", "rb").read().replace(b"\\x00", b" ").decode("utf-8", "replace")
(work / "pins_f6.json").write_text(json.dumps(pins, indent=2), encoding="utf-8")
print("Updated pins_f6.json with post-load GPU snapshot + vLLM cmdline")
PY

echo "=== vllm_f6 pid ==="
cat "$WORKDIR/vllm_f6.pid"
echo "=== vllm_f6 log tail ==="
tail -40 "$WORKDIR/vllm_f6.log"
