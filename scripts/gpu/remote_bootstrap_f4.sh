#!/usr/bin/env bash
# Runs ON the RunPod pod. Stops prior vLLM, starts isolated F4 (wrong chat template only).
set -euo pipefail
MODEL="${SFB_F4_MODEL:-meta-llama/Llama-3.1-8B-Instruct}"
REV="${SFB_F4_MODEL_REVISION:-${SFB_HEALTHY_REVISION:-0e9e39f249a16976918f6564b8830bc894c89659}}"
TOKENIZER_REPO="${SFB_F4_TOKENIZER:-$MODEL}"
TOKENIZER_REV="${SFB_F4_TOKENIZER_REVISION:-$REV}"
TEMPLATE_SOURCE="${SFB_F4_TEMPLATE_SOURCE:-local:no_assistant_gen_prompt}"
SERVED_NAME="${SFB_F4_SERVED_MODEL_NAME:-meta-llama/Llama-3.1-8B-Instruct}"
PORT="${SFB_PORT:-8000}"
GPU="${SFB_HEALTHY_GPU:-0}"
WORKDIR="${SFB_POD_WORKDIR:-/workspace/semafailbench}"
F4_LOCAL_TEMPLATE="${F4_LOCAL_TEMPLATE:-}"
export MODEL REV TOKENIZER_REPO TOKENIZER_REV TEMPLATE_SOURCE SERVED_NAME PORT GPU WORKDIR F4_LOCAL_TEMPLATE

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

for pidfile in "$WORKDIR/vllm_healthy.pid" "$WORKDIR/vllm_f1.pid" "$WORKDIR/vllm_f2.pid" "$WORKDIR/vllm_f3.pid" "$WORKDIR/vllm_f4.pid"; do
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
rm -f "$WORKDIR/pins_f4.json" "$WORKDIR/f4_wrong_chat_template.jinja"

python3 - <<PY
import json, os, subprocess, sys
from datetime import datetime, timezone
from pathlib import Path

work = Path(os.environ.get("WORKDIR", "/workspace/semafailbench"))
model = os.environ.get("MODEL", "meta-llama/Llama-3.1-8B-Instruct")
rev = os.environ.get("REV", "")
tokenizer_repo = os.environ.get("TOKENIZER_REPO", model)
tokenizer_rev = os.environ.get("TOKENIZER_REV", rev)
template_source = os.environ.get("TEMPLATE_SOURCE", "local:system_stripped_chatml")
local_template = os.environ.get("F4_LOCAL_TEMPLATE", "")
served = os.environ.get("SERVED_NAME", model)

