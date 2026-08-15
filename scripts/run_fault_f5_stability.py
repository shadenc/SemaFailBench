#!/usr/bin/env python3
"""F5 decoding-config drift fault — preflight + 120 core × N deterministic passes."""

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
from sem_fail_bench.paths import REPO_ROOT, fault_serving_path  # noqa: E402
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

DEFAULT_OUT = REPO_ROOT / "results" / "f5-retest"
PREFLIGHT_MANIFEST = "preflight_manifest.json"
ISOLATION_MANIFEST = "f5_isolation_manifest.json"
HEALTHY_RESTORE_MANIFEST = "healthy_restore_manifest.json"


def load_f5_config() -> dict:
    return yaml.safe_load(fault_serving_path("f5").read_text(encoding="utf-8"))


def f5_models(f5_cfg: dict) -> tuple[str, str, str, str]:
    model = os.getenv(
        "SFB_F5_MODEL",
        f5_cfg.get("model", {}).get("repo", "Qwen/Qwen2.5-7B-Instruct"),
    )
    revision = os.getenv(
        "SFB_F5_MODEL_REVISION",
        f5_cfg.get("model", {}).get("revision", ""),
    )
    override_source = os.getenv(
        "SFB_F5_OVERRIDE_SOURCE",
        (f5_cfg.get("wrong_generation_defaults") or {}).get("path", "configs/f5_wrong_generation_config.json"),
    )
    served = os.getenv(
        "SFB_F5_SERVED_MODEL_NAME",
        f5_cfg.get("served_model_name", model),
    )
    return model, revision, override_source, served


def load_healthy_baseline() -> dict | None:
    if os.getenv("SFB_CONFIG_PROFILE") == "mistral":
        path = REPO_ROOT / "results" / "mistral-v03" / "healthy-stability-5x" / "campaign_manifest.json"
    else:
        path = REPO_ROOT / "results" / "healthy-stability-120x20-v2" / "campaign_manifest.json"
    if not path.exists():
        return None
    return json.loads(path.read_text(encoding="utf-8"))


def healthy_run1_failures() -> set[str]:
    if os.getenv("SFB_CONFIG_PROFILE") == "mistral":
        path = REPO_ROOT / "results" / "mistral-v03" / "healthy-stability-5x" / "run_01_manifest.json"
    else:
        path = REPO_ROOT / "results" / "healthy-stability-120x20-v2" / "run_01_manifest.json"
    if not path.exists():
        return set()
    return {f["canary_id"] for f in json.loads(path.read_text())["strict_failures"]}


def canary_delta(h_fails: set[str], f_fails: set[str]) -> tuple[list[str], list[str], list[str]]:
    regressions = sorted(f_fails - h_fails)
    recoveries = sorted(h_fails - f_fails)
    stable_fail = sorted(h_fails & f_fails)
    return regressions, recoveries, stable_fail


