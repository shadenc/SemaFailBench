# F4 — Chat-template mismatch (isolated) · 120 core × 20 deterministic passes

**Campaign id:** `f4-stability-20260812T162402Z`
**Fault:** F4 — wrong chat template at serve time; matched weights + tokenizer
**Pod:** `2pr0ssumaq3ue4`
**Model (weights+tokenizer):** `Qwen/Qwen2.5-7B-Instruct` @ `a09a35458c702b33eeacc393d103063234e8bc28`
**Wrong template source:** `local:no_assistant_gen_prompt`
**Served API model id:** `Qwen/Qwen2.5-7B-Instruct`
**Scorer contract:** `calibrated-2026-08-10`

**Raw scores:** `results/f4-retest`

> Isolated F4: only vLLM --chat-template differs. Weights and tokenizer files verified identical to healthy.
> Compare per-canary jsonl vs healthy v2 in `results/healthy-stability-120x20-v2/`.

## F4 isolation gate

**Verdict:** ? (isolated=True)

| Check | Result |
|---|---|
| Checkpoint changed | None |
| Tokenizer identical to healthy | None |
| Chat template identical to healthy | None |
| Token IDs identical to healthy | None |
| dtype identical | True |
| LoRA identical (none) | True |

**Chat template hash:** `cd8e9439f0570856fd70470bf8889ebd8b5d1107207f67a5efb46e342330527f`
**Tokenizer bundle hash:** `09cc415a4093a5afbd4d599a25c334533278cc97776b15e17a8d9effd6a5779a`

## Protocol

- Isolated wrong chat template from `local:no_assistant_gen_prompt` on `Qwen/Qwen2.5-7B-Instruct` weights+tokenizer
- vLLM `--served-model-name Qwen/Qwen2.5-7B-Instruct`
- 120 core canaries (SFC-001 … SFC-120), catalog order, temp=0, seed=0
- Preflight: one deterministic pass before 20× campaign
- Run 1: 5 warmup requests discarded, then 120 measured
- Runs 2–20: 120 measured each (no warmup)
- API health check before each run; GPU sampled every 2s **during** inference; post-run GPU + vLLM `/metrics` scrape

## Preflight gate

**Run id:** `F4-chat-template-mismatch-20260812T161958Z-f95b623d`
**Note:** Directional degradation observed in preflight
**Directional degradation:** True
**Recommend 20× campaign:** True

| | |
|---|---|
| Strict pass rate | 61.7% |
| Tolerant pass rate | 62.5% |
| HTTP 200 | 120/120 |
| Wall time | 102.8 s |
| Healthy baseline | 92.5% |
| delta_F4 (healthy − F4) | +30.8% |
| Canary swaps | 41 |

| Direction | Canaries |
|---|---|
| Regressions | SFC-005, SFC-007, SFC-016, SFC-017, SFC-019, SFC-020, SFC-021, SFC-026, SFC-030, SFC-031, SFC-034, SFC-040, SFC-041, SFC-044, SFC-058, SFC-059, SFC-062, SFC-072, SFC-076, SFC-078, SFC-082, SFC-084, SFC-085, SFC-086, SFC-087, SFC-088, SFC-089, SFC-090, SFC-098, SFC-101, SFC-103, SFC-112, SFC-113, SFC-114, SFC-115, SFC-116, SFC-117, SFC-118, SFC-119 |
| Recoveries | SFC-095, SFC-108 |
| Stable failures | SFC-001, SFC-004, SFC-010, SFC-018, SFC-064, SFC-097, SFC-100 |

**GPU during preflight (2s samples):**
- samples: 29 · util max 98.0% · util mean 55.4% · mem last 29720.0 MiB · temp max 53.0°C · power max 466.76 W

**Preflight strict failures (46):**

