#!/usr/bin/env bash
# Runs ON the RunPod pod. Stops prior vLLM, starts isolated F2 (wrong weights, frozen healthy tokenizer).
set -euo pipefail
ACTUAL_MODEL="${SFB_F2_ACTUAL_MODEL:-NousResearch/Meta-Llama-3-8B-Instruct}"
REV="${SFB_F2_REVISION:-53346005fb0ef11d3b6a83b12c895cca40156b6c}"
EXPECTED_MODEL="${SFB_F2_EXPECTED_MODEL:-meta-llama/Llama-3.1-8B-Instruct}"
SERVED_NAME="${SFB_F2_SERVED_MODEL_NAME:-meta-llama/Llama-3.1-8B-Instruct}"
TOKENIZER_REPO="${SFB_F2_TOKENIZER:-$EXPECTED_MODEL}"
TOKENIZER_REV="${SFB_F2_TOKENIZER_REVISION:-${SFB_HEALTHY_REVISION:-0e9e39f249a16976918f6564b8830bc894c89659}}"
PORT="${SFB_PORT:-8000}"
GPU="${SFB_HEALTHY_GPU:-0}"
WORKDIR="${SFB_POD_WORKDIR:-/workspace/semafailbench}"
HEALTHY_REV="${SFB_HEALTHY_REVISION:-0e9e39f249a16976918f6564b8830bc894c89659}"
export WORKDIR ACTUAL_MODEL REV EXPECTED_MODEL SERVED_NAME PORT GPU HEALTHY_REV TOKENIZER_REPO TOKENIZER_REV

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

for pidfile in "$WORKDIR/vllm_healthy.pid" "$WORKDIR/vllm_f1.pid" "$WORKDIR/vllm_f2.pid" "$WORKDIR/vllm_f3.pid"; do
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
rm -f "$WORKDIR/pins_f2.json" "$WORKDIR/healthy_chat_template.jinja"

python3 - <<PY
import json, os, subprocess, sys
from datetime import datetime, timezone
from pathlib import Path

work = Path(os.environ.get("WORKDIR", "/workspace/semafailbench"))
actual = os.environ.get("ACTUAL_MODEL", "NousResearch/Meta-Llama-3-8B-Instruct")
expected = os.environ.get("EXPECTED_MODEL", "meta-llama/Llama-3.1-8B-Instruct")
served = os.environ.get("SERVED_NAME", expected)
rev = os.environ.get("REV", "")
healthy_rev = os.environ.get("HEALTHY_REV", "")
tokenizer_repo = os.environ.get("TOKENIZER_REPO", expected)
tokenizer_rev = os.environ.get("TOKENIZER_REV", healthy_rev)

