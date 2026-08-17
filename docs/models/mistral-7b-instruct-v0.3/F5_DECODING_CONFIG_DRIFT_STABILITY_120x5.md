# Mistral F5 — Decoding-config drift (isolated) · 120 core × 5 stochastic passes

**Campaign id:** `f5-stability-20260815T184929Z`
**Fault:** F5 — wrong server generation defaults at serve time; matched weights + tokenizer + chat template
**Pod:** `t1c0946v78zeni` (`democratic_apricot_antlion`) · RTX 5090 · vLLM 0.27.1
**Model (weights + tokenizer):** `mistralai/Mistral-7B-Instruct-v0.3` @ `c170c708c41dac9275d15a8fff4eca08d52bab71`
**Wrong generation defaults:** `configs/f5_wrong_generation_config.json` — `temperature: 1.4`, `top_p: 0.95`, `do_sample: true` (same override JSON as Qwen F5)
**Client mode:** `trust_server_decoding: true` — benchmark client omits decoding params so vLLM server defaults apply
**Served API model id:** `mistralai/Mistral-7B-Instruct-v0.3`
**Scorer contract:** `calibrated-2026-08-10`

**Raw scores:** `results/mistral-v03/f5-retest`

> Compare per-canary jsonl vs healthy in `results/mistral-v03/healthy-stability-5x/` (Mistral healthy mean **79.2%** strict — not Qwen 92.5%).

## Campaign status

| | |
|---|---|
| Planned runs | 5 |
| **Completed runs** | **5** |
| Preflight | Complete |
| Isolation gate | **PASS** (`isolated: true`) |
| All HTTP 200 | True |
| Stability gate | **PASS** (74.2% – 78.3% strict; 4.1 pp spread) |

Unlike deterministic faults (F4), F5 uses **stochastic server sampling**. Pass rates vary across runs and **29 canaries are flaky** (strict outcome differs across the 5 passes). Mean campaign strict **76.3%** sits below Mistral healthy **79.2%**.

## F5 isolation gate

**Verdict:** ISOLATED (`isolated: true`)

| Check | Result |
|---|---|
| Weights unchanged | True — same model + revision as healthy |
| Tokenizer files on disk identical to healthy | True — bundle hash `903fc086…` |
| Chat template identical to healthy | True — hash `e16746b4…` |
| Token IDs identical to healthy | True |
| **Server generation config differs** | True — override hash `f630f953…` vs healthy `ae0a80df…` |
| dtype identical | True — `bfloat16` |
| LoRA identical (none) | True |

**Serving delta vs healthy envelope:** only `--override-generation-config` with the wrong JSON. Weights, tokenizer files, and chat template verified unchanged.

**Wrong override (served):**

```json
{"temperature": 1.4, "top_p": 0.95, "do_sample": true}
```

**vLLM command (observed):**

```
python3 -m vllm.entrypoints.openai.api_server \
  --model mistralai/Mistral-7B-Instruct-v0.3 \
  --revision c170c708c41dac9275d15a8fff4eca08d52bab71 \
  --served-model-name mistralai/Mistral-7B-Instruct-v0.3 \
  --host 127.0.0.1 --port 8000 \
  --tensor-parallel-size 1 --dtype bfloat16 \
  --max-model-len 8192 --gpu-memory-utilization 0.90 --enforce-eager \
  --override-generation-config {"temperature": 1.4, "top_p": 0.95, "do_sample": true}
```

Manifest: `results/mistral-v03/f5-retest/f5_isolation_manifest.json`

## Protocol

- Isolated F5: official Mistral v0.3 weights + tokenizer + chat template; wrong decoding defaults via vLLM `--override-generation-config` only
- Fault class: realistic ops mistake — production server left on high-temperature sampling while clients assume deterministic defaults
- 120 core canaries (SFC-001 … SFC-120), catalog order; client sends **no** temperature/seed (trusts server)
- Preflight: one pass before campaign (includes warmup)
- Run 1: 5 warmup requests discarded, then 120 measured
- Runs 2–5: 120 measured each (no warmup)
- API health check before each run; GPU sampled every 2s during preflight inference

## Preflight gate

**Run id:** `F5-decoding-config-drift-20260815T184638Z-e591b419`
**Note:** Directional degradation observed in preflight
**Recommend campaign:** True

