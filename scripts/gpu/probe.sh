#!/usr/bin/env bash
# Probe the RunPod GPU host. Run from the Mac. Does not install anything.
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
export SFB_RUNPOD_SSH="${SFB_RUNPOD_SSH:-qp386qvf6p72gg-64411ac1@ssh.runpod.io}"
export SFB_RUNPOD_KEY="${SFB_RUNPOD_KEY:-$HOME/.ssh/sfb_runpod}"
python3 "$ROOT/scripts/gpu/ssh_run.py" --timeout 120 <<'REMOTE'
echo PROXY_OK
hostname
whoami
nvidia-smi -L
nvidia-smi --query-gpu=index,name,memory.total,driver_version --format=csv
python3 --version
which python3
df -h / /workspace 2>/dev/null || df -h /
free -h 2>/dev/null || true
python3 - <<'PY'
import sys
print("executable", sys.executable)
for name in ("torch", "vllm", "transformers"):
    try:
        m = __import__(name)
        print(name, getattr(m, "__version__", "?"))
        if name == "torch":
            print(" cuda_available", m.cuda.is_available())
            print(" torch_cuda", getattr(m.version, "cuda", None))
            if m.cuda.is_available():
                print(" device_count", m.cuda.device_count())
                for i in range(m.cuda.device_count()):
                    print(f" gpu{i}", m.cuda.get_device_name(i))
    except Exception as exc:
        print(name, "NOT_INSTALLED", type(exc).__name__)
PY
echo ===ENV_SAFE===
env | egrep -i '^(CUDA_VERSION|NVIDIA_VISIBLE_DEVICES|RUNPOD_GPU_|RUNPOD_POD_|RUNPOD_PUBLIC_|RUNPOD_TCP_|RUNPOD_DC_|HF_HOME|HF_HUB_)=' | sort
REMOTE
