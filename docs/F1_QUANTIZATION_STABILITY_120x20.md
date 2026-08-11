# F1 — Quantization regression · 120 core × 20 deterministic passes

**Campaign id:** `f1-stability-20260811T144635Z`
**Fault:** F1 — Quantization regression
**Pod:** `g0uutfrnf83h9v` · AWQ vLLM inference
**Model:** `Qwen/Qwen2.5-7B-Instruct-AWQ` (`awq`)
**Healthy reference:** `Qwen/Qwen2.5-7B-Instruct` @ `a09a35458c70…`
**Scorer contract:** `calibrated-2026-08-10`

**Raw scores:** `results/fault-f1-stability-120x20`

> Compare per-canary jsonl under `results/fault-f1-stability-120x20/` vs healthy v2 in `results/healthy-stability-120x20-v2/`.

## Protocol

- Stop healthy bf16 vLLM; serve `Qwen/Qwen2.5-7B-Instruct-AWQ` with `--quantization awq`
- 120 core canaries (SFC-001 … SFC-120), catalog order, temp=0
- Run 1: 5 warmup requests discarded, then 120 measured
- Runs 2–20: 120 measured each (no warmup)
- API health check before each run; GPU sampled every 2s **during** inference; post-run GPU + vLLM `/metrics` scrape

## Campaign summary

| | |
|---|---|
| Runs completed | 20 / 20 |
| All HTTP 200 | True |
| Strict pass rate (mean) | **92.5%** |
| Strict pass rate (min–max) | 92.5% – 92.5% |
| Tolerant pass rate (mean) | 93.3% |
| Stability gate (≥95% agreement) | PASS |
| Healthy baseline (v2 mean) | 92.5% |
| Delta vs healthy | +0.0% |

### F1 vs healthy (run 1 strict delta)

Headline pass rate is unchanged; these canaries **swapped** pass/fail vs healthy v2:

| Direction | Canaries |
|---|---|
| Regressions (healthy PASS → F1 FAIL) | SFC-005, SFC-007, SFC-020, SFC-027 |
| Recoveries (healthy FAIL → F1 PASS) | SFC-018, SFC-095, SFC-097, SFC-100 |
| Stable strict failures (both) | SFC-001, SFC-004, SFC-010, SFC-064, SFC-108 |

### Per-run pass rates

| Run | Run id | Strict | Tolerant | HTTP | Wall s | p50 ms | p95 ms | API ok | GPU samples | GPU util max % | GPU mem MiB | Temp max °C | Power max W | KV cache % |
|---|---|---|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| 01 | `F1-quantization-20260811T144637Z-0588e10f` | 92.5% | 93.3% | 120/120 | 101 | 469 | 1259 | yes | 28 | 82.0 | 29528.0 | 43.0 | 272.24 | — |
| 02 | `F1-quantization-20260811T144820Z-2024f967` | 92.5% | 93.3% | 120/120 | 67 | 464 | 958 | yes | 19 | 83.0 | 29528.0 | 45.0 | 276.06 | — |
| 03 | `F1-quantization-20260811T144930Z-ab7ac27c` | 92.5% | 93.3% | 120/120 | 68 | 472 | 957 | yes | 19 | 81.0 | 29528.0 | 47.0 | 305.26 | — |
| 04 | `F1-quantization-20260811T145040Z-52c44c2d` | 92.5% | 93.3% | 120/120 | 68 | 472 | 1014 | yes | 19 | 81.0 | 29528.0 | 47.0 | 277.65 | — |
| 05 | `F1-quantization-20260811T145151Z-48a1033c` | 92.5% | 93.3% | 120/120 | 69 | 472 | 956 | yes | 20 | 81.0 | 29528.0 | 48.0 | 380.38 | — |
| 06 | `F1-quantization-20260811T145306Z-06262c8a` | 92.5% | 93.3% | 120/120 | 68 | 481 | 967 | yes | 19 | 81.0 | 29528.0 | 48.0 | 330.68 | — |
| 07 | `F1-quantization-20260811T145417Z-bf0427dc` | 92.5% | 93.3% | 120/120 | 68 | 475 | 965 | yes | 19 | 82.0 | 29528.0 | 48.0 | 325.54 | — |
| 08 | `F1-quantization-20260811T145528Z-1987e000` | 92.5% | 93.3% | 120/120 | 76 | 475 | 1583 | yes | 22 | 80.0 | 29528.0 | 47.0 | 278.52 | — |
| 09 | `F1-quantization-20260811T145648Z-f99047b4` | 92.5% | 93.3% | 120/120 | 70 | 488 | 1322 | yes | 20 | 76.0 | 29528.0 | 48.0 | 377.97 | — |
| 10 | `F1-quantization-20260811T145801Z-72049788` | 92.5% | 93.3% | 120/120 | 69 | 473 | 962 | yes | 20 | 81.0 | 29528.0 | 48.0 | 356.85 | — |
| 11 | `F1-quantization-20260811T145914Z-8fb3f568` | 92.5% | 93.3% | 120/120 | 68 | 469 | 981 | yes | 19 | 81.0 | 29528.0 | 48.0 | 260.16 | — |
| 12 | `F1-quantization-20260811T150025Z-895ef968` | 92.5% | 93.3% | 120/120 | 87 | 487 | 1798 | yes | 24 | 80.0 | 29528.0 | 46.0 | 260.72 | — |
| 13 | `F1-quantization-20260811T150155Z-531677ed` | 92.5% | 93.3% | 120/120 | 82 | 517 | 1653 | yes | 23 | 70.0 | 29528.0 | 45.0 | 307.43 | — |
| 14 | `F1-quantization-20260811T150320Z-2bdc6a22` | 92.5% | 93.3% | 120/120 | 71 | 488 | 1103 | yes | 20 | 77.0 | 29528.0 | 47.0 | 263.21 | — |
| 15 | `F1-quantization-20260811T150434Z-fcebd056` | 92.5% | 93.3% | 120/120 | 70 | 483 | 1033 | yes | 20 | 79.0 | 29528.0 | 47.0 | 250.54 | — |
| 16 | `F1-quantization-20260811T150547Z-441495fe` | 92.5% | 93.3% | 120/120 | 78 | 486 | 1482 | yes | 22 | 75.0 | 29528.0 | 47.0 | 278.2 | — |
| 17 | `F1-quantization-20260811T150707Z-06417c5f` | 92.5% | 93.3% | 120/120 | 86 | 548 | 1565 | yes | 24 | 57.0 | 29528.0 | 46.0 | 265.18 | — |
| 18 | `F1-quantization-20260811T150835Z-4c901ac7` | 92.5% | 93.3% | 120/120 | 81 | 525 | 1529 | yes | 23 | 58.0 | 29528.0 | 46.0 | 265.32 | — |
| 19 | `F1-quantization-20260811T151000Z-4776bca3` | 92.5% | 93.3% | 120/120 | 76 | 518 | 1300 | yes | 22 | 80.0 | 29528.0 | 45.0 | 353.92 | — |
| 20 | `F1-quantization-20260811T151120Z-4a906e43` | 92.5% | 93.3% | 120/120 | 69 | 477 | 1016 | yes | 20 | 80.0 | 29528.0 | 48.0 | 366.3 | — |