| | |
|---|---|
| Strict pass rate | **75.8%** |
| Tolerant pass rate | 81.7% |
| HTTP 200 | 120/120 |
| Wall time | 148 s |
| Healthy baseline (Mistral) | **79.2%** |
| delta_F5 (healthy − F5) | **+3.3 pp** |
| Regressions vs healthy run 1 | 9 |
| Recoveries | 5 |

**Preflight regressions (healthy PASS → F5 FAIL):** SFC-005, SFC-011, SFC-017, SFC-024, SFC-030, SFC-071, SFC-084, SFC-093, SFC-095

**Preflight recoveries (healthy FAIL → F5 PASS):** SFC-002, SFC-006, SFC-023, SFC-090, SFC-119

**Capability breakdown (preflight strict):**

| Capability | Score |
|---|---|
| Instruction-following | 19/30 |
| Structured-output | 28/30 |
| Factual/Knowledge | 23/30 |
| Safety/Alignment | 21/30 |

## Campaign summary (5 completed runs)

| | |
|---|---|
| Runs completed | 5 / 5 |
| Strict pass rate (mean) | **76.3%** |
| Strict pass rate (min–max) | 74.2% – 78.3% |
| Tolerant pass rate (mean) | 83.7% |
| Stability gate | **PASS** (≤ 5 pp spread) |
| Healthy baseline (Mistral) | **79.2%** |
| Delta vs healthy (mean) | **−2.8 pp** |
| Flaky canaries | 29 (stochastic sampling) |

### Per-run pass rates

| Run | Run id | Strict | Tolerant | HTTP | Wall s | p50 ms | p95 ms |
|---|---|---|---|---|---:|---:|---:|
| 01 | `F5-decoding-config-drift-20260815T184931Z-10dec1dc` | 74.2% | 81.7% | 120/120 | 116 | 622 | 2633 |
| 02 | `F5-decoding-config-drift-20260815T185127Z-55d6d4ce` | 74.2% | 83.3% | 120/120 | 110 | 613 | 2933 |
| 03 | `F5-decoding-config-drift-20260815T185318Z-1c3381ef` | 77.5% | 83.3% | 120/120 | 114 | 670 | 2816 |
| 04 | `F5-decoding-config-drift-20260815T185513Z-b884ba05` | 78.3% | 84.2% | 120/120 | 115 | 615 | 2921 |
| 05 | `F5-decoding-config-drift-20260815T185710Z-a11a427c` | 77.5% | 85.8% | 120/120 | 115 | 622 | 2923 |

### Per-run capability breakdown (strict, run 1)

| Capability | Score |
|---|---|
| Instruction-following | 21/30 |
| Structured-output | 28/30 |
| Factual/Knowledge | 21/30 |
| Safety/Alignment | 19/30 |

(Capability counts vary slightly across runs due to stochastic decoding.)

## Interpretation vs Mistral F4

| Fault | Mean strict | Delta vs healthy | Nature |
|---|---:|---:|---|
| F4 chat-template | 43.3% | −35.8 pp | Deterministic structural break |
| **F5 decoding-config** | **76.3%** | **−2.8 pp** | Stochastic drift — modest aggregate drop, many flaky canaries |

F5 on Mistral v0.3 produces a **subtle but real** degradation vs healthy: aggregate pass rate drops ~3 pp, with per-canary swaps concentrated in instruction-following, safety/refusal, and fact-recall canaries. The fault is harder to detect than F4 because mean scores stay close to healthy.

## Reproduce

```bash
bash scripts/activate_mistral_profile.sh   # or SFB_CONFIG_PROFILE=mistral in .env
bash scripts/gpu/bootstrap_f5.sh
bash scripts/gpu/tunnel.sh                 # separate terminal
python3 scripts/verify_f5_isolation.py --out results/mistral-v03/f5-retest/f5_isolation_manifest.json
python3 scripts/run_fault_f5_stability.py --preflight-only --out-dir results/mistral-v03/f5-retest
python3 scripts/run_fault_f5_stability.py --repeats 5 --skip-preflight --out-dir results/mistral-v03/f5-retest
```

## Related artifacts

| Artifact | Path |
|---|---|
| Isolation manifest | `results/mistral-v03/f5-retest/f5_isolation_manifest.json` |
| Preflight manifest | `results/mistral-v03/f5-retest/preflight_manifest.json` |
| Campaign manifest | `results/mistral-v03/f5-retest/campaign_manifest.json` |
| Wrong generation JSON | `configs/f5_wrong_generation_config.json` |
| Serving config | `configs/mistral/serving_f5.yaml` |
| Healthy baseline | `results/mistral-v03/healthy-stability-5x/` |
