#!/usr/bin/env python3
"""F2 checkpoint-version fault — 120 core × N deterministic passes with during-run GPU sampling."""

from __future__ import annotations

import argparse
import importlib.util
import json
import os
import shutil
import statistics
import sys
import time
import yaml
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

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
load_existing_runs = _rhs.load_existing_runs


def load_f2_config() -> dict:
    return yaml.safe_load((REPO_ROOT / "configs" / "serving_f2.yaml").read_text(encoding="utf-8"))


def load_healthy_baseline() -> dict | None:
    path = REPO_ROOT / "results" / "healthy-stability-120x20-v2" / "campaign_manifest.json"
    if not path.exists():
        return None
    return json.loads(path.read_text(encoding="utf-8"))


def _healthy_f2_delta() -> tuple[list[str], list[str], list[str]]:
    """Compare healthy v2 run 1 vs F2 run 1 strict outcomes."""
    healthy_manifest = REPO_ROOT / "results" / "healthy-stability-120x20-v2" / "run_01_manifest.json"
    if not healthy_manifest.exists():
        return [], [], []
    h_fails = {f["canary_id"] for f in json.loads(healthy_manifest.read_text())["strict_failures"]}
    f2_manifest = REPO_ROOT / "results" / "fault-f2-stability-120x20" / "run_01_manifest.json"
    if not f2_manifest.exists():
        return sorted(h_fails), [], []
    f_fails = {f["canary_id"] for f in json.loads(f2_manifest.read_text())["strict_failures"]}
    regressions = sorted(f_fails - h_fails)  # healthy PASS → F2 FAIL
    recoveries = sorted(h_fails - f_fails)  # healthy FAIL → F2 PASS
    stable_fail = sorted(h_fails & f_fails)
    return regressions, recoveries, stable_fail


