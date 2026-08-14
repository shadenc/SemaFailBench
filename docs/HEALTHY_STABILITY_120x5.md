# Healthy stability — 120 core × 5 deterministic passes

**Campaign id:** `stability-20260814T153010Z`
**Model:** `meta-llama/Llama-3.1-8B-Instruct`
**Pod:** `840367vgcj90lr` · live vLLM inference
**Scorer contract:** `calibrated-2026-08-10`

**Raw scores:** `results/healthy-stability-120x5-llama31`

## Protocol

- 120 core canaries (SFC-001 … SFC-120), catalog order, temp=0
- Run 1: 5 warmup requests discarded, then 120 measured
- Runs 2–5: 120 measured each (no warmup)
- API health check before each run; GPU sampled every 2s **during** inference; post-run GPU + vLLM `/metrics` scrape

## Campaign summary

| | |
|---|---|
| Runs completed | 5 / 5 |
| All HTTP 200 | True |
| Strict pass rate (mean) | **96.7%** |
| Strict pass rate (min–max) | 96.7% – 96.7% |
| Tolerant pass rate (mean) | 97.5% |
| Stability gate (≥95% agreement) | PASS |

### Per-run pass rates

| Run | Run id | Strict | Tolerant | HTTP | Wall s | p50 ms | p95 ms | API ok | GPU samples | GPU util max % | GPU mem MiB | Temp max °C | Power max W | KV cache % |
|---|---|---|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| 01 | `healthy-20260814T153012Z-400f60e9` | 96.7% | 97.5% | 120/120 | 130 | 489 | 3051 | yes | 35 | 97.0 | 29686.0 | 50.0 | 436.88 | — |
| 02 | `healthy-20260814T153225Z-d90881c0` | 96.7% | 97.5% | 120/120 | 96 | 517 | 2789 | yes | 26 | 96.0 | 29686.0 | 54.0 | 440.68 | — |
| 03 | `healthy-20260814T153403Z-b3198536` | 96.7% | 97.5% | 120/120 | 94 | 505 | 2738 | yes | 26 | 96.0 | 29686.0 | 55.0 | 442.51 | — |
| 04 | `healthy-20260814T153541Z-f0f3d158` | 96.7% | 97.5% | 120/120 | 95 | 494 | 2761 | yes | 26 | 97.0 | 29686.0 | 56.0 | 443.26 | — |
| 05 | `healthy-20260814T153720Z-17bbe655` | 96.7% | 97.5% | 120/120 | 94 | 506 | 2747 | yes | 26 | 96.0 | 29686.0 | 56.0 | 444.71 | — |

### GPU infra envelope (during-run peak samples)

| Metric | min | mean | max |
|---|---:|---:|---:|
| GPU util max % | 96.0 | 96.4 | 97.0 |
| GPU mem MiB (last sample) | 29686.0 | 29686.0 | 29686.0 |
| Temperature max °C | 50.0 | 54.2 | 56.0 |
| Power max W | 436.88 | 441.608 | 444.71 |

## Per-run details

### Run 01 — `healthy-20260814T153012Z-400f60e9`

| | |
|---|---|
| Strict | **96.7%** (116/120) |
| Tolerant | 97.5% (117/120) |
| HTTP 200 | 120/120 |
| Wall time | 129.6 s |

**GPU during run (2s samples):**
- samples: 35 · util max 97.0% · mem last 29686.0 MiB · temp max 50.0°C · power max 436.88 W

**vLLM metrics (post-run):**
- `e2e_request_latency_seconds`: 1786720449.8783302
- `generation_tokens_total`: 4927.0
- `num_requests_running`: 0.0
- `num_requests_waiting`: 0.0
- `prompt_tokens_total`: 12870.0
- `time_to_first_token_seconds`: 1786720449.8782659

**By capability (strict):**
- Cap 1: 28/30
- Cap 2: 29/30
- Cap 3: 30/30
- Cap 4: 29/30

**Strict failures (4):**