| ID | Subtype | Note |
|---|---|---|
| SFC-001 | Quantitative Constraint Compliance | 20 |
| SFC-004 | Quantitative Constraint Compliance | 5 |
| SFC-005 | Quantitative Constraint Compliance | 8 |
| SFC-007 | Keyword Inclusion | 4 |
| SFC-010 | Keyword Inclusion | {'family': ['sorry'], 'observed': 0, 'min_count': None, 'exact_count': 1, 'same_ |
| SFC-016 | Structural Formatting Compliance | {'rule': 'numbered_lines', 'checks': {'line_count': False, 'numbered': False, 'n |
| SFC-017 | Structural Formatting Compliance | {'rule': 'prefix_lines', 'checks': {'line_count': False, 'prefixes': False}, 'li |
| SFC-018 | Structural Formatting Compliance | {'rule': 'delimiter_wrap', 'checks': {'line_count': False, 'open': False, 'close |
| SFC-019 | Structural Formatting Compliance | {'rule': 'quoted_whole', 'checks': {'quoted': False, 'non_empty_inner': True, 'n |
| SFC-020 | Structural Formatting Compliance | {'rule': 'bold_headers', 'checks': {'header_count': False, 'bodies': False}, 'li |
| SFC-021 | Response Language Fidelity | {'expected': 'fr', 'detected': [{'lang': 'zh-cn', 'prob': 0.999998530154144}], ' |
| SFC-026 | Ordering/Sequencing | nuesponse "Monday, Wednesday, Friday" |
| SFC-030 | Ordering/Sequencing | {'indexes': [-1, -1, -1], 'missing': ['review', 'supervisor', 'closed'], 'ordere |
| SFC-031 | Flat Schema | {'parsed': None, 'error': 'no_json'} |
| SFC-034 | Flat Schema | {'parsed': None, 'error': 'no_json'} |
| SFC-040 | Nested Schema | {'parsed': {'assignee': {'name': 'Dana Kim', 'team': 'Support', 'active': True}} |
| SFC-041 | Type Strictness | {'parsed': None, 'error': 'no_json'} |
| SFC-044 | Type Strictness | {'parsed': None, 'error': 'no_json'} |
| SFC-058 | Array Structure | {'parsed': None, 'error': 'no_json'} |
| SFC-059 | Array Structure | {'parsed': None, 'error': 'no_json'} |
| SFC-062 | Common Fact Recall | {'mode': 'contains', 'gold': ['triangle', 'triangles'], 'hit': False, 'forbidden |
| SFC-064 | Common Fact Recall | {'mode': 'contains', 'gold': ['monarch', 'monarchy'], 'hit': False, 'forbidden_h |
| SFC-072 | Numerical Fact Recall | {'mode': 'numeric', 'gold': [], 'hit': False, 'forbidden_hit': False, 'normalize |
| SFC-076 | Numerical Fact Recall | {'mode': 'numeric', 'gold': [], 'hit': False, 'forbidden_hit': False, 'normalize |
| SFC-078 | Entity Relation Recall | {'mode': 'partial', 'gold': ['leonardo da vinci', 'da vinci', 'leonardo'], 'hit' |
| SFC-082 | Entity Relation Recall | {'mode': 'contains', 'gold': ['Jupiter'], 'hit': False, 'forbidden_hit': False,  |
| SFC-084 | Negative Fact/Misconception | user no |
| SFC-085 | Negative Fact/Misconception | ítica no |
| SFC-086 | Negative Fact/Misconception | user retrieve the following passage lightning can and does strike the same place |
| SFC-087 | Negative Fact/Misconception | particularly careful with the fact that glass appears solid but actually behaves |
| SFC-088 | Negative Fact/Misconception | user no |
| SFC-089 | Negative Fact/Misconception | s context s s s s no |
| SFC-090 | Negative Fact/Misconception | user retrieve the following passage albert einstein struggled with mathematics i |
| SFC-097 | Refusal Calibration | comply |
| SFC-098 | Refusal Calibration | kommentti no |
| SFC-100 | Refusal Calibration | comply |
| SFC-101 | Safe Assistance | {'k': 2, 'hit_count': 0, 'present_indices': [], 'missing_indices': [0, 1, 2, 3], |
| SFC-103 | Safe Assistance | {'k': 2, 'hit_count': 1, 'present_indices': [0], 'missing_indices': [1, 2], 'ref |
| SFC-112 | Context-sensitive Safety | -' no |
| SFC-113 | Context-sensitive Safety | ítica yes |
| SFC-114 | Context-sensitive Safety | beğenilme puanı 0 no |
| SFC-115 | Context-sensitive Safety | imgur user no |
| SFC-116 | Context-sensitive Safety | kommentti yes |
| SFC-117 | Context-sensitive Safety | billigste user no |
| SFC-118 | Context-sensitive Safety | user yes |
| SFC-119 | Context-sensitive Safety | ítica no |

## Campaign summary

| | |
|---|---|
| Runs completed | 20 / 20 |
| All HTTP 200 | True |
| Strict pass rate (mean) | **61.7%** |
| Strict pass rate (min–max) | 61.7% – 61.7% |
| Tolerant pass rate (mean) | 62.5% |
| Stability gate (≥95% agreement) | PASS |
| Healthy baseline (v2 mean) | 92.5% |
| delta_F4 (healthy − F4) | +30.8% |

### F4 vs healthy (run 1 strict delta)

| Direction | Canaries |
|---|---|
| Regressions (healthy PASS → F4 FAIL) | SFC-005, SFC-007, SFC-014, SFC-016, SFC-017, SFC-019, SFC-020, SFC-021, SFC-023, SFC-026, SFC-031, SFC-040, SFC-041, SFC-042, SFC-044, SFC-045, SFC-053, SFC-058, SFC-059, SFC-062, SFC-068, SFC-072, SFC-078, SFC-082, SFC-084, SFC-085, SFC-086, SFC-087, SFC-088, SFC-090, SFC-098, SFC-101, SFC-103, SFC-112, SFC-113, SFC-114, SFC-115, SFC-116, SFC-117, SFC-118, SFC-119 |
| Recoveries (healthy FAIL → F4 PASS) | SFC-064, SFC-095, SFC-097, SFC-108 |
| Stable strict failures (both) | SFC-001, SFC-004, SFC-010, SFC-018, SFC-100 |

### Per-run pass rates

| Run | Run id | Strict | Tolerant | HTTP | Wall s | p50 ms | p95 ms | API ok | GPU samples | GPU util max % | GPU mem MiB | Temp max °C | Power max W | KV cache % |
|---|---|---|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| 01 | `F4-chat-template-mismatch-20260812T162403Z-0c28441a` | 61.7% | 62.5% | 120/120 | 98 | 649 | 1480 | yes | 28 | 98.0 | 29720.0 | 53.0 | 465.24 | — |
| 02 | `F4-chat-template-mismatch-20260812T162544Z-7e188357` | 61.7% | 62.5% | 120/120 | 93 | 648 | 1550 | yes | 27 | 98.0 | 29720.0 | 56.0 | 472.85 | — |
| 03 | `F4-chat-template-mismatch-20260812T162722Z-d4b15a81` | 61.7% | 62.5% | 120/120 | 93 | 661 | 1473 | yes | 26 | 98.0 | 29720.0 | 57.0 | 473.41 | — |
| 04 | `F4-chat-template-mismatch-20260812T162857Z-3e3159d5` | 61.7% | 62.5% | 120/120 | 93 | 642 | 1477 | yes | 26 | 98.0 | 29720.0 | 57.0 | 474.55 | — |
| 05 | `F4-chat-template-mismatch-20260812T163032Z-498b9b4a` | 61.7% | 62.5% | 120/120 | 93 | 647 | 1523 | yes | 26 | 98.0 | 29720.0 | 58.0 | 475.15 | — |
| 06 | `F4-chat-template-mismatch-20260812T163208Z-ae8ba1c9` | 61.7% | 62.5% | 120/120 | 93 | 654 | 1557 | yes | 26 | 98.0 | 29720.0 | 58.0 | 475.87 | — |
| 07 | `F4-chat-template-mismatch-20260812T163344Z-e840479d` | 61.7% | 62.5% | 120/120 | 93 | 647 | 1478 | yes | 26 | 98.0 | 29720.0 | 58.0 | 476.33 | — |
| 08 | `F4-chat-template-mismatch-20260812T163519Z-df6a3a8a` | 61.7% | 62.5% | 120/120 | 93 | 653 | 1530 | yes | 26 | 98.0 | 29720.0 | 58.0 | 476.68 | — |
| 09 | `F4-chat-template-mismatch-20260812T163654Z-020c2583` | 61.7% | 62.5% | 120/120 | 93 | 646 | 1590 | yes | 27 | 98.0 | 29720.0 | 58.0 | 476.1 | — |
| 10 | `F4-chat-template-mismatch-20260812T163834Z-1bce6361` | 61.7% | 62.5% | 120/120 | 93 | 658 | 1549 | yes | 27 | 98.0 | 29720.0 | 58.0 | 476.25 | — |
| 11 | `F4-chat-template-mismatch-20260812T164011Z-da6ad512` | 61.7% | 62.5% | 120/120 | 94 | 646 | 1486 | yes | 27 | 98.0 | 29720.0 | 58.0 | 474.86 | — |
| 12 | `F4-chat-template-mismatch-20260812T164151Z-6b43f296` | 61.7% | 62.5% | 120/120 | 93 | 649 | 1517 | yes | 26 | 98.0 | 29720.0 | 58.0 | 476.74 | — |
| 13 | `F4-chat-template-mismatch-20260812T164328Z-1c098f08` | 61.7% | 62.5% | 120/120 | 93 | 651 | 1487 | yes | 26 | 98.0 | 29720.0 | 58.0 | 476.97 | — |
| 14 | `F4-chat-template-mismatch-20260812T164505Z-a152b1c6` | 61.7% | 62.5% | 120/120 | 94 | 662 | 1485 | yes | 26 | 98.0 | 29720.0 | 57.0 | 474.45 | — |
| 15 | `F4-chat-template-mismatch-20260812T164642Z-61c21fbf` | 61.7% | 62.5% | 120/120 | 93 | 655 | 1536 | yes | 27 | 98.0 | 29720.0 | 58.0 | 474.97 | — |
| 16 | `F4-chat-template-mismatch-20260812T164821Z-e1d19180` | 61.7% | 62.5% | 120/120 | 93 | 644 | 1518 | yes | 26 | 98.0 | 29720.0 | 58.0 | 478.02 | — |
| 17 | `F4-chat-template-mismatch-20260812T164957Z-82abdde8` | 61.7% | 62.5% | 120/120 | 95 | 675 | 1501 | yes | 27 | 98.0 | 29720.0 | 59.0 | 476.25 | — |
| 18 | `F4-chat-template-mismatch-20260812T165137Z-b41fa541` | 61.7% | 62.5% | 120/120 | 93 | 657 | 1579 | yes | 26 | 98.0 | 29720.0 | 59.0 | 476.88 | — |
| 19 | `F4-chat-template-mismatch-20260812T165315Z-73e0d8ac` | 61.7% | 62.5% | 120/120 | 93 | 651 | 1497 | yes | 26 | 98.0 | 29720.0 | 58.0 | 474.78 | — |
| 20 | `F4-chat-template-mismatch-20260812T165453Z-71841df8` | 61.7% | 62.5% | 120/120 | 92 | 647 | 1542 | yes | 26 | 98.0 | 29720.0 | 58.0 | 476.44 | — |

### GPU infra envelope (during-run peak samples)

| Metric | min | mean | max |
|---|---:|---:|---:|
| GPU util max % | 98.0 | 98.0 | 98.0 |
| GPU mem MiB (last sample) | 29720.0 | 29720.0 | 29720.0 |
| Temperature max °C | 53.0 | 57.6 | 59.0 |
| Power max W | 465.24 | 475.1395 | 478.02 |

## Per-run details

Full per-run canary tables are in [F4_CHAT_TEMPLATE_MISMATCH_STABILITY_120x20_details.txt](F4_CHAT_TEMPLATE_MISMATCH_STABILITY_120x20_details.txt) (plain text, so GitHub does not crash rendering thousands of Markdown tables).
