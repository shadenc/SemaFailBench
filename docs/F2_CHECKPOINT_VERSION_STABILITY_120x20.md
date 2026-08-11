# F2 — Model / checkpoint version regression · 120 core × 20 deterministic passes

**Campaign id:** `f2-stability-20260811T174720Z`
**Fault:** F2 — wrong model-version artifact deployment
**Pod:** `g0uutfrnf83h9v`
**Expected model (logical):** `Qwen/Qwen2.5-7B-Instruct`
**Actual model (loaded):** `Qwen/Qwen2-7B-Instruct` @ `f2826a00ceef68f0f2b946d945ecc0477ce4450c`
**Served API model id:** `Qwen/Qwen2.5-7B-Instruct`
**Scorer contract:** `calibrated-2026-08-10`

**Raw scores:** `results/fault-f2-stability-120x20`

> Compare per-canary jsonl vs healthy v2 in `results/healthy-stability-120x20-v2/`.
> Prior revision-only F2 attempt (`results/fault-f2-stability-120x20/`, Qwen2.5 @ 52e20a6…) was an **invalid artifact selection** — not evidence that F2 has no effect.

## Protocol

- Wrong-version artifact: serve `Qwen/Qwen2-7B-Instruct` with `--served-model-name Qwen/Qwen2.5-7B-Instruct`
- 120 core canaries (SFC-001 … SFC-120), catalog order, temp=0
- Preflight: one deterministic pass; abort 20× if ineffective
- Run 1: 5 warmup requests discarded, then 120 measured
- Runs 2–20: 120 measured each (no warmup)
- API health check before each run; GPU sampled every 2s during inference

## Campaign summary

| | |
|---|---|
| Runs completed | 20 / 20 |
| All HTTP 200 | True |
| Strict pass rate (mean) | **90.8%** |
| Tolerant pass rate (mean) | 92.5% |
| Stability gate | PASS |
| Healthy baseline (v2 mean) | 92.5% |
| delta_F2 (healthy − F2) | +1.7% |

### F2 vs healthy (run 1 strict delta)

| Direction | Canaries |
|---|---|
| Regressions (healthy PASS → F2 FAIL) | SFC-005, SFC-007, SFC-014, SFC-029, SFC-030, SFC-093, SFC-110 |
| Recoveries (healthy FAIL → F2 PASS) | SFC-004, SFC-010, SFC-018, SFC-097, SFC-108 |
| Stable strict failures (both) | SFC-001, SFC-064, SFC-095, SFC-100 |

### Per-run pass rates

| Run | Run id | Strict | Tolerant | HTTP | Wall s | API ok | GPU util max % |
|---|---|---|---|---|---:|---:|---:|
| 01 | `F2-checkpoint-version-20260811T174721Z-626d9012` | 90.8% | 92.5% | 120/120 | 99 | yes | 98.0 |
| 02 | `F2-checkpoint-version-20260811T174906Z-7966fac9` | 90.8% | 92.5% | 120/120 | 95 | yes | 98.0 |
| 03 | `F2-checkpoint-version-20260811T175046Z-b1d411bf` | 90.8% | 92.5% | 120/120 | 94 | yes | 98.0 |
| 04 | `F2-checkpoint-version-20260811T175223Z-88bbbd24` | 90.8% | 92.5% | 120/120 | 93 | yes | 98.0 |
| 05 | `F2-checkpoint-version-20260811T175401Z-08972588` | 90.8% | 92.5% | 120/120 | 95 | yes | 98.0 |
| 06 | `F2-checkpoint-version-20260811T175541Z-e56c20a4` | 90.8% | 92.5% | 120/120 | 95 | yes | 98.0 |
| 07 | `F2-checkpoint-version-20260811T175721Z-e8c65343` | 90.8% | 92.5% | 120/120 | 102 | yes | 98.0 |
| 08 | `F2-checkpoint-version-20260811T175908Z-6e5efaee` | 90.8% | 92.5% | 120/120 | 93 | yes | 98.0 |
| 09 | `F2-checkpoint-version-20260811T180047Z-50dd3150` | 90.8% | 92.5% | 120/120 | 93 | yes | 98.0 |
| 10 | `F2-checkpoint-version-20260811T180222Z-f3495c68` | 90.8% | 92.5% | 120/120 | 93 | yes | 98.0 |
| 11 | `F2-checkpoint-version-20260811T180358Z-6314e780` | 90.8% | 92.5% | 120/120 | 93 | yes | 98.0 |
| 12 | `F2-checkpoint-version-20260811T180535Z-316b8446` | 90.8% | 92.5% | 120/120 | 94 | yes | 98.0 |
| 13 | `F2-checkpoint-version-20260811T180713Z-4b3cb338` | 90.8% | 92.5% | 120/120 | 93 | yes | 98.0 |
| 14 | `F2-checkpoint-version-20260811T180851Z-bed15f20` | 90.8% | 92.5% | 120/120 | 98 | yes | 98.0 |
| 15 | `F2-checkpoint-version-20260811T181034Z-777ba2bf` | 90.8% | 92.5% | 120/120 | 92 | yes | 98.0 |
| 16 | `F2-checkpoint-version-20260811T181209Z-98b25adb` | 90.8% | 92.5% | 120/120 | 92 | yes | 98.0 |
| 17 | `F2-checkpoint-version-20260811T181345Z-b3d441b1` | 90.8% | 92.5% | 120/120 | 93 | yes | 98.0 |
| 18 | `F2-checkpoint-version-20260811T181521Z-87c8b820` | 90.8% | 92.5% | 120/120 | 92 | yes | 98.0 |
| 19 | `F2-checkpoint-version-20260811T181657Z-3065e82b` | 90.8% | 92.5% | 120/120 | 92 | yes | 98.0 |
| 20 | `F2-checkpoint-version-20260811T181833Z-0e384116` | 90.8% | 92.5% | 120/120 | 92 | yes | 98.0 |
