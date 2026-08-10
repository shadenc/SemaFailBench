#!/usr/bin/env python3
"""Run N deterministic healthy passes with per-run infra snapshots."""

from __future__ import annotations

import argparse
import json
import os
import shutil
import statistics
import subprocess
import sys
import time
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import httpx
from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from sem_fail_bench.paths import REPO_ROOT  # noqa: E402
from sem_fail_bench.runner import run_suite, write_run, _rate  # noqa: E402

load_dotenv(REPO_ROOT / ".env", override=True)


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def expand(path: str) -> Path:
    return Path(os.path.expanduser(path))


def check_api(base_url: str) -> dict[str, Any]:
    root = base_url.rstrip("/").removesuffix("/v1")
    out: dict[str, Any] = {"ok": False, "timestamp_utc": utc_now()}
    try:
        with httpx.Client(timeout=15.0) as client:
            models = client.get(f"{base_url.rstrip('/')}/models")
            out["models_status"] = models.status_code
            out["ok"] = models.status_code == 200
            if out["ok"]:
                data = models.json()
                out["model_ids"] = [m.get("id") for m in (data.get("data") or [])]
            health = client.get(f"{root}/health")
            out["health_status"] = health.status_code
            try:
                metrics = client.get(f"{root}/metrics")
                out["metrics_status"] = metrics.status_code
                if metrics.status_code == 200:
                    text = metrics.text
                    out["metrics_lines"] = len(text.splitlines())
            except Exception as exc:  # noqa: BLE001
                out["metrics_error"] = str(exc)
    except Exception as exc:  # noqa: BLE001
        out["error"] = str(exc)
    return out


def snapshot_gpu(ssh_key: Path, host: str, port: int) -> dict[str, Any]:
    cmd = [
        "ssh",
        "-o",
        "BatchMode=yes",
        "-o",
        "ConnectTimeout=20",
        "-o",
        "StrictHostKeyChecking=accept-new",
        "-i",
        str(ssh_key),
        "-p",
        str(port),
        f"root@{host}",
        (
            "nvidia-smi --query-gpu=index,name,utilization.gpu,utilization.memory,"
            "memory.used,memory.total,temperature.gpu,power.draw,driver_version "
            "--format=csv,noheader,nounits; "
            "pgrep -af 'vllm.entrypoints.openai.api_server' | head -1 || echo VLLM_NOT_RUNNING"
        ),
    ]
    out: dict[str, Any] = {"timestamp_utc": utc_now(), "ok": False}
    try:
        proc = subprocess.run(cmd, capture_output=True, text=True, check=False, timeout=30)
        out["exit_code"] = proc.returncode
        text = (proc.stdout or "").strip()
        out["raw"] = text
        if proc.returncode == 0 and text:
            lines = [ln.strip() for ln in text.splitlines() if ln.strip()]
            if lines and not lines[0].startswith("python"):
                parts = [p.strip() for p in lines[0].split(",")]
                if len(parts) >= 8:
                    out["gpu"] = {
                        "index": int(parts[0]),
                        "name": parts[1],
                        "util_gpu_pct": float(parts[2]),
                        "util_mem_pct": float(parts[3]),
                        "memory_used_mib": float(parts[4]),
                        "memory_total_mib": float(parts[5]),
                        "temperature_c": float(parts[6]),
                        "power_w": float(parts[7]),
                        "driver_version": parts[8] if len(parts) > 8 else None,
                    }
                    out["ok"] = True
            for ln in lines:
                if "vllm.entrypoints" in ln:
                    out["vllm_process"] = ln
                    break
        if proc.stderr:
            out["stderr"] = proc.stderr.strip()
    except Exception as exc:  # noqa: BLE001
        out["error"] = str(exc)
    return out