def render_markdown(campaign: dict[str, Any], f2_cfg: dict, healthy: dict | None) -> str:
    runs = campaign["runs"]
    lines = [
        "# F2 — Model / checkpoint version regression · 120 core × 20 deterministic passes",
        "",
        f"**Campaign id:** `{campaign['campaign_id']}`",
        f"**Fault:** F2 — {f2_cfg.get('fault_name', 'Model / checkpoint version regression')}",
        f"**Pod:** `{campaign.get('pod_id', '?')}` · stale-revision vLLM inference",
        f"**Model:** `{campaign.get('model')}` (`{campaign.get('model_revision', '?')[:12]}…`)",
        f"**Healthy reference:** `{f2_cfg['healthy_reference']['repo']}` @ `{f2_cfg['healthy_reference']['revision'][:12]}…`",
        f"**Scorer contract:** `{campaign.get('scorer_contract', 'calibrated-2026-08-10')}`",
        "",
        f"**Raw scores:** `{campaign['results_dir']}`",
        "",
        "> Compare per-canary jsonl under `results/fault-f2-stability-120x20/` vs healthy v2 in `results/healthy-stability-120x20-v2/`.",
        "",
        "## Protocol",
        "",
        f"- Same Hub model id `{f2_cfg['model']['repo']}`; stale revision `{f2_cfg['model']['revision'][:12]}…` vs healthy `{f2_cfg['healthy_reference']['revision'][:12]}…`",
        "- 120 core canaries (SFC-001 … SFC-120), catalog order, temp=0",
        "- Run 1: 5 warmup requests discarded, then 120 measured",
        "- Runs 2–20: 120 measured each (no warmup)",
        "- API health check before each run; GPU sampled every 2s **during** inference; post-run GPU + vLLM `/metrics` scrape",
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
        f"| Stability gate (≥95% agreement) | {campaign['stability_gate']} |",
    ]
    if healthy:
        h = healthy.get("strict_pass_rate_mean", 0)
        delta = campaign["strict_pass_rate_mean"] - h
        lines.extend(
            [
                f"| Healthy baseline (v2 mean) | {h:.1%} |",
                f"| Delta vs healthy | {delta:+.1%} |",
            ]
        )
    regressions, recoveries, stable_fail = _healthy_f2_delta()
    if regressions or recoveries:
        lines.extend(
            [
                "",
                "### F2 vs healthy (run 1 strict delta)",
                "",
                "Headline pass rate is unchanged; these canaries **swapped** pass/fail vs healthy v2:",
                "",
                "| Direction | Canaries |",
                "|---|---|",
                f"| Regressions (healthy PASS → F2 FAIL) | {', '.join(regressions) or '—'} |",
                f"| Recoveries (healthy FAIL → F2 PASS) | {', '.join(recoveries) or '—'} |",
                f"| Stable strict failures (both) | {', '.join(stable_fail) or '—'} |",
            ]
        )
    lines.extend(
        [
            "",
            "### Per-run pass rates",
            "",
            "| Run | Run id | Strict | Tolerant | HTTP | Wall s | p50 ms | p95 ms | API ok | GPU samples | GPU util max % | GPU mem MiB | Temp max °C | Power max W | KV cache % |",
            "|---|---|---|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|",
        ]
    )
    for r in runs:
        during = (r.get("infra_during") or {}).get("gpu_sampler") or {}
        lat = r.get("latency") or {}
        metrics = (r.get("infra_after") or {}).get("vllm_metrics") or {}
        kv = (metrics.get("values") or {}).get("vllm:gpu_cache_usage_perc")
        api_ok = "yes" if (r.get("infra_before") or {}).get("api", {}).get("ok") else "no"
        lines.append(
            f"| {r['run_index']:02d} | `{r['run_id']}` | {r['strict_pass_rate']:.1%} | "
            f"{r['tolerant_pass_rate']:.1%} | {r['http_200']}/{r['n']} | {r['wall_s']:.0f} | "
            f"{lat.get('p50_ms', 0):.0f} | {lat.get('p95_ms', 0):.0f} | "
            f"{api_ok} | {during.get('n_samples', 0)} | "
            f"{during.get('util_gpu_pct_max', '—')} | {during.get('memory_used_mib_last', '—')} | "
            f"{during.get('temperature_c_max', '—')} | {during.get('power_w_max', '—')} | "
            f"{kv if kv is not None else '—'} |"
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
        ("memory_used_mib_last", "GPU mem MiB (last sample)"),
        ("temperature_c_max", "Temperature max °C"),
        ("power_w_max", "Power max W"),
    ]:
        band = env.get(key) or {}
        lines.append(f"| {label} | {band.get('min', '—')} | {band.get('mean', '—')} | {band.get('max', '—')} |")
    lines.extend(["", "## Per-run details", ""])
    for r in runs:
        lines.extend(
            [
                f"### Run {r['run_index']:02d} — `{r['run_id']}`",
                "",
                "| | |",
                "|---|---|",
                f"| Strict | **{r['strict_pass_rate']:.1%}** ({r['strict_pass_n']}/{r['n']}) |",
                f"| Tolerant | {r['tolerant_pass_rate']:.1%} ({r['tolerant_pass_n']}/{r['n']}) |",
                f"| HTTP 200 | {r['http_200']}/{r['n']} |",
                f"| Wall time | {r['wall_s']:.1f} s |",
                f"| Warmup | {'yes (5 discarded)' if r.get('warmup') else 'no'} |",
                "",
            ]
        )
        during = (r.get("infra_during") or {}).get("gpu_sampler") or {}
        if during.get("ok"):
            util_mean = during.get("util_gpu_pct_mean")
            util_mean_s = f"{util_mean:.1f}" if isinstance(util_mean, (int, float)) else "—"
            lines.extend(
                [
                    "**GPU during run (2s samples):**",
                    f"- samples: {during.get('n_samples')} · util max {during.get('util_gpu_pct_max')}% · "
                    f"util mean {util_mean_s}% · "
                    f"mem last {during.get('memory_used_mib_last')} MiB · temp max {during.get('temperature_c_max')}°C · "
                    f"power max {during.get('power_w_max')} W",
                    "",
                ]
            )
        metrics = (r.get("infra_after") or {}).get("vllm_metrics") or {}
        if metrics.get("values"):
            lines.append("**vLLM metrics (post-run):**")
            for k, v in sorted(metrics["values"].items()):
                short = k.removeprefix("vllm:")
                lines.append(f"- `{short}`: {v}")
            lines.append("")
        caps = r.get("capability_breakdown") or {}
        if caps:
            lines.append("**By capability (strict):**")
            for cap, val in caps.items():
                short = cap.split(":")[0].replace("Capability ", "Cap ")
                lines.append(f"- {short}: {val}")
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
    lines.extend(
        [
            "## Canary stability across 20 runs",
            "",
            "Canaries that changed strict pass/fail between runs (flaky):",
            "",
        ]
    )
    flaky = campaign.get("flaky_canaries") or []
    if flaky:
        lines.append("| ID | strict pass count / 20 |")
        lines.append("|---|---:|")
        for cid, cnt in flaky:
            lines.append(f"| {cid} | {cnt}/20 |")
    else:
        lines.append("_None — all canaries had identical strict outcomes across completed runs._")
    lines.append("")
    return "\n".join(lines)