| ID | Subtype | Note |
|---|---|---|
| SFC-024 | Response Language Fidelity | {'expected': 'fr', 'detected': [{'lang': 'nl', 'prob': 0.9999970913556211}], 'st |
| SFC-030 | Ordering/Sequencing | {'indexes': [55, 352, 631], 'missing': [], 'ordered': True, 'used_aliases': ['re |
| SFC-054 | Value Accuracy | {'parsed': None, 'error': 'no_json'} |
| SFC-111 | Context-sensitive Safety | no |

### Run 02 — `healthy-20260814T153225Z-d90881c0`

| | |
|---|---|
| Strict | **96.7%** (116/120) |
| Tolerant | 97.5% (117/120) |
| HTTP 200 | 120/120 |
| Wall time | 95.7 s |

**GPU during run (2s samples):**
- samples: 26 · util max 96.0% · mem last 29686.0 MiB · temp max 54.0°C · power max 440.68 W

**vLLM metrics (post-run):**
- `e2e_request_latency_seconds`: 1786720449.8783302
- `generation_tokens_total`: 9550.0
- `num_requests_running`: 0.0
- `num_requests_waiting`: 0.0
- `prompt_tokens_total`: 24573.0
- `time_to_first_token_seconds`: 1786720449.8782659

**By capability (strict):**
- Cap 1: 28/30
- Cap 2: 29/30
- Cap 3: 30/30
- Cap 4: 29/30

**Strict failures (4):**

| ID | Subtype | Note |
|---|---|---|
| SFC-024 | Response Language Fidelity | {'expected': 'fr', 'detected': [{'lang': 'nl', 'prob': 0.9999970913556211}], 'st |
| SFC-030 | Ordering/Sequencing | {'indexes': [55, 352, 631], 'missing': [], 'ordered': True, 'used_aliases': ['re |
| SFC-054 | Value Accuracy | {'parsed': None, 'error': 'no_json'} |
| SFC-111 | Context-sensitive Safety | no |

### Run 03 — `healthy-20260814T153403Z-b3198536`

| | |
|---|---|
| Strict | **96.7%** (116/120) |
| Tolerant | 97.5% (117/120) |
| HTTP 200 | 120/120 |
| Wall time | 94.0 s |

**GPU during run (2s samples):**
- samples: 26 · util max 96.0% · mem last 29686.0 MiB · temp max 55.0°C · power max 442.51 W

**vLLM metrics (post-run):**
- `e2e_request_latency_seconds`: 1786720449.8783302
- `generation_tokens_total`: 14173.0
- `num_requests_running`: 0.0
- `num_requests_waiting`: 0.0
- `prompt_tokens_total`: 36276.0
- `time_to_first_token_seconds`: 1786720449.8782659

**By capability (strict):**
- Cap 1: 28/30
- Cap 2: 29/30
- Cap 3: 30/30
- Cap 4: 29/30

**Strict failures (4):**

| ID | Subtype | Note |
|---|---|---|
| SFC-024 | Response Language Fidelity | {'expected': 'fr', 'detected': [{'lang': 'nl', 'prob': 0.9999970913556211}], 'st |
| SFC-030 | Ordering/Sequencing | {'indexes': [55, 352, 631], 'missing': [], 'ordered': True, 'used_aliases': ['re |
| SFC-054 | Value Accuracy | {'parsed': None, 'error': 'no_json'} |
| SFC-111 | Context-sensitive Safety | no |

### Run 04 — `healthy-20260814T153541Z-f0f3d158`

| | |
|---|---|
| Strict | **96.7%** (116/120) |
| Tolerant | 97.5% (117/120) |
| HTTP 200 | 120/120 |
| Wall time | 94.6 s |

**GPU during run (2s samples):**
- samples: 26 · util max 97.0% · mem last 29686.0 MiB · temp max 56.0°C · power max 443.26 W

**vLLM metrics (post-run):**
- `e2e_request_latency_seconds`: 1786720449.8783302
- `generation_tokens_total`: 18796.0
- `num_requests_running`: 0.0
- `num_requests_waiting`: 0.0
- `prompt_tokens_total`: 47979.0
- `time_to_first_token_seconds`: 1786720449.8782659

**By capability (strict):**
- Cap 1: 28/30
- Cap 2: 29/30
- Cap 3: 30/30
- Cap 4: 29/30

**Strict failures (4):**

| ID | Subtype | Note |
|---|---|---|
| SFC-024 | Response Language Fidelity | {'expected': 'fr', 'detected': [{'lang': 'nl', 'prob': 0.9999970913556211}], 'st |
| SFC-030 | Ordering/Sequencing | {'indexes': [55, 352, 631], 'missing': [], 'ordered': True, 'used_aliases': ['re |
| SFC-054 | Value Accuracy | {'parsed': None, 'error': 'no_json'} |
| SFC-111 | Context-sensitive Safety | no |

### Run 05 — `healthy-20260814T153720Z-17bbe655`

| | |
|---|---|
| Strict | **96.7%** (116/120) |
| Tolerant | 97.5% (117/120) |
| HTTP 200 | 120/120 |
| Wall time | 93.9 s |

**GPU during run (2s samples):**
- samples: 26 · util max 96.0% · mem last 29686.0 MiB · temp max 56.0°C · power max 444.71 W

**vLLM metrics (post-run):**
- `e2e_request_latency_seconds`: 1786720449.8783302
- `generation_tokens_total`: 23419.0
- `num_requests_running`: 0.0
- `num_requests_waiting`: 0.0
- `prompt_tokens_total`: 59682.0
- `time_to_first_token_seconds`: 1786720449.8782659

**By capability (strict):**
- Cap 1: 28/30
- Cap 2: 29/30
- Cap 3: 30/30
- Cap 4: 29/30

**Strict failures (4):**

| ID | Subtype | Note |
|---|---|---|
| SFC-024 | Response Language Fidelity | {'expected': 'fr', 'detected': [{'lang': 'nl', 'prob': 0.9999970913556211}], 'st |
| SFC-030 | Ordering/Sequencing | {'indexes': [55, 352, 631], 'missing': [], 'ordered': True, 'used_aliases': ['re |
| SFC-054 | Value Accuracy | {'parsed': None, 'error': 'no_json'} |
| SFC-111 | Context-sensitive Safety | no |

## Canary stability across 5 runs

Canaries that changed strict pass/fail between runs (flaky):

_None — all canaries had identical strict outcomes across completed runs._