def evaluate_f5_preflight(
    f5_strict_rate: float,
    f5_fail_ids: set[str],
    f5_cfg: dict,
    healthy: dict | None,
) -> dict[str, Any]:
    h_rate = float(
        (healthy or {}).get("strict_pass_rate_mean")
        or f5_cfg.get("healthy_reference", {}).get("strict_pass_rate_mean")
        or 0.925
    )
    h_fails = healthy_run1_failures()
    regressions, recoveries, stable_fail = canary_delta(h_fails, f5_fail_ids)
    delta_f5 = h_rate - f5_strict_rate
    pf = f5_cfg.get("preflight") or {}
    min_delta = float(pf.get("min_abs_strict_delta", 0.01))
    swaps = len(regressions) + len(recoveries)
    n_regressions = len(regressions)
    directional = delta_f5 > 0 and n_regressions > 0
    if delta_f5 > 0 and n_regressions == 0:
        preflight_note = "No clear directional degradation observed in preflight (pass rate dropped but no regressions)"
    elif delta_f5 > 0 and n_regressions > 0:
        preflight_note = "Directional degradation observed in preflight"
    elif delta_f5 <= 0:
        preflight_note = "No clear directional degradation observed in preflight"
    else:
        preflight_note = "Preflight inconclusive"
    return {
        "delta_F5": delta_f5,
        "healthy_strict_pass_rate": h_rate,
        "f5_strict_pass_rate": f5_strict_rate,
        "regressions": regressions,
        "recoveries": recoveries,
        "stable_failures": stable_fail,
        "canary_swaps": swaps,
        "regression_count": n_regressions,
        "recovery_count": len(recoveries),
        "min_abs_strict_delta": min_delta,
        "directional_degradation": directional,
        "preflight_note": preflight_note,
        "proceed_to_campaign_recommended": directional and abs(delta_f5) >= min_delta,
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
    print(f"\n=== F5 {label} ===", flush=True)
    infra_before = {"api": check_api(base_url)}
    if not infra_before["api"].get("ok"):
        raise RuntimeError("API not reachable")

    during_summary: dict[str, Any] = {}
    if sampler:
        sampler.start()
    t0 = time.perf_counter()
    try:
        summary = run_suite(
            condition="F5-decoding-config-drift",
            temperature=0.0,
            seed=0,
            shuffle=False,
            limit=limit,
            split=split,
            warmup=warmup,
            client=client,
            trust_server_decoding=True,
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
            condition="F5-decoding-config-drift",
            temperature=0.0,
            seed=0,
            shuffle=False,
            limit=limit,
            split=split,
            warmup=False,
            client=client,
            trust_server_decoding=True,
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
    f5_cfg: dict,
    model: str,
    revision: str,
    override_source: str,
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
    client = ServingClient(timeout=180.0, model=served)
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
    evaluation = evaluate_f5_preflight(float(summary["strict_pass_rate"]), fail_ids, f5_cfg, healthy)

    jsonl_path = write_run(summary)
    meta_src = jsonl_path.with_suffix(".meta.json")
    dest_jsonl = out_dir / f"preflight_{summary['run_id']}.jsonl"
    dest_meta = out_dir / f"preflight_{summary['run_id']}.meta.json"
    shutil.copy2(jsonl_path, dest_jsonl)
    shutil.copy2(meta_src, dest_meta)

    manifest: dict[str, Any] = {
        "phase": "preflight",
        "timestamp_utc": datetime.now(timezone.utc).isoformat(),
        "fault_id": "F5",
        "model": model,
        "model_revision": revision,
        "generation_override_source": override_source,
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
        f"\nPreflight delta_F5={evaluation['delta_F5']:+.1%} "
        f"regressions={evaluation['regression_count']} recoveries={evaluation['recovery_count']} "
        f"note={evaluation['preflight_note']}",
        flush=True,
    )
    return manifest


def _load_run_records(rel_path: str) -> list[dict[str, Any]]:
    path = REPO_ROOT / rel_path
    if not path.is_file():
        return []
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def _score_note(record: dict[str, Any]) -> str:
    details = record.get("score_details")
    if details not in (None, ""):
        return str(details).replace("|", "/").replace("\n", " ")[:120]
    return str(record.get("note", "")).replace("|", "/")[:120]


def _healthy_f5_delta(out_dir: Path) -> tuple[list[str], list[str], list[str]]:
    h_fails = healthy_run1_failures()
    if not h_fails:
        return [], [], []
    f5_manifest = out_dir / "run_01_manifest.json"
    if not f5_manifest.exists():
        return sorted(h_fails), [], []
    f_fails = {f["canary_id"] for f in json.loads(f5_manifest.read_text())["strict_failures"]}
    return canary_delta(h_fails, f_fails)


def render_markdown(campaign: dict[str, Any], f5_cfg: dict, healthy: dict | None) -> str:
    runs = campaign["runs"]
    model = campaign.get("model", f5_cfg["model"]["repo"])
    override_source = campaign.get(
        "generation_override_source",
        (f5_cfg.get("wrong_generation_defaults") or {}).get("path", ""),
    )
    revision = campaign.get("model_revision", f5_cfg["model"]["revision"])
    results_dir = Path(REPO_ROOT / campaign["results_dir"])
    iso_path = results_dir / "f5_isolation_manifest.json"
    iso = {}
    if iso_path.is_file():
        iso = json.loads(iso_path.read_text(encoding="utf-8"))

    lines = [
        "# F5 — Decoding-config drift (isolated) · 120 core × 20 server-default passes",
        "",
        f"**Campaign id:** `{campaign['campaign_id']}`",
        f"**Fault:** F5 — wrong server generation defaults at serve time; matched weights + tokenizer",
        f"**Pod:** `{campaign.get('pod_id', '?')}`",
        f"**Model (weights+tokenizer):** `{model}` @ `{revision}`",
        f"**Generation override source:** `{override_source}`",
        f"**Served API model id:** `{campaign.get('served_model_name', model)}`",
        f"**Scorer contract:** `{campaign.get('scorer_contract', 'calibrated-2026-08-10')}`",
        "",
        f"**Raw scores:** `{campaign['results_dir']}`",
        "",
        "> Isolated F5: only vLLM --override-generation-config differs. Weights, tokenizer, and chat template verified identical to healthy.",
        "> Compare per-canary jsonl vs healthy v2 in `results/healthy-stability-120x20-v2/`.",
        "",
    ]
    if iso:
        lines.extend(
            [
                "## F5 isolation gate",
                "",
                f"**Verdict:** {iso.get('verdict', '?')} (isolated={iso.get('isolated')})",
                "",
                "| Check | Result |",
                "|---|---|",
                f"| Checkpoint changed | {iso.get('checkpoint_changed')} |",
                f"| Tokenizer identical to healthy | {iso.get('tokenizer_same_as_healthy')} |",
                f"| Chat template identical to healthy | {iso.get('chat_template_same_as_healthy')} |",
                f"| Token IDs identical to healthy | {iso.get('token_ids_same_as_healthy')} |",
                f"| dtype identical | {iso.get('dtype_same_as_healthy')} |",
                f"| LoRA identical (none) | {iso.get('lora_same_as_healthy')} |",
                "",
                f"**Wrong generation override:** `{iso.get('wrong_generation_override')}`",
                f"**Tokenizer bundle hash:** `{((iso.get('artifact_comparison') or {}).get('bundle_hash_healthy'))}`",
                "",
            ]
        )
    lines.extend(
        [
            "## Protocol",
            "",
            f"- Isolated generation override from `{override_source}` on `{model}` weights+tokenizer+template",
            f"- vLLM `--served-model-name {model}`",
            "- 120 core canaries (SFC-001 … SFC-120), catalog order; client omits temperature/seed (trust_server_decoding)",
            "- Preflight: one deterministic pass before 20× campaign",
            "- Run 1: 5 warmup requests discarded, then 120 measured",
            "- Runs 2–20: 120 measured each (no warmup)",
            "- API health check before each run; GPU sampled every 2s **during** inference; post-run GPU + vLLM `/metrics` scrape",
            "",
        ]
    )
    preflight = campaign.get("preflight")
    if preflight:
        ev = preflight.get("evaluation") or {}
        lines.extend(
            [
                "## Preflight gate",
                "",
                f"**Run id:** `{preflight.get('run_id', '?')}`",
                f"**Note:** {ev.get('preflight_note', '?')}",
                f"**Directional degradation:** {ev.get('directional_degradation')}",
                f"**Recommend 20× campaign:** {ev.get('proceed_to_campaign_recommended')}",
                "",
                "| | |",
                "|---|---|",
                f"| Strict pass rate | {preflight.get('strict_pass_rate', 0):.1%} |",
                f"| Tolerant pass rate | {preflight.get('tolerant_pass_rate', 0):.1%} |",
                f"| HTTP 200 | {preflight.get('http_200', 0)}/{preflight.get('n', 120)} |",
                f"| Wall time | {preflight.get('wall_s', 0):.1f} s |",
                f"| Healthy baseline | {ev.get('healthy_strict_pass_rate', 0):.1%} |",
                f"| delta_F5 (healthy − F5) | {ev.get('delta_F5', 0):+.1%} |",
                f"| Canary swaps | {ev.get('canary_swaps', 0)} |",
                "",
                "| Direction | Canaries |",
                "|---|---|",
                f"| Regressions | {', '.join(ev.get('regressions') or []) or '—'} |",
                f"| Recoveries | {', '.join(ev.get('recoveries') or []) or '—'} |",
                f"| Stable failures | {', '.join(ev.get('stable_failures') or []) or '—'} |",
                "",
            ]
        )
        pf_during = (preflight.get("infra_during") or {}).get("gpu_sampler") or {}
        if pf_during.get("ok"):
            util_mean = pf_during.get("util_gpu_pct_mean")
            util_mean_s = f"{util_mean:.1f}" if isinstance(util_mean, (int, float)) else "—"
            lines.extend(
                [
                    "**GPU during preflight (2s samples):**",
                    f"- samples: {pf_during.get('n_samples')} · util max {pf_during.get('util_gpu_pct_max')}% · "
                    f"util mean {util_mean_s}% · "
                    f"mem last {pf_during.get('memory_used_mib_last')} MiB · temp max {pf_during.get('temperature_c_max')}°C · "
                    f"power max {pf_during.get('power_w_max')} W",
                    "",
                ]
            )
        pf_fails = preflight.get("strict_failures") or []
        if pf_fails:
            lines.append(f"**Preflight strict failures ({len(pf_fails)}):**")
            lines.append("")
            lines.append("| ID | Subtype | Note |")
            lines.append("|---|---|---|")
            for f in pf_fails:
                note = str(f.get("note", "")).replace("|", "/")[:80]
                lines.append(f"| {f['canary_id']} | {f['subtype']} | {note} |")
            lines.append("")
    lines.extend(
        [
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
    )
    if healthy:
        h = healthy.get("strict_pass_rate_mean", 0)
        delta_f5 = h - campaign["strict_pass_rate_mean"]
        lines.extend(
            [
                f"| Healthy baseline (v2 mean) | {h:.1%} |",
                f"| delta_F5 (healthy − F5) | {delta_f5:+.1%} |",
            ]
        )
    regressions, recoveries, stable_fail = _healthy_f5_delta(Path(REPO_ROOT / campaign["results_dir"]))
    if regressions or recoveries:
        lines.extend(
            [
                "",
                "### F5 vs healthy (run 1 strict delta)",
                "",
                "| Direction | Canaries |",
                "|---|---|",
                f"| Regressions (healthy PASS → F5 FAIL) | {', '.join(regressions) or '—'} |",
                f"| Recoveries (healthy FAIL → F5 PASS) | {', '.join(recoveries) or '—'} |",
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
            mem_mean = during.get("memory_used_mib_mean")
            mem_mean_s = f"{mem_mean:.0f}" if isinstance(mem_mean, (int, float)) else "—"
            lines.extend(
                [
                    "**GPU during run (2s samples):**",
                    "",
                    "| Metric | Value |",
                    "|---|---|",
                    f"| samples | {during.get('n_samples')} |",
                    f"| util max % | {during.get('util_gpu_pct_max')} |",
                    f"| util mean % | {util_mean_s} |",
                    f"| mem last MiB | {during.get('memory_used_mib_last')} |",
                    f"| mem mean MiB | {mem_mean_s} |",
                    f"| temp max °C | {during.get('temperature_c_max')} |",
                    f"| power max W | {during.get('power_w_max')} |",
                    "",
                ]
            )
        post_gpu = (r.get("infra_after") or {}).get("gpu") or {}
        if post_gpu.get("gpu"):
            g = post_gpu["gpu"]
            lines.extend(
                [
                    "**GPU snapshot (post-run):**",
                    "",
                    "| Field | Value |",
                    "|---|---|",
                    f"| name | {g.get('name', '—')} |",
                    f"| util_gpu_pct | {g.get('util_gpu_pct')} |",
                    f"| util_mem_pct | {g.get('util_mem_pct')} |",
                    f"| memory_used_mib | {g.get('memory_used_mib')} |",
                    f"| memory_total_mib | {g.get('memory_total_mib')} |",
                    f"| temperature_c | {g.get('temperature_c')} |",
                    f"| power_w | {g.get('power_w')} |",
                    "",
                ]
            )
        metrics = (r.get("infra_after") or {}).get("vllm_metrics") or {}
        if metrics.get("values"):
            lines.append("**vLLM metrics (post-run):**")
            lines.append("")
            lines.append("| Metric | Value |")
            lines.append("|---|---|")
            for k, v in sorted(metrics["values"].items()):
                short = k.removeprefix("vllm:")
                lines.append(f"| `{short}` | {v} |")
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
        rel_jsonl = (r.get("artifacts") or {}).get("results_jsonl")
        records = _load_run_records(rel_jsonl) if rel_jsonl else []
        if records:
            lines.append(f"**All canaries ({len(records)}) — strict / tolerant / score:**")
            lines.append("")
            lines.append("| ID | Subtype | Strict | Tolerant | Score | Note / score_details |")
            lines.append("|---|---|:---:|:---:|---:|---|")
            for rec in records:
                lines.append(
                    f"| {rec['canary_id']} | {rec.get('subtype', '')} | "
                    f"{'PASS' if rec.get('strict_pass') else 'FAIL'} | "
                    f"{'PASS' if rec.get('tolerant_pass') else 'FAIL'} | "
                    f"{rec.get('semantic_score', 0):.2f} | {_score_note(rec)} |"
                )
            lines.append("")

    # Cross-run canary pass matrix
    canary_runs: dict[str, list[bool]] = defaultdict(list)
    canary_meta: dict[str, str] = {}
    for r in runs:
        rel_jsonl = (r.get("artifacts") or {}).get("results_jsonl")
        records = _load_run_records(rel_jsonl) if rel_jsonl else []
        by_id = {rec["canary_id"]: rec for rec in records}
        for cid in sorted(by_id):
            canary_meta.setdefault(cid, by_id[cid].get("subtype", ""))
            canary_runs[cid].append(bool(by_id[cid].get("strict_pass")))

    lines.extend(
        [
            "## Per-canary strict pass frequency (all 120 × 20 runs)",
            "",
            "| ID | Subtype | Pass count | Fail count | Pass rate |",
            "|---|---|---:|---:|---:|",
        ]
    )
    for cid in sorted(canary_runs):
        passes = sum(canary_runs[cid])
        fails_n = len(canary_runs[cid]) - passes
        rate = passes / len(canary_runs[cid]) if canary_runs[cid] else 0.0
        lines.append(f"| {cid} | {canary_meta.get(cid, '')} | {passes} | {fails_n} | {rate:.0%} |")
    lines.extend(
        [
            "",
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
    f5_cfg: dict,
    model: str,
    revision: str,
    override_source: str,
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
    if os.getenv("SFB_CONFIG_PROFILE") == "mistral":
        healthy_ref = "results/mistral-v03/healthy-stability-5x"
    else:
        healthy_ref = "results/healthy-stability-120x20-v2"
    h_mean = healthy.get("strict_pass_rate_mean") if healthy else None
    f_mean = statistics.mean(strict_rates)
    campaign: dict[str, Any] = {
        "campaign_id": existing_id or f"f5-stability-{datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ')}",
        "fault_id": "F5",
        "fault_name": f5_cfg.get("fault_name", "Decoding-config drift"),
        "deployment_kind": "decoding_config_drift_isolated",
        "model": model,
        "model_revision": revision,
        "generation_override_source": override_source,
        "served_model_name": served,
        "pod_id": pod_id,
        "scorer_contract": "calibrated-2026-08-10",
        "healthy_baseline_ref": healthy_ref,
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
        campaign["delta_F5"] = h_mean - f_mean

    preflight_path = out_dir / PREFLIGHT_MANIFEST
    if preflight_path.exists():
        campaign["preflight"] = json.loads(preflight_path.read_text(encoding="utf-8"))

    manifest_path.write_text(json.dumps(campaign, indent=2), encoding="utf-8")
    md_path = REPO_ROOT / "docs" / "F5_DECODING_CONFIG_DRIFT_STABILITY_120x20.md"
    md_path.write_text(render_markdown(campaign, f5_cfg, healthy), encoding="utf-8")
    (out_dir / "README.md").write_text(
        f"# F5 stability 120×20\n\nCampaign `{campaign['campaign_id']}`\n\nSee `docs/F5_DECODING_CONFIG_DRIFT_STABILITY_120x20.md`\n",
        encoding="utf-8",
    )
    return campaign


def main() -> int:
    parser = argparse.ArgumentParser(description="F5 stability campaign — preflight + 120 core × N passes")
    parser.add_argument("--repeats", type=int, default=20)
    parser.add_argument("--limit", type=int, default=120)
    parser.add_argument("--split", default="core")
    parser.add_argument("--out-dir", type=Path, default=DEFAULT_OUT)
    parser.add_argument("--start-run", type=int, default=1)
    parser.add_argument("--preflight-only", action="store_true", help="Run one preflight pass and evaluate effectiveness")
    parser.add_argument("--skip-preflight", action="store_true", help="Skip preflight gate (not recommended)")
    parser.add_argument("--skip-isolation-check", action="store_true", help="Skip f5_isolation_manifest.json gate (not recommended)")
    parser.add_argument("--finalize-only", action="store_true")
    args = parser.parse_args()

    f5_cfg = load_f5_config()
    model, revision, override_source, served = f5_models(f5_cfg)
    args.out_dir = (REPO_ROOT / args.out_dir).resolve() if not args.out_dir.is_absolute() else args.out_dir.resolve()
    pod_id = (os.getenv("SFB_RUNPOD_SSH") or "").split("@")[0].split("-")[0]

    if args.finalize_only:
        finalize_campaign(args.out_dir, args.repeats, pod_id, f5_cfg, model, revision, override_source, served)
        print(f"Wrote {args.out_dir / 'campaign_manifest.json'}")
        return 0

    os.environ["SFB_MODEL"] = model
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
        print("API not reachable. Ensure tunnel + F5 vLLM are running.", file=sys.stderr)
        return 2
    model_ids = api0.get("model_ids") or []
    if model_ids and served not in model_ids:
        print(f"WARNING: expected served model id {served!r}, got {model_ids}", file=sys.stderr)

    if not args.skip_isolation_check:
        iso_path = args.out_dir / ISOLATION_MANIFEST
        if not iso_path.exists():
            print(
                f"Missing {iso_path}. Run: python3 scripts/verify_f5_isolation.py",
                file=sys.stderr,
            )
            return 3
        iso = json.loads(iso_path.read_text(encoding="utf-8"))
        if not iso.get("isolated"):
            print("F5 CANDIDATE REJECTED: CONFOUNDED WITH F2/F3/F4 — isolation gate failed", file=sys.stderr)
            return 3

    preflight_needed = not args.skip_preflight and (
        args.preflight_only or (args.start_run == 1 and not (args.out_dir / PREFLIGHT_MANIFEST).exists())
    )
    if preflight_needed:
        pf = run_preflight(
            out_dir=args.out_dir,
            f5_cfg=f5_cfg,
            model=model,
            revision=revision,
            override_source=override_source,
            served=served,
            pod_id=pod_id,
            limit=args.limit,
            split=args.split,
            base_url=base_url,
            ssh_key=ssh_key,
            tcp_host=tcp_host,
            tcp_port=tcp_port,
        )
        if not pf["evaluation"].get("proceed_to_campaign_recommended"):
            print(
                f"F5 preflight: {pf['evaluation'].get('preflight_note')} — "
                "20-repeat campaign not recommended from one pass alone.",
                file=sys.stderr,
            )
            if args.preflight_only:
                print(f"Wrote {args.out_dir / PREFLIGHT_MANIFEST}")
                return 0
            return 4
        if args.preflight_only:
            print(f"Preflight complete. Wrote {args.out_dir / PREFLIGHT_MANIFEST}")
            return 0

    if args.preflight_only:
        return 0

    campaign_id = f"f5-stability-{datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ')}"
    campaign: dict[str, Any] = {
        "campaign_id": campaign_id,
        "fault_id": "F5",
        "model": model,
        "model_revision": revision,
        "generation_override_source": override_source,
        "n_planned": args.repeats,
        "n_completed": 0,
        "runs": [],
    }

    if args.start_run > 1:
        prior = load_existing_runs(args.out_dir, args.start_run)
        campaign["runs"] = prior
        campaign["n_completed"] = len(prior)
        print(f"Resuming from run {args.start_run} ({len(prior)} prior runs loaded)", flush=True)

    client = ServingClient(timeout=180.0, model=served)
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
            "fault_id": "F5",
            "run_index": i,
            "run_id": summary["run_id"],
            "model": model,
            "model_revision": revision,
            "generation_override_source": override_source,
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

    finalize_campaign(args.out_dir, args.repeats, pod_id, f5_cfg, model, revision, override_source, served, campaign_id)
    print(f"\nWrote {args.out_dir / 'campaign_manifest.json'}")
    return 0 if n == args.repeats else 1


if __name__ == "__main__":
    raise SystemExit(main())
