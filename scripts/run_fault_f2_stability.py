#!/usr/bin/env python3
"""F2 checkpoint-version fault — preflight + 120 core × N deterministic passes."""

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
from collections import defaultdict
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

DEFAULT_OUT = REPO_ROOT / "results" / "fault-f2-stability-120x20"
PREFLIGHT_MANIFEST = "preflight_manifest.json"


def load_f2_config() -> dict:
    return yaml.safe_load((REPO_ROOT / "configs" / "serving_f2.yaml").read_text(encoding="utf-8"))


def f2_models(f2_cfg: dict) -> tuple[str, str, str, str]:
    expected = os.getenv(
        "SFB_F2_EXPECTED_MODEL",
        f2_cfg.get("expected_model", {}).get("repo", "Qwen/Qwen2.5-7B-Instruct"),
    )
    actual = os.getenv(
        "SFB_F2_ACTUAL_MODEL",
        f2_cfg.get("actual_model", {}).get("repo", "Qwen/Qwen2-7B-Instruct"),
    )
    revision = os.getenv(
        "SFB_F2_REVISION",
        f2_cfg.get("actual_model", {}).get("revision", ""),
    )
    served = os.getenv(
        "SFB_F2_SERVED_MODEL_NAME",
        f2_cfg.get("served_model_name", expected),
    )
    return expected, actual, revision, served


def load_healthy_baseline() -> dict | None:
    path = REPO_ROOT / "results" / "healthy-stability-120x20-v2" / "campaign_manifest.json"
    if not path.exists():
        return None
    return json.loads(path.read_text(encoding="utf-8"))


def healthy_run1_failures() -> set[str]:
    path = REPO_ROOT / "results" / "healthy-stability-120x20-v2" / "run_01_manifest.json"
    if not path.exists():
        return set()
    return {f["canary_id"] for f in json.loads(path.read_text())["strict_failures"]}


def canary_delta(h_fails: set[str], f_fails: set[str]) -> tuple[list[str], list[str], list[str]]:
    regressions = sorted(f_fails - h_fails)
    recoveries = sorted(h_fails - f_fails)
    stable_fail = sorted(h_fails & f_fails)
    return regressions, recoveries, stable_fail


def evaluate_preflight(
    f2_strict_rate: float,
    f2_fail_ids: set[str],
    f2_cfg: dict,
    healthy: dict | None,
) -> dict[str, Any]:
    h_rate = float(
        (healthy or {}).get("strict_pass_rate_mean")
        or f2_cfg.get("healthy_reference", {}).get("strict_pass_rate_mean")
        or 0.925
    )
    h_fails = healthy_run1_failures()
    regressions, recoveries, stable_fail = canary_delta(h_fails, f2_fail_ids)
    delta_f2 = h_rate - f2_strict_rate
    pf = f2_cfg.get("preflight") or {}
    min_delta = float(pf.get("min_abs_strict_delta", 0.01))
    min_swaps = int(pf.get("min_canary_swaps", 1))
    swaps = len(regressions) + len(recoveries)
    effective = abs(delta_f2) >= min_delta or swaps >= min_swaps
    return {
        "delta_F2": delta_f2,
        "healthy_strict_pass_rate": h_rate,
        "f2_strict_pass_rate": f2_strict_rate,
        "regressions": regressions,
        "recoveries": recoveries,
        "stable_failures": stable_fail,
        "canary_swaps": swaps,
        "min_abs_strict_delta": min_delta,
        "min_canary_swaps": min_swaps,
        "effective": effective,
        "verdict": "EFFECTIVE" if effective else "INEFFECTIVE_CANDIDATE",
    }


