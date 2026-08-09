from __future__ import annotations

import json

import jsonschema

from sem_fail_bench.paths import run_record_schema_path


def test_run_record_schema_accepts_minimal_record():
    schema = json.loads(run_record_schema_path().read_text(encoding="utf-8"))
    record = {
        "run_id": "healthy-test",
        "timestamp_utc": "2026-08-09T00:00:00+00:00",
        "condition": "healthy",
        "condition_regime": "deterministic",
        "canary_id": "SFC-001",
        "capability": "Capability 1: Instruction-following Fidelity",
        "subtype": "Quantitative Constraint Compliance",
        "split": "core",
        "prompt": "Write exactly 25 words.",
        "response": "word " * 25,
        "strict_pass": True,
    }
    jsonschema.validate(record, schema)


def test_run_record_schema_rejects_bad_regime():
    schema = json.loads(run_record_schema_path().read_text(encoding="utf-8"))
    record = {
        "run_id": "x",
        "timestamp_utc": "2026-08-09T00:00:00+00:00",
        "condition": "healthy",
        "condition_regime": "maybe",
        "canary_id": "SFC-001",
        "capability": "IF",
        "subtype": "IF-QC",
        "split": "core",
        "prompt": "p",
        "response": "r",
    }
    try:
        jsonschema.validate(record, schema)
    except jsonschema.ValidationError:
        return
    raise AssertionError("invalid regime should fail")
