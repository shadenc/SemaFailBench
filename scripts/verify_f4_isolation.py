#!/usr/bin/env python3
"""Compare HEALTHY vs F4 serving artifacts; write f4_isolation_manifest.json."""

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
        default=ROOT / "results" / "f4-retest" / "healthy_restore_manifest.json",
    )
    parser.add_argument(
        "--out",
        type=Path,
        default=ROOT / "results" / "f4-retest" / "f4_isolation_manifest.json",
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
    expected_model = os.getenv("SFB_F4_MODEL", frozen["model_repo"])
    expected_rev = os.getenv("SFB_F4_MODEL_REVISION", frozen["model_revision"])

    key = Path(expand(os.getenv("SFB_RUNPOD_KEY", "~/.ssh/sfb_runpod")))
    host = os.getenv("SFB_RUNPOD_TCP_HOST", "")
    port = int(os.getenv("SFB_RUNPOD_TCP_PORT", "22"))
    workdir = os.getenv("SFB_POD_WORKDIR", "/workspace/semafailbench")
    base_url = os.getenv("SFB_BASE_URL", "http://127.0.0.1:8000/v1")

    api = check_api(base_url)
    pins_f4 = read_remote_json(key, host, port, f"{workdir}/pins_f4.json")

    healthy_probe = healthy_manifest.get("tokenizer_probe") or {}
    f4_tok_dir = pins_f4.get("tokenizer_local_path") or pins_f4.get("model_local_path")
    if not f4_tok_dir:
        print("pins_f4.json missing tokenizer_local_path", file=sys.stderr)
        return 2

    f4_probe = probe_remote_dir(key, host, port, workdir, f4_tok_dir)
    if healthy_probe.get("tokenizer_dir") != f4_probe.get("tokenizer_dir"):
        healthy_probe = probe_remote_dir(key, host, port, workdir, f4_tok_dir)

    artifact_cmp = compare_probes(healthy_probe, f4_probe)
    tokenize_cmp = compare_tokenize_probes(
        healthy_probe.get("tokenize_probe") or {},
        f4_probe.get("tokenize_probe") or {},
    )

    gpu_snap = snapshot_gpu(key, host, port) or {}
    vllm_proc = gpu_snap.get("vllm_process") or pins_f4.get("vllm_command") or ""
    weights_unchanged = expected_model in vllm_proc
    if expected_rev and expected_rev[:8] not in vllm_proc:
        weights_unchanged = weights_unchanged and pins_f4.get("model_repo") == expected_model

    dtype_same = "bfloat16" in vllm_proc or "--dtype bfloat16" in vllm_proc
    lora_same = "--lora" not in vllm_proc and "--enable-lora" not in vllm_proc
    isolation_probe = pins_f4.get("isolation_probe") or {}

    wrong_template_served = (
        "--chat-template" in vllm_proc
        and "f4_wrong_chat_template.jinja" in vllm_proc
    )
    served_template_differs = not isolation_probe.get("chat_template_equal_healthy_vs_wrong_source", True)
    served_token_ids_differ = not isolation_probe.get("token_ids_equal_healthy_vs_wrong_served", True)

    isolated = (
        weights_unchanged
        and artifact_cmp["tokenizer_files_identical"]
        and artifact_cmp["chat_template_identical"]
        and tokenize_cmp["token_ids_equal"]
        and wrong_template_served
        and served_template_differs
        and served_token_ids_differ
        and dtype_same
        and lora_same
    )

    manifest = {
        "fault": "F4",
        "deployment_kind": pins_f4.get("deployment_kind", "wrong_chat_template_isolated"),
        "timestamp_utc": datetime.now(timezone.utc).isoformat(),
        "expected_model": expected_model,
        "expected_model_revision": expected_rev,
        "weights_unchanged": weights_unchanged,
        "tokenizer_files_same_as_healthy": artifact_cmp["tokenizer_files_identical"],
        "chat_template_in_files_same_as_healthy": artifact_cmp["chat_template_identical"],
        "served_chat_template_differs": served_template_differs,
        "served_token_ids_differ": served_token_ids_differ,
        "token_ids_in_tokenizer_files_same_as_healthy": tokenize_cmp["token_ids_equal"],
        "dtype_same_as_healthy": dtype_same,
        "lora_same_as_healthy": lora_same,
        "wrong_template_served_via_vllm_flag": wrong_template_served,
        "vllm_command": vllm_proc,
        "artifact_comparison": artifact_cmp,
        "tokenize_comparison": tokenize_cmp,
        "isolation_probe": isolation_probe,
        "api_check": api,
        "isolated": isolated,
        "notes": (
            "F4 isolated: matched weights+tokenizer; vLLM --chat-template points at wrong family template."
            if isolated
            else "F4 CONFOUNDED — check weights, tokenizer files, or served template."
        ),
    }

    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    print(json.dumps(manifest, indent=2))
    if not isolated:
        print("F4 CANDIDATE REJECTED: CONFOUNDED WITH F2/F3", file=sys.stderr)
        return 1
    print(f"Wrote {args.out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