def _run_pass(
    *,
    client: ServingClient,
    sampler: Any | None,
    ssh_key: Path,
    tcp_host: str,
    tcp_port: int,
    base_url: str,
    limit: int,
    split: str,
    warmup: bool,
    run_index: int | None = None,
) -> dict[str, Any]:
    label = "PREFLIGHT" if run_index is None else f"RUN {run_index}"
    print(f"\n=== F2 {label} ===", flush=True)
    infra_before = {"api": check_api(base_url)}
    if not infra_before["api"].get("ok"):
        raise RuntimeError("API not reachable")

    during_summary: dict[str, Any] = {}
    if sampler:
        sampler.start()
    t0 = time.perf_counter()
    try:
        summary = run_suite(
            condition="F2-checkpoint-version",
            temperature=0.0,
            seed=0,
            shuffle=False,
            limit=limit,
            split=split,
            warmup=warmup,
            client=client,
        )
    except Exception as exc:  # noqa: BLE001
        if sampler:
            during_summary = sampler.stop()
        print(f"  run failed ({exc}); retrying once...", flush=True)
        time.sleep(5)
        if not check_api(base_url).get("ok"):
            raise
        if sampler:
            sampler.start()
        summary = run_suite(
            condition="F2-checkpoint-version",
            temperature=0.0,
            seed=0,
            shuffle=False,
            limit=limit,
            split=split,
            warmup=False,
            client=client,
        )
    wall_s = time.perf_counter() - t0
    if sampler:
        during_summary = sampler.stop()
        if during_summary.get("ok"):
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
    records = summary["records"]
    http_200 = sum(1 for r in records if r.get("http_status") == 200)
    print(
        f"  strict={summary['strict_pass_rate']:.1%} http={http_200}/{len(records)} wall={wall_s:.0f}s",
        flush=True,
    )
    return {
        "summary": summary,
        "records": records,
        "http_200": http_200,
        "wall_s": wall_s,
        "warmup": warmup,
        "infra_before": infra_before,
        "infra_during": {"gpu_sampler": during_summary},
        "infra_after": infra_after,
    }


def run_preflight(
    *,
    out_dir: Path,
    f2_cfg: dict,
    expected: str,
    actual: str,
    revision: str,
    served: str,
    pod_id: str,
    limit: int,
    split: str,
    base_url: str,
    ssh_key: Path,
    tcp_host: str,
    tcp_port: int,
) -> dict[str, Any]:
    healthy = load_healthy_baseline()
    client = ServingClient(timeout=180.0, model=expected)
    sampler = GpuSampler(ssh_key, tcp_host, tcp_port, interval_s=2.0) if tcp_host else None
    if not sampler:
        raise RuntimeError("GPU sampler unavailable without SFB_RUNPOD_TCP_HOST")

    passed = _run_pass(
        client=client,
        sampler=sampler,
        ssh_key=ssh_key,
        tcp_host=tcp_host,
        tcp_port=tcp_port,
        base_url=base_url,
        limit=limit,
        split=split,
        warmup=True,
        run_index=None,
    )
    summary = passed["summary"]
    records = passed["records"]
    fail_ids = {r["canary_id"] for r in records if not r.get("strict_pass")}
    evaluation = evaluate_preflight(float(summary["strict_pass_rate"]), fail_ids, f2_cfg, healthy)

    jsonl_path = write_run(summary)
    meta_src = jsonl_path.with_suffix(".meta.json")
    dest_jsonl = out_dir / f"preflight_{summary['run_id']}.jsonl"
    dest_meta = out_dir / f"preflight_{summary['run_id']}.meta.json"
    shutil.copy2(jsonl_path, dest_jsonl)
    shutil.copy2(meta_src, dest_meta)

    manifest: dict[str, Any] = {
        "phase": "preflight",
        "timestamp_utc": datetime.now(timezone.utc).isoformat(),
        "fault_id": "F2",
        "expected_model": expected,
        "actual_model": actual,
        "actual_model_revision": revision,
        "served_model_name": served,
        "run_id": summary["run_id"],
        "strict_pass_rate": summary["strict_pass_rate"],
        "tolerant_pass_rate": summary["tolerant_pass_rate"],
        "n": len(records),
        "http_200": passed["http_200"],
        "wall_s": passed["wall_s"],
        "warmup": True,
        "strict_failures": strict_failures(records),
        "capability_breakdown": capability_breakdown(records),
        "evaluation": evaluation,
        "artifacts": {
            "results_jsonl": str(dest_jsonl.relative_to(REPO_ROOT)),
            "results_meta": str(dest_meta.relative_to(REPO_ROOT)),
        },
        "infra_before": passed["infra_before"],
        "infra_during": passed["infra_during"],
        "infra_after": passed["infra_after"],
        "pod_id": pod_id,
    }
    (out_dir / PREFLIGHT_MANIFEST).write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    print(
        f"\nPreflight delta_F2={evaluation['delta_F2']:+.1%} "
        f"swaps={evaluation['canary_swaps']} verdict={evaluation['verdict']}",
        flush=True,
    )
    return manifest


