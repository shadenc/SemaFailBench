#!/usr/bin/env python3
"""Run 10 stochastic healthy passes (seeds 0–9) with per-run infra snapshots."""

from __future__ import annotations

import argparse
import importlib.util
import json
import os
import shutil
import statistics
import sys
import time
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from sem_fail_bench.catalog import load_serving_config  # noqa: E402
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


def render_markdown(campaign: dict[str, Any]) -> str:
    runs = campaign["runs"]
    lines = [
        "# Healthy stochastic — 120 core × 10 passes (seeds 0–9)",
        "",
        f"**Campaign id:** `{campaign['campaign_id']}`",
        f"**Pod:** `{campaign.get('pod_id', '?')}` · live vLLM inference",
        f"**Regime:** stochastic (`temperature={campaign['temperature']}`, `top_p={campaign['top_p']}`)",
        f"**Scorer contract:** `{campaign.get('scorer_contract', 'calibrated-2026-08-10')}`",
        "",
        f"**Raw scores:** `{campaign['results_dir']}`",
        "",
        "## Protocol",
        "",
        "- 120 core canaries (SFC-001 … SFC-120), catalog order",
        "- 10 runs with seeds 0 … 9 (one seed per run)",
        "- Run 1: 5 warmup requests discarded, then 120 measured",
        "- Runs 2–10: 120 measured each (no warmup)",
        "- API health check before each run; GPU sampled every 2s during inference",
        "",
        "## Campaign summary",
        "",
        "| | |",
        "|---|---|",
        f"| Runs completed | {campaign['n_completed']} / {campaign['n_planned']} |",
        f"| All HTTP 200 | {campaign['all_http_200']} |",
        f"| Strict pass rate (mean) | **{campaign['strict_pass_rate_mean']:.1%}** |",
        f"| Strict pass rate (min–max) | {campaign['strict_pass_rate_min']:.1%} – {campaign['strict_pass_rate_max']:.1%} |",
        f"| Tolerant pass rate (mean) | {campaign['tolerant_pass_rate_mean']:.1%} |",
        f"| Canaries with varying strict outcome | {len(campaign.get('flaky_canaries') or [])} |",
        "",
        "### Per-run pass rates",
        "",
        "| Run | Seed | Run id | Strict | Tolerant | HTTP | Wall s | p50 ms | p95 ms | GPU samples | GPU util max % | Temp max °C | Power max W |",
        "|---|---:|---|---|---|---|---:|---:|---:|---:|---:|---:|---:|",
    ]
    for r in runs:
        during = (r.get("infra_during") or {}).get("gpu_sampler") or {}
        lat = r.get("latency") or {}
        lines.append(
            f"| {r['run_index']:02d} | {r['seed']} | `{r['run_id']}` | {r['strict_pass_rate']:.1%} | "
            f"{r['tolerant_pass_rate']:.1%} | {r['http_200']}/{r['n']} | {r['wall_s']:.0f} | "
            f"{lat.get('p50_ms', 0):.0f} | {lat.get('p95_ms', 0):.0f} | "
            f"{during.get('n_samples', 0)} | {during.get('util_gpu_pct_max', '—')} | "
            f"{during.get('temperature_c_max', '—')} | {during.get('power_w_max', '—')} |"
        )
    env = campaign.get("gpu_envelope") or {}
    lines.extend(
        [
            "",
            "### GPU infra envelope (during-run peak samples)",
            "",
            "| Metric | min | mean | max |",
            "|---|---:|---:|---:|",
        ]
    )
    for key, label in [
        ("util_gpu_pct_max", "GPU util max %"),
        ("temperature_c_max", "Temperature max °C"),
        ("power_w_max", "Power max W"),
    ]:
        band = env.get(key) or {}
        lines.append(f"| {label} | {band.get('min', '—')} | {band.get('mean', '—')} | {band.get('max', '—')} |")
    flaky = campaign.get("flaky_canaries") or []
    lines.extend(["", "## Canaries with varying strict outcomes across seeds", ""])
    if flaky:
        lines.append("| ID | strict pass count / 10 |")
        lines.append("|---|---:|")
        for cid, cnt in flaky:
            lines.append(f"| {cid} | {cnt}/10 |")
    else:
        lines.append("_None — all canaries had identical strict outcomes across seeds._")
    lines.extend(["", "## Per-run details", ""])
    for r in runs:
        lines.extend(
            [
                f"### Run {r['run_index']:02d} seed={r['seed']} — `{r['run_id']}`",
                "",
                "| | |",
                "|---|---|",
                f"| Strict | **{r['strict_pass_rate']:.1%}** ({r['strict_pass_n']}/{r['n']}) |",
                f"| Tolerant | {r['tolerant_pass_rate']:.1%} ({r['tolerant_pass_n']}/{r['n']}) |",
                f"| HTTP 200 | {r['http_200']}/{r['n']} |",
                f"| Wall time | {r['wall_s']:.1f} s |",
                "",
            ]
        )
        during = (r.get("infra_during") or {}).get("gpu_sampler") or {}
        if during.get("ok"):
            lines.append(
                f"**GPU during run:** {during.get('n_samples')} samples · util max {during.get('util_gpu_pct_max')}% · "
                f"power max {during.get('power_w_max')} W"
            )
            lines.append("")
        fails = r.get("strict_failures") or []
        if fails:
            lines.append(f"**Strict failures ({len(fails)}):**")
            lines.append("")
            lines.append("| ID | Subtype | Note |")
            lines.append("|---|---|---|")
            for f in fails:
                note = str(f.get("note", "")).replace("|", "/")[:80]
                lines.append(f"| {f['canary_id']} | {f['subtype']} | {note} |")
            lines.append("")
    lines.append("")
    return "\n".join(lines)