def latency_stats(records: list[dict[str, Any]]) -> dict[str, float | None]:
    vals = sorted(float(r["latency_ms"]) for r in records if r.get("latency_ms") is not None)
    if not vals:
        return {"n": 0, "p50_ms": None, "p95_ms": None, "max_ms": None}
    return {
        "n": len(vals),
        "p50_ms": vals[len(vals) // 2],
        "p95_ms": vals[int(len(vals) * 0.95)],
        "max_ms": vals[-1],
    }


def capability_breakdown(records: list[dict[str, Any]]) -> dict[str, str]:
    total = Counter(r["capability"] for r in records)
    passed = Counter(r["capability"] for r in records if r.get("strict_pass"))
    return {cap: f"{passed[cap]}/{total[cap]}" for cap in sorted(total.keys())}


def strict_failures(records: list[dict[str, Any]]) -> list[dict[str, Any]]:
    fails = []
    for r in records:
        if r.get("strict_pass"):
            continue
        details = r.get("score_details") or {}
        note = details.get("note") or details.get("observed") or str(details)[:120]
        fails.append({"canary_id": r["canary_id"], "subtype": r["subtype"], "note": note})
    return fails


def render_markdown(campaign: dict[str, Any]) -> str:
    runs = campaign["runs"]
    lines = [
        "# Healthy stability — 120 core × 20 deterministic passes",
        "",
        f"**Campaign id:** `{campaign['campaign_id']}`",
        f"**Pod:** `{campaign.get('pod_id', '?')}` · live vLLM inference",
        f"**Scorer contract:** `{campaign.get('scorer_contract', 'calibrated-2026-08-10')}`",
        "",
        f"**Raw scores:** `{campaign['results_dir']}`",
        "",
        "## Protocol",
        "",
        "- 120 core canaries (SFC-001 … SFC-120), catalog order, temp=0",
        "- Run 1: 5 warmup requests discarded, then 120 measured",
        "- Runs 2–20: 120 measured each (no warmup)",
        "- API + GPU snapshot collected before each run",
        "- GPU snapshots backfilled post-campaign where live SSH used stale shell TCP env (API snapshots are from run time)",
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
        "",
        "### Per-run pass rates",
        "",
        "| Run | Run id | Strict | Tolerant | HTTP | Wall s | p50 ms | p95 ms | API ok | GPU ok | GPU util % | GPU mem MiB | Temp °C | Power W |",
        "|---|---|---|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|",
    ]
    for r in runs:
        gpu_snap = (r.get("infra_before") or {}).get("gpu") or {}
        gpu = gpu_snap.get("gpu") or {}
        api = (r.get("infra_before") or {}).get("api") or {}
        lat = r.get("latency") or {}
        api_ok = "yes" if api.get("ok") else "no"
        gpu_ok = "yes" if gpu_snap.get("ok") else "no"
        lines.append(
            f"| {r['run_index']:02d} | `{r['run_id']}` | {r['strict_pass_rate']:.1%} | "
            f"{r['tolerant_pass_rate']:.1%} | {r['http_200']}/{r['n']} | {r['wall_s']:.0f} | "
            f"{lat.get('p50_ms', 0):.0f} | {lat.get('p95_ms', 0):.0f} | "
            f"{api_ok} | {gpu_ok} | "
            f"{gpu.get('util_gpu_pct', '—')} | {gpu.get('memory_used_mib', '—')} | "
            f"{gpu.get('temperature_c', '—')} | {gpu.get('power_w', '—')} |"
        )
    lines.extend(
        [
            "",
            "### GPU infra envelope (before-run snapshots)",
            "",
            "| Metric | min | mean | max |",
            "|---|---:|---:|---:|",
        ]
    )
    env = campaign.get("gpu_envelope") or {}
    for key, label in [
        ("util_gpu_pct", "GPU util %"),
        ("memory_used_mib", "GPU mem used MiB"),
        ("temperature_c", "Temperature °C"),
        ("power_w", "Power W"),
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
                "",
            ]
        )
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


def load_existing_runs(out_dir: Path, until_index: int) -> list[dict[str, Any]]:
    runs: list[dict[str, Any]] = []
    for i in range(1, until_index):
        manifest = out_dir / f"run_{i:02d}_manifest.json"
        if not manifest.exists():
            raise FileNotFoundError(f"Missing prior run manifest: {manifest}")
        runs.append(json.loads(manifest.read_text(encoding="utf-8")))
    return runs


