#!/usr/bin/env bash
# Runs ON the RunPod pod. Installs vLLM if missing, pins artifacts, starts healthy server.
set +e
MODEL="${SFB_MODEL:-Qwen/Qwen2.5-7B-Instruct}"
REV="${SFB_HEALTHY_REVISION:-a09a35458c702b33eeacc393d103063234e8bc28}"
export MODEL REV
PORT="${SFB_PORT:-8000}"
GPU="${SFB_HEALTHY_GPU:-0}"
WORKDIR="${SFB_POD_WORKDIR:-/workspace/semafailbench}"
mkdir -p "$WORKDIR" /root/.ssh
chmod 700 /root/.ssh

if [[ -n "${SFB_PUBKEY:-}" ]]; then
  touch /root/.ssh/authorized_keys
  chmod 600 /root/.ssh/authorized_keys
  grep -qxF "$SFB_PUBKEY" /root/.ssh/authorized_keys || echo "$SFB_PUBKEY" >> /root/.ssh/authorized_keys
  echo "authorized_keys updated"
fi

# This template sets NVIDIA_VISIBLE_DEVICES=void; that hides GPUs from some CUDA apps.
unset NVIDIA_VISIBLE_DEVICES
export NVIDIA_VISIBLE_DEVICES="$GPU"
export CUDA_VISIBLE_DEVICES="$GPU"
export HF_HOME="${HF_HOME:-/workspace/.cache/huggingface}"
export PIP_PROGRESS_BAR=off
export PYTHONUNBUFFERED=1
# RTX 5090 (sm_120) + CUDA toolkit 12.8: FlashInfer JIT dies with a misleading
# "sm75 or higher" error. vLLM 0.26 native sampler fallback:
# https://github.com/vllm-project/vllm/issues/50705
export VLLM_USE_FLASHINFER_SAMPLER=0

python3 -m pip install -U pip huggingface_hub
if python3 -c "import vllm" 2>/dev/null; then
  echo "vllm already importable"
else
  echo "Installing vllm via pip (no version invented; whatever this CUDA resolves)"
  python3 -m pip install vllm
fi

python3 - <<'PY'
import json, os, subprocess, sys
from datetime import datetime, timezone
from pathlib import Path

work = Path(os.environ.get("WORKDIR", "/workspace/semafailbench"))
work.mkdir(parents=True, exist_ok=True)
pins = {
    "timestamp_utc": datetime.now(timezone.utc).isoformat(),
    "python": sys.version,
    "executable": sys.executable,
    "model_repo": os.environ.get("MODEL", "Qwen/Qwen2.5-7B-Instruct"),
    "model_revision_requested": os.environ.get("REV", ""),
    "tokenizer_repo": os.environ.get("MODEL", "Qwen/Qwen2.5-7B-Instruct"),
    "tokenizer_revision_requested": os.environ.get("REV", ""),
    "healthy_gpu": os.environ.get("GPU", "0"),
    "port": os.environ.get("PORT", "8000"),
    "cuda_version_env": os.environ.get("CUDA_VERSION"),
    "nvidia_visible_devices_at_pin": os.environ.get("NVIDIA_VISIBLE_DEVICES"),
    "gpu_count_observed": None,
}
try:
    smi = subprocess.check_output(
        ["nvidia-smi", "--query-gpu=index,name,memory.total,driver_version", "--format=csv,noheader"],
        text=True,
    ).strip()
    pins["nvidia_smi"] = smi
    pins["gpu_count_observed"] = len([ln for ln in smi.splitlines() if ln.strip()])
except Exception as exc:
    pins["nvidia_smi_error"] = str(exc)

for name in ("torch", "vllm", "transformers"):
    try:
        m = __import__(name)
        pins[f"{name}_version"] = getattr(m, "__version__", None)
        if name == "torch":
            pins["torch_cuda"] = getattr(m.version, "cuda", None)
            pins["cuda_available"] = bool(m.cuda.is_available())
            pins["device_count"] = int(m.cuda.device_count()) if m.cuda.is_available() else 0
            pins["gpu_names"] = [m.cuda.get_device_name(i) for i in range(pins["device_count"])]
    except Exception as exc:
        pins[f"{name}_error"] = str(exc)

from huggingface_hub import snapshot_download, HfApi
rev = pins["model_revision_requested"] or None
path = snapshot_download(pins["model_repo"], revision=rev, local_files_only=False)
pins["model_local_path"] = path
pins["tokenizer_local_path"] = path
try:
    info = HfApi().model_info(pins["model_repo"], revision=rev)
    pins["model_revision"] = info.sha
    pins["tokenizer_revision"] = info.sha
except Exception as exc:
    pins["model_revision_error"] = str(exc)

(work / "pins.json").write_text(json.dumps(pins, indent=2), encoding="utf-8")
(work / "pip_freeze.txt").write_text(
    subprocess.check_output([sys.executable, "-m", "pip", "freeze"], text=True),
    encoding="utf-8",
)
print(json.dumps(pins, indent=2))
PY

REV=$(python3 -c "import json; print(json.load(open('$WORKDIR/pins.json')).get('model_revision') or '')")
echo "model_revision=${REV:-unpinned}"

if [[ -f "$WORKDIR/vllm_healthy.pid" ]] && kill -0 "$(cat "$WORKDIR/vllm_healthy.pid")" 2>/dev/null; then
  echo "vLLM already running pid=$(cat "$WORKDIR/vllm_healthy.pid")"
else
  echo "Starting vLLM on GPU $GPU port $PORT (nohup, FlashInfer sampler off)"
  nohup env \
    NVIDIA_VISIBLE_DEVICES="$GPU" \
    CUDA_VISIBLE_DEVICES="$GPU" \
    VLLM_USE_FLASHINFER_SAMPLER=0 \
    PYTHONUNBUFFERED=1 \
    python3 -m vllm.entrypoints.openai.api_server \
    --model "$MODEL" \
    --revision "$REV" \
    --host 127.0.0.1 \
    --port "$PORT" \
    --tensor-parallel-size 1 \
    --dtype bfloat16 \
    --max-model-len 8192 \
    --gpu-memory-utilization 0.90 \
    --enforce-eager \
    > "$WORKDIR/vllm_healthy.log" 2>&1 &
  echo $! > "$WORKDIR/vllm_healthy.pid"
fi
sleep 8
echo "=== vllm pid ==="
cat "$WORKDIR/vllm_healthy.pid"
echo "=== vllm log tail ==="
tail -40 "$WORKDIR/vllm_healthy.log"
