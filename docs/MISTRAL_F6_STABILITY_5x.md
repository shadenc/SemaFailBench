# Mistral F6 — Wrong / stale LoRA adapter (isolated) · 120 core × 5 deterministic passes

**Campaign id:** `f6-stability-20260815T193128Z`
**Fault:** F6 — wrong LoRA adapter mounted on healthy base; matched weights + tokenizer + chat template + generation defaults
**Pod:** `t1c0946v78zeni` (`democratic_apricot_antlion`) · RTX 5090 · vLLM 0.27.1
**Model (base weights + tokenizer):** `mistralai/Mistral-7B-Instruct-v0.3` @ `c170c708c41dac9275d15a8fff4eca08d52bab71`
**Wrong LoRA:** `stale-cyber-lora` ← `dpevzner/CyberOps_Mistral_7B_LoRA` (CyberOps ops adapter left on general instruct endpoint)
**Client mode:** requests use `model=stale-cyber-lora` (same fault shape as Qwen tool-call LoRA F6)
**Served API model ids:** `mistralai/Mistral-7B-Instruct-v0.3`, `stale-cyber-lora`
**Scorer contract:** `calibrated-2026-08-10`

**Raw scores:** `results/mistral-v03/f6-retest` (primary) · retest: `results/mistral-v03/f6-retest-retry`

> Compare per-canary jsonl vs healthy in `results/mistral-v03/healthy-stability-5x/` (Mistral healthy mean **79.2%** strict).

## Determinism retest (2026-08-15)

Fair-comparison rerun (`f6-retest-retry`, same protocol, 5×120): **46.0%** mean, **1.7 pp** spread, **5 flaky canaries** (SFC-012, 014, 038, 051, 053). Still not Qwen-parity (`flaky_canaries: []`). Primary campaign below remains the cited result; use **Δ vs healthy** for cross-model comparison.

## Campaign status

| | |
|---|---|
| Planned runs | 5 |
| **Completed runs** | **5** |
| Preflight | Complete |
| Isolation gate | **PASS** (`isolated: true`) |
| All HTTP 200 | True |
| Stability gate | **PASS** (45.0% – 47.5% strict; 2.5 pp spread) |

Runs are **highly stable** (only **4 flaky canaries**). Mean campaign strict **46.3%** — large drop vs healthy **79.2%**, driven almost entirely by **Factual/Knowledge (0/30)** collapse under the cyber LoRA.

## F6 isolation gate

**Verdict:** ISOLATED (`isolated: true`)

| Check | Result |
|---|---|
| Weights unchanged | True — same model + revision as healthy |
| Tokenizer files on disk identical to healthy | True — bundle hash `903fc086…` |
| Chat template identical to healthy | True — hash `e16746b4…` |
| Token IDs identical to healthy | True |
| Generation config same as healthy | True — no `--override-generation-config` |
| dtype identical | True — `bfloat16` |
| **Wrong LoRA mounted** | True — `stale-cyber-lora` in API + vLLM cmdline |
| Healthy LoRA | none |

**Serving delta vs healthy envelope:** only `--enable-lora` + `--lora-modules stale-cyber-lora=dpevzner/CyberOps_Mistral_7B_LoRA`. Base weights, tokenizer, chat template, and generation defaults verified unchanged.

**vLLM command (observed):**

```
python3 -m vllm.entrypoints.openai.api_server \
  --model mistralai/Mistral-7B-Instruct-v0.3 \
  --revision c170c708c41dac9275d15a8fff4eca08d52bab71 \
  --served-model-name mistralai/Mistral-7B-Instruct-v0.3 \
  --host 127.0.0.1 --port 8000 \
  --tensor-parallel-size 1 --dtype bfloat16 \
  --max-model-len 8192 --gpu-memory-utilization 0.90 --enforce-eager \
  --enable-lora --max-lora-rank 16 --max-loras 1 \
  --lora-modules stale-cyber-lora=dpevzner/CyberOps_Mistral_7B_LoRA
```

Manifest: `results/mistral-v03/f6-retest/f6_isolation_manifest.json`

## Protocol

- Isolated F6: official Mistral v0.3 weights + tokenizer + chat template; wrong cybersecurity LoRA left mounted
- Fault class: realistic ops mistake — stale task-specific adapter still routed by clients after base model restore
- 120 core canaries (SFC-001 … SFC-120), catalog order, temp=0, seed=0
- Client sends completions to **`stale-cyber-lora`** module (not bare base id)
- Preflight: one pass before campaign
- Run 1: 5 global warmup requests discarded, then 120 measured
- Runs 2–5: 120 measured each (no warmup)
- API health check before each run; GPU sampled every 2s during inference (~80% util max)

## Preflight gate

