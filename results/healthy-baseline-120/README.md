# Healthy baseline — first 120 core canaries

Run id: `healthy-20260810T082058Z-3369eb0d`

| File | What it is |
|---|---|
| `healthy-20260810T082058Z-3369eb0d.jsonl` | One row per canary (SFC-001 … SFC-120) |
| `healthy-20260810T082058Z-3369eb0d.meta.json` | Pass rates + config hashes |

Condition: healthy, deterministic (`temperature=0`, no faults).  
Strict pass rate: **90.0%** (108/120). Tolerant: **90.8%** (109/120).

Search fails in the jsonl: `"strict_pass": false`
