#!/usr/bin/env python3
"""Build F4 faulty template: official Qwen2.5 ChatML minus assistant generation header."""
import json
import re
import sys
from pathlib import Path

from transformers import AutoTokenizer

TOK_PATH = Path(
    "/workspace/.cache/huggingface/hub/models--Qwen--Qwen2.5-7B-Instruct/snapshots/"
    "a09a35458c702b33eeacc393d103063234e8bc28"
)
OUT = Path("/workspace/semafailbench/f4_no_gen_prompt_from_official.jinja")
LOCAL_OUT = Path(__file__).resolve().parents[1] / "configs/f4_wrong_chat_template_no_gen_prompt.jinja"

healthy = json.loads((TOK_PATH / "tokenizer_config.json").read_text())["chat_template"]
marker = "{%- if add_generation_prompt %}"
if marker not in healthy:
    raise SystemExit("healthy template missing add_generation_prompt block")
faulty = healthy[: healthy.rindex(marker)].rstrip() + "\n"

out_path = OUT if TOK_PATH.is_dir() else LOCAL_OUT
out_path.parent.mkdir(parents=True, exist_ok=True)
header = (
    "{# F4: official Qwen2.5 template with assistant generation header omitted #}\n"
)
out_path.write_text(header + faulty, encoding="utf-8")

tok = AutoTokenizer.from_pretrained(str(TOK_PATH if TOK_PATH.is_dir() else "Qwen/Qwen2.5-7B-Instruct"), trust_remote_code=True)
if not TOK_PATH.is_dir():
    healthy = json.loads(
        __import__("huggingface_hub").hf_hub_download(
            "Qwen/Qwen2.5-7B-Instruct",
            revision="a09a35458c702b33eeacc393d103063234e8bc28",
            filename="tokenizer_config.json",
        )
    )["chat_template"]
    faulty = header + healthy[: healthy.rindex(marker)].rstrip() + "\n"
    LOCAL_OUT.write_text(faulty if faulty.startswith("{#") else header + faulty, encoding="utf-8")

msgs = [
    {"role": "system", "content": "You are a careful assistant."},
    {"role": "user", "content": "Reply with exactly three words."},
]
h_ids = list(tok.apply_chat_template(msgs, tokenize=True, add_generation_prompt=True, chat_template=healthy)["input_ids"])
f_ids = list(tok.apply_chat_template(msgs, tokenize=True, add_generation_prompt=True, chat_template=faulty)["input_ids"])
print(json.dumps({
    "out": str(out_path),
    "healthy_len": len(healthy),
    "faulty_len": len(faulty),
    "token_ids_equal": h_ids == f_ids,
    "healthy_tail": tok.decode(h_ids)[-100:],
    "faulty_tail": tok.decode(f_ids)[-100:],
}, indent=2))