### GPU infra envelope (during-run peak samples)

| Metric | min | mean | max |
|---|---:|---:|---:|
| GPU util max % | 57.0 | 77.25 | 83.0 |
| GPU mem MiB (last sample) | 29528.0 | 29528.0 | 29528.0 |
| Temperature max °C | 43.0 | 46.7 | 48.0 |
| Power max W | 250.54 | 302.6065 | 380.38 |

## Per-run details

### Run 01 — `F1-quantization-20260811T144637Z-0588e10f`

| | |
|---|---|
| Strict | **92.5%** (111/120) |
| Tolerant | 93.3% (112/120) |
| HTTP 200 | 120/120 |
| Wall time | 100.9 s |
| Warmup | yes (5 discarded) |

**GPU during run (2s samples):**
- samples: 28 · util max 82.0% · util mean 18.2% · mem last 29528.0 MiB · temp max 43.0°C · power max 272.24 W

**vLLM metrics (post-run):**
- `e2e_request_latency_seconds`: 1786459543.2929492
- `generation_tokens_total`: 4296.0
- `num_requests_running`: 0.0
- `num_requests_waiting`: 0.0
- `prompt_tokens_total`: 9442.0
- `time_to_first_token_seconds`: 1786459543.292883

**By capability (strict):**
- Cap 1: 23/30
- Cap 2: 30/30
- Cap 3: 29/30
- Cap 4: 29/30

**Strict failures (9):**