def _healthy_f2_delta(out_dir: Path) -> tuple[list[str], list[str], list[str]]:
    h_fails = healthy_run1_failures()
    if not h_fails:
        return [], [], []
    f2_manifest = out_dir / "run_01_manifest.json"
    if not f2_manifest.exists():
        return sorted(h_fails), [], []
    f_fails = {f["canary_id"] for f in json.loads(f2_manifest.read_text())["strict_failures"]}
    return canary_delta(h_fails, f_fails)


def render_markdown(campaign: dict[str, Any], f2_cfg: dict, healthy: dict | None) -> str:
    runs = campaign["runs"]
    expected = campaign.get("expected_model", f2_cfg["expected_model"]["repo"])
    actual = campaign.get("actual_model", f2_cfg["actual_model"]["repo"])
    revision = campaign.get("actual_model_revision", f2_cfg["actual_model"]["revision"])
    lines = [
        "# F2 — Model / checkpoint version regression · 120 core × 20 deterministic passes",
        "",
        f"**Campaign id:** `{campaign['campaign_id']}`",
        f"**Fault:** F2 — wrong model-version artifact deployment",
        f"**Pod:** `{campaign.get('pod_id', '?')}`",
        f"**Expected model (logical):** `{expected}`",
        f"**Actual model (loaded):** `{actual}` @ `{revision}`",
        f"**Served API model id:** `{campaign.get('served_model_name', expected)}`",
        f"**Scorer contract:** `{campaign.get('scorer_contract', 'calibrated-2026-08-10')}`",
        "",
        f"**Raw scores:** `{campaign['results_dir']}`",
        "",
        "> Compare per-canary jsonl vs healthy v2 in `results/healthy-stability-120x20-v2/`.",
        "> Prior revision-only F2 attempt (`results/fault-f2-stability-120x20/`, Qwen2.5 @ 52e20a6…) was an **invalid artifact selection** — not evidence that F2 has no effect.",
        "",
        "## Protocol",
        "",
        f"- Wrong-version artifact: serve `{actual}` with `--served-model-name {expected}`",
        "- 120 core canaries (SFC-001 … SFC-120), catalog order, temp=0",
        "- Preflight: one deterministic pass; abort 20× if ineffective",
        "- Run 1: 5 warmup requests discarded, then 120 measured",
        "- Runs 2–20: 120 measured each (no warmup)",
        "- API health check before each run; GPU sampled every 2s during inference",
        "",
        "## Campaign summary",
        "",
        "| | |",
        "|---|---|",
        f"| Runs completed | {campaign['n_completed']} / {campaign['n_planned']} |",
        f"| All HTTP 200 | {campaign['all_http_200']} |",
        f"| Strict pass rate (mean) | **{campaign['strict_pass_rate_mean']:.1%}** |",
        f"| Tolerant pass rate (mean) | {campaign['tolerant_pass_rate_mean']:.1%} |",
        f"| Stability gate | {campaign['stability_gate']} |",
    ]
    if healthy:
        h = healthy.get("strict_pass_rate_mean", 0)
        delta_f2 = h - campaign["strict_pass_rate_mean"]
        lines.extend(
            [
                f"| Healthy baseline (v2 mean) | {h:.1%} |",
                f"| delta_F2 (healthy − F2) | {delta_f2:+.1%} |",
            ]
        )
    regressions, recoveries, stable_fail = _healthy_f2_delta(Path(REPO_ROOT / campaign["results_dir"]))
    if regressions or recoveries:
        lines.extend(
            [
                "",
                "### F2 vs healthy (run 1 strict delta)",
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
            "| Run | Run id | Strict | Tolerant | HTTP | Wall s | API ok | GPU util max % |",
            "|---|---|---|---|---|---:|---:|---:|",
        ]
    )
    for r in runs:
        during = (r.get("infra_during") or {}).get("gpu_sampler") or {}
        api_ok = "yes" if (r.get("infra_before") or {}).get("api", {}).get("ok") else "no"
        lines.append(
            f"| {r['run_index']:02d} | `{r['run_id']}` | {r['strict_pass_rate']:.1%} | "
            f"{r['tolerant_pass_rate']:.1%} | {r['http_200']}/{r['n']} | {r['wall_s']:.0f} | "
            f"{api_ok} | {during.get('util_gpu_pct_max', '—')} |"
        )
    lines.append("")
    return "\n".join(lines)