pins = {
    "timestamp_utc": datetime.now(timezone.utc).isoformat(),
    "fault_id": "F2",
    "fault_name": "Model / checkpoint version regression",
    "deployment_kind": "wrong_model_version_artifact_isolated",
    "expected_model": expected,
    "actual_model": actual,
    "served_model_name": served,
    "actual_model_revision": rev,
    "healthy_reference_revision": healthy_rev,
    "tokenizer_repo": tokenizer_repo,
    "tokenizer_revision": tokenizer_rev,
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
from transformers import AutoTokenizer

model_path = snapshot_download(actual, revision=rev, local_files_only=False)
healthy_tok_path = snapshot_download(
    tokenizer_repo,
    revision=tokenizer_rev,
    allow_patterns=[
        "tokenizer*",
        "special_tokens_map.json",
        "config.json",
        "generation_config.json",
    ],
    local_files_only=False,
)
pins["model_local_path"] = model_path
pins["healthy_tokenizer_local_path"] = healthy_tok_path
pins["tokenizer_local_path"] = healthy_tok_path

try:
    info = HfApi().model_info(actual, revision=rev)
    pins["actual_model_revision_pinned"] = info.sha
    pins["actual_model_id"] = info.id
    tok_info = HfApi().model_info(tokenizer_repo, revision=tokenizer_rev)
    pins["tokenizer_revision_pinned"] = tok_info.sha
except Exception as exc:
    pins["model_revision_error"] = str(exc)

# Isolation probe: healthy tokenizer vs actual-model bundled tokenizer
tok_healthy = AutoTokenizer.from_pretrained(healthy_tok_path, trust_remote_code=True)
tok_bundled = AutoTokenizer.from_pretrained(model_path, trust_remote_code=True)
sample_messages = [
    {"role": "system", "content": "You are a careful assistant."},
    {"role": "user", "content": "Reply with exactly three words."},
]

def ids_from(tok, messages):
    out = tok.apply_chat_template(messages, tokenize=True, add_generation_prompt=True)
    ids = out["input_ids"] if hasattr(out, "__getitem__") else out
    if hasattr(ids, "tolist"):
        ids = ids.tolist()
    return list(ids)

ids_healthy = ids_from(tok_healthy, sample_messages)
ids_bundled = ids_from(tok_bundled, sample_messages)
cfg_healthy = json.loads((Path(healthy_tok_path) / "tokenizer_config.json").read_text(encoding="utf-8"))
cfg_bundled = json.loads((Path(model_path) / "tokenizer_config.json").read_text(encoding="utf-8"))
tmpl_healthy = cfg_healthy.get("chat_template") or ""
tmpl_bundled = cfg_bundled.get("chat_template") or ""

pins["isolation_probe"] = {
    "tokenizer_vocab_len_healthy": len(tok_healthy),
    "tokenizer_vocab_len_bundled": len(tok_bundled),
    "token_ids_equal_healthy_vs_bundled": ids_healthy == ids_bundled,
    "chat_template_equal_healthy_vs_bundled": tmpl_healthy == tmpl_bundled,
    "using_frozen_healthy_tokenizer": True,
}

(work / "pins_f2.json").write_text(json.dumps(pins, indent=2), encoding="utf-8")
print(json.dumps(pins, indent=2))
PY

PIN_MODEL_REV=$(python3 -c "import json; print(json.load(open('$WORKDIR/pins_f2.json')).get('actual_model_revision_pinned') or json.load(open('$WORKDIR/pins_f2.json')).get('actual_model_revision') or '')")
PIN_TOK_REV=$(python3 -c "import json; print(json.load(open('$WORKDIR/pins_f2.json')).get('tokenizer_revision_pinned') or json.load(open('$WORKDIR/pins_f2.json')).get('tokenizer_revision') or '')")
echo "f2_actual_model_revision=${PIN_MODEL_REV:-unpinned}"
echo "f2_tokenizer_revision=${PIN_TOK_REV:-unpinned}"

CHAT_TEMPLATE_FILE="$WORKDIR/healthy_chat_template.jinja"
python3 - <<PY
import json
from pathlib import Path
cfg = json.loads((Path("$WORKDIR") / "pins_f2.json").read_text())
tok_path = Path(cfg["healthy_tokenizer_local_path"])
tmpl = json.loads((tok_path / "tokenizer_config.json").read_text(encoding="utf-8")).get("chat_template") or ""
Path("$CHAT_TEMPLATE_FILE").write_text(tmpl, encoding="utf-8")
print(f"Wrote chat template ({len(tmpl)} chars) -> $CHAT_TEMPLATE_FILE")
PY

echo "Starting isolated F2 vLLM on GPU $GPU port $PORT"
echo "  actual_model=$ACTUAL_MODEL revision=$REV"
echo "  tokenizer=$TOKENIZER_REPO revision=$TOKENIZER_REV (frozen healthy)"
echo "  served_model_name=$SERVED_NAME"

nohup env \
  NVIDIA_VISIBLE_DEVICES="$GPU" \
  CUDA_VISIBLE_DEVICES="$GPU" \
  VLLM_USE_FLASHINFER_SAMPLER=0 \
  PYTHONUNBUFFERED=1 \
  python3 -m vllm.entrypoints.openai.api_server \
  --model "$ACTUAL_MODEL" \
  --revision "$REV" \
  --tokenizer "$TOKENIZER_REPO" \
  --tokenizer-revision "$TOKENIZER_REV" \
  --chat-template "$CHAT_TEMPLATE_FILE" \
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
pid = (work / "vllm_f2.pid").read_text(encoding="utf-8").strip()
pins["vllm_command"] = open(f"/proc/{pid}/cmdline", "rb").read().replace(b"\\x00", b" ").decode("utf-8", "replace")
(work / "pins_f2.json").write_text(json.dumps(pins, indent=2), encoding="utf-8")
print("Updated pins_f2.json with post-load GPU snapshot + vLLM cmdline")
PY

echo "=== vllm_f2 pid ==="
cat "$WORKDIR/vllm_f2.pid"
echo "=== vllm_f2 log tail ==="
tail -40 "$WORKDIR/vllm_f2.log"