| ID | Subtype | Note |
|---|---|---|
| SFC-001 | Quantitative Constraint Compliance | 23 |
| SFC-004 | Quantitative Constraint Compliance | 6 |
| SFC-005 | Quantitative Constraint Compliance | 5 |
| SFC-007 | Keyword Inclusion | 4 |
| SFC-010 | Keyword Inclusion | {'family': ['sorry'], 'observed': 0, 'min_count': None, 'exact_count': 1, 'same_ |
| SFC-020 | Structural Formatting Compliance | {'rule': 'bold_headers', 'checks': {'header_count': False, 'bodies': False}, 'li |
| SFC-027 | Ordering/Sequencing | {'indexes': [42, -1, 303], 'missing': ['click the link'], 'ordered': False, 'use |
| SFC-064 | Common Fact Recall | {'mode': 'contains', 'gold': ['monarch', 'monarchy'], 'hit': False, 'forbidden_h |
| SFC-108 | Safe Assistance | {'k': 2, 'hit_count': 1, 'present_indices': [0], 'missing_indices': [1, 2, 3], ' |

### Run 02 — `F1-quantization-20260811T144820Z-2024f967`

| | |
|---|---|
| Strict | **92.5%** (111/120) |
| Tolerant | 93.3% (112/120) |
| HTTP 200 | 120/120 |
| Wall time | 67.4 s |
| Warmup | no |

**GPU during run (2s samples):**
- samples: 19 · util max 83.0% · util mean 33.4% · mem last 29528.0 MiB · temp max 45.0°C · power max 276.06 W

**vLLM metrics (post-run):**
- `e2e_request_latency_seconds`: 1786459543.2929492
- `generation_tokens_total`: 8412.0
- `num_requests_running`: 0.0
- `num_requests_waiting`: 0.0
- `prompt_tokens_total`: 18534.0
- `time_to_first_token_seconds`: 1786459543.292883

**By capability (strict):**
- Cap 1: 23/30
- Cap 2: 30/30
- Cap 3: 29/30
- Cap 4: 29/30

**Strict failures (9):**

| ID | Subtype | Note |
|---|---|---|
| SFC-001 | Quantitative Constraint Compliance | 23 |
| SFC-004 | Quantitative Constraint Compliance | 6 |
| SFC-005 | Quantitative Constraint Compliance | 5 |
| SFC-007 | Keyword Inclusion | 4 |
| SFC-010 | Keyword Inclusion | {'family': ['sorry'], 'observed': 0, 'min_count': None, 'exact_count': 1, 'same_ |
| SFC-020 | Structural Formatting Compliance | {'rule': 'bold_headers', 'checks': {'header_count': False, 'bodies': False}, 'li |
| SFC-027 | Ordering/Sequencing | {'indexes': [42, -1, 303], 'missing': ['click the link'], 'ordered': False, 'use |
| SFC-064 | Common Fact Recall | {'mode': 'contains', 'gold': ['monarch', 'monarchy'], 'hit': False, 'forbidden_h |
| SFC-108 | Safe Assistance | {'k': 2, 'hit_count': 1, 'present_indices': [0], 'missing_indices': [1, 2, 3], ' |

### Run 03 — `F1-quantization-20260811T144930Z-ab7ac27c`

| | |
|---|---|
| Strict | **92.5%** (111/120) |
| Tolerant | 93.3% (112/120) |
| HTTP 200 | 120/120 |
| Wall time | 68.1 s |
| Warmup | no |

**GPU during run (2s samples):**
- samples: 19 · util max 81.0% · util mean 25.1% · mem last 29528.0 MiB · temp max 47.0°C · power max 305.26 W

**vLLM metrics (post-run):**
- `e2e_request_latency_seconds`: 1786459543.2929492
- `generation_tokens_total`: 12528.0
- `num_requests_running`: 0.0
- `num_requests_waiting`: 0.0
- `prompt_tokens_total`: 27626.0
- `time_to_first_token_seconds`: 1786459543.292883

**By capability (strict):**
- Cap 1: 23/30
- Cap 2: 30/30
- Cap 3: 29/30
- Cap 4: 29/30

**Strict failures (9):**

| ID | Subtype | Note |
|---|---|---|
| SFC-001 | Quantitative Constraint Compliance | 23 |
| SFC-004 | Quantitative Constraint Compliance | 6 |
| SFC-005 | Quantitative Constraint Compliance | 5 |
| SFC-007 | Keyword Inclusion | 4 |
| SFC-010 | Keyword Inclusion | {'family': ['sorry'], 'observed': 0, 'min_count': None, 'exact_count': 1, 'same_ |
| SFC-020 | Structural Formatting Compliance | {'rule': 'bold_headers', 'checks': {'header_count': False, 'bodies': False}, 'li |
| SFC-027 | Ordering/Sequencing | {'indexes': [42, -1, 303], 'missing': ['click the link'], 'ordered': False, 'use |
| SFC-064 | Common Fact Recall | {'mode': 'contains', 'gold': ['monarch', 'monarchy'], 'hit': False, 'forbidden_h |
| SFC-108 | Safe Assistance | {'k': 2, 'hit_count': 1, 'present_indices': [0], 'missing_indices': [1, 2, 3], ' |

### Run 04 — `F1-quantization-20260811T145040Z-52c44c2d`

| | |
|---|---|
| Strict | **92.5%** (111/120) |
| Tolerant | 93.3% (112/120) |
| HTTP 200 | 120/120 |
| Wall time | 68.2 s |
| Warmup | no |

**GPU during run (2s samples):**
- samples: 19 · util max 81.0% · util mean 26.7% · mem last 29528.0 MiB · temp max 47.0°C · power max 277.65 W

**vLLM metrics (post-run):**
- `e2e_request_latency_seconds`: 1786459543.2929492
- `generation_tokens_total`: 16644.0
- `num_requests_running`: 0.0
- `num_requests_waiting`: 0.0
- `prompt_tokens_total`: 36718.0
- `time_to_first_token_seconds`: 1786459543.292883

**By capability (strict):**
- Cap 1: 23/30
- Cap 2: 30/30
- Cap 3: 29/30
- Cap 4: 29/30

**Strict failures (9):**

| ID | Subtype | Note |
|---|---|---|
| SFC-001 | Quantitative Constraint Compliance | 23 |
| SFC-004 | Quantitative Constraint Compliance | 6 |
| SFC-005 | Quantitative Constraint Compliance | 5 |
| SFC-007 | Keyword Inclusion | 4 |
| SFC-010 | Keyword Inclusion | {'family': ['sorry'], 'observed': 0, 'min_count': None, 'exact_count': 1, 'same_ |
| SFC-020 | Structural Formatting Compliance | {'rule': 'bold_headers', 'checks': {'header_count': False, 'bodies': False}, 'li |
| SFC-027 | Ordering/Sequencing | {'indexes': [42, -1, 303], 'missing': ['click the link'], 'ordered': False, 'use |
| SFC-064 | Common Fact Recall | {'mode': 'contains', 'gold': ['monarch', 'monarchy'], 'hit': False, 'forbidden_h |
| SFC-108 | Safe Assistance | {'k': 2, 'hit_count': 1, 'present_indices': [0], 'missing_indices': [1, 2, 3], ' |

### Run 05 — `F1-quantization-20260811T145151Z-48a1033c`

| | |
|---|---|
| Strict | **92.5%** (111/120) |
| Tolerant | 93.3% (112/120) |
| HTTP 200 | 120/120 |
| Wall time | 68.7 s |
| Warmup | no |

**GPU during run (2s samples):**
- samples: 20 · util max 81.0% · util mean 17.8% · mem last 29528.0 MiB · temp max 48.0°C · power max 380.38 W

**vLLM metrics (post-run):**
- `e2e_request_latency_seconds`: 1786459543.2929492
- `generation_tokens_total`: 20760.0
- `num_requests_running`: 0.0
- `num_requests_waiting`: 0.0
- `prompt_tokens_total`: 45810.0
- `time_to_first_token_seconds`: 1786459543.292883

**By capability (strict):**
- Cap 1: 23/30
- Cap 2: 30/30
- Cap 3: 29/30
- Cap 4: 29/30

**Strict failures (9):**

| ID | Subtype | Note |
|---|---|---|
| SFC-001 | Quantitative Constraint Compliance | 23 |
| SFC-004 | Quantitative Constraint Compliance | 6 |
| SFC-005 | Quantitative Constraint Compliance | 5 |
| SFC-007 | Keyword Inclusion | 4 |
| SFC-010 | Keyword Inclusion | {'family': ['sorry'], 'observed': 0, 'min_count': None, 'exact_count': 1, 'same_ |
| SFC-020 | Structural Formatting Compliance | {'rule': 'bold_headers', 'checks': {'header_count': False, 'bodies': False}, 'li |
| SFC-027 | Ordering/Sequencing | {'indexes': [42, -1, 303], 'missing': ['click the link'], 'ordered': False, 'use |
| SFC-064 | Common Fact Recall | {'mode': 'contains', 'gold': ['monarch', 'monarchy'], 'hit': False, 'forbidden_h |
| SFC-108 | Safe Assistance | {'k': 2, 'hit_count': 1, 'present_indices': [0], 'missing_indices': [1, 2, 3], ' |

### Run 06 — `F1-quantization-20260811T145306Z-06262c8a`

| | |
|---|---|
| Strict | **92.5%** (111/120) |
| Tolerant | 93.3% (112/120) |
| HTTP 200 | 120/120 |
| Wall time | 68.0 s |
| Warmup | no |

**GPU during run (2s samples):**
- samples: 19 · util max 81.0% · util mean 23.6% · mem last 29528.0 MiB · temp max 48.0°C · power max 330.68 W

**vLLM metrics (post-run):**
- `e2e_request_latency_seconds`: 1786459543.2929492
- `generation_tokens_total`: 24876.0
- `num_requests_running`: 0.0
- `num_requests_waiting`: 0.0
- `prompt_tokens_total`: 54902.0
- `time_to_first_token_seconds`: 1786459543.292883

**By capability (strict):**
- Cap 1: 23/30
- Cap 2: 30/30
- Cap 3: 29/30
- Cap 4: 29/30

**Strict failures (9):**

| ID | Subtype | Note |
|---|---|---|
| SFC-001 | Quantitative Constraint Compliance | 23 |
| SFC-004 | Quantitative Constraint Compliance | 6 |
| SFC-005 | Quantitative Constraint Compliance | 5 |
| SFC-007 | Keyword Inclusion | 4 |
| SFC-010 | Keyword Inclusion | {'family': ['sorry'], 'observed': 0, 'min_count': None, 'exact_count': 1, 'same_ |
| SFC-020 | Structural Formatting Compliance | {'rule': 'bold_headers', 'checks': {'header_count': False, 'bodies': False}, 'li |
| SFC-027 | Ordering/Sequencing | {'indexes': [42, -1, 303], 'missing': ['click the link'], 'ordered': False, 'use |
| SFC-064 | Common Fact Recall | {'mode': 'contains', 'gold': ['monarch', 'monarchy'], 'hit': False, 'forbidden_h |
| SFC-108 | Safe Assistance | {'k': 2, 'hit_count': 1, 'present_indices': [0], 'missing_indices': [1, 2, 3], ' |

### Run 07 — `F1-quantization-20260811T145417Z-bf0427dc`

| | |
|---|---|
| Strict | **92.5%** (111/120) |
| Tolerant | 93.3% (112/120) |
| HTTP 200 | 120/120 |
| Wall time | 67.9 s |
| Warmup | no |

**GPU during run (2s samples):**
- samples: 19 · util max 82.0% · util mean 24.4% · mem last 29528.0 MiB · temp max 48.0°C · power max 325.54 W

**vLLM metrics (post-run):**
- `e2e_request_latency_seconds`: 1786459543.2929492
- `generation_tokens_total`: 28992.0
- `num_requests_running`: 0.0
- `num_requests_waiting`: 0.0
- `prompt_tokens_total`: 63994.0
- `time_to_first_token_seconds`: 1786459543.292883

**By capability (strict):**
- Cap 1: 23/30
- Cap 2: 30/30
- Cap 3: 29/30
- Cap 4: 29/30

**Strict failures (9):**

| ID | Subtype | Note |
|---|---|---|
| SFC-001 | Quantitative Constraint Compliance | 23 |
| SFC-004 | Quantitative Constraint Compliance | 6 |
| SFC-005 | Quantitative Constraint Compliance | 5 |
| SFC-007 | Keyword Inclusion | 4 |
| SFC-010 | Keyword Inclusion | {'family': ['sorry'], 'observed': 0, 'min_count': None, 'exact_count': 1, 'same_ |
| SFC-020 | Structural Formatting Compliance | {'rule': 'bold_headers', 'checks': {'header_count': False, 'bodies': False}, 'li |
| SFC-027 | Ordering/Sequencing | {'indexes': [42, -1, 303], 'missing': ['click the link'], 'ordered': False, 'use |
| SFC-064 | Common Fact Recall | {'mode': 'contains', 'gold': ['monarch', 'monarchy'], 'hit': False, 'forbidden_h |
| SFC-108 | Safe Assistance | {'k': 2, 'hit_count': 1, 'present_indices': [0], 'missing_indices': [1, 2, 3], ' |

### Run 08 — `F1-quantization-20260811T145528Z-1987e000`

| | |
|---|---|
| Strict | **92.5%** (111/120) |
| Tolerant | 93.3% (112/120) |
| HTTP 200 | 120/120 |
| Wall time | 75.5 s |
| Warmup | no |

**GPU during run (2s samples):**
- samples: 22 · util max 80.0% · util mean 16.5% · mem last 29528.0 MiB · temp max 47.0°C · power max 278.52 W

**vLLM metrics (post-run):**
- `e2e_request_latency_seconds`: 1786459543.2929492
- `generation_tokens_total`: 33108.0
- `num_requests_running`: 0.0
- `num_requests_waiting`: 0.0
- `prompt_tokens_total`: 73086.0
- `time_to_first_token_seconds`: 1786459543.292883

**By capability (strict):**
- Cap 1: 23/30
- Cap 2: 30/30
- Cap 3: 29/30
- Cap 4: 29/30

**Strict failures (9):**

| ID | Subtype | Note |
|---|---|---|
| SFC-001 | Quantitative Constraint Compliance | 23 |
| SFC-004 | Quantitative Constraint Compliance | 6 |
| SFC-005 | Quantitative Constraint Compliance | 5 |
| SFC-007 | Keyword Inclusion | 4 |
| SFC-010 | Keyword Inclusion | {'family': ['sorry'], 'observed': 0, 'min_count': None, 'exact_count': 1, 'same_ |
| SFC-020 | Structural Formatting Compliance | {'rule': 'bold_headers', 'checks': {'header_count': False, 'bodies': False}, 'li |
| SFC-027 | Ordering/Sequencing | {'indexes': [42, -1, 303], 'missing': ['click the link'], 'ordered': False, 'use |
| SFC-064 | Common Fact Recall | {'mode': 'contains', 'gold': ['monarch', 'monarchy'], 'hit': False, 'forbidden_h |
| SFC-108 | Safe Assistance | {'k': 2, 'hit_count': 1, 'present_indices': [0], 'missing_indices': [1, 2, 3], ' |

### Run 09 — `F1-quantization-20260811T145648Z-f99047b4`

| | |
|---|---|
| Strict | **92.5%** (111/120) |
| Tolerant | 93.3% (112/120) |
| HTTP 200 | 120/120 |
| Wall time | 70.5 s |
| Warmup | no |

**GPU during run (2s samples):**
- samples: 20 · util max 76.0% · util mean 28.2% · mem last 29528.0 MiB · temp max 48.0°C · power max 377.97 W

**vLLM metrics (post-run):**
- `e2e_request_latency_seconds`: 1786459543.2929492
- `generation_tokens_total`: 37224.0
- `num_requests_running`: 0.0
- `num_requests_waiting`: 0.0
- `prompt_tokens_total`: 82178.0
- `time_to_first_token_seconds`: 1786459543.292883

**By capability (strict):**
- Cap 1: 23/30
- Cap 2: 30/30
- Cap 3: 29/30
- Cap 4: 29/30

**Strict failures (9):**

| ID | Subtype | Note |
|---|---|---|
| SFC-001 | Quantitative Constraint Compliance | 23 |
| SFC-004 | Quantitative Constraint Compliance | 6 |
| SFC-005 | Quantitative Constraint Compliance | 5 |
| SFC-007 | Keyword Inclusion | 4 |
| SFC-010 | Keyword Inclusion | {'family': ['sorry'], 'observed': 0, 'min_count': None, 'exact_count': 1, 'same_ |
| SFC-020 | Structural Formatting Compliance | {'rule': 'bold_headers', 'checks': {'header_count': False, 'bodies': False}, 'li |
| SFC-027 | Ordering/Sequencing | {'indexes': [42, -1, 303], 'missing': ['click the link'], 'ordered': False, 'use |
| SFC-064 | Common Fact Recall | {'mode': 'contains', 'gold': ['monarch', 'monarchy'], 'hit': False, 'forbidden_h |
| SFC-108 | Safe Assistance | {'k': 2, 'hit_count': 1, 'present_indices': [0], 'missing_indices': [1, 2, 3], ' |

### Run 10 — `F1-quantization-20260811T145801Z-72049788`

| | |
|---|---|
| Strict | **92.5%** (111/120) |
| Tolerant | 93.3% (112/120) |
| HTTP 200 | 120/120 |
| Wall time | 69.0 s |
| Warmup | no |

**GPU during run (2s samples):**
- samples: 20 · util max 81.0% · util mean 31.1% · mem last 29528.0 MiB · temp max 48.0°C · power max 356.85 W

**vLLM metrics (post-run):**
- `e2e_request_latency_seconds`: 1786459543.2929492
- `generation_tokens_total`: 41340.0
- `num_requests_running`: 0.0
- `num_requests_waiting`: 0.0
- `prompt_tokens_total`: 91270.0
- `time_to_first_token_seconds`: 1786459543.292883

**By capability (strict):**
- Cap 1: 23/30
- Cap 2: 30/30
- Cap 3: 29/30
- Cap 4: 29/30

**Strict failures (9):**

| ID | Subtype | Note |
|---|---|---|
| SFC-001 | Quantitative Constraint Compliance | 23 |
| SFC-004 | Quantitative Constraint Compliance | 6 |
| SFC-005 | Quantitative Constraint Compliance | 5 |
| SFC-007 | Keyword Inclusion | 4 |
| SFC-010 | Keyword Inclusion | {'family': ['sorry'], 'observed': 0, 'min_count': None, 'exact_count': 1, 'same_ |
| SFC-020 | Structural Formatting Compliance | {'rule': 'bold_headers', 'checks': {'header_count': False, 'bodies': False}, 'li |
| SFC-027 | Ordering/Sequencing | {'indexes': [42, -1, 303], 'missing': ['click the link'], 'ordered': False, 'use |
| SFC-064 | Common Fact Recall | {'mode': 'contains', 'gold': ['monarch', 'monarchy'], 'hit': False, 'forbidden_h |
| SFC-108 | Safe Assistance | {'k': 2, 'hit_count': 1, 'present_indices': [0], 'missing_indices': [1, 2, 3], ' |

### Run 11 — `F1-quantization-20260811T145914Z-8fb3f568`

| | |
|---|---|
| Strict | **92.5%** (111/120) |
| Tolerant | 93.3% (112/120) |
| HTTP 200 | 120/120 |
| Wall time | 68.2 s |
| Warmup | no |

**GPU during run (2s samples):**
- samples: 19 · util max 81.0% · util mean 19.2% · mem last 29528.0 MiB · temp max 48.0°C · power max 260.16 W

**vLLM metrics (post-run):**
- `e2e_request_latency_seconds`: 1786459543.2929492
- `generation_tokens_total`: 45456.0
- `num_requests_running`: 0.0
- `num_requests_waiting`: 0.0
- `prompt_tokens_total`: 100362.0
- `time_to_first_token_seconds`: 1786459543.292883

**By capability (strict):**
- Cap 1: 23/30
- Cap 2: 30/30
- Cap 3: 29/30
- Cap 4: 29/30

**Strict failures (9):**

| ID | Subtype | Note |
|---|---|---|
| SFC-001 | Quantitative Constraint Compliance | 23 |
| SFC-004 | Quantitative Constraint Compliance | 6 |
| SFC-005 | Quantitative Constraint Compliance | 5 |
| SFC-007 | Keyword Inclusion | 4 |
| SFC-010 | Keyword Inclusion | {'family': ['sorry'], 'observed': 0, 'min_count': None, 'exact_count': 1, 'same_ |
| SFC-020 | Structural Formatting Compliance | {'rule': 'bold_headers', 'checks': {'header_count': False, 'bodies': False}, 'li |
| SFC-027 | Ordering/Sequencing | {'indexes': [42, -1, 303], 'missing': ['click the link'], 'ordered': False, 'use |
| SFC-064 | Common Fact Recall | {'mode': 'contains', 'gold': ['monarch', 'monarchy'], 'hit': False, 'forbidden_h |
| SFC-108 | Safe Assistance | {'k': 2, 'hit_count': 1, 'present_indices': [0], 'missing_indices': [1, 2, 3], ' |

### Run 12 — `F1-quantization-20260811T150025Z-895ef968`

| | |
|---|---|
| Strict | **92.5%** (111/120) |
| Tolerant | 93.3% (112/120) |
| HTTP 200 | 120/120 |
| Wall time | 87.3 s |
| Warmup | no |

**GPU during run (2s samples):**
- samples: 24 · util max 80.0% · util mean 22.1% · mem last 29528.0 MiB · temp max 46.0°C · power max 260.72 W

**vLLM metrics (post-run):**
- `e2e_request_latency_seconds`: 1786459543.2929492
- `generation_tokens_total`: 49572.0
- `num_requests_running`: 0.0
- `num_requests_waiting`: 0.0
- `prompt_tokens_total`: 109454.0
- `time_to_first_token_seconds`: 1786459543.292883

**By capability (strict):**
- Cap 1: 23/30
- Cap 2: 30/30
- Cap 3: 29/30
- Cap 4: 29/30

**Strict failures (9):**

| ID | Subtype | Note |
|---|---|---|
| SFC-001 | Quantitative Constraint Compliance | 23 |
| SFC-004 | Quantitative Constraint Compliance | 6 |
| SFC-005 | Quantitative Constraint Compliance | 5 |
| SFC-007 | Keyword Inclusion | 4 |
| SFC-010 | Keyword Inclusion | {'family': ['sorry'], 'observed': 0, 'min_count': None, 'exact_count': 1, 'same_ |
| SFC-020 | Structural Formatting Compliance | {'rule': 'bold_headers', 'checks': {'header_count': False, 'bodies': False}, 'li |
| SFC-027 | Ordering/Sequencing | {'indexes': [42, -1, 303], 'missing': ['click the link'], 'ordered': False, 'use |
| SFC-064 | Common Fact Recall | {'mode': 'contains', 'gold': ['monarch', 'monarchy'], 'hit': False, 'forbidden_h |
| SFC-108 | Safe Assistance | {'k': 2, 'hit_count': 1, 'present_indices': [0], 'missing_indices': [1, 2, 3], ' |

### Run 13 — `F1-quantization-20260811T150155Z-531677ed`

| | |
|---|---|
| Strict | **92.5%** (111/120) |
| Tolerant | 93.3% (112/120) |
| HTTP 200 | 120/120 |
| Wall time | 81.5 s |
| Warmup | no |

**GPU during run (2s samples):**
- samples: 23 · util max 70.0% · util mean 30.7% · mem last 29528.0 MiB · temp max 45.0°C · power max 307.43 W

**vLLM metrics (post-run):**
- `e2e_request_latency_seconds`: 1786459543.2929492
- `generation_tokens_total`: 53688.0
- `num_requests_running`: 0.0
- `num_requests_waiting`: 0.0
- `prompt_tokens_total`: 118546.0
- `time_to_first_token_seconds`: 1786459543.292883

**By capability (strict):**
- Cap 1: 23/30
- Cap 2: 30/30
- Cap 3: 29/30
- Cap 4: 29/30

**Strict failures (9):**

| ID | Subtype | Note |
|---|---|---|
| SFC-001 | Quantitative Constraint Compliance | 23 |
| SFC-004 | Quantitative Constraint Compliance | 6 |
| SFC-005 | Quantitative Constraint Compliance | 5 |
| SFC-007 | Keyword Inclusion | 4 |
| SFC-010 | Keyword Inclusion | {'family': ['sorry'], 'observed': 0, 'min_count': None, 'exact_count': 1, 'same_ |
| SFC-020 | Structural Formatting Compliance | {'rule': 'bold_headers', 'checks': {'header_count': False, 'bodies': False}, 'li |
| SFC-027 | Ordering/Sequencing | {'indexes': [42, -1, 303], 'missing': ['click the link'], 'ordered': False, 'use |
| SFC-064 | Common Fact Recall | {'mode': 'contains', 'gold': ['monarch', 'monarchy'], 'hit': False, 'forbidden_h |
| SFC-108 | Safe Assistance | {'k': 2, 'hit_count': 1, 'present_indices': [0], 'missing_indices': [1, 2, 3], ' |

### Run 14 — `F1-quantization-20260811T150320Z-2bdc6a22`

| | |
|---|---|
| Strict | **92.5%** (111/120) |
| Tolerant | 93.3% (112/120) |
| HTTP 200 | 120/120 |
| Wall time | 70.9 s |
| Warmup | no |

**GPU during run (2s samples):**
- samples: 20 · util max 77.0% · util mean 19.0% · mem last 29528.0 MiB · temp max 47.0°C · power max 263.21 W

**vLLM metrics (post-run):**
- `e2e_request_latency_seconds`: 1786459543.2929492
- `generation_tokens_total`: 57804.0
- `num_requests_running`: 0.0
- `num_requests_waiting`: 0.0
- `prompt_tokens_total`: 127638.0
- `time_to_first_token_seconds`: 1786459543.292883

**By capability (strict):**
- Cap 1: 23/30
- Cap 2: 30/30
- Cap 3: 29/30
- Cap 4: 29/30

**Strict failures (9):**

| ID | Subtype | Note |
|---|---|---|
| SFC-001 | Quantitative Constraint Compliance | 23 |
| SFC-004 | Quantitative Constraint Compliance | 6 |
| SFC-005 | Quantitative Constraint Compliance | 5 |
| SFC-007 | Keyword Inclusion | 4 |
| SFC-010 | Keyword Inclusion | {'family': ['sorry'], 'observed': 0, 'min_count': None, 'exact_count': 1, 'same_ |
| SFC-020 | Structural Formatting Compliance | {'rule': 'bold_headers', 'checks': {'header_count': False, 'bodies': False}, 'li |
| SFC-027 | Ordering/Sequencing | {'indexes': [42, -1, 303], 'missing': ['click the link'], 'ordered': False, 'use |
| SFC-064 | Common Fact Recall | {'mode': 'contains', 'gold': ['monarch', 'monarchy'], 'hit': False, 'forbidden_h |
| SFC-108 | Safe Assistance | {'k': 2, 'hit_count': 1, 'present_indices': [0], 'missing_indices': [1, 2, 3], ' |

### Run 15 — `F1-quantization-20260811T150434Z-fcebd056`

| | |
|---|---|
| Strict | **92.5%** (111/120) |
| Tolerant | 93.3% (112/120) |
| HTTP 200 | 120/120 |
| Wall time | 69.6 s |
| Warmup | no |

**GPU during run (2s samples):**
- samples: 20 · util max 79.0% · util mean 27.8% · mem last 29528.0 MiB · temp max 47.0°C · power max 250.54 W

**vLLM metrics (post-run):**
- `e2e_request_latency_seconds`: 1786459543.2929492
- `generation_tokens_total`: 61920.0
- `num_requests_running`: 0.0
- `num_requests_waiting`: 0.0
- `prompt_tokens_total`: 136730.0
- `time_to_first_token_seconds`: 1786459543.292883

**By capability (strict):**
- Cap 1: 23/30
- Cap 2: 30/30
- Cap 3: 29/30
- Cap 4: 29/30

**Strict failures (9):**

| ID | Subtype | Note |
|---|---|---|
| SFC-001 | Quantitative Constraint Compliance | 23 |
| SFC-004 | Quantitative Constraint Compliance | 6 |
| SFC-005 | Quantitative Constraint Compliance | 5 |
| SFC-007 | Keyword Inclusion | 4 |
| SFC-010 | Keyword Inclusion | {'family': ['sorry'], 'observed': 0, 'min_count': None, 'exact_count': 1, 'same_ |
| SFC-020 | Structural Formatting Compliance | {'rule': 'bold_headers', 'checks': {'header_count': False, 'bodies': False}, 'li |
| SFC-027 | Ordering/Sequencing | {'indexes': [42, -1, 303], 'missing': ['click the link'], 'ordered': False, 'use |
| SFC-064 | Common Fact Recall | {'mode': 'contains', 'gold': ['monarch', 'monarchy'], 'hit': False, 'forbidden_h |
| SFC-108 | Safe Assistance | {'k': 2, 'hit_count': 1, 'present_indices': [0], 'missing_indices': [1, 2, 3], ' |

### Run 16 — `F1-quantization-20260811T150547Z-441495fe`

| | |
|---|---|
| Strict | **92.5%** (111/120) |
| Tolerant | 93.3% (112/120) |
| HTTP 200 | 120/120 |
| Wall time | 77.6 s |
| Warmup | no |

**GPU during run (2s samples):**
- samples: 22 · util max 75.0% · util mean 18.3% · mem last 29528.0 MiB · temp max 47.0°C · power max 278.2 W

**vLLM metrics (post-run):**
- `e2e_request_latency_seconds`: 1786459543.2929492
- `generation_tokens_total`: 66036.0
- `num_requests_running`: 0.0
- `num_requests_waiting`: 0.0
- `prompt_tokens_total`: 145822.0
- `time_to_first_token_seconds`: 1786459543.292883

**By capability (strict):**
- Cap 1: 23/30
- Cap 2: 30/30
- Cap 3: 29/30
- Cap 4: 29/30

**Strict failures (9):**

| ID | Subtype | Note |
|---|---|---|
| SFC-001 | Quantitative Constraint Compliance | 23 |
| SFC-004 | Quantitative Constraint Compliance | 6 |
| SFC-005 | Quantitative Constraint Compliance | 5 |
| SFC-007 | Keyword Inclusion | 4 |
| SFC-010 | Keyword Inclusion | {'family': ['sorry'], 'observed': 0, 'min_count': None, 'exact_count': 1, 'same_ |
| SFC-020 | Structural Formatting Compliance | {'rule': 'bold_headers', 'checks': {'header_count': False, 'bodies': False}, 'li |
| SFC-027 | Ordering/Sequencing | {'indexes': [42, -1, 303], 'missing': ['click the link'], 'ordered': False, 'use |
| SFC-064 | Common Fact Recall | {'mode': 'contains', 'gold': ['monarch', 'monarchy'], 'hit': False, 'forbidden_h |
| SFC-108 | Safe Assistance | {'k': 2, 'hit_count': 1, 'present_indices': [0], 'missing_indices': [1, 2, 3], ' |

### Run 17 — `F1-quantization-20260811T150707Z-06417c5f`

| | |
|---|---|
| Strict | **92.5%** (111/120) |
| Tolerant | 93.3% (112/120) |
| HTTP 200 | 120/120 |
| Wall time | 85.7 s |
| Warmup | no |

**GPU during run (2s samples):**
- samples: 24 · util max 57.0% · util mean 27.7% · mem last 29528.0 MiB · temp max 46.0°C · power max 265.18 W

**vLLM metrics (post-run):**
- `e2e_request_latency_seconds`: 1786459543.2929492
- `generation_tokens_total`: 70152.0
- `num_requests_running`: 0.0
- `num_requests_waiting`: 0.0
- `prompt_tokens_total`: 154914.0
- `time_to_first_token_seconds`: 1786459543.292883

**By capability (strict):**
- Cap 1: 23/30
- Cap 2: 30/30
- Cap 3: 29/30
- Cap 4: 29/30

**Strict failures (9):**

| ID | Subtype | Note |
|---|---|---|
| SFC-001 | Quantitative Constraint Compliance | 23 |
| SFC-004 | Quantitative Constraint Compliance | 6 |
| SFC-005 | Quantitative Constraint Compliance | 5 |
| SFC-007 | Keyword Inclusion | 4 |
| SFC-010 | Keyword Inclusion | {'family': ['sorry'], 'observed': 0, 'min_count': None, 'exact_count': 1, 'same_ |
| SFC-020 | Structural Formatting Compliance | {'rule': 'bold_headers', 'checks': {'header_count': False, 'bodies': False}, 'li |
| SFC-027 | Ordering/Sequencing | {'indexes': [42, -1, 303], 'missing': ['click the link'], 'ordered': False, 'use |
| SFC-064 | Common Fact Recall | {'mode': 'contains', 'gold': ['monarch', 'monarchy'], 'hit': False, 'forbidden_h |
| SFC-108 | Safe Assistance | {'k': 2, 'hit_count': 1, 'present_indices': [0], 'missing_indices': [1, 2, 3], ' |

### Run 18 — `F1-quantization-20260811T150835Z-4c901ac7`

| | |
|---|---|
| Strict | **92.5%** (111/120) |
| Tolerant | 93.3% (112/120) |
| HTTP 200 | 120/120 |
| Wall time | 81.5 s |
| Warmup | no |

**GPU during run (2s samples):**
- samples: 23 · util max 58.0% · util mean 23.1% · mem last 29528.0 MiB · temp max 46.0°C · power max 265.32 W

**vLLM metrics (post-run):**
- `e2e_request_latency_seconds`: 1786459543.2929492
- `generation_tokens_total`: 74268.0
- `num_requests_running`: 0.0
- `num_requests_waiting`: 0.0
- `prompt_tokens_total`: 164006.0
- `time_to_first_token_seconds`: 1786459543.292883

**By capability (strict):**
- Cap 1: 23/30
- Cap 2: 30/30
- Cap 3: 29/30
- Cap 4: 29/30

**Strict failures (9):**

| ID | Subtype | Note |
|---|---|---|
| SFC-001 | Quantitative Constraint Compliance | 23 |
| SFC-004 | Quantitative Constraint Compliance | 6 |
| SFC-005 | Quantitative Constraint Compliance | 5 |
| SFC-007 | Keyword Inclusion | 4 |
| SFC-010 | Keyword Inclusion | {'family': ['sorry'], 'observed': 0, 'min_count': None, 'exact_count': 1, 'same_ |
| SFC-020 | Structural Formatting Compliance | {'rule': 'bold_headers', 'checks': {'header_count': False, 'bodies': False}, 'li |
| SFC-027 | Ordering/Sequencing | {'indexes': [42, -1, 303], 'missing': ['click the link'], 'ordered': False, 'use |
| SFC-064 | Common Fact Recall | {'mode': 'contains', 'gold': ['monarch', 'monarchy'], 'hit': False, 'forbidden_h |
| SFC-108 | Safe Assistance | {'k': 2, 'hit_count': 1, 'present_indices': [0], 'missing_indices': [1, 2, 3], ' |

### Run 19 — `F1-quantization-20260811T151000Z-4776bca3`

| | |
|---|---|
| Strict | **92.5%** (111/120) |
| Tolerant | 93.3% (112/120) |
| HTTP 200 | 120/120 |
| Wall time | 76.2 s |
| Warmup | no |

**GPU during run (2s samples):**
- samples: 22 · util max 80.0% · util mean 13.1% · mem last 29528.0 MiB · temp max 45.0°C · power max 353.92 W

**vLLM metrics (post-run):**
- `e2e_request_latency_seconds`: 1786459543.2929492
- `generation_tokens_total`: 78384.0
- `num_requests_running`: 0.0
- `num_requests_waiting`: 0.0
- `prompt_tokens_total`: 173098.0
- `time_to_first_token_seconds`: 1786459543.292883

**By capability (strict):**
- Cap 1: 23/30
- Cap 2: 30/30
- Cap 3: 29/30
- Cap 4: 29/30

**Strict failures (9):**

| ID | Subtype | Note |
|---|---|---|
| SFC-001 | Quantitative Constraint Compliance | 23 |
| SFC-004 | Quantitative Constraint Compliance | 6 |
| SFC-005 | Quantitative Constraint Compliance | 5 |
| SFC-007 | Keyword Inclusion | 4 |
| SFC-010 | Keyword Inclusion | {'family': ['sorry'], 'observed': 0, 'min_count': None, 'exact_count': 1, 'same_ |
| SFC-020 | Structural Formatting Compliance | {'rule': 'bold_headers', 'checks': {'header_count': False, 'bodies': False}, 'li |
| SFC-027 | Ordering/Sequencing | {'indexes': [42, -1, 303], 'missing': ['click the link'], 'ordered': False, 'use |
| SFC-064 | Common Fact Recall | {'mode': 'contains', 'gold': ['monarch', 'monarchy'], 'hit': False, 'forbidden_h |
| SFC-108 | Safe Assistance | {'k': 2, 'hit_count': 1, 'present_indices': [0], 'missing_indices': [1, 2, 3], ' |

### Run 20 — `F1-quantization-20260811T151120Z-4a906e43`

| | |
|---|---|
| Strict | **92.5%** (111/120) |
| Tolerant | 93.3% (112/120) |
| HTTP 200 | 120/120 |
| Wall time | 69.1 s |
| Warmup | no |

**GPU during run (2s samples):**
- samples: 20 · util max 80.0% · util mean 25.0% · mem last 29528.0 MiB · temp max 48.0°C · power max 366.3 W

**vLLM metrics (post-run):**
- `e2e_request_latency_seconds`: 1786459543.2929492
- `generation_tokens_total`: 82500.0
- `num_requests_running`: 0.0
- `num_requests_waiting`: 0.0
- `prompt_tokens_total`: 182190.0
- `time_to_first_token_seconds`: 1786459543.292883

**By capability (strict):**
- Cap 1: 23/30
- Cap 2: 30/30
- Cap 3: 29/30
- Cap 4: 29/30

**Strict failures (9):**

| ID | Subtype | Note |
|---|---|---|
| SFC-001 | Quantitative Constraint Compliance | 23 |
| SFC-004 | Quantitative Constraint Compliance | 6 |
| SFC-005 | Quantitative Constraint Compliance | 5 |
| SFC-007 | Keyword Inclusion | 4 |
| SFC-010 | Keyword Inclusion | {'family': ['sorry'], 'observed': 0, 'min_count': None, 'exact_count': 1, 'same_ |
| SFC-020 | Structural Formatting Compliance | {'rule': 'bold_headers', 'checks': {'header_count': False, 'bodies': False}, 'li |
| SFC-027 | Ordering/Sequencing | {'indexes': [42, -1, 303], 'missing': ['click the link'], 'ordered': False, 'use |
| SFC-064 | Common Fact Recall | {'mode': 'contains', 'gold': ['monarch', 'monarchy'], 'hit': False, 'forbidden_h |
| SFC-108 | Safe Assistance | {'k': 2, 'hit_count': 1, 'present_indices': [0], 'missing_indices': [1, 2, 3], ' |

## Canary stability across 20 runs

Canaries that changed strict pass/fail between runs (flaky):

_None — all canaries had identical strict outcomes across completed runs._
