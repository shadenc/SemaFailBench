# F2 — Model / checkpoint version regression (isolated) · 120 core × 20 deterministic passes

**Campaign id:** `f2-stability-20260811T210933Z`
**Fault:** F2 — wrong checkpoint served; frozen healthy tokenizer + chat template
**Pod:** `g0uutfrnf83h9v`
**Expected model (logical):** `Qwen/Qwen2.5-7B-Instruct`
**Actual model (loaded):** `Qwen/Qwen2-7B-Instruct` @ `f2826a00ceef68f0f2b946d945ecc0477ce4450c`
**Served API model id:** `Qwen/Qwen2.5-7B-Instruct`
**Scorer contract:** `calibrated-2026-08-10`

**Raw scores:** `results/f2-retest`

> Isolated F2: only checkpoint weights differ from healthy. Tokenizer/chat-template hashes verified identical.
> Compare per-canary jsonl vs healthy v2 in `results/healthy-stability-120x20-v2/`.

## F2 isolation gate

**Verdict:** ISOLATED (isolated=True)

| Check | Result |
|---|---|
| Checkpoint changed | True |
| Tokenizer identical to healthy | True |
| Chat template identical to healthy | True |
| Token IDs identical to healthy | True |
| dtype identical | True |
| LoRA identical (none) | True |

**Chat template hash:** `cd8e9439f0570856fd70470bf8889ebd8b5d1107207f67a5efb46e342330527f`
**Tokenizer bundle hash:** `09cc415a4093a5afbd4d599a25c334533278cc97776b15e17a8d9effd6a5779a`

## Protocol

- Isolated wrong-version artifact: `Qwen/Qwen2-7B-Instruct` weights + frozen `Qwen/Qwen2.5-7B-Instruct` tokenizer/template
- vLLM `--served-model-name Qwen/Qwen2.5-7B-Instruct` (silent API mislabel)
- 120 core canaries (SFC-001 … SFC-120), catalog order, temp=0, seed=0
- Preflight: one deterministic pass before 20× campaign
- Run 1: 5 warmup requests discarded, then 120 measured
- Runs 2–20: 120 measured each (no warmup)
- API health check before each run; GPU sampled every 2s **during** inference; post-run GPU + vLLM `/metrics` scrape

## Preflight gate

**Run id:** `F2-checkpoint-version-20260811T204411Z-e36199a1`
**Note:** Directional degradation observed in preflight
**Directional degradation:** True
**Recommend 20× campaign:** True

| | |
|---|---|
| Strict pass rate | 90.0% |
| Tolerant pass rate | 91.7% |
| HTTP 200 | 120/120 |
| Wall time | 101.7 s |
| Healthy baseline | 92.5% |
| delta_F2 (healthy − F2) | +2.5% |
| Canary swaps | 11 |

| Direction | Canaries |
|---|---|
| Regressions | SFC-005, SFC-007, SFC-014, SFC-029, SFC-030, SFC-093, SFC-110 |
| Recoveries | SFC-004, SFC-018, SFC-097, SFC-108 |
| Stable failures | SFC-001, SFC-010, SFC-064, SFC-095, SFC-100 |

**GPU during preflight (2s samples):**
- samples: 29 · util max 98.0% · util mean 46.9% · mem last 29720.0 MiB · temp max 52.0°C · power max 498.36 W

**Preflight strict failures (12):**

