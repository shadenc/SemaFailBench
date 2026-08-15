#!/usr/bin/env python3
"""Build F4 faulty chat template: missing assistant generation header (deletion only)."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from huggingface_hub import hf_hub_download
from transformers import AutoTokenizer

ROOT = Path(__file__).resolve().parents[1]
QWEN_MARKER = "{%- if add_generation_prompt %}"

QWEN_REPO = "Qwen/Qwen2.5-7B-Instruct"
QWEN_REV = "a09a35458c702b33eeacc393d103063234e8bc28"
MISTRAL_REPO = "mistralai/Mistral-7B-Instruct-v0.3"
MISTRAL_REV = "c170c708c41dac9275d15a8fff4eca08d52bab71"

INST_CLOSE = ' + "[/INST]"'

PROFILE_DEFAULTS = {
    "qwen": {
        "out": ROOT / "configs/f4_wrong_chat_template_no_gen_prompt.jinja",
        "tokenizer_repo": QWEN_REPO,
        "tokenizer_rev": QWEN_REV,
        "header": "{# F4: official Qwen2.5 template with assistant generation header omitted #}\n",
        "build": "qwen_strip",
    },
    "mistral": {
        "out": ROOT / "configs/mistral/f4_wrong_chat_template_no_gen_prompt.jinja",
        "tokenizer_repo": MISTRAL_REPO,
        "tokenizer_rev": MISTRAL_REV,
        "header": (
            "{# F4 Mistral v0.3: official bundled jinja with [/INST] closers deleted #}\n"
            "{# Realistic ops mistake: bad edit removes generation-close suffix from user turns. #}\n"
        ),
        "build": "mistral_delete_inst_close",
    },
}


def load_chat_template(repo: str, revision: str) -> str:
    path = hf_hub_download(repo, revision=revision, filename="tokenizer_config.json")
    return json.loads(Path(path).read_text(encoding="utf-8"))["chat_template"]


def strip_qwen_generation_block(healthy: str) -> str:
    if QWEN_MARKER not in healthy:
        raise ValueError("healthy Qwen template missing add_generation_prompt block")
    return healthy[: healthy.rindex(QWEN_MARKER)].rstrip() + "\n"


def delete_mistral_inst_close(healthy: str) -> str:
    """Delete [/INST] generation-close suffixes only (no new jinja branches added)."""
    if INST_CLOSE not in healthy:
        raise ValueError("healthy Mistral template missing [/INST] close suffix")
    removed = healthy.count(INST_CLOSE)
    faulty = healthy.replace(INST_CLOSE, "")
    if faulty == healthy:
        raise ValueError("Mistral F4 deletion made no change")
    return faulty


def build_faulty(profile: str, healthy: str) -> str:
    mode = PROFILE_DEFAULTS[profile]["build"]
    if mode == "qwen_strip":
        return strip_qwen_generation_block(healthy)
    if mode == "mistral_delete_inst_close":
        return delete_mistral_inst_close(healthy)
    raise ValueError(f"unknown build mode: {mode}")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--profile",
        choices=sorted(PROFILE_DEFAULTS),
        default="qwen",
    )
    args = parser.parse_args()
    cfg = PROFILE_DEFAULTS[args.profile]

    healthy = load_chat_template(cfg["tokenizer_repo"], cfg["tokenizer_rev"])
    faulty = build_faulty(args.profile, healthy)

    out_path = cfg["out"]
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(cfg["header"] + faulty, encoding="utf-8")

    tok = AutoTokenizer.from_pretrained(cfg["tokenizer_repo"], revision=cfg["tokenizer_rev"], trust_remote_code=True)
    msgs = [
        {"role": "system", "content": "You are a careful assistant."},
        {"role": "user", "content": "Reply with exactly three words."},
    ]

    def token_ids(template: str) -> list[int]:
        out = tok.apply_chat_template(
            msgs,
            tokenize=True,
            add_generation_prompt=True,
            chat_template=template,
        )
        return list(out["input_ids"])

    h_ids = token_ids(healthy)
    f_ids = token_ids(faulty)
    h_text = tok.apply_chat_template(
        msgs, tokenize=False, add_generation_prompt=True, chat_template=healthy
    )
    f_text = tok.apply_chat_template(
        msgs, tokenize=False, add_generation_prompt=True, chat_template=faulty
    )

    report = {
        "profile": args.profile,
        "build": cfg["build"],
        "out": str(out_path),
        "healthy_template_len": len(healthy),
        "faulty_template_len": len(faulty),
        "deleted_inst_close_count": healthy.count(INST_CLOSE) if args.profile == "mistral" else None,
        "token_ids_equal_healthy_vs_faulty": h_ids == f_ids,
        "healthy_tail": h_text[-120:],
        "faulty_tail": f_text[-120:],
    }
    print(json.dumps(report, indent=2))
    if h_ids == f_ids:
        print("ERROR: F4 faulty template does not change served token IDs", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
