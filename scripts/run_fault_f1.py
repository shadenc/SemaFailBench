#!/usr/bin/env python3
"""Run 120 core canaries under F1 (quantization regression) with infra snapshots."""

from __future__ import annotations

import argparse
import importlib.util
import json
import os
import shutil
import sys
import time
import yaml
from datetime import datetime, timezone
from pathlib import Path

from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from sem_fail_bench.client import ServingClient  # noqa: E402
from sem_fail_bench.paths import REPO_ROOT  # noqa: E402
from sem_fail_bench.runner import run_suite, write_run  # noqa: E402

load_dotenv(REPO_ROOT / ".env", override=True)

_spec = importlib.util.spec_from_file_location(
    "run_healthy_stability", ROOT / "scripts" / "run_healthy_stability.py"
)
_rhs = importlib.util.module_from_spec(_spec)
assert _spec.loader is not None
_spec.loader.exec_module(_rhs)

check_api = _rhs.check_api
snapshot_gpu = _rhs.snapshot_gpu
parse_vllm_metrics = _rhs.parse_vllm_metrics
GpuSampler = _rhs.GpuSampler
latency_stats = _rhs.latency_stats
capability_breakdown = _rhs.capability_breakdown
strict_failures = _rhs.strict_failures
expand = _rhs.expand


def load_f1_config() -> dict:
    path = REPO_ROOT / "configs" / "serving_f1.yaml"
    return yaml.safe_load(path.read_text(encoding="utf-8"))


def load_healthy_baseline_summary() -> dict | None:
    manifest = REPO_ROOT / "results" / "healthy-stability-120x20-v2" / "campaign_manifest.json"
    if not manifest.exists():
        return None
    return json.loads(manifest.read_text(encoding="utf-8"))


def render_markdown(run: dict, f1_cfg: dict, healthy: dict | None) -> str:
    lines = [
        "# F1 — Quantization regression · 120 core pass",
        "",
        f"**Run id:** `{run['run_id']}`",
        f"**Fault:** F1 — {f1_cfg.get('fault_name', 'Quantization regression')}",
        f"**Model:** `{run['model']}` (`{run.get('quantization', 'awq')}`)",
        f"**Healthy reference:** `{f1_cfg['healthy_reference']['repo']}` @ `{f1_cfg['healthy_reference']['revision'][:12]}…`",
        "",
        f"**Raw scores:** `{run['artifacts']['results_jsonl'].rsplit('/', 1)[0]}`",
        "",
        "## Protocol",
        "",
        "- Stop healthy bf16 vLLM; start `Qwen/Qwen2.5-7B-Instruct-AWQ` with `--quantization awq`",
        "- 120 core canaries, catalog order, temp=0, 5 warmup then 120 measured",
        "- Compare pass rates vs healthy stability v2 baseline (92.5% strict)",
        "",
        "## Results",
        "",
        "| | |",
        "|---|---|",
        f"| Strict | **{run['strict_pass_rate']:.1%}** ({run['strict_pass_n']}/{run['n']}) |",
        f"| Tolerant | {run['tolerant_pass_rate']:.1%} ({run['tolerant_pass_n']}/{run['n']}) |",
        f"| HTTP 200 | {run['http_200']}/{run['n']} |",
        f"| Wall time | {run['wall_s']:.1f} s |",
    ]
    if healthy:
        h_strict = healthy.get("strict_pass_rate_mean", 0)
        delta = run["strict_pass_rate"] - h_strict
        lines.extend(
            [
                f"| Healthy baseline (v2 mean) | {h_strict:.1%} |",
                f"| Delta vs healthy | {delta:+.1%} |",
            ]
        )
    during = (run.get("infra_during") or {}).get("gpu_sampler") or {}
    if during.get("ok"):
        lines.extend(
            [
                "",
                "**GPU during run:**",
                f"- util max {during.get('util_gpu_pct_max')}% · mem last {during.get('memory_used_mib_last')} MiB",
                f"- temp max {during.get('temperature_c_max')}°C · power max {during.get('power_w_max')} W",
            ]
        )
    caps = run.get("capability_breakdown") or {}
    if caps:
        lines.extend(["", "**By capability (strict):**"])
        for cap, val in caps.items():
            short = cap.split(":")[0].replace("Capability ", "Cap ")
            lines.append(f"- {short}: {val}")
    fails = run.get("strict_failures") or []
    if fails:
        lines.extend(["", f"**Strict failures ({len(fails)}):**", ""])
        lines.append("| ID | Subtype | Note |")
        lines.append("|---|---|---|")
        for f in fails:
            note = str(f.get("note", "")).replace("|", "/")[:80]
            lines.append(f"| {f['canary_id']} | {f['subtype']} | {note} |")
    lines.append("")
    return "\n".join(lines)