**Run id:** `F6-lora-adapter-mismatch-20260815T192144Z-7647ef13`
**Note:** Directional degradation observed in preflight
**Recommend campaign:** True

| | |
|---|---|
| Strict pass rate | **47.5%** |
| Tolerant pass rate | 60.8% |
| HTTP 200 | 120/120 |
| Wall time | 511 s |
| Healthy baseline (Mistral) | **79.2%** |
| delta_F6 (healthy − F6) | **+31.7 pp** |
| Regressions vs healthy run 1 | 43 |
| Recoveries | 5 |

**Capability breakdown (preflight strict):**

| Capability | Score |
|---|---|
| Instruction-following | 16/30 |
| Structured-output | 28/30 |
| **Factual/Knowledge** | **0/30** |
| Safety/Alignment | 13/30 |

Dominant failure mode: fact-recall canaries return **`invalid_json_response`** / tool-call shaped output instead of plain answers.

## Campaign summary (5 completed runs)

| | |
|---|---|
| Runs completed | 5 / 5 |
| Strict pass rate (mean) | **46.3%** |
| Strict pass rate (min–max) | 45.0% – 47.5% |
| Tolerant pass rate (mean) | 59.7% |
| Stability gate | **PASS** (≤ 5 pp spread) |
| Healthy baseline (Mistral) | **79.2%** |
| Delta vs healthy (mean) | **−32.8 pp** |
| Flaky canaries | 4 |

### Per-run pass rates

| Run | Run id | Strict | Tolerant | HTTP | Wall s | p50 ms | p95 ms |
|---|---|---|---|---|---:|---:|---:|
| 01 | `F6-lora-adapter-mismatch-20260815T193150Z-b4f183ea` | 46.7% | 60.0% | 120/120 | 489 | 4026 | 4459 |
| 02 | `F6-lora-adapter-mismatch-20260815T194005Z-00f3e280` | 45.0% | 58.3% | 120/120 | 489 | 4035 | 4376 |
| 03 | `F6-lora-adapter-mismatch-20260815T194819Z-6912c3d8` | 45.8% | 59.2% | 120/120 | 494 | 4044 | 4538 |
| 04 | `F6-lora-adapter-mismatch-20260815T195637Z-dea0a484` | 47.5% | 60.8% | 120/120 | 490 | 4046 | 4304 |
| 05 | `F6-lora-adapter-mismatch-20260815T200452Z-58643509` | 46.7% | 60.0% | 120/120 | 493 | 4051 | 4533 |

### Per-run capability breakdown (strict, run 1)

| Capability | Score |
|---|---|
| Instruction-following | 16/30 |
| Structured-output | 27/30 |
| **Factual/Knowledge** | **0/30** |
| Safety/Alignment | 13/30 |

All five runs show **0/30** on Factual/Knowledge strict.

## Interpretation vs other Mistral faults

| Fault | Mean strict | Delta vs healthy | Nature |
|---|---:|---:|---|
| F4 chat-template | 43.3% | −35.8 pp | Deterministic structural break |
| **F6 stale LoRA** | **46.3%** | **−32.8 pp** | Task adapter hijacks general behavior |
| F5 decoding-config | 76.3% | −2.8 pp | Stochastic drift — subtle aggregate drop |

F6 on Mistral v0.3 produces **severe, stable degradation** comparable to F4 in aggregate score, but the failure signature differs: structured JSON canaries mostly survive while **all 30 fact-recall canaries fail** (cyber LoRA JSON/tool bias).

## Reproduce

```bash
bash scripts/activate_mistral_profile.sh   # SFB_CONFIG_PROFILE=mistral; ensure legacy Qwen F6 vars commented in .env
bash scripts/gpu/bootstrap_f6.sh
bash scripts/gpu/tunnel.sh                 # separate terminal
python3 scripts/verify_f6_isolation.py \
  --healthy-manifest results/mistral-v03/f6-retest/healthy_restore_manifest.json \
  --out results/mistral-v03/f6-retest/f6_isolation_manifest.json
python3 scripts/run_fault_f6_stability.py --preflight-only --out-dir results/mistral-v03/f6-retest
python3 scripts/run_fault_f6_stability.py --repeats 5 --skip-preflight --out-dir results/mistral-v03/f6-retest
```

## Related artifacts

| Artifact | Path |
|---|---|
| Isolation manifest | `results/mistral-v03/f6-retest/f6_isolation_manifest.json` |
| Preflight manifest | `results/mistral-v03/f6-retest/preflight_manifest.json` |
| Campaign manifest | `results/mistral-v03/f6-retest/campaign_manifest.json` |
| Serving config | `configs/mistral/serving_f6.yaml` |
| Healthy baseline | `results/mistral-v03/healthy-stability-5x/` |
