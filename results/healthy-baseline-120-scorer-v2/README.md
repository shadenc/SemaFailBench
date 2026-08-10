# Healthy baseline — first 120 core canaries (scorer v2)

Run id: `healthy-20260810T095450Z-59cb186f`

| File | What it is |
|---|---|
| `healthy-20260810T095450Z-59cb186f.jsonl` | One row per canary (SFC-001 … SFC-120), calibrated scores |
| `healthy-20260810T095450Z-59cb186f.meta.json` | Pass rates + config hashes |

**Scorer contract:** `calibrated-2026-08-10` (see `docs/SCORER_CONTRACT.md`)

**Responses:** same model outputs as `healthy-20260810T082058Z-3369eb0d`; only scoring changed after JSON-unwrap, comma-list normalize, meta-decline, and evasive-empty fixes.

Condition: healthy, deterministic (`temperature=0`, no faults).  
Strict pass rate: **92.5%** (111/120). Tolerant: **93.3%** (112/120).

**Read first:** `docs/HEALTHY_BASELINE_120_SCORER_V2.md`

Search fails in the jsonl: `"strict_pass": false`