def finalize_campaign(
    out_dir: Path,
    repeats: int,
    pod_id: str,
    f2_cfg: dict,
    expected: str,
    actual: str,
    revision: str,
    served: str,
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
            if line.strip() and json.loads(line).get("strict_pass"):
                canary_pass_counts[json.loads(line)["canary_id"]] += 1

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
    h_mean = healthy.get("strict_pass_rate_mean") if healthy else None
    f_mean = statistics.mean(strict_rates)
    campaign: dict[str, Any] = {
        "campaign_id": existing_id or f"f2-stability-{datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ')}",
        "fault_id": "F2",
        "fault_name": f2_cfg.get("fault_name", "Model / checkpoint version regression"),
        "deployment_kind": "wrong_model_version_artifact",
        "expected_model": expected,
        "actual_model": actual,
        "actual_model_revision": revision,
        "served_model_name": served,
        "pod_id": pod_id,
        "scorer_contract": "calibrated-2026-08-10",
        "healthy_baseline_ref": "results/healthy-stability-120x20-v2",
        "healthy_strict_pass_rate_mean": h_mean,
        "results_dir": str(out_dir.relative_to(REPO_ROOT)),
        "n_planned": repeats,
        "n_completed": n,
        "runs": runs,
        "all_http_200": all(r["http_200"] == r["n"] for r in runs),
        "strict_pass_rate_mean": f_mean,
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
    if h_mean is not None:
        campaign["delta_F2"] = h_mean - f_mean

    preflight_path = out_dir / PREFLIGHT_MANIFEST
    if preflight_path.exists():
        campaign["preflight"] = json.loads(preflight_path.read_text(encoding="utf-8"))

    manifest_path.write_text(json.dumps(campaign, indent=2), encoding="utf-8")
    md_path = REPO_ROOT / "docs" / "F2_CHECKPOINT_VERSION_STABILITY_120x20.md"
    md_path.write_text(render_markdown(campaign, f2_cfg, healthy), encoding="utf-8")
    (out_dir / "README.md").write_text(
        f"# F2 stability 120×20\n\nCampaign `{campaign['campaign_id']}`\n\nSee `docs/F2_CHECKPOINT_VERSION_STABILITY_120x20.md`\n",
        encoding="utf-8",
    )
    return campaign


def main() -> int:
    parser = argparse.ArgumentParser(description="F2 stability campaign — preflight + 120 core × N passes")
    parser.add_argument("--repeats", type=int, default=20)
    parser.add_argument("--limit", type=int, default=120)
    parser.add_argument("--split", default="core")
    parser.add_argument("--out-dir", type=Path, default=DEFAULT_OUT)
    parser.add_argument("--start-run", type=int, default=1)
    parser.add_argument("--preflight-only", action="store_true", help="Run one preflight pass and evaluate effectiveness")
    parser.add_argument("--skip-preflight", action="store_true", help="Skip preflight gate (not recommended)")
    parser.add_argument("--finalize-only", action="store_true")
    args = parser.parse_args()

    f2_cfg = load_f2_config()
    expected, actual, revision, served = f2_models(f2_cfg)
    args.out_dir = (REPO_ROOT / args.out_dir).resolve() if not args.out_dir.is_absolute() else args.out_dir.resolve()
    pod_id = (os.getenv("SFB_RUNPOD_SSH") or "").split("@")[0].split("-")[0]

    if args.finalize_only:
        finalize_campaign(args.out_dir, args.repeats, pod_id, f2_cfg, expected, actual, revision, served)
        print(f"Wrote {args.out_dir / 'campaign_manifest.json'}")
        return 0

    os.environ["SFB_MODEL"] = expected
    args.out_dir.mkdir(parents=True, exist_ok=True)

    base_url = os.getenv("SFB_BASE_URL", "http://127.0.0.1:8000/v1")
    ssh_key = expand(os.getenv("SFB_RUNPOD_KEY", "~/.ssh/sfb_runpod"))
    tcp_host = os.getenv("SFB_RUNPOD_TCP_HOST", "")
    tcp_port = int(os.getenv("SFB_RUNPOD_TCP_PORT", "22"))
    if not tcp_host:
        print("SFB_RUNPOD_TCP_HOST not set — GPU during-run sampling disabled", file=sys.stderr)
        return 2

    api0 = check_api(base_url)
    if not api0.get("ok"):
        print("API not reachable. Ensure tunnel + F2 vLLM are running.", file=sys.stderr)
        return 2
    model_ids = api0.get("model_ids") or []
    if model_ids and expected not in model_ids:
        print(f"WARNING: expected served model id {expected!r}, got {model_ids}", file=sys.stderr)

    preflight_needed = not args.skip_preflight and (
        args.preflight_only or (args.start_run == 1 and not (args.out_dir / PREFLIGHT_MANIFEST).exists())
    )
    if preflight_needed:
        pf = run_preflight(
            out_dir=args.out_dir,
            f2_cfg=f2_cfg,
            expected=expected,
            actual=actual,
            revision=revision,
            served=served,
            pod_id=pod_id,
            limit=args.limit,
            split=args.split,
            base_url=base_url,
            ssh_key=ssh_key,
            tcp_host=tcp_host,
            tcp_port=tcp_port,
        )
        if not pf["evaluation"]["effective"]:
            print(
                "F2 preflight INEFFECTIVE — no meaningful semantic delta vs healthy. "
                "Stopping before 20-repeat campaign.",
                file=sys.stderr,
            )
            return 4
        if args.preflight_only:
            print(f"Preflight EFFECTIVE. Wrote {args.out_dir / PREFLIGHT_MANIFEST}")
            return 0

    if args.preflight_only:
        return 0

    campaign_id = f"f2-stability-{datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ')}"
    campaign: dict[str, Any] = {
        "campaign_id": campaign_id,
        "fault_id": "F2",
        "expected_model": expected,
        "actual_model": actual,
        "actual_model_revision": revision,
        "n_planned": args.repeats,
        "n_completed": 0,
        "runs": [],
    }

    if args.start_run > 1:
        prior = load_existing_runs(args.out_dir, args.start_run)
        campaign["runs"] = prior
        campaign["n_completed"] = len(prior)
        print(f"Resuming from run {args.start_run} ({len(prior)} prior runs loaded)", flush=True)

    client = ServingClient(timeout=180.0, model=expected)
    sampler = GpuSampler(ssh_key, tcp_host, tcp_port, interval_s=2.0) if tcp_host else None
    if not sampler:
        print("ERROR: GPU sampler unavailable without TCP host", file=sys.stderr)
        return 2

    for i in range(args.start_run, args.repeats + 1):
        passed = _run_pass(
            client=client,
            sampler=sampler,
            ssh_key=ssh_key,
            tcp_host=tcp_host,
            tcp_port=tcp_port,
            base_url=base_url,
            limit=args.limit,
            split=args.split,
            warmup=(i == 1),
            run_index=i,
        )
        summary = passed["summary"]
        records = passed["records"]
        jsonl_path = write_run(summary)
        meta_src = jsonl_path.with_suffix(".meta.json")

        run_entry = {
            "fault_id": "F2",
            "run_index": i,
            "run_id": summary["run_id"],
            "expected_model": expected,
            "actual_model": actual,
            "actual_model_revision": revision,
            "served_model_name": served,
            "strict_pass_rate": summary["strict_pass_rate"],
            "tolerant_pass_rate": summary["tolerant_pass_rate"],
            "strict_pass_n": sum(1 for r in records if r.get("strict_pass")),
            "tolerant_pass_n": sum(1 for r in records if r.get("tolerant_pass")),
            "n": len(records),
            "http_200": passed["http_200"],
            "wall_s": passed["wall_s"],
            "warmup": i == 1,
            "latency": latency_stats(records),
            "capability_breakdown": capability_breakdown(records),
            "strict_failures": strict_failures(records),
            "infra_before": passed["infra_before"],
            "infra_during": passed["infra_during"],
            "infra_after": passed["infra_after"],
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

    n = campaign["n_completed"]
    if n == 0:
        return 2

    finalize_campaign(args.out_dir, args.repeats, pod_id, f2_cfg, expected, actual, revision, served, campaign_id)
    print(f"\nWrote {args.out_dir / 'campaign_manifest.json'}")
    return 0 if n == args.repeats else 1


if __name__ == "__main__":
    raise SystemExit(main())
