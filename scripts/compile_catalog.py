#!/usr/bin/env python3
"""Compile frozen v3 CSV canaries + explicit scorer specs into configs/canaries_v3.yaml."""

from __future__ import annotations

import csv
import re
import sys
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from sem_fail_bench.paths import canaries_path, core_canaries_csv, held_out_csv  # noqa: E402
from sem_fail_bench.scorer_specs import (  # noqa: E402
    CAPABILITY_CODE,
    SCORER_SPECS,
    SUBTYPE_SLUG,
    spec_for,
)

FAULT_RE = re.compile(r"\bF[1-8]\b")


def _read_csv(path: Path) -> list[dict[str, str]]:
    with path.open(encoding="utf-8", newline="") as fh:
        return list(csv.DictReader(fh))


def _hypothesized_faults(text: str) -> list[str]:
    return sorted(set(FAULT_RE.findall(text or "")))


def _item_from_core(row: dict[str, str]) -> dict:
    cid = row["Prompt ID"].strip()
    capability = row["Capability"].strip()
    subtype = row["Subtype"].strip()
    return {
        "id": cid,
        "split": "core",
        "capability": capability,
        "capability_code": CAPABILITY_CODE[capability],
        "subtype": subtype,
        "subtype_slug": SUBTYPE_SLUG[subtype],
        "difficulty": row.get("Difficulty") or None,
        "difficulty_status": row.get("Difficulty Status") or None,
        "prompt": row["Prompt"].strip(),
        "expected_behavior": row["Expected Behavior"].strip(),
        "primary_assertion": (row.get("Primary Assertion") or "").strip() or None,
        "fixture_conditions": (row.get("Fixture Conditions") or "").strip() or None,
        "reason_for_inclusion": (row.get("Reason for Inclusion") or "").strip() or None,
        "primary_semantic_behavior": (row.get("Primary Semantic Behavior") or "").strip() or None,
        "hypothesized_faults": _hypothesized_faults(row.get("Faults Potentially Sensitive To") or ""),
        "hypothesized_faults_raw": (row.get("Faults Potentially Sensitive To") or "").strip() or None,
        "source_rationale": (row.get("Source / Design Rationale") or "").strip() or None,
        "revision_status": (row.get("Revision Status") or "").strip() or None,
        "revision_note": (row.get("Revision Note") or "").strip() or None,
        "scorer": spec_for(cid),
    }


def _item_from_held(row: dict[str, str]) -> dict:
    cid = row["Prompt ID"].strip()
    capability = row["Capability"].strip()
    subtype = row["Subtype"].strip()
    return {
        "id": cid,
        "split": "held_out",
        "capability": capability,
        "capability_code": CAPABILITY_CODE[capability],
        "subtype": subtype,
        "subtype_slug": SUBTYPE_SLUG[subtype],
        "difficulty": None,
        "difficulty_status": None,
        "prompt": row["Prompt"].strip(),
        "expected_behavior": row["Expected Behavior"].strip(),
        "primary_assertion": None,
        "fixture_conditions": None,
        "reason_for_inclusion": (row.get("What Makes It Held-Out") or "").strip() or None,
        "primary_semantic_behavior": None,
        "hypothesized_faults": [],
        "hypothesized_faults_raw": None,
        "source_rationale": None,
        "revision_status": None,
        "revision_note": None,
        "scorer": spec_for(cid),
    }


def main() -> int:
    core_rows = _read_csv(core_canaries_csv())
    held_rows = _read_csv(held_out_csv())
    core_ids = [r["Prompt ID"].strip() for r in core_rows]
    held_ids = [r["Prompt ID"].strip() for r in held_rows]

    missing_specs = [cid for cid in core_ids + held_ids if cid not in SCORER_SPECS]
    extra_specs = sorted(set(SCORER_SPECS) - set(core_ids) - set(held_ids))
    if missing_specs or extra_specs:
        raise SystemExit(
            f"scorer spec mismatch: missing={missing_specs} extra={extra_specs}"
        )
    if len(core_ids) != 150 or len(set(core_ids)) != 150:
        raise SystemExit(f"Core_Canaries must have 150 unique IDs, got {len(core_ids)}")
    if len(held_ids) != 24 or len(set(held_ids)) != 24:
        raise SystemExit(f"Held_Out must have 24 unique IDs, got {len(held_ids)}")

    canaries = [_item_from_core(r) for r in core_rows] + [_item_from_held(r) for r in held_rows]
    payload = {
        "suite_version": "v3-frozen",
        "source_workbook": "SemaFailBench_Final_Canary_Dataset_v3_FROZEN.xlsx",
        "source_csv": {
            "core": str(core_canaries_csv().relative_to(ROOT)),
            "held_out": str(held_out_csv().relative_to(ROOT)),
        },
        "n_core": 150,
        "n_held_out": 24,
        "n_total": 174,
        "notes": [
            "Scorer dicts are explicit contracts compiled from Expected Behavior + Prompt.",
            "Fault mappings on core items are hypothesized only, not empirical.",
            "Cap 5 items embed context in the prompt; no live retriever is required to score.",
            "Retrieval faults (old F6/F7) were deleted. Cap 5 stays; context is in-prompt.",
        ],
        "canaries": canaries,
    }
    out = canaries_path()
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(
        yaml.safe_dump(payload, sort_keys=False, allow_unicode=True, width=120),
        encoding="utf-8",
    )
    print(f"wrote {out.relative_to(ROOT)}  n={len(canaries)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
