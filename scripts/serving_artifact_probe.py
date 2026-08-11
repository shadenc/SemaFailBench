#!/usr/bin/env python3
"""Hash and compare frozen healthy vs fault serving artifacts (tokenizer, chat template)."""

from __future__ import annotations

import hashlib
import json
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
if (ROOT / "src").is_dir():
    sys.path.insert(0, str(ROOT / "src"))

try:
    from sem_fail_bench.hash_utils import sha256_file, sha256_text  # type: ignore
except ModuleNotFoundError:
    def sha256_text(text: str) -> str:
        return hashlib.sha256((text or "").encode("utf-8")).hexdigest()

    def sha256_file(path: str | Path) -> str:
        digest = hashlib.sha256()
        with open(path, "rb") as fh:
            for chunk in iter(lambda: fh.read(1024 * 1024), b""):
                digest.update(chunk)
        return digest.hexdigest()

TOKENIZER_FILES = (
    "tokenizer.json",
    "vocab.json",
    "merges.txt",
    "tokenizer_config.json",
    "special_tokens_map.json",
)


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def load_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def tokenizer_file_hashes(tokenizer_dir: Path) -> dict[str, str | None]:
    out: dict[str, str | None] = {}
    for name in TOKENIZER_FILES:
        path = tokenizer_dir / name
        out[name] = sha256_file(path) if path.is_file() else None
    return out


def chat_template_hash(tokenizer_dir: Path) -> dict[str, Any]:
    cfg_path = tokenizer_dir / "tokenizer_config.json"
    if not cfg_path.is_file():
        return {"present": False, "hash": None, "length": 0}
    cfg = load_json(cfg_path)
    template = cfg.get("chat_template")
    if template is None:
        return {"present": False, "hash": None, "length": 0}
    if not isinstance(template, str):
        template = json.dumps(template, sort_keys=True, ensure_ascii=False)
    return {"present": True, "hash": sha256_text(template), "length": len(template)}


def probe_tokenizer_dir(tokenizer_dir: str | Path) -> dict[str, Any]:
    path = Path(tokenizer_dir)
    files = tokenizer_file_hashes(path)
    chat = chat_template_hash(path)
    bundle_parts = [f"{k}={v or ''}" for k, v in sorted(files.items())]
    bundle_parts.append(f"chat_template={chat.get('hash') or ''}")
    return {
        "tokenizer_dir": str(path),
        "file_hashes": files,
        "chat_template": chat,
        "bundle_hash": sha256_text(";".join(bundle_parts)),
    }


def tokenize_probe(tokenizer_dir: str | Path) -> dict[str, Any]:
    from transformers import AutoTokenizer

    tok = AutoTokenizer.from_pretrained(str(tokenizer_dir), trust_remote_code=True)
    messages = [
        {"role": "system", "content": "You are a careful assistant."},
        {"role": "user", "content": "Reply with exactly three words."},
    ]
    out = tok.apply_chat_template(messages, tokenize=True, add_generation_prompt=True)
    ids = out["input_ids"] if hasattr(out, "__getitem__") else out
    if hasattr(ids, "tolist"):
        ids = ids.tolist()
    ids = list(ids)
    return {
        "vocab_len": len(tok),
        "token_ids": ids,
        "token_ids_hash": sha256_text(json.dumps(ids)),
        "decode_prefix": tok.decode(ids[:40]),
    }


def compare_probes(healthy: dict[str, Any], candidate: dict[str, Any]) -> dict[str, Any]:
    h_files = healthy.get("file_hashes") or {}
    c_files = candidate.get("file_hashes") or {}
    file_diffs = sorted(k for k in TOKENIZER_FILES if h_files.get(k) != c_files.get(k))
    h_chat = (healthy.get("chat_template") or {}).get("hash")
    c_chat = (candidate.get("chat_template") or {}).get("hash")
    return {
        "tokenizer_files_identical": not file_diffs,
        "tokenizer_file_diffs": file_diffs,
        "chat_template_identical": h_chat == c_chat and h_chat is not None,
        "chat_template_hash_healthy": h_chat,
        "chat_template_hash_candidate": c_chat,
        "bundle_hash_healthy": healthy.get("bundle_hash"),
        "bundle_hash_candidate": candidate.get("bundle_hash"),
        "bundle_identical": healthy.get("bundle_hash") == candidate.get("bundle_hash"),
    }


def compare_tokenize_probes(healthy: dict[str, Any], candidate: dict[str, Any]) -> dict[str, Any]:
    h_ids = healthy.get("token_ids") or []
    c_ids = candidate.get("token_ids") or []
    return {
        "token_ids_equal": h_ids == c_ids,
        "vocab_len_healthy": healthy.get("vocab_len"),
        "vocab_len_candidate": candidate.get("vocab_len"),
        "token_ids_hash_healthy": healthy.get("token_ids_hash"),
        "token_ids_hash_candidate": candidate.get("token_ids_hash"),
    }


def frozen_healthy_spec() -> dict[str, str]:
    return {
        "model_repo": "Qwen/Qwen2.5-7B-Instruct",
        "model_revision": "a09a35458c702b33eeacc393d103063234e8bc28",
        "tokenizer_repo": "Qwen/Qwen2.5-7B-Instruct",
        "tokenizer_revision": "a09a35458c702b33eeacc393d103063234e8bc28",
        "dtype": "bfloat16",
        "quantization": "none",
        "lora": "none",
        "max_model_len": "8192",
        "gpu_memory_utilization": "0.90",
    }


def main() -> int:
    import argparse

    parser = argparse.ArgumentParser(description="Probe tokenizer/chat-template artifacts")
    parser.add_argument("tokenizer_dir", type=Path)
    parser.add_argument("--tokenize-probe", action="store_true")
    args = parser.parse_args()
    probe = probe_tokenizer_dir(args.tokenizer_dir)
    if args.tokenize_probe:
        probe["tokenize_probe"] = tokenize_probe(args.tokenizer_dir)
    print(json.dumps(probe, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
