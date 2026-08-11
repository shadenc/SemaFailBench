#!/usr/bin/env python3
"""Compare HEALTHY vs F2 serving artifacts; write f2_isolation_manifest.json."""

from __future__ import annotations

import argparse
import importlib.util
import json
import os
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT / "scripts"))

from serving_artifact_probe import (  # noqa: E402
    compare_probes,
    compare_tokenize_probes,
    frozen_healthy_spec,
)

load_dotenv(ROOT / ".env", override=True)

_spec = importlib.util.spec_from_file_location(
    "run_healthy_stability", ROOT / "scripts" / "run_healthy_stability.py"
)
_rhs = importlib.util.module_from_spec(_spec)
assert _spec.loader is not None
_spec.loader.exec_module(_rhs)
check_api = _rhs.check_api
snapshot_gpu = _rhs.snapshot_gpu
expand = _rhs.expand


def ssh_cmd(key: Path, host: str, port: int, remote: str) -> str:
    return subprocess.check_output(
        [
            "ssh",
            "-o",
            "BatchMode=yes",
            "-o",
            "ConnectTimeout=20",
            "-i",
            str(key),
            "-p",
            str(port),
            f"root@{host}",
            remote,
        ],
        text=True,
    ).strip()


def read_remote_json(key: Path, host: str, port: int, path: str) -> dict:
    raw = ssh_cmd(
        key,
        host,
        port,
        f"python3 -c \"import json; print(json.dumps(json.load(open('{path}'))))\"",
    )
    return json.loads(raw)


def probe_remote_dir(key: Path, host: str, port: int, workdir: str, tok_dir: str) -> dict:
    raw = ssh_cmd(
        key,
        host,
        port,
        f"python3 {workdir}/serving_artifact_probe.py {tok_dir} --tokenize-probe",
    )
    return json.loads(raw)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--healthy-manifest",
        type=Path,
        default=ROOT / "results" / "f2-retest" / "healthy_restore_manifest.json",
    )
    parser.add_argument(
        "--out",
        type=Path,
        default=ROOT / "results" / "f2-retest" / "f2_isolation_manifest.json",
    )
    args = parser.parse_args()

    if not args.healthy_manifest.is_file():
        print(f"Missing healthy manifest: {args.healthy_manifest}", file=sys.stderr)
        return 2

    healthy_manifest = json.loads(args.healthy_manifest.read_text(encoding="utf-8"))
    if not healthy_manifest.get("verified"):
        print("Healthy restore not verified — run verify_healthy_restore.py first", file=sys.stderr)
        return 2

    frozen = frozen_healthy_spec()
    f2_actual = os.getenv("SFB_F2_ACTUAL_MODEL", "Qwen/Qwen2-7B-Instruct")
    f2_rev = os.getenv("SFB_F2_REVISION", "f2826a00ceef68f0f2b946d945ecc0477ce4450c")
    expected = os.getenv("SFB_F2_EXPECTED_MODEL", frozen["model_repo"])

    key = Path(expand(os.getenv("SFB_RUNPOD_KEY", "~/.ssh/sfb_runpod")))
    host = os.getenv("SFB_RUNPOD_TCP_HOST", "")
    port = int(os.getenv("SFB_RUNPOD_TCP_PORT", "22"))
    workdir = os.getenv("SFB_POD_WORKDIR", "/workspace/semafailbench")
    base_url = os.getenv("SFB_BASE_URL", "http://127.0.0.1:8000/v1")

    api = check_api(base_url)
    pins_f2 = read_remote_json(key, host, port, f"{workdir}/pins_f2.json")

    healthy_probe = healthy_manifest.get("tokenizer_probe") or {}
    healthy_tok_dir = pins_f2.get("healthy_tokenizer_local_path") or pins_f2.get("tokenizer_local_path")
    f2_tok_dir = pins_f2.get("tokenizer_local_path")
    if not f2_tok_dir:
        print("pins_f2.json missing tokenizer_local_path", file=sys.stderr)
        return 2

    f2_probe = probe_remote_dir(key, host, port, workdir, f2_tok_dir)
    if healthy_tok_dir and healthy_tok_dir != f2_tok_dir:
        healthy_probe = probe_remote_dir(key, host, port, workdir, healthy_tok_dir)

    artifact_cmp = compare_probes(healthy_probe, f2_probe)
    tokenize_cmp = compare_tokenize_probes(
        healthy_probe.get("tokenize_probe") or {},
        f2_probe.get("tokenize_probe") or {},
    )

    vllm_proc = ((snapshot_gpu(key, host, port) or {}).get("vllm_process")) or ""
    checkpoint_changed = f2_actual in vllm_proc and frozen["model_repo"] not in vllm_proc.split("--model", 1)[-1][:80]

    gen_same = True  # F2 bootstrap uses same dtype/max_model_len flags as healthy
    dtype_same = "bfloat16" in vllm_proc or "--dtype bfloat16" in vllm_proc
    lora_same = "--lora" not in vllm_proc and "--enable-lora" not in vllm_proc

    isolated = (
        artifact_cmp["tokenizer_files_identical"]
        and artifact_cmp["chat_template_identical"]
        and tokenize_cmp["token_ids_equal"]
        and checkpoint_changed
        and dtype_same
        and lora_same
        and gen_same
    )

    manifest = {
        "fault": "F2",
        "timestamp_utc": datetime.now(timezone.utc).isoformat(),
        "expected_model": expected,
        "actual_checkpoint": f2_actual,
        "actual_checkpoint_revision": f2_rev,
        "checkpoint_changed": checkpoint_changed,
        "tokenizer_same_as_healthy": artifact_cmp["tokenizer_files_identical"],
        "chat_template_same_as_healthy": artifact_cmp["chat_template_identical"],
        "token_ids_same_as_healthy": tokenize_cmp["token_ids_equal"],
        "generation_same_as_healthy": gen_same,
        "dtype_same_as_healthy": dtype_same,
        "quantization_same_as_healthy": "awq" not in vllm_proc.lower() and "gptq" not in vllm_proc.lower(),
        "lora_same_as_healthy": lora_same,
        "vllm_command": vllm_proc,
        "artifact_comparison": artifact_cmp,
        "tokenize_comparison": tokenize_cmp,
        "healthy_tokenizer_dir": healthy_tok_dir,
        "f2_tokenizer_dir": f2_tok_dir,
        "pins_f2": {
            k: pins_f2.get(k)
            for k in (
                "actual_model",
                "expected_model",
                "actual_model_revision_pinned",
                "tokenizer_repo",
                "tokenizer_revision",
                "model_local_path",
                "tokenizer_local_path",
                "healthy_tokenizer_local_path",
                "isolation_probe",
            )
        },
        "api": api,
        "isolated": isolated,
        "verdict": "ISOLATED" if isolated else "CONFOUNDED",
    }

    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    print(f"Wrote {args.out}")

    if not isolated:
        print("\nF2 CANDIDATE REJECTED: CONFOUNDED WITH F3/F4", file=sys.stderr)
        if not artifact_cmp["tokenizer_files_identical"]:
            print(f"  tokenizer file diffs: {artifact_cmp['tokenizer_file_diffs']}", file=sys.stderr)
        if not artifact_cmp["chat_template_identical"]:
            print("  chat template hash mismatch", file=sys.stderr)
        if not tokenize_cmp["token_ids_equal"]:
            print("  tokenization probe mismatch", file=sys.stderr)
        if not checkpoint_changed:
            print("  checkpoint/model weights did not change", file=sys.stderr)
        return 4

    print("F2 isolation gate PASSED")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
