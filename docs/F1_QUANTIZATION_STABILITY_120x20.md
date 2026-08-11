# F1 — Quantization regression · 120 core × 20 deterministic passes

**Campaign id:** `f1-stability-20260811T144635Z`
**Fault:** F1 — Quantization regression
**Pod:** `g0uutfrnf83h9v` · AWQ vLLM inference
**Model:** `Qwen/Qwen2.5-7B-Instruct-AWQ` (`awq`)
**Healthy reference:** `Qwen/Qwen2.5-7B-Instruct` @ `a09a35458c70…`
**Scorer contract:** `calibrated-2026-08-10`

**Raw scores:** `results/fault-f1-stability-120x20`

## Protocol

- Stop healthy bf16 vLLM; serve `Qwen/Qwen2.5-7B-Instruct-AWQ` with `--quantization awq`
- 120 core canaries (SFC-001 … SFC-120), catalog order, temp=0
- Run 1: 5 warmup requests discarded, then 120 measured
- Runs 2–20: 120 measured each (no warmup)
- API health check before each run; GPU sampled every 2s **during** inference

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

### Per-run pass rates

| Run | Run id | Strict | Tolerant | HTTP | Wall s | p50 ms | API ok | GPU samples | GPU util max % | GPU mem MiB | Temp max °C | Power max W |
|---|---|---|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| 01 | `F1-quantization-20260811T144637Z-0588e10f` | 92.5% | 93.3% | 120/120 | 101 | 469 | yes | 28 | 82.0 | 29528.0 | 43.0 | 272.24 |
| 02 | `F1-quantization-20260811T144820Z-2024f967` | 92.5% | 93.3% | 120/120 | 67 | 464 | yes | 19 | 83.0 | 29528.0 | 45.0 | 276.06 |
| 03 | `F1-quantization-20260811T144930Z-ab7ac27c` | 92.5% | 93.3% | 120/120 | 68 | 472 | yes | 19 | 81.0 | 29528.0 | 47.0 | 305.26 |
| 04 | `F1-quantization-20260811T145040Z-52c44c2d` | 92.5% | 93.3% | 120/120 | 68 | 472 | yes | 19 | 81.0 | 29528.0 | 47.0 | 277.65 |
| 05 | `F1-quantization-20260811T145151Z-48a1033c` | 92.5% | 93.3% | 120/120 | 69 | 472 | yes | 20 | 81.0 | 29528.0 | 48.0 | 380.38 |
| 06 | `F1-quantization-20260811T145306Z-06262c8a` | 92.5% | 93.3% | 120/120 | 68 | 481 | yes | 19 | 81.0 | 29528.0 | 48.0 | 330.68 |
| 07 | `F1-quantization-20260811T145417Z-bf0427dc` | 92.5% | 93.3% | 120/120 | 68 | 475 | yes | 19 | 82.0 | 29528.0 | 48.0 | 325.54 |
| 08 | `F1-quantization-20260811T145528Z-1987e000` | 92.5% | 93.3% | 120/120 | 76 | 475 | yes | 22 | 80.0 | 29528.0 | 47.0 | 278.52 |
| 09 | `F1-quantization-20260811T145648Z-f99047b4` | 92.5% | 93.3% | 120/120 | 70 | 488 | yes | 20 | 76.0 | 29528.0 | 48.0 | 377.97 |
| 10 | `F1-quantization-20260811T145801Z-72049788` | 92.5% | 93.3% | 120/120 | 69 | 473 | yes | 20 | 81.0 | 29528.0 | 48.0 | 356.85 |
| 11 | `F1-quantization-20260811T145914Z-8fb3f568` | 92.5% | 93.3% | 120/120 | 68 | 469 | yes | 19 | 81.0 | 29528.0 | 48.0 | 260.16 |
| 12 | `F1-quantization-20260811T150025Z-895ef968` | 92.5% | 93.3% | 120/120 | 87 | 487 | yes | 24 | 80.0 | 29528.0 | 46.0 | 260.72 |
| 13 | `F1-quantization-20260811T150155Z-531677ed` | 92.5% | 93.3% | 120/120 | 82 | 517 | yes | 23 | 70.0 | 29528.0 | 45.0 | 307.43 |
| 14 | `F1-quantization-20260811T150320Z-2bdc6a22` | 92.5% | 93.3% | 120/120 | 71 | 488 | yes | 20 | 77.0 | 29528.0 | 47.0 | 263.21 |
| 15 | `F1-quantization-20260811T150434Z-fcebd056` | 92.5% | 93.3% | 120/120 | 70 | 483 | yes | 20 | 79.0 | 29528.0 | 47.0 | 250.54 |
| 16 | `F1-quantization-20260811T150547Z-441495fe` | 92.5% | 93.3% | 120/120 | 78 | 486 | yes | 22 | 75.0 | 29528.0 | 47.0 | 278.2 |
| 17 | `F1-quantization-20260811T150707Z-06417c5f` | 92.5% | 93.3% | 120/120 | 86 | 548 | yes | 24 | 57.0 | 29528.0 | 46.0 | 265.18 |
| 18 | `F1-quantization-20260811T150835Z-4c901ac7` | 92.5% | 93.3% | 120/120 | 81 | 525 | yes | 23 | 58.0 | 29528.0 | 46.0 | 265.32 |
| 19 | `F1-quantization-20260811T151000Z-4776bca3` | 92.5% | 93.3% | 120/120 | 76 | 518 | yes | 22 | 80.0 | 29528.0 | 45.0 | 353.92 |
| 20 | `F1-quantization-20260811T151120Z-4a906e43` | 92.5% | 93.3% | 120/120 | 69 | 477 | yes | 20 | 80.0 | 29528.0 | 48.0 | 366.3 |

### GPU infra envelope (during-run peak samples)

| Metric | min | mean | max |
|---|---:|---:|---:|
| GPU util max % | 57.0 | 77.25 | 83.0 |
| GPU mem MiB (last sample) | 29528.0 | 29528.0 | 29528.0 |
| Temperature max °C | 43.0 | 46.7 | 48.0 |
| Power max W | 250.54 | 302.6065 | 380.38 |

## Canary stability across 20 runs

_None — all canaries had identical strict outcomes across completed runs._