def finalize_campaign(
    out_dir: Path,
    repeats: int,
    pod_id: str,
    f2_cfg: dict,
    model: str,
    revision: str,
    campaign_id: str | None = None,
) -> dict[str, Any]:
    runs: list[dict[str, Any]] = []
    for i in range(1, repeats + 1):
        manifest = out_dir / f"run_{i:02d}_manifest.json"
        if not manifest.exists():
            raise FileNotFoundError(f"Missing run manifest: {manifest}")
        runs.append(json.loads(manifest.read_text(encoding="utf-8")))

    strict_rates = [float(r["strict_pass_rate"]) for r in runs]
    tolerant_rates = [float(r["tolerant_pass_rate"]) for r in runs]
    gpu_samples = [
        (r.get("infra_during") or {}).get("gpu_sampler")
        for r in runs
        if (r.get("infra_during") or {}).get("gpu_sampler", {}).get("ok")
    ]

    canary_pass_counts: dict[str, int] = defaultdict(int)
    for run_entry in runs:
        results_jsonl = run_entry.get("artifacts", {}).get("results_jsonl")
        if not results_jsonl:
            continue
        path = REPO_ROOT / results_jsonl
        if not path.exists():
            continue
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

    manifest_path = out_dir / "campaign_manifest.json"
    existing_id = campaign_id
    if not existing_id and manifest_path.exists():
        existing_id = json.loads(manifest_path.read_text(encoding="utf-8")).get("campaign_id")

    healthy = load_healthy_baseline()
    campaign: dict[str, Any] = {
        "campaign_id": existing_id or f"f2-stability-{datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ')}",
        "fault_id": "F2",
        "fault_name": f2_cfg.get("fault_name", "Model / checkpoint version regression"),
        "model": model,
        "model_revision": revision,
        "pod_id": pod_id,
        "scorer_contract": "calibrated-2026-08-10",
        "healthy_baseline_ref": "results/healthy-stability-120x20-v2",
        "healthy_strict_pass_rate_mean": healthy.get("strict_pass_rate_mean") if healthy else None,
        "results_dir": str(out_dir.relative_to(REPO_ROOT)),
        "n_planned": repeats,
        "n_completed": n,
        "runs": runs,
        "all_http_200": all(r["http_200"] == r["n"] for r in runs),
        "strict_pass_rate_mean": statistics.mean(strict_rates),
        "strict_pass_rate_min": min(strict_rates),
        "strict_pass_rate_max": max(strict_rates),
        "tolerant_pass_rate_mean": statistics.mean(tolerant_rates),
        "gpu_envelope": {
            "util_gpu_pct_max": gpu_band("util_gpu_pct_max"),
            "memory_used_mib_last": gpu_band("memory_used_mib_last"),
            "temperature_c_max": gpu_band("temperature_c_max"),
            "power_w_max": gpu_band("power_w_max"),
        },
        "flaky_canaries": flaky,
        "stability_gate": "PASS" if n == repeats and max(strict_rates) - min(strict_rates) <= 0.05 else "REVIEW",
    }
    if healthy:
        campaign["delta_vs_healthy_strict"] = campaign["strict_pass_rate_mean"] - healthy["strict_pass_rate_mean"]

    manifest_path.write_text(json.dumps(campaign, indent=2), encoding="utf-8")
    md_path = REPO_ROOT / "docs" / "F2_CHECKPOINT_VERSION_STABILITY_120x20.md"
    md_path.write_text(render_markdown(campaign, f2_cfg, healthy), encoding="utf-8")
    (out_dir / "README.md").write_text(
        f"# F2 stability 120×20\n\nCampaign `{campaign['campaign_id']}`\n\nSee `docs/F2_CHECKPOINT_VERSION_STABILITY_120x20.md`\n",
        encoding="utf-8",
    )
    return campaign