def finalize_campaign(
    out_dir: Path,
    repeats: int,
    pod_id: str,
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
        ((r.get("infra_before") or {}).get("gpu") or {}).get("gpu")
        for r in runs
    ]
    gpu_samples = [g for g in gpu_samples if g]

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
    flaky.sort(key=lambda x: (x[1], x[0]))

    existing_id = campaign_id
    manifest_path = out_dir / "campaign_manifest.json"
    if not existing_id and manifest_path.exists():
        existing_id = json.loads(manifest_path.read_text(encoding="utf-8")).get("campaign_id")

    campaign: dict[str, Any] = {
        "campaign_id": existing_id or f"stability-{datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ')}",
        "pod_id": pod_id,
        "scorer_contract": "calibrated-2026-08-10",
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
            "util_gpu_pct": gpu_band("util_gpu_pct"),
            "memory_used_mib": gpu_band("memory_used_mib"),
            "temperature_c": gpu_band("temperature_c"),
            "power_w": gpu_band("power_w"),
        },
        "flaky_canaries": flaky,
        "stability_gate": "PASS" if n == repeats and max(strict_rates) - min(strict_rates) <= 0.05 else "REVIEW",
    }
    manifest_path.write_text(json.dumps(campaign, indent=2), encoding="utf-8")
    md_path = REPO_ROOT / "docs" / "HEALTHY_STABILITY_120x20.md"
    md_path.write_text(render_markdown(campaign), encoding="utf-8")
    (out_dir / "README.md").write_text(
        f"# Healthy stability 120×20\n\nCampaign `{campaign['campaign_id']}`\n\nSee `docs/HEALTHY_STABILITY_120x20.md`\n",
        encoding="utf-8",
    )
    return campaign


def backfill_gpu_snapshots(out_dir: Path, ssh_key: Path, tcp_host: str, tcp_port: int) -> int:
    updated = 0
    for manifest in sorted(out_dir.glob("run_*_manifest.json")):
        run_entry = json.loads(manifest.read_text(encoding="utf-8"))
        gpu_snap = snapshot_gpu(ssh_key, tcp_host, tcp_port)
        infra = run_entry.setdefault("infra_before", {})
        infra["gpu"] = gpu_snap
        manifest.write_text(json.dumps(run_entry, indent=2), encoding="utf-8")
        updated += 1
        print(f"  backfilled GPU for {manifest.name}: ok={gpu_snap.get('ok')}", flush=True)
    return updated


