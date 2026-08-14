#!/usr/bin/env python3
"""Compare HEALTHY vs F6 serving artifacts; write f6_isolation_manifest.json."""

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

from serving_artifact_probe import compare_probes, compare_tokenize_probes, frozen_healthy_spec

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
        default=ROOT / "results" / "f6-retest" / "healthy_restore_manifest.json",
    )
    parser.add_argument(
        "--out",
        type=Path,
        default=ROOT / "results" / "f6-retest" / "f6_isolation_manifest.json",
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
    expected_model = os.getenv("SFB_F6_MODEL", frozen["model_repo"])
    expected_rev = os.getenv("SFB_F6_MODEL_REVISION", frozen["model_revision"])
    expected_lora_module = os.getenv("SFB_F6_LORA_MODULE", "stale-tool-lora")
    expected_lora_repo = os.getenv("SFB_F6_LORA_REPO", "arvindcr4/tool-call-lora-qwen2.5-7b")

    key = Path(expand(os.getenv("SFB_RUNPOD_KEY", "~/.ssh/sfb_runpod")))
    host = os.getenv("SFB_RUNPOD_TCP_HOST", "")
    port = int(os.getenv("SFB_RUNPOD_TCP_PORT", "22"))
    workdir = os.getenv("SFB_POD_WORKDIR", "/workspace/semafailbench")
    base_url = os.getenv("SFB_BASE_URL", "http://127.0.0.1:8000/v1")

    api = check_api(base_url)
    pins_f6 = read_remote_json(key, host, port, f"{workdir}/pins_f6.json")

    healthy_probe = healthy_manifest.get("tokenizer_probe") or {}
    f6_tok_dir = pins_f6.get("tokenizer_local_path") or pins_f6.get("model_local_path")
    if not f6_tok_dir:
        print("pins_f6.json missing tokenizer_local_path", file=sys.stderr)
        return 2

    f6_probe = probe_remote_dir(key, host, port, workdir, f6_tok_dir)
    if healthy_probe.get("tokenizer_dir") != f6_probe.get("tokenizer_dir"):
        healthy_probe = probe_remote_dir(key, host, port, workdir, f6_tok_dir)

    artifact_cmp = compare_probes(healthy_probe, f6_probe)
    tokenize_cmp = compare_tokenize_probes(
        healthy_probe.get("tokenize_probe") or {},
        f6_probe.get("tokenize_probe") or {},
    )

    gpu_snap = snapshot_gpu(key, host, port) or {}
    vllm_proc = gpu_snap.get("vllm_process") or pins_f6.get("vllm_command") or ""
    weights_unchanged = expected_model in vllm_proc
    if expected_rev and expected_rev[:8] not in vllm_proc:
        weights_unchanged = weights_unchanged and pins_f6.get("model_repo") == expected_model

    dtype_same = "bfloat16" in vllm_proc or "--dtype bfloat16" in vllm_proc
    lora_enabled = "--enable-lora" in vllm_proc
    lora_module_served = expected_lora_module in vllm_proc
    lora_repo_loaded = expected_lora_repo.split("/")[-1] in vllm_proc or expected_lora_repo in vllm_proc
    lora_adapter_differs_from_healthy = lora_enabled and lora_module_served
    generation_same = "--override-generation-config" not in vllm_proc
    chat_template_same = artifact_cmp["chat_template_identical"]
    no_custom_template = "--chat-template" not in vllm_proc
    lora_in_models = expected_lora_module in (api.get("model_ids") or [])

    isolated = (
        weights_unchanged
        and artifact_cmp["tokenizer_files_identical"]
        and chat_template_same
        and tokenize_cmp["token_ids_equal"]
        and no_custom_template
        and generation_same
        and dtype_same
        and lora_adapter_differs_from_healthy
        and lora_repo_loaded
        and lora_in_models
        and api.get("ok")
    )

    manifest = {
        "fault": "F6",
        "deployment_kind": pins_f6.get("deployment_kind", "lora_adapter_mismatch_isolated"),
        "timestamp_utc": datetime.now(timezone.utc).isoformat(),
        "expected_model": expected_model,
        "expected_model_revision": expected_rev,
        "expected_lora_module": expected_lora_module,
        "expected_lora_repo": expected_lora_repo,
        "weights_unchanged": weights_unchanged,
        "tokenizer_files_same_as_healthy": artifact_cmp["tokenizer_files_identical"],
        "chat_template_same_as_healthy": chat_template_same,
        "token_ids_same_as_healthy": tokenize_cmp["token_ids_equal"],
        "generation_config_same_as_healthy": generation_same,
        "dtype_same_as_healthy": dtype_same,
        "lora_enabled": lora_enabled,
        "lora_module_served": lora_module_served,
        "lora_adapter_differs_from_healthy": lora_adapter_differs_from_healthy,
        "lora_module_in_api_models": lora_in_models,
        "lora_adapter_repo": pins_f6.get("lora_adapter_repo"),
        "lora_adapter_config_hash": pins_f6.get("lora_adapter_config_hash"),
        "healthy_lora": "none",
        "vllm_command": vllm_proc,
        "artifact_comparison": artifact_cmp,
        "tokenize_comparison": tokenize_cmp,
        "api_check": api,
        "isolated": isolated,
        "notes": (
            "F6 isolated: matched base weights+tokenizer+template+generation; only wrong LoRA adapter differs."
            if isolated
            else "F6 CONFOUNDED — check weights, tokenizer, chat template, generation override, or LoRA mount."
        ),
    }

    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    print(json.dumps(manifest, indent=2))
    if not isolated:
        print("F6 CANDIDATE REJECTED: CONFOUNDED WITH F2/F3/F4/F5", file=sys.stderr)
        return 1
    print(f"Wrote {args.out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
