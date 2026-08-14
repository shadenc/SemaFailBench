from __future__ import annotations

import json
import random
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from sem_fail_bench.catalog import load_canaries, load_serving_config
from sem_fail_bench.client import ServingClient
from sem_fail_bench.hash_utils import sha256_json
from sem_fail_bench.paths import OUTPUTS, REPO_ROOT
from sem_fail_bench.provenance import snapshot_hashes
from sem_fail_bench.scorers import score_canary


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def run_suite(
    *,
    condition: str = "healthy",
    temperature: float = 0.0,
    seed: int | None = 0,
    shuffle: bool = True,
    limit: int | None = None,
    subtype: str | None = None,
    split: str | None = None,
    capability: str | None = None,
    client: ServingClient | None = None,
    dry_run: bool = False,
    warmup: bool = False,
    trust_server_decoding: bool = False,
    exclude_canary_ids: set[str] | frozenset[str] | None = None,
) -> dict[str, Any]:
    catalog = load_canaries()
    serving = load_serving_config()
    canaries = list(catalog["canaries"])
    if split:
        canaries = [c for c in canaries if c.get("split") == split]
    if subtype:
        canaries = [c for c in canaries if c["subtype"] == subtype or c.get("subtype_slug") == subtype]
    if capability:
        canaries = [
            c
            for c in canaries
            if c["capability"] == capability or c.get("capability_code") == capability
        ]
    if shuffle:
        random.Random(seed or 0).shuffle(canaries)
    if limit:
        canaries = canaries[:limit]
    if exclude_canary_ids:
        canaries = [c for c in canaries if c["id"] not in exclude_canary_ids]

    client = client or ServingClient()
    system_prompt = serving.get("system_prompt", "")
    run_id = f"{condition}-{datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ')}-{uuid.uuid4().hex[:8]}"
    records: list[dict[str, Any]] = []
    regime = (
        "server-defaults"
        if trust_server_decoding
        else ("deterministic" if temperature == 0 else "stochastic")
    )
    max_new = int(serving.get("max_new_tokens", 256))
    warmup_n = int(serving.get("warmup_requests", 5)) if warmup else 0

    if warmup_n and not dry_run and canaries:
        for _ in range(warmup_n):
            client.chat(
                canaries[0]["prompt"],
                temperature=temperature,
                top_p=None if temperature == 0 else serving.get("generation", {}).get("stochastic", {}).get("top_p", 0.9),
                max_tokens=max_new,
                seed=seed,
                system_prompt=system_prompt or None,
                trust_server_decoding=trust_server_decoding,
            )

    stochastic_cfg = serving.get("generation", {}).get("stochastic", {})
    for canary in canaries:
        max_tokens = int(canary.get("max_tokens") or max_new)
        if dry_run:
            completion = {"response": "", "http_status": None, "latency_ms": None}
            score = {"strict_pass": None, "tolerant_pass": None, "semantic_score": None, "details": None}
        else:
            completion = client.chat(
                canary["prompt"],
                temperature=temperature,
                top_p=None if temperature == 0 else stochastic_cfg.get("top_p", 0.9),
                max_tokens=max_tokens,
                seed=seed,
                system_prompt=system_prompt or None,
                trust_server_decoding=trust_server_decoding,
            )
            score = score_canary(canary, completion.get("response") or "")
        records.append(
            {
                "run_id": run_id,
                "timestamp_utc": utc_now(),
                "condition": condition,
                "condition_regime": regime,
                "canary_id": canary["id"],
                "capability": canary["capability"],
                "subtype": canary["subtype"],
                "split": canary.get("split", "core"),
                "prompt_version": catalog.get("suite_version"),
                "prompt": canary["prompt"],
                "response": completion.get("response"),
                "expected_answer": canary.get("expected_behavior"),
                "http_status": completion.get("http_status"),
                "latency_ms": completion.get("latency_ms"),
                "strict_pass": score.get("strict_pass"),
                "tolerant_pass": score.get("tolerant_pass"),
                "semantic_score": score.get("semantic_score"),
                "score_details": score.get("details"),
                "temperature": None if trust_server_decoding else temperature,
                "seed": None if trust_server_decoding else seed,
                "trust_server_decoding": trust_server_decoding,
                # Record the model actually requested by the client. Fault runs
                # intentionally override SFB_MODEL while serving.yaml remains
                # the frozen healthy reference.
                "model_id": client.model,
                "canary_suite_version": catalog.get("suite_version"),
            }
        )

    fault_id = condition.split("-", 1)[0].upper()
    fault_config = REPO_ROOT / "configs" / f"serving_{fault_id.lower()}.yaml"
    extra_files = [fault_config] if fault_id.startswith("F") and fault_config.is_file() else []
    hashes = snapshot_hashes(
        extra_files=extra_files,
        extra_objects={
            "suite_version": catalog.get("suite_version"),
            "condition": condition,
            "requested_model": client.model,
        },
    )
    summary = {
        "run_id": run_id,
        "condition": condition,
        "condition_regime": regime,
        "n": len(records),
        "strict_pass_rate": _rate(records, "strict_pass"),
        "tolerant_pass_rate": _rate(records, "tolerant_pass"),
        "config_hash": hashes["bundle"],
        "artifact_hashes": hashes,
        "catalog_hash": sha256_json([c["id"] for c in canaries]),
        "records": records,
    }
    return summary


def write_run(summary: dict[str, Any], out_dir: Path | None = None) -> Path:
    out_dir = out_dir or (OUTPUTS / "runs")
    out_dir.mkdir(parents=True, exist_ok=True)
    path = out_dir / f"{summary['run_id']}.jsonl"
    with open(path, "w", encoding="utf-8") as fh:
        for record in summary["records"]:
            fh.write(json.dumps(record, ensure_ascii=False) + "\n")
    meta = path.with_suffix(".meta.json")
    meta.write_text(
        json.dumps({k: v for k, v in summary.items() if k != "records"}, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )
    return path


def _rate(records: list[dict[str, Any]], field: str) -> float | None:
    values = [r[field] for r in records if r.get(field) is not None]
    if not values:
        return None
    return sum(1 for v in values if v) / len(values)