def main() -> int:
    parser = argparse.ArgumentParser(description="Healthy stability campaign")
    parser.add_argument("--repeats", type=int, default=20)
    parser.add_argument("--limit", type=int, default=120)
    parser.add_argument("--split", default="core")
    parser.add_argument("--out-dir", type=Path, default=REPO_ROOT / "results" / "healthy-stability-120x20")
    parser.add_argument(
        "--start-run",
        type=int,
        default=1,
        help="Resume from this run index (loads run_01..run_{start-1} manifests from --out-dir)",
    )
    parser.add_argument(
        "--backfill-gpu",
        action="store_true",
        help="Refresh GPU snapshots in existing run manifests (uses .env TCP host/port)",
    )
    parser.add_argument(
        "--finalize-only",
        action="store_true",
        help="Rebuild campaign_manifest.json and docs/HEALTHY_STABILITY_120x20.md from run manifests",
    )
    args = parser.parse_args()
    if args.start_run < 1 or args.start_run > args.repeats:
        print("--start-run must be between 1 and --repeats", file=sys.stderr)
        return 2

    base_url = os.getenv("SFB_BASE_URL", "http://127.0.0.1:8000/v1")
    ssh_key = expand(os.getenv("SFB_RUNPOD_KEY", "~/.ssh/sfb_runpod"))
    tcp_host = os.getenv("SFB_RUNPOD_TCP_HOST", "")
    tcp_port = int(os.getenv("SFB_RUNPOD_TCP_PORT", "22"))
    pod_id = (os.getenv("SFB_RUNPOD_SSH") or "").split("@")[0].split("-")[0]

    if args.backfill_gpu or args.finalize_only:
        if args.backfill_gpu:
            if not tcp_host:
                print("SFB_RUNPOD_TCP_HOST not set", file=sys.stderr)
                return 2
            print(f"Backfilling GPU snapshots via {tcp_host}:{tcp_port} ...", flush=True)
            n = backfill_gpu_snapshots(args.out_dir, ssh_key, tcp_host, tcp_port)
            print(f"Updated {n} manifests", flush=True)
        campaign = finalize_campaign(args.out_dir, args.repeats, pod_id)
        print(f"Wrote {args.out_dir / 'campaign_manifest.json'}")
        print(f"Wrote {REPO_ROOT / 'docs' / 'HEALTHY_STABILITY_120x20.md'}")
        return 0

    args.out_dir.mkdir(parents=True, exist_ok=True)
    campaign_id = f"stability-{datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ')}"
    campaign: dict[str, Any] = {
        "campaign_id": campaign_id,
        "pod_id": pod_id,
        "scorer_contract": "calibrated-2026-08-10",
        "results_dir": str(args.out_dir.relative_to(REPO_ROOT)),
        "n_planned": args.repeats,
        "n_completed": 0,
        "runs": [],
    }

    api0 = check_api(base_url)
    if not api0.get("ok"):
        print("API not reachable:", json.dumps(api0, indent=2), file=sys.stderr)
        return 2

    canary_pass_counts: dict[str, int] = defaultdict(int)
    strict_rates: list[float] = []
    tolerant_rates: list[float] = []
    gpu_samples: list[dict[str, float]] = []

    if args.start_run > 1:
        prior = load_existing_runs(args.out_dir, args.start_run)
        campaign["runs"] = prior
        campaign["n_completed"] = len(prior)
        for run_entry in prior:
            strict_rates.append(float(run_entry["strict_pass_rate"]))
            tolerant_rates.append(float(run_entry["tolerant_pass_rate"]))
            gpu = (run_entry.get("infra_before") or {}).get("gpu") or {}
            if gpu.get("gpu"):
                gpu_samples.append(gpu["gpu"])
            for fail in run_entry.get("strict_failures") or []:
                pass  # failures only; rebuild pass counts below
            # Rebuild pass counts from jsonl if present
            results_jsonl = run_entry.get("artifacts", {}).get("results_jsonl")
            if results_jsonl:
                path = REPO_ROOT / results_jsonl
                if path.exists():
                    for line in path.read_text(encoding="utf-8").splitlines():
                        if not line.strip():
                            continue
                        row = json.loads(line)
                        if row.get("strict_pass"):
                            canary_pass_counts[row["canary_id"]] += 1
        print(f"Resuming: loaded {len(prior)} prior runs from {args.out_dir}", flush=True)

    for i in range(args.start_run, args.repeats + 1):
        print(f"\n=== RUN {i}/{args.repeats} ===", flush=True)
        infra_before = {
            "api": check_api(base_url),
            "gpu": snapshot_gpu(ssh_key, tcp_host, tcp_port),
        }
        if not infra_before["api"].get("ok"):
            print("API down before run; aborting campaign.", file=sys.stderr)
            break
        if infra_before["gpu"].get("gpu"):
            gpu_samples.append(infra_before["gpu"]["gpu"])

        t0 = time.perf_counter()
        try:
            summary = run_suite(
                condition="healthy",
                temperature=0.0,
                seed=0,
                shuffle=False,
                limit=args.limit,
                split=args.split,
                warmup=(i == 1),
            )
        except Exception as exc:  # noqa: BLE001
            print(f"  run failed ({exc}); retrying once after API check...", flush=True)
            time.sleep(5)
            if not check_api(base_url).get("ok"):
                print("API down after failure; aborting campaign.", file=sys.stderr)
                break
            summary = run_suite(
                condition="healthy",
                temperature=0.0,
                seed=0,
                shuffle=False,
                limit=args.limit,
                split=args.split,
                warmup=False,
            )
        wall_s = time.perf_counter() - t0
        jsonl_path = write_run(summary)
        meta_src = jsonl_path.with_suffix(".meta.json")

        records = summary["records"]
        http_200 = sum(1 for r in records if r.get("http_status") == 200)
        strict_n = sum(1 for r in records if r.get("strict_pass"))
        tolerant_n = sum(1 for r in records if r.get("tolerant_pass"))
        for r in records:
            if r.get("strict_pass"):
                canary_pass_counts[r["canary_id"]] += 1

        run_entry = {
            "run_index": i,
            "run_id": summary["run_id"],
            "strict_pass_rate": summary["strict_pass_rate"],
            "tolerant_pass_rate": summary["tolerant_pass_rate"],
            "strict_pass_n": strict_n,
            "tolerant_pass_n": tolerant_n,
            "n": len(records),
            "http_200": http_200,
            "wall_s": wall_s,
            "warmup": i == 1,
            "latency": latency_stats(records),
            "capability_breakdown": capability_breakdown(records),
            "strict_failures": strict_failures(records),
            "infra_before": infra_before,
            "artifacts": {
                "jsonl": str(jsonl_path.relative_to(REPO_ROOT)),
                "meta": str(meta_src.relative_to(REPO_ROOT)),
            },
        }
        strict_rates.append(float(summary["strict_pass_rate"] or 0))
        tolerant_rates.append(float(summary["tolerant_pass_rate"] or 0))

        dest_jsonl = args.out_dir / f"run_{i:02d}_{summary['run_id']}.jsonl"
        dest_meta = args.out_dir / f"run_{i:02d}_{summary['run_id']}.meta.json"
        shutil.copy2(jsonl_path, dest_jsonl)
        shutil.copy2(meta_src, dest_meta)
        run_entry["artifacts"]["results_jsonl"] = str(dest_jsonl.relative_to(REPO_ROOT))
        run_entry["artifacts"]["results_meta"] = str(dest_meta.relative_to(REPO_ROOT))

        run_manifest = args.out_dir / f"run_{i:02d}_manifest.json"
        run_manifest.write_text(json.dumps(run_entry, indent=2), encoding="utf-8")

        campaign["runs"].append(run_entry)
        campaign["n_completed"] = i
        print(
            f"  strict={summary['strict_pass_rate']:.1%} http={http_200}/{len(records)} "
            f"wall={wall_s:.0f}s run_id={summary['run_id']}",
            flush=True,
        )

    n = campaign["n_completed"]
    if n == 0:
        return 2

    def gpu_band(key: str) -> dict[str, float]:
        vals = [g[key] for g in gpu_samples if key in g]
        return {"min": min(vals), "mean": statistics.mean(vals), "max": max(vals)} if vals else {}

    flaky = [(cid, cnt) for cid, cnt in sorted(canary_pass_counts.items()) if 0 < cnt < n]
    flaky.sort(key=lambda x: (x[1], x[0]))

    campaign.update(
        {
            "all_http_200": all(r["http_200"] == r["n"] for r in campaign["runs"]),
            "strict_pass_rate_mean": statistics.mean(strict_rates),
            "strict_pass_rate_min": min(strict_rates),
            "strict_pass_rate_max": max(strict_rates),
            "tolerant_pass_rate_mean": statistics.mean(tolerant_rates),
            "gpu_envelope": {
                "util_gpu_pct": gpu_band("util_gpu_pct"),
                "memory_used_mib": gpu_band("memory_used_mib"),
                "temperature_c": gpu_band("temperature_c"),
                "power_w": gpu_band("power_w"),
            },
            "flaky_canaries": flaky,
            "stability_gate": "PASS" if n == args.repeats and max(strict_rates) - min(strict_rates) <= 0.05 else "REVIEW",
        }
    )

    finalize_campaign(args.out_dir, args.repeats, pod_id, campaign_id=campaign["campaign_id"])
    print(f"\nWrote {args.out_dir / 'campaign_manifest.json'}")
    print(f"Wrote {REPO_ROOT / 'docs' / 'HEALTHY_STABILITY_120x20.md'}")
    return 0 if n == args.repeats else 1


if __name__ == "__main__":
    raise SystemExit(main())
