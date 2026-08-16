#!/usr/bin/env python3
"""Verify that F1 changes weight representation only (bf16 -> AWQ INT4)."""

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
sys.path.insert(0, str(ROOT / "scripts"))

from serving_artifact_probe import compare_probes, compare_tokenize_probes  # noqa: E402

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


def remote_json(key: Path, host: str, port: int, expression: str) -> dict:
    return json.loads(ssh_cmd(key, host, port, f"python3 -c \"{expression}\""))


def probe_dir(key: Path, host: str, port: int, workdir: str, path: str) -> dict:
    return json.loads(
        ssh_cmd(
            key,
            host,
            port,
            f"python3 {workdir}/serving_artifact_probe.py {path} --tokenize-probe",
        )
    )


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--healthy-manifest",
        type=Path,
        default=ROOT / "results" / "f1-gemma2-retest" / "healthy_restore_manifest.json",
    )
    parser.add_argument(
        "--out",
        type=Path,
        default=ROOT / "results" / "f1-gemma2-retest" / "f1_isolation_manifest.json",
    )
    args = parser.parse_args()

    if not args.healthy_manifest.is_file():
        print(f"Missing healthy manifest: {args.healthy_manifest}", file=sys.stderr)
        return 2
    healthy = json.loads(args.healthy_manifest.read_text(encoding="utf-8"))
    if not healthy.get("verified"):
        print("Healthy reference is not verified", file=sys.stderr)
        return 2

    key = Path(expand(os.getenv("SFB_RUNPOD_KEY", "~/.ssh/sfb_runpod")))
    host = os.getenv("SFB_RUNPOD_TCP_HOST", "")
    port = int(os.getenv("SFB_RUNPOD_TCP_PORT", "22"))
    workdir = os.getenv("SFB_POD_WORKDIR", "/workspace/semafailbench")
    base_url = os.getenv("SFB_BASE_URL", "http://127.0.0.1:8000/v1")

    pins = remote_json(
        key,
        host,
        port,
        f"import json; print(json.dumps(json.load(open('{workdir}/pins_f1.json'))))",
    )
    f1_path = pins.get("model_local_path")
    tokenizer_path = pins.get("tokenizer_local_path")
    if not f1_path or not tokenizer_path:
        print("pins_f1.json missing model/tokenizer local path", file=sys.stderr)
        return 2

    healthy_probe = healthy.get("tokenizer_probe") or {}
    f1_probe = probe_dir(key, host, port, workdir, tokenizer_path)
    artifact_cmp = compare_probes(healthy_probe, f1_probe)
    token_cmp = compare_tokenize_probes(
        healthy_probe.get("tokenize_probe") or {},
        f1_probe.get("tokenize_probe") or {},
    )

    config = remote_json(
        key,
        host,
        port,
        (
            "import json, pathlib; "
            f"p=pathlib.Path('{f1_path}'); "
            "c=json.load(open(p/'config.json')); "
            "q=json.load(open(p/'quant_config.json')) if (p/'quant_config.json').exists() "
            "else c.get('quantization_config', {}); "
            "print(json.dumps({'model_type': c.get('model_type'), "
            "'architectures': c.get('architectures'), 'quantization_config': q}))"
        ),
    )

    api = check_api(base_url)
    proc = ((snapshot_gpu(key, host, port) or {}).get("vllm_process")) or ""
    requested_model = os.getenv(
        "SFB_F1_MODEL", "hugging-quants/gemma-2-9b-it-AWQ-INT4"
    )
    quant = os.getenv("SFB_F1_QUANTIZATION", "awq_marlin")
    expected_arch = os.getenv("SFB_F1_ARCH", "gemma2")
    model_loaded = requested_model in proc
    quantization_active = (
        f"--quantization {quant}" in proc
        and bool(config.get("quantization_config"))
    )
    architecture_matches = config.get("model_type") == expected_arch
    healthy_tokenizer_loaded = f"--tokenizer {tokenizer_path}" in proc
    no_other_fault = all(
        flag not in proc
        for flag in ("--chat-template", "--enable-lora", "--lora-modules",
                     "--override-generation-config")
    )
    isolated = all(
        [
            api.get("ok") is True,
            model_loaded,
            quantization_active,
            architecture_matches,
            artifact_cmp["tokenizer_files_identical"],
            artifact_cmp["chat_template_identical"],
            token_cmp["token_ids_equal"],
            healthy_tokenizer_loaded,
            no_other_fault,
        ]
    )

    manifest = {
        "fault": "F1",
        "timestamp_utc": datetime.now(timezone.utc).isoformat(),
        "healthy_model": (healthy.get("frozen_spec") or {}).get("model_repo"),
        "healthy_revision": (healthy.get("frozen_spec") or {}).get("model_revision"),
        "fault_model": requested_model,
        "fault_revision": pins.get("model_revision"),
        "quantization": quant,
        "model_loaded": model_loaded,
        "quantization_active": quantization_active,
        "architecture_matches": architecture_matches,
        "expected_architecture": expected_arch,
        "tokenizer_same_as_healthy": artifact_cmp["tokenizer_files_identical"],
        "chat_template_same_as_healthy": artifact_cmp["chat_template_identical"],
        "token_ids_same_as_healthy": token_cmp["token_ids_equal"],
        "healthy_tokenizer_loaded": healthy_tokenizer_loaded,
        "other_fault_flags_absent": no_other_fault,
        "model_config": config,
        "artifact_comparison": artifact_cmp,
        "tokenize_comparison": token_cmp,
        "pins_f1": pins,
        "api": api,
        "vllm_command": proc,
        "isolated": isolated,
        "verdict": "ISOLATED" if isolated else "CONFOUNDED",
    }
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    print(f"Wrote {args.out}")
    print(f"F1 isolation: {manifest['verdict']}")
    return 0 if isolated else 4


if __name__ == "__main__":
    raise SystemExit(main())
