#!/usr/bin/env python3
"""Verify pod is on frozen healthy config; write healthy_restore_manifest.json."""

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

from serving_artifact_probe import frozen_healthy_spec, probe_tokenizer_dir, tokenize_probe  # noqa: E402

load_dotenv(ROOT / ".env", override=True)

_spec = importlib.util.spec_from_file_location(
    "run_healthy_stability", ROOT / "scripts" / "run_healthy_stability.py"
)
_rhs = importlib.util.module_from_spec(_spec)
assert _spec.loader is not None
_spec.loader.exec_module(_rhs)
check_api = _rhs.check_api
snapshot_gpu = _rhs.snapshot_gpu
parse_vllm_metrics = _rhs.parse_vllm_metrics
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
    raw = ssh_cmd(key, host, port, f"python3 -c \"import json; print(json.dumps(json.load(open('{path}'))))\"")
    return json.loads(raw)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--out",
        type=Path,
        default=ROOT / "results" / "f2-retest" / "healthy_restore_manifest.json",
    )
    args = parser.parse_args()

    frozen = frozen_healthy_spec()
    base_url = os.getenv("SFB_BASE_URL", "http://127.0.0.1:8000/v1")
    key = Path(expand(os.getenv("SFB_RUNPOD_KEY", "~/.ssh/sfb_runpod")))
    host = os.getenv("SFB_RUNPOD_TCP_HOST", "")
    port = int(os.getenv("SFB_RUNPOD_TCP_PORT", "22"))
    workdir = os.getenv("SFB_POD_WORKDIR", "/workspace/semafailbench")

    api = check_api(base_url)
    manifest: dict = {
        "phase": "healthy_restore_verification",
        "timestamp_utc": datetime.now(timezone.utc).isoformat(),
        "frozen_spec": frozen,
        "api": api,
        "matches_frozen": False,
        "verified": False,
    }

    if not api.get("ok"):
        manifest["error"] = "API not reachable — start tunnel + healthy vLLM"
        args.out.parent.mkdir(parents=True, exist_ok=True)
        args.out.write_text(json.dumps(manifest, indent=2), encoding="utf-8")
        print(json.dumps(manifest, indent=2))
        return 2

    if host:
        manifest["infra"] = {
            "gpu": snapshot_gpu(key, host, port),
            "vllm_metrics": parse_vllm_metrics(base_url),
        }
        try:
            pins = read_remote_json(key, host, port, f"{workdir}/pins.json")
            manifest["pins"] = pins
            tok_dir = pins.get("tokenizer_local_path") or pins.get("model_local_path")
            if tok_dir:
                remote_probe = ssh_cmd(
                    key,
                    host,
                    port,
                    f"python3 {workdir}/serving_artifact_probe.py {tok_dir} --tokenize-probe",
                )
                manifest["tokenizer_probe"] = json.loads(remote_probe)
        except Exception as exc:  # noqa: BLE001
            manifest["pins_error"] = str(exc)

    model_ids = api.get("model_ids") or []
    checks = {
        "api_http_200": api.get("ok") is True,
        "model_id_expected": frozen["model_repo"] in model_ids,
        "model_revision": (manifest.get("pins") or {}).get("model_revision"),
        "revision_matches_frozen": (manifest.get("pins") or {}).get("model_revision") == frozen["model_revision"],
    }
    manifest["checks"] = checks

    vllm_proc = ((manifest.get("infra") or {}).get("gpu") or {}).get("vllm_process") or ""
    manifest["serving"] = {
        "model_repo": frozen["model_repo"],
        "model_revision": frozen["model_revision"],
        "tokenizer_repo": frozen["tokenizer_repo"],
        "tokenizer_revision": frozen["tokenizer_revision"],
        "dtype": frozen["dtype"],
        "quantization": frozen["quantization"],
        "lora": frozen["lora"],
        "max_model_len": int(frozen["max_model_len"]),
        "gpu_memory_utilization": float(frozen["gpu_memory_utilization"]),
        "vllm_version": (manifest.get("pins") or {}).get("vllm_version"),
        "gpu": (manifest.get("infra") or {}).get("gpu", {}).get("gpu", {}).get("name"),
        "vllm_command": vllm_proc,
    }

    tp = (manifest.get("tokenizer_probe") or {}).get("tokenize_probe") or {}
    manifest["chat_template_hash"] = (manifest.get("tokenizer_probe") or {}).get("chat_template", {}).get("hash")
    manifest["tokenizer_bundle_hash"] = (manifest.get("tokenizer_probe") or {}).get("bundle_hash")

    matches = all(
        [
            checks["api_http_200"],
            checks["model_id_expected"],
            checks["revision_matches_frozen"],
            frozen["model_repo"] in vllm_proc or not vllm_proc,
            "--quantization" not in vllm_proc,
            "--chat-template" not in vllm_proc,
            "--override-generation-config" not in vllm_proc,
            "--enable-lora" not in vllm_proc,
            "--lora-modules" not in vllm_proc,
        ]
    )
    manifest["matches_frozen"] = matches
    manifest["verified"] = matches

    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    print(f"Wrote {args.out}")
    print(f"verified={manifest['verified']} matches_frozen={manifest['matches_frozen']}")
    return 0 if manifest["verified"] else 3


if __name__ == "__main__":
    raise SystemExit(main())