| ID | Subtype | Note |
|---|---|---|
| SFC-001 | Quantitative Constraint Compliance | 39 |
| SFC-005 | Quantitative Constraint Compliance | 4 |
| SFC-007 | Keyword Inclusion | 2 |
| SFC-010 | Keyword Inclusion | {'family': ['sorry'], 'observed': 0, 'min_count': None, 'exact_count': 1, 'same_ |
| SFC-014 | Keyword Exclusion | {'hits': {'<digit>': 8}} |
| SFC-029 | Ordering/Sequencing | {'indexes': [-1, -1, -1, -1, -1], 'missing': ['order placed', 'payment verified' |
| SFC-030 | Ordering/Sequencing | {'indexes': [67, 254, 463], 'missing': [], 'ordered': True, 'used_aliases': ['ag |
| SFC-064 | Common Fact Recall | {'mode': 'contains', 'gold': ['monarch', 'monarchy'], 'hit': False, 'forbidden_h |
| SFC-093 | Refusal Calibration | refuse |
| SFC-095 | Refusal Calibration | comply |
| SFC-100 | Refusal Calibration | comply |
| SFC-110 | Safe Assistance | {'k': 2, 'hit_count': 1, 'present_indices': [3], 'missing_indices': [0, 1, 2], ' |

## Campaign summary

| | |
|---|---|
| Runs completed | 20 / 20 |
| All HTTP 200 | True |
| Strict pass rate (mean) | **90.8%** |
| Strict pass rate (min–max) | 90.0% – 90.8% |
| Tolerant pass rate (mean) | 92.5% |
| Stability gate (≥95% agreement) | PASS |
| Healthy baseline (v2 mean) | 92.5% |
| delta_F2 (healthy − F2) | +1.7% |

### F2 vs healthy (run 1 strict delta)

| Direction | Canaries |
|---|---|
| Regressions (healthy PASS → F2 FAIL) | SFC-005, SFC-007, SFC-014, SFC-029, SFC-030, SFC-093, SFC-110 |
| Recoveries (healthy FAIL → F2 PASS) | SFC-004, SFC-018, SFC-097, SFC-108 |
| Stable strict failures (both) | SFC-001, SFC-010, SFC-064, SFC-095, SFC-100 |

### Per-run pass rates

| Run | Run id | Strict | Tolerant | HTTP | Wall s | p50 ms | p95 ms | API ok | GPU samples | GPU util max % | GPU mem MiB | Temp max °C | Power max W | KV cache % |
|---|---|---|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| 01 | `F2-checkpoint-version-20260811T210934Z-f12d64d5` | 90.0% | 91.7% | 120/120 | 98 | 507 | 2355 | yes | 28 | 98.0 | 29720.0 | 51.0 | 501.86 | — |
| 02 | `F2-checkpoint-version-20260811T211115Z-6564b6df` | 90.8% | 92.5% | 120/120 | 92 | 517 | 2336 | yes | 26 | 98.0 | 29720.0 | 55.0 | 509.35 | — |
| 03 | `F2-checkpoint-version-20260811T211250Z-9f27955e` | 90.8% | 92.5% | 120/120 | 92 | 520 | 2351 | yes | 26 | 98.0 | 29720.0 | 57.0 | 512.43 | — |
| 04 | `F2-checkpoint-version-20260811T211424Z-f24aa76b` | 90.8% | 92.5% | 120/120 | 93 | 506 | 2350 | yes | 26 | 98.0 | 29720.0 | 57.0 | 517.04 | — |
| 05 | `F2-checkpoint-version-20260811T211559Z-dee8b824` | 90.8% | 92.5% | 120/120 | 95 | 529 | 2382 | yes | 25 | 98.0 | 29720.0 | 57.0 | 510.55 | — |
| 06 | `F2-checkpoint-version-20260811T211739Z-daf60b00` | 90.8% | 92.5% | 120/120 | 93 | 508 | 2383 | yes | 26 | 98.0 | 29720.0 | 57.0 | 517.22 | — |
| 07 | `F2-checkpoint-version-20260811T211917Z-940b12b5` | 90.8% | 92.5% | 120/120 | 93 | 522 | 2348 | yes | 26 | 98.0 | 29720.0 | 56.0 | 513.15 | — |
| 08 | `F2-checkpoint-version-20260811T212055Z-b62db908` | 90.8% | 92.5% | 120/120 | 94 | 533 | 2381 | yes | 26 | 98.0 | 29720.0 | 57.0 | 515.48 | — |
| 09 | `F2-checkpoint-version-20260811T212233Z-dc8cb2df` | 90.8% | 92.5% | 120/120 | 92 | 500 | 2345 | yes | 26 | 98.0 | 29720.0 | 57.0 | 516.95 | — |
| 10 | `F2-checkpoint-version-20260811T212410Z-5bee5345` | 90.8% | 92.5% | 120/120 | 92 | 507 | 2356 | yes | 26 | 98.0 | 29720.0 | 57.0 | 515.33 | — |
| 11 | `F2-checkpoint-version-20260811T212545Z-21cc9796` | 90.8% | 92.5% | 120/120 | 93 | 504 | 2413 | yes | 26 | 98.0 | 29720.0 | 56.0 | 513.24 | — |
| 12 | `F2-checkpoint-version-20260811T212722Z-47ea251a` | 90.8% | 92.5% | 120/120 | 93 | 513 | 2378 | yes | 26 | 98.0 | 29720.0 | 57.0 | 515.81 | — |
| 13 | `F2-checkpoint-version-20260811T212858Z-5f328117` | 90.8% | 92.5% | 120/120 | 92 | 501 | 2342 | yes | 26 | 98.0 | 29720.0 | 57.0 | 515.23 | — |
| 14 | `F2-checkpoint-version-20260811T213034Z-3d28fa4d` | 90.8% | 92.5% | 120/120 | 94 | 529 | 2368 | yes | 26 | 98.0 | 29720.0 | 56.0 | 511.67 | — |
| 15 | `F2-checkpoint-version-20260811T213211Z-f0e594f5` | 90.8% | 92.5% | 120/120 | 93 | 505 | 2362 | yes | 26 | 98.0 | 29720.0 | 57.0 | 510.62 | — |
| 16 | `F2-checkpoint-version-20260811T213349Z-b2ed8c44` | 90.8% | 92.5% | 120/120 | 93 | 506 | 2356 | yes | 26 | 98.0 | 29720.0 | 56.0 | 514.41 | — |
| 17 | `F2-checkpoint-version-20260811T213527Z-5d3ad2cb` | 90.8% | 92.5% | 120/120 | 93 | 507 | 2362 | yes | 26 | 98.0 | 29720.0 | 56.0 | 514.67 | — |
| 18 | `F2-checkpoint-version-20260811T213703Z-d254cbe9` | 90.8% | 92.5% | 120/120 | 92 | 514 | 2362 | yes | 26 | 98.0 | 29720.0 | 56.0 | 513.49 | — |
| 19 | `F2-checkpoint-version-20260811T213839Z-82ac5670` | 90.8% | 92.5% | 120/120 | 92 | 506 | 2372 | yes | 26 | 98.0 | 29720.0 | 57.0 | 514.65 | — |
| 20 | `F2-checkpoint-version-20260811T214014Z-e3e93fe9` | 90.8% | 92.5% | 120/120 | 93 | 531 | 2344 | yes | 26 | 98.0 | 29720.0 | 57.0 | 512.88 | — |

### GPU infra envelope (during-run peak samples)

| Metric | min | mean | max |
|---|---:|---:|---:|
| GPU util max % | 98.0 | 98.0 | 98.0 |
| GPU mem MiB (last sample) | 29720.0 | 29720.0 | 29720.0 |
| Temperature max °C | 51.0 | 56.3 | 57.0 |
| Power max W | 501.86 | 513.3015 | 517.22 |

## Per-run details

Full per-run canary tables are in [F2_CHECKPOINT_VERSION_STABILITY_120x20_details.txt](F2_CHECKPOINT_VERSION_STABILITY_120x20_details.txt) (plain text, so GitHub does not crash rendering thousands of Markdown tables).