def finalize_campaign(out_dir: Path, repeats: int, pod_id: str, campaign_meta: dict[str, Any]) -> dict[str, Any]:
    runs = [json.loads((out_dir / f"run_{i:02d}_manifest.json").read_text(encoding="utf-8")) for i in range(1, repeats + 1)]
    strict_rates = [float(r["strict_pass_rate"]) for r in runs]
    tolerant_rates = [float(r["tolerant_pass_rate"]) for r in runs]
    gpu_samples = [
        g
        for g in ((r.get("infra_during") or {}).get("gpu_sampler") for r in runs)
        if g and g.get("ok")
    ]

    canary_pass_counts: dict[str, int] = defaultdict(int)
    for run_entry in runs:
        path = REPO_ROOT / run_entry["artifacts"]["results_jsonl"]
        for line in path.read_text(encoding="utf-8").splitlines():
            if not line.strip():
                continue
            row = json.loads(line)
            if row.get("strict_pass"):
                canary_pass_counts[row["canary_id"]] += 1

    def gpu_band(key: str) -> dict[str, float]:
        vals = [g[key] for g in gpu_samples if key in g]
        return {"min": min(vals), "mean": statistics.mean(vals), "max": max(vals)} if vals else {}

    n = len(runs)
    flaky = [(cid, cnt) for cid, cnt in sorted(canary_pass_counts.items()) if 0 < cnt < n]
    flaky.sort(key=lambda x: (-(min(x[1], n - x[1])), x[0]))

    campaign = {
        **campaign_meta,
        "n_completed": n,
        "runs": runs,
        "all_http_200": all(r["http_200"] == r["n"] for r in runs),
        "strict_pass_rate_mean": statistics.mean(strict_rates),
        "strict_pass_rate_min": min(strict_rates),
        "strict_pass_rate_max": max(strict_rates),
        "tolerant_pass_rate_mean": statistics.mean(tolerant_rates),
        "gpu_envelope": {
            "util_gpu_pct_max": gpu_band("util_gpu_pct_max"),
            "temperature_c_max": gpu_band("temperature_c_max"),
            "power_w_max": gpu_band("power_w_max"),
        },
        "flaky_canaries": flaky,
    }
    (out_dir / "campaign_manifest.json").write_text(json.dumps(campaign, indent=2), encoding="utf-8")
    md_path = REPO_ROOT / "docs" / "HEALTHY_STOCHASTIC_120x10.md"
    md_path.write_text(render_markdown(campaign), encoding="utf-8")
    (out_dir / "README.md").write_text(
        f"# Healthy stochastic 120×10\n\nCampaign `{campaign['campaign_id']}`\n\nSee `docs/HEALTHY_STOCHASTIC_120x10.md`\n",
        encoding="utf-8",
    )
    return campaign