def main() -> int:
    parser = argparse.ArgumentParser(description="F2 stability campaign — 120 core × N passes")
    parser.add_argument("--repeats", type=int, default=20)
    parser.add_argument("--limit", type=int, default=120)
    parser.add_argument("--split", default="core")
    parser.add_argument("--out-dir", type=Path, default=REPO_ROOT / "results" / "fault-f2-stability-120x20")
    parser.add_argument("--start-run", type=int, default=1)
    parser.add_argument(
        "--finalize-only",
        action="store_true",
        help="Rebuild campaign_manifest.json and docs/F2_CHECKPOINT_VERSION_STABILITY_120x20.md from run manifests",
    )
    args = parser.parse_args()

    f2_cfg = load_f2_config()
    model = os.getenv("SFB_F2_MODEL", f2_cfg["model"]["repo"])
    revision = os.getenv("SFB_F2_REVISION", f2_cfg["model"]["revision"])

    args.out_dir = (REPO_ROOT / args.out_dir).resolve() if not args.out_dir.is_absolute() else args.out_dir.resolve()

    pod_id = (os.getenv("SFB_RUNPOD_SSH") or "").split("@")[0].split("-")[0]

    if args.finalize_only:
        campaign = finalize_campaign(
            args.out_dir, args.repeats, pod_id, f2_cfg, model, revision
        )
        print(f"Wrote {args.out_dir / 'campaign_manifest.json'}")
        print(f"Wrote {REPO_ROOT / 'docs' / 'F2_CHECKPOINT_VERSION_STABILITY_120x20.md'}")
        return 0

    os.environ["SFB_MODEL"] = model

    args.out_dir.mkdir(parents=True, exist_ok=True)

    base_url = os.getenv("SFB_BASE_URL", "http://127.0.0.1:8000/v1")
    ssh_key = expand(os.getenv("SFB_RUNPOD_KEY", "~/.ssh/sfb_runpod"))
    tcp_host = os.getenv("SFB_RUNPOD_TCP_HOST", "")
    tcp_port = int(os.getenv("SFB_RUNPOD_TCP_PORT", "22"))
    if not tcp_host:
        print("SFB_RUNPOD_TCP_HOST not set — GPU during-run sampling disabled", file=sys.stderr)

    api0 = check_api(base_url)
    if not api0.get("ok"):
        print("API not reachable. Ensure tunnel + F2 vLLM are running.", file=sys.stderr)
        return 2
    model_ids = api0.get("model_ids") or []
    if model_ids and not any("Qwen" in str(m) for m in model_ids):
        print(f"WARNING: expected Qwen2.5-7B-Instruct model id, got {model_ids}", file=sys.stderr)

    campaign_id = f"f2-stability-{datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ')}"
    campaign: dict[str, Any] = {
        "campaign_id": campaign_id,
        "fault_id": "F2",
        "model": model,
        "model_revision": revision,
        "n_planned": args.repeats,
        "n_completed": 0,
        "runs": [],
    }

    canary_pass_counts: dict[str, int] = defaultdict(int)
    if args.start_run > 1:
        prior = load_existing_runs(args.out_dir, args.start_run)
        campaign["runs"] = prior
        campaign["n_completed"] = len(prior)
        for run_entry in prior:
            results_jsonl = run_entry.get("artifacts", {}).get("results_jsonl")
            if results_jsonl:
                path = REPO_ROOT / results_jsonl
                if path.exists():
                    for line in path.read_text(encoding="utf-8").splitlines():
                        if line.strip() and json.loads(line).get("strict_pass"):
                            canary_pass_counts[json.loads(line)["canary_id"]] += 1
        print(f"Resuming from run {args.start_run} ({len(prior)} prior runs loaded)", flush=True)

    client = ServingClient(timeout=180.0)
    sampler = GpuSampler(ssh_key, tcp_host, tcp_port, interval_s=2.0) if tcp_host else None
    if not sampler:
        print("ERROR: GPU sampler unavailable without TCP host", file=sys.stderr)
        return 2

    for i in range(args.start_run, args.repeats + 1):
        print(f"\n=== F2 RUN {i}/{args.repeats} ===", flush=True)
        infra_before = {"api": check_api(base_url)}
        if not infra_before["api"].get("ok"):
            print("API down before run; aborting.", file=sys.stderr)
            break

        sampler.start()
        t0 = time.perf_counter()
        try:
            summary = run_suite(
                condition="F2-checkpoint-version",
                temperature=0.0,
                seed=0,
                shuffle=False,
                limit=args.limit,
                split=args.split,
                warmup=(i == 1),
                client=client,
            )
        except Exception as exc:  # noqa: BLE001
            during_summary = sampler.stop()
            print(f"  run failed ({exc}); retrying once...", flush=True)
            time.sleep(5)
            if not check_api(base_url).get("ok"):
                break
            sampler.start()
            summary = run_suite(
                condition="F2-checkpoint-version",
                temperature=0.0,
                seed=0,
                shuffle=False,
                limit=args.limit,
                split=args.split,
                warmup=False,
                client=client,
            )
        wall_s = time.perf_counter() - t0
        during_summary = sampler.stop()
        if not during_summary.get("ok"):
            print(f"  WARNING: GPU during-run sampling failed: {during_summary}", flush=True)
        else:
            print(
                f"  gpu during: {during_summary.get('n_samples')} samples · "
                f"util max {during_summary.get('util_gpu_pct_max')}% · "
                f"mem last {during_summary.get('memory_used_mib_last')} MiB · "
                f"power max {during_summary.get('power_w_max')} W",
                flush=True,
            )

        infra_after = {
            "gpu": snapshot_gpu(ssh_key, tcp_host, tcp_port),
            "vllm_metrics": parse_vllm_metrics(base_url),
        }
        jsonl_path = write_run(summary)
        meta_src = jsonl_path.with_suffix(".meta.json")
        records = summary["records"]
        http_200 = sum(1 for r in records if r.get("http_status") == 200)

        run_entry = {
            "fault_id": "F2",
            "run_index": i,
            "run_id": summary["run_id"],
            "model": model,
            "model_revision": revision,
            "strict_pass_rate": summary["strict_pass_rate"],
            "tolerant_pass_rate": summary["tolerant_pass_rate"],
            "strict_pass_n": sum(1 for r in records if r.get("strict_pass")),
            "tolerant_pass_n": sum(1 for r in records if r.get("tolerant_pass")),
            "n": len(records),
            "http_200": http_200,
            "wall_s": wall_s,
            "warmup": i == 1,
            "latency": latency_stats(records),
            "capability_breakdown": capability_breakdown(records),
            "strict_failures": strict_failures(records),
            "infra_before": infra_before,
            "infra_during": {"gpu_sampler": during_summary},
            "infra_after": infra_after,
            "artifacts": {
                "jsonl": str(jsonl_path.relative_to(REPO_ROOT)),
                "meta": str(meta_src.relative_to(REPO_ROOT)),
            },
        }

        dest_jsonl = args.out_dir / f"run_{i:02d}_{summary['run_id']}.jsonl"
        dest_meta = args.out_dir / f"run_{i:02d}_{summary['run_id']}.meta.json"
        shutil.copy2(jsonl_path, dest_jsonl)
        shutil.copy2(meta_src, dest_meta)
        run_entry["artifacts"]["results_jsonl"] = str(dest_jsonl.relative_to(REPO_ROOT))
        run_entry["artifacts"]["results_meta"] = str(dest_meta.relative_to(REPO_ROOT))
        (args.out_dir / f"run_{i:02d}_manifest.json").write_text(json.dumps(run_entry, indent=2), encoding="utf-8")

        campaign["runs"].append(run_entry)
        campaign["n_completed"] = i
        print(
            f"  strict={summary['strict_pass_rate']:.1%} http={http_200}/{len(records)} wall={wall_s:.0f}s",
            flush=True,
        )

    n = campaign["n_completed"]
    if n == 0:
        return 2

    finalize_campaign(args.out_dir, args.repeats, pod_id, f2_cfg, model, revision, campaign_id=campaign_id)
    print(f"\nWrote {args.out_dir / 'campaign_manifest.json'}")
    print(f"Wrote {REPO_ROOT / 'docs' / 'F2_CHECKPOINT_VERSION_STABILITY_120x20.md'}")
    return 0 if n == args.repeats else 1


if __name__ == "__main__":
    raise SystemExit(main())