pins = {
    "timestamp_utc": datetime.now(timezone.utc).isoformat(),
    "fault_id": "F4",
    "fault_name": "Chat-template mismatch",
    "deployment_kind": "wrong_chat_template_isolated",
    "model_repo": model,
    "model_revision_requested": rev,
    "tokenizer_repo": tokenizer_repo,
    "tokenizer_revision_requested": tokenizer_rev,
    "wrong_template_source": template_source,
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
from transformers import AutoTokenizer

model_path = snapshot_download(model, revision=rev or None, local_files_only=False)
tokenizer_path = snapshot_download(tokenizer_repo, revision=tokenizer_rev or None, local_files_only=False)
pins["model_local_path"] = model_path
pins["tokenizer_local_path"] = tokenizer_path

local_tmpl_path = Path(local_template) if local_template else None
if local_tmpl_path and local_tmpl_path.is_file():
    tmpl_wrong = local_tmpl_path.read_text(encoding="utf-8")
    pins["wrong_template_source_local_path"] = str(local_tmpl_path)
    pins["wrong_template_kind"] = "local_injected"
else:
    from huggingface_hub import snapshot_download as _snap
    template_path = _snap(
        template_source,
        allow_patterns=["tokenizer_config.json", "chat_template.jinja", "*.jinja"],
        local_files_only=False,
    )
    pins["wrong_template_source_local_path"] = template_path
    pins["wrong_template_kind"] = "hub_tokenizer_config"
    wrong_cfg_path = Path(template_path) / "tokenizer_config.json"
    wrong_cfg = json.loads(wrong_cfg_path.read_text(encoding="utf-8")) if wrong_cfg_path.is_file() else {}
    tmpl_wrong = wrong_cfg.get("chat_template") or ""
    if not tmpl_wrong:
        jinja_path = Path(template_path) / "chat_template.jinja"
        if jinja_path.is_file():
            tmpl_wrong = jinja_path.read_text(encoding="utf-8")
try:
    info = HfApi().model_info(model, revision=rev or None)
    pins["model_revision_pinned"] = info.sha
    tok_info = HfApi().model_info(tokenizer_repo, revision=tokenizer_rev or None)
    pins["tokenizer_revision_pinned"] = tok_info.sha
    if pins.get("wrong_template_kind") == "hub_tokenizer_config":
        tmpl_info = HfApi().model_info(template_source)
        pins["wrong_template_source_revision_pinned"] = tmpl_info.sha
except Exception as exc:
    pins["model_revision_error"] = str(exc)

healthy_cfg = json.loads((Path(tokenizer_path) / "tokenizer_config.json").read_text(encoding="utf-8"))
tmpl_healthy = healthy_cfg.get("chat_template") or ""
if not tmpl_wrong:
    raise SystemExit("Could not load wrong chat template")

healthy_tok = AutoTokenizer.from_pretrained(tokenizer_path, trust_remote_code=True)
sample_messages = [
    {"role": "system", "content": "You are a careful assistant."},
    {"role": "user", "content": "Reply with exactly three words."},
]

def ids_with_template(tok, messages, template):
    if template:
        out = tok.apply_chat_template(messages, tokenize=True, add_generation_prompt=True, chat_template=template)
    else:
        out = tok.apply_chat_template(messages, tokenize=True, add_generation_prompt=True)
    ids = out["input_ids"] if hasattr(out, "__getitem__") else out
    if hasattr(ids, "tolist"):
        ids = ids.tolist()
    return list(ids)

ids_healthy = ids_with_template(healthy_tok, sample_messages, tmpl_healthy)
ids_wrong = ids_with_template(healthy_tok, sample_messages, tmpl_wrong)

pins["isolation_probe"] = {
    "chat_template_equal_healthy_vs_wrong_source": tmpl_healthy == tmpl_wrong,
    "chat_template_len_healthy": len(tmpl_healthy),
    "chat_template_len_wrong": len(tmpl_wrong),
    "token_ids_equal_healthy_vs_wrong_served": ids_healthy == ids_wrong,
    "token_ids_healthy": ids_healthy[:20],
    "token_ids_wrong_served": ids_wrong[:20],
    "tokenizer_vocab_len": len(healthy_tok),
}

(work / "pins_f4.json").write_text(json.dumps(pins, indent=2), encoding="utf-8")
print(json.dumps(pins, indent=2))
PY

PIN_MODEL_REV=$(python3 -c "import json; print(json.load(open('$WORKDIR/pins_f4.json')).get('model_revision_pinned') or json.load(open('$WORKDIR/pins_f4.json')).get('model_revision_requested') or '')")
PIN_TOK_REV=$(python3 -c "import json; print(json.load(open('$WORKDIR/pins_f4.json')).get('tokenizer_revision_pinned') or json.load(open('$WORKDIR/pins_f4.json')).get('tokenizer_revision_requested') or '')")
echo "f4_model_revision=${PIN_MODEL_REV:-unpinned}"
echo "f4_tokenizer_revision=${PIN_TOK_REV:-unpinned}"

HEALTHY_TEMPLATE_FILE="$WORKDIR/healthy_chat_template.jinja"
WRONG_TEMPLATE_FILE="$WORKDIR/f4_wrong_chat_template.jinja"
python3 - <<PY
import json
from pathlib import Path
pins = json.loads((Path("$WORKDIR") / "pins_f4.json").read_text())
tok_path = Path(pins["tokenizer_local_path"])
wrong_path = Path(pins["wrong_template_source_local_path"])
healthy_tmpl = json.loads((tok_path / "tokenizer_config.json").read_text(encoding="utf-8")).get("chat_template") or ""
if wrong_path.is_file() and wrong_path.suffix == ".jinja":
    wrong_tmpl = wrong_path.read_text(encoding="utf-8")
else:
    wrong_cfg = json.loads((wrong_path / "tokenizer_config.json").read_text(encoding="utf-8")) if (wrong_path / "tokenizer_config.json").is_file() else {}
    wrong_tmpl = wrong_cfg.get("chat_template") or ""
    if not wrong_tmpl:
        jp = wrong_path / "chat_template.jinja"
        if jp.is_file():
            wrong_tmpl = jp.read_text(encoding="utf-8")
if not wrong_tmpl:
    raise SystemExit("Could not extract wrong chat template from template source")
Path("$HEALTHY_TEMPLATE_FILE").write_text(healthy_tmpl, encoding="utf-8")
Path("$WRONG_TEMPLATE_FILE").write_text(wrong_tmpl, encoding="utf-8")
print(f"Wrote healthy template ({len(healthy_tmpl)} chars) -> $HEALTHY_TEMPLATE_FILE")
print(f"Wrote wrong template ({len(wrong_tmpl)} chars) -> $WRONG_TEMPLATE_FILE")
PY

echo "Starting isolated F4 vLLM on GPU $GPU port $PORT"
echo "  model=$MODEL revision=$REV"
echo "  tokenizer=$TOKENIZER_REPO revision=$TOKENIZER_REV (matched healthy)"
echo "  chat-template=$WRONG_TEMPLATE_FILE (Llama template missing assistant generation header)"
echo "  served_model_name=$SERVED_NAME"

nohup env \
  NVIDIA_VISIBLE_DEVICES="$GPU" \
  CUDA_VISIBLE_DEVICES="$GPU" \
  VLLM_USE_FLASHINFER_SAMPLER=0 \
  PYTHONUNBUFFERED=1 \
  python3 -m vllm.entrypoints.openai.api_server \
  --model "$MODEL" \
  --revision "$PIN_MODEL_REV" \
  --tokenizer "$TOKENIZER_REPO" \
  --tokenizer-revision "$PIN_TOK_REV" \
  --chat-template "$WRONG_TEMPLATE_FILE" \
  --served-model-name "$SERVED_NAME" \
  --host 127.0.0.1 \
  --port "$PORT" \
  --tensor-parallel-size 1 \
  --dtype bfloat16 \
  --max-model-len 8192 \
  --gpu-memory-utilization 0.90 \
  --enforce-eager \
  > "$WORKDIR/vllm_f4.log" 2>&1 &
echo $! > "$WORKDIR/vllm_f4.pid"

echo "Waiting for F4 vLLM to load..."
for i in $(seq 1 90); do
  if curl -sf "http://127.0.0.1:${PORT}/v1/models" >/dev/null 2>&1; then
    echo "F4 API ready after ${i}0s"
    curl -s "http://127.0.0.1:${PORT}/v1/models" | head -c 400
    echo
    break
  fi
  sleep 10
  if ! kill -0 "$(cat "$WORKDIR/vllm_f4.pid")" 2>/dev/null; then
    echo "F4 vLLM exited early"
    tail -60 "$WORKDIR/vllm_f4.log"
    exit 1
  fi
done

python3 - <<PY
import json, subprocess
from pathlib import Path
work = Path("$WORKDIR")
pins = json.loads((work / "pins_f4.json").read_text())
try:
    smi = subprocess.check_output(
        ["nvidia-smi", "--query-gpu=index,name,memory.used,memory.total,utilization.gpu", "--format=csv,noheader"],
        text=True,
    ).strip()
    pins["nvidia_smi_after_load"] = smi
except Exception as exc:
    pins["nvidia_smi_after_error"] = str(exc)
pid = (work / "vllm_f4.pid").read_text(encoding="utf-8").strip()
pins["vllm_command"] = open(f"/proc/{pid}/cmdline", "rb").read().replace(b"\\x00", b" ").decode("utf-8", "replace")
(work / "pins_f4.json").write_text(json.dumps(pins, indent=2), encoding="utf-8")
print("Updated pins_f4.json with post-load GPU snapshot + vLLM cmdline")
PY

echo "=== vllm_f4 pid ==="
cat "$WORKDIR/vllm_f4.pid"
echo "=== vllm_f4 log tail ==="
tail -40 "$WORKDIR/vllm_f4.log"