def main() -> int:
    parser = argparse.ArgumentParser(description="Healthy stochastic campaign (seeds 0–9)")
    parser.add_argument("--repeats", type=int, default=10)
    parser.add_argument("--limit", type=int, default=120)
    parser.add_argument("--split", default="core")
    parser.add_argument("--out-dir", type=Path, default=REPO_ROOT / "results" / "healthy-stochastic-120x10")
    parser.add_argument("--start-run", type=int, default=1)
    args = parser.parse_args()

    args.out_dir = (REPO_ROOT / args.out_dir).resolve() if not args.out_dir.is_absolute() else args.out_dir.resolve()
    args.out_dir.mkdir(parents=True, exist_ok=True)

    serving = load_serving_config()
    stochastic = serving.get("generation", {}).get("stochastic", {})
    temperature = float(stochastic.get("temperature", 0.7))
    top_p = float(stochastic.get("top_p", 0.9))
    seeds = list(stochastic.get("seeds", list(range(10))))[: args.repeats]

    base_url = os.getenv("SFB_BASE_URL", "http://127.0.0.1:8000/v1")
    ssh_key = expand(os.getenv("SFB_RUNPOD_KEY", "~/.ssh/sfb_runpod"))
    tcp_host = os.getenv("SFB_RUNPOD_TCP_HOST", "")
    tcp_port = int(os.getenv("SFB_RUNPOD_TCP_PORT", "22"))
    pod_id = (os.getenv("SFB_RUNPOD_SSH") or "").split("@")[0].split("-")[0]

    if not check_api(base_url).get("ok"):
        print("API not reachable", file=sys.stderr)
        return 2

    campaign_id = f"stochastic-{datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ')}"
    campaign_meta = {
        "campaign_id": campaign_id,
        "pod_id": pod_id,
        "regime": "stochastic",
        "temperature": temperature,
        "top_p": top_p,
        "seeds": seeds,
        "scorer_contract": "calibrated-2026-08-10",
        "results_dir": str(args.out_dir.relative_to(REPO_ROOT)),
        "n_planned": args.repeats,
    }

    client = ServingClient(timeout=180.0)
    sampler = GpuSampler(ssh_key, tcp_host, tcp_port, interval_s=2.0) if tcp_host else None
    completed = 0

    for i in range(args.start_run, args.repeats + 1):
        seed = seeds[i - 1]
        print(f"\n=== RUN {i}/{args.repeats} seed={seed} ===", flush=True)
        if not check_api(base_url).get("ok"):
            print("API down; aborting.", file=sys.stderr)
            break

        if sampler:
            sampler.start()
        t0 = time.perf_counter()
        try:
            summary = run_suite(
                condition="healthy",
                temperature=temperature,
                seed=seed,
                shuffle=False,
                limit=args.limit,
                split=args.split,
                warmup=(i == 1),
                client=client,
            )
        except Exception as exc:  # noqa: BLE001
            if sampler:
                sampler.stop()
            print(f"  failed ({exc}); retrying once...", flush=True)
            time.sleep(5)
            if sampler:
                sampler.start()
            summary = run_suite(
                condition="healthy",
                temperature=temperature,
                seed=seed,
                shuffle=False,
                limit=args.limit,
                split=args.split,
                warmup=False,
                client=client,
            )
        wall_s = time.perf_counter() - t0
        during_summary = sampler.stop() if sampler else {"ok": False}
        jsonl_path = write_run(summary)
        meta_src = jsonl_path.with_suffix(".meta.json")
        records = summary["records"]

        run_entry = {
            "run_index": i,
            "seed": seed,
            "run_id": summary["run_id"],
            "strict_pass_rate": summary["strict_pass_rate"],
            "tolerant_pass_rate": summary["tolerant_pass_rate"],
            "strict_pass_n": sum(1 for r in records if r.get("strict_pass")),
            "tolerant_pass_n": sum(1 for r in records if r.get("tolerant_pass")),
            "n": len(records),
            "http_200": sum(1 for r in records if r.get("http_status") == 200),
            "wall_s": wall_s,
            "warmup": i == 1,
            "latency": latency_stats(records),
            "capability_breakdown": capability_breakdown(records),
            "strict_failures": strict_failures(records),
            "infra_before": {"api": check_api(base_url)},
            "infra_during": {"gpu_sampler": during_summary},
            "infra_after": {
                "gpu": snapshot_gpu(ssh_key, tcp_host, tcp_port) if tcp_host else {"ok": False},
                "vllm_metrics": parse_vllm_metrics(base_url),
            },
            "artifacts": {},
        }

        dest_jsonl = args.out_dir / f"run_{i:02d}_seed{seed}_{summary['run_id']}.jsonl"
        dest_meta = args.out_dir / f"run_{i:02d}_seed{seed}_{summary['run_id']}.meta.json"
        shutil.copy2(jsonl_path, dest_jsonl)
        shutil.copy2(meta_src, dest_meta)
        run_entry["artifacts"] = {
            "jsonl": str(jsonl_path.relative_to(REPO_ROOT)),
            "meta": str(meta_src.relative_to(REPO_ROOT)),
            "results_jsonl": str(dest_jsonl.relative_to(REPO_ROOT)),
            "results_meta": str(dest_meta.relative_to(REPO_ROOT)),
        }
        (args.out_dir / f"run_{i:02d}_manifest.json").write_text(json.dumps(run_entry, indent=2), encoding="utf-8")
        completed = i
        print(
            f"  strict={summary['strict_pass_rate']:.1%} http={run_entry['http_200']}/{run_entry['n']} "
            f"wall={wall_s:.0f}s gpu_util_max={during_summary.get('util_gpu_pct_max', '—')}",
            flush=True,
        )

    if completed == 0:
        return 2
    finalize_campaign(args.out_dir, completed, pod_id, campaign_meta)
    print(f"\nWrote {args.out_dir / 'campaign_manifest.json'}")
    print(f"Wrote {REPO_ROOT / 'docs/HEALTHY_STOCHASTIC_120x10.md'}")
    return 0 if completed == args.repeats else 1


if __name__ == "__main__":
    raise SystemExit(main())
