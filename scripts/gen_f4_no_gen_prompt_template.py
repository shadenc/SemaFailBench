#!/usr/bin/env python3
"""Build F4 faulty template: official family chat template minus generation header.

Same mechanism as Qwen and Llama: delete the final add_generation_prompt block from
the healthy tokenizer_config.json chat_template. Do not import a cross-family template.

Official jinja varies whitespace control (`{%-` vs `{%`); match the if-block, not one family.
"""
from __future__ import annotations

import json
import os
import re
from pathlib import Path

from huggingface_hub import hf_hub_download
from transformers import AutoTokenizer

ROOT = Path(__file__).resolve().parents[1]
REPO = os.getenv("SFB_F4_MODEL", os.getenv("SFB_MODEL", "google/gemma-2-9b-it"))
REVISION = os.getenv(
    "SFB_F4_MODEL_REVISION",
    os.getenv("SFB_HEALTHY_REVISION", "11c9b309abf73637e4b6f9a3fa1e92e615547819"),
)
LOCAL_OUT = ROOT / "configs/f4_wrong_chat_template_no_gen_prompt.jinja"
GEN_PROMPT_IF = re.compile(r"\{%-?\s*if\s+add_generation_prompt\s*-?%\}")


def sample_messages_for(tok, template: str) -> list[dict[str, str]]:
    """Use system+user when the template allows it; otherwise fold system into user.

    Templates that raise on role=system (Gemma and others) must not be probed with a
    system turn. Message text stays the same either way.
    """
    system = "You are a careful assistant."
    user = "Reply with exactly three words."
    with_system = [
        {"role": "system", "content": system},
        {"role": "user", "content": user},
    ]
    try:
        tok.apply_chat_template(
            with_system, tokenize=True, add_generation_prompt=True, chat_template=template
        )
        return with_system
    except Exception:
        return [{"role": "user", "content": f"{system}\n\n{user}"}]


def token_ids(tok, messages: list[dict[str, str]], template: str) -> list[int]:
    out = tok.apply_chat_template(
        messages, tokenize=True, add_generation_prompt=True, chat_template=template
    )
    if hasattr(out, "input_ids"):
        ids = out.input_ids
    elif isinstance(out, dict) and "input_ids" in out:
        ids = out["input_ids"]
    else:
        ids = out
    if hasattr(ids, "tolist"):
        ids = ids.tolist()
    if ids and isinstance(ids[0], (list, tuple)):
        ids = ids[0]
    return [int(x) for x in ids]


def main() -> int:
    cfg_path = hf_hub_download(
        REPO,
        revision=REVISION,
        filename="tokenizer_config.json",
        token=os.getenv("HF_TOKEN") or os.getenv("HUGGING_FACE_HUB_TOKEN"),
    )
    healthy = json.loads(Path(cfg_path).read_text(encoding="utf-8"))["chat_template"]
    matches = list(GEN_PROMPT_IF.finditer(healthy))
    if not matches:
        raise SystemExit("healthy template missing add_generation_prompt block")
    faulty = healthy[: matches[-1].start()].rstrip() + "\n"
    if GEN_PROMPT_IF.search(faulty):
        raise SystemExit("generation block still present after strip")

    LOCAL_OUT.parent.mkdir(parents=True, exist_ok=True)
    header = f"{{# F4: official {REPO} template with assistant generation header omitted #}}\n"
    LOCAL_OUT.write_text(header + faulty, encoding="utf-8")

    tok = AutoTokenizer.from_pretrained(REPO, revision=REVISION, trust_remote_code=True)
    messages = sample_messages_for(tok, healthy)
    h_ids = token_ids(tok, messages, healthy)
    f_ids = token_ids(tok, messages, faulty)
    h_text = tok.apply_chat_template(
        messages, tokenize=False, add_generation_prompt=True, chat_template=healthy
    )
    f_text = tok.apply_chat_template(
        messages, tokenize=False, add_generation_prompt=True, chat_template=faulty
    )
    report = {
        "out": str(LOCAL_OUT),
        "repo": REPO,
        "revision": REVISION,
        "healthy_len": len(healthy),
        "faulty_len": len(faulty),
        "generation_block_removed": GEN_PROMPT_IF.search(faulty) is None,
        "used_system_role": any(m.get("role") == "system" for m in messages),
        "token_ids_equal": h_ids == f_ids,
        "has_llama_header": "<|start_header_id|>" in faulty,
        "has_mistral_inst": "[INST]" in faulty,
        "has_gemma_turn": "<start_of_turn>" in faulty,
        "healthy_tail": h_text[-180:],
        "faulty_tail": f_text[-180:],
    }
    print(json.dumps(report, indent=2))
    if h_ids == f_ids:
        print("ERROR: F4 faulty template does not change served token IDs", file=sys.stderr)
        return 1
    if report["has_llama_header"] or report["has_mistral_inst"]:
        print("ERROR: faulty template still contains cross-family markers", file=sys.stderr)
        return 1
    if REPO.lower().startswith("google/gemma") and not report["has_gemma_turn"]:
        print("ERROR: Gemma F4 template is missing <start_of_turn>", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