def main() -> int:
    parser = argparse.ArgumentParser(description="F1 fault run — 120 core canaries")
    parser.add_argument("--limit", type=int, default=120)
    parser.add_argument("--split", default="core")
    parser.add_argument("--out-dir", type=Path, default=REPO_ROOT / "results" / "fault-f1-quantization-120")
    args = parser.parse_args()

    f1_cfg = load_f1_config()
    model = os.getenv("SFB_F1_MODEL", f1_cfg["model"]["repo"])
    quant = os.getenv("SFB_F1_QUANTIZATION", f1_cfg["model"]["quantization"])
    os.environ["SFB_MODEL"] = model

    args.out_dir = (REPO_ROOT / args.out_dir).resolve() if not args.out_dir.is_absolute() else args.out_dir.resolve()
    args.out_dir.mkdir(parents=True, exist_ok=True)

    base_url = os.getenv("SFB_BASE_URL", "http://127.0.0.1:8000/v1")
    if not check_api(base_url).get("ok"):
        print("API not reachable. Start tunnel and ensure F1 vLLM is running.", file=sys.stderr)
        return 2

    ssh_key = expand(os.getenv("SFB_RUNPOD_KEY", "~/.ssh/sfb_runpod"))
    tcp_host = os.getenv("SFB_RUNPOD_TCP_HOST", "")
    tcp_port = int(os.getenv("SFB_RUNPOD_TCP_PORT", "22"))
    sampler = GpuSampler(ssh_key, tcp_host, tcp_port) if tcp_host else None

    client = ServingClient(timeout=180.0)
    if sampler:
        sampler.start()
    t0 = time.perf_counter()
    summary = run_suite(
        condition="F1-quantization",
        temperature=0.0,
        seed=0,
        shuffle=False,
        limit=args.limit,
        split=args.split,
        warmup=True,
        client=client,
    )
    wall_s = time.perf_counter() - t0
    during = sampler.stop() if sampler else {"ok": False}

    jsonl_path = write_run(summary)
    meta_src = jsonl_path.with_suffix(".meta.json")
    records = summary["records"]

    run_entry = {
        "fault_id": "F1",
        "run_id": summary["run_id"],
        "model": model,
        "quantization": quant,
        "strict_pass_rate": summary["strict_pass_rate"],
        "tolerant_pass_rate": summary["tolerant_pass_rate"],
        "strict_pass_n": sum(1 for r in records if r.get("strict_pass")),
        "tolerant_pass_n": sum(1 for r in records if r.get("tolerant_pass")),
        "n": len(records),
        "http_200": sum(1 for r in records if r.get("http_status") == 200),
        "wall_s": wall_s,
        "latency": latency_stats(records),
        "capability_breakdown": capability_breakdown(records),
        "strict_failures": strict_failures(records),
        "infra_before": {"api": check_api(base_url)},
        "infra_during": {"gpu_sampler": during},
        "infra_after": {
            "gpu": snapshot_gpu(ssh_key, tcp_host, tcp_port) if tcp_host else {"ok": False},
            "vllm_metrics": parse_vllm_metrics(base_url),
        },
        "artifacts": {},
    }

    dest_jsonl = args.out_dir / f"f1_{summary['run_id']}.jsonl"
    dest_meta = args.out_dir / f"f1_{summary['run_id']}.meta.json"
    shutil.copy2(jsonl_path, dest_jsonl)
    shutil.copy2(meta_src, dest_meta)
    run_entry["artifacts"] = {
        "jsonl": str(jsonl_path.relative_to(REPO_ROOT)),
        "meta": str(meta_src.relative_to(REPO_ROOT)),
        "results_jsonl": str(dest_jsonl.relative_to(REPO_ROOT)),
        "results_meta": str(dest_meta.relative_to(REPO_ROOT)),
    }
    (args.out_dir / "run_manifest.json").write_text(json.dumps(run_entry, indent=2), encoding="utf-8")

    healthy = load_healthy_baseline_summary()
    md = render_markdown(run_entry, f1_cfg, healthy)
    md_path = REPO_ROOT / "docs" / "F1_QUANTIZATION_120.md"
    md_path.write_text(md, encoding="utf-8")

    print(f"strict={summary['strict_pass_rate']:.1%} http={run_entry['http_200']}/{run_entry['n']} wall={wall_s:.0f}s")
    print(f"Wrote {args.out_dir / 'run_manifest.json'}")
    print(f"Wrote {md_path}")
    return 0 if run_entry["http_200"] == run_entry["n"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
