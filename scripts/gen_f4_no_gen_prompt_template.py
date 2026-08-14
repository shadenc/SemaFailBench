#!/usr/bin/env python3
"""Build F4 faulty template: official Llama 3.1 template minus generation header."""
import json
import os
from pathlib import Path

from huggingface_hub import hf_hub_download

REPO = "meta-llama/Llama-3.1-8B-Instruct"
REVISION = "0e9e39f249a16976918f6564b8830bc894c89659"
LOCAL_OUT = Path(__file__).resolve().parents[1] / "configs/f4_wrong_chat_template_no_gen_prompt.jinja"

cfg_path = hf_hub_download(
    REPO,
    revision=REVISION,
    filename="tokenizer_config.json",
    token=os.getenv("HF_TOKEN") or os.getenv("HUGGING_FACE_HUB_TOKEN"),
)
healthy = json.loads(Path(cfg_path).read_text(encoding="utf-8"))["chat_template"]
marker = "{%- if add_generation_prompt %}"
if marker not in healthy:
    raise SystemExit("healthy template missing add_generation_prompt block")
faulty = healthy[: healthy.rindex(marker)].rstrip() + "\n"

LOCAL_OUT.parent.mkdir(parents=True, exist_ok=True)
header = "{# F4: official Llama 3.1 template with assistant generation header omitted #}\n"
LOCAL_OUT.write_text(header + faulty, encoding="utf-8")

print(json.dumps({
    "out": str(LOCAL_OUT),
    "healthy_len": len(healthy),
    "faulty_len": len(faulty),
    "generation_block_removed": marker not in faulty,
    "healthy_tail": healthy[-240:],
    "faulty_tail": faulty[-240:],
}, indent=2))
