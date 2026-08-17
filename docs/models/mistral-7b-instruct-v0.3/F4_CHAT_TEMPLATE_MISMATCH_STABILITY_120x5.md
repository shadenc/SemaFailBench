# Mistral F4 — Chat-template mismatch (isolated) · 120 core × 5 deterministic passes

**Campaign id:** `f4-stability-20260815T171432Z`
**Fault:** F4 — wrong chat template at serve time; matched weights + tokenizer
**Pod:** `qbbern7zxhj1fo` (`key_fuchsia_hare-migration`) · RTX 5090 · vLLM 0.27.1
**Model (weights + tokenizer):** `mistralai/Mistral-7B-Instruct-v0.3` @ `c170c708c41dac9275d15a8fff4eca08d52bab71`
**Wrong template:** delete-only removal of `[/INST]` closers from official Mistral v0.3 jinja (`configs/mistral/f4_wrong_chat_template_no_gen_prompt.jinja`)
**Served API model id:** `mistralai/Mistral-7B-Instruct-v0.3`
**Scorer contract:** `calibrated-2026-08-10`

**Raw scores:** `results/mistral-v03/f4-retest`

> Compare per-canary jsonl vs healthy in `results/mistral-v03/healthy-stability-5x/`.

## Campaign status

| | |
|---|---|
| Planned runs | 5 |
| **Completed runs** | **3** (runs 4–5 not finished — pod stopped mid run 4) |
| Preflight | Complete |
| Isolation gate | **PASS** (`isolated: true`) |
| All HTTP 200 (completed runs) | True |

Runs 1–3 are **bit-identical** at 43.3% strict (52/120). Stability gate **PASS** on completed slice (0 pp spread).

## F4 isolation gate

**Verdict:** ISOLATED (`isolated: true`)

| Check | Result |
|---|---|
| Weights unchanged | True — same model + revision as healthy |
| Tokenizer files on disk identical to healthy | True — bundle hash `903fc086…` |
| Chat template in tokenizer files identical | True — hash `e16746b4…` |
| Token IDs from default tokenizer files identical | True |
| **Served chat template differs** | True — wrong jinja 3838 chars vs healthy 3959 chars |
| **Served token IDs differ** | True — missing `[/INST]` generation-close tokens |
| dtype identical | True — `bfloat16` |
| LoRA identical (none) | True |

**Serving delta vs healthy envelope:** only `--chat-template` points at the wrong jinja file. vLLM 0.27 also requires `--tokenizer-mode hf` on Mistral so the override is honored (same HF tokenizer files; not a separate semantic fault).

**vLLM command (observed):**

```
python3 -m vllm.entrypoints.openai.api_server \
  --model mistralai/Mistral-7B-Instruct-v0.3 \
  --revision c170c708c41dac9275d15a8fff4eca08d52bab71 \
  --tokenizer-mode hf \
  --chat-template /workspace/semafailbench/f4_wrong_chat_template.jinja \
  --host 127.0.0.1 --port 8000 \
  --tensor-parallel-size 1 --dtype bfloat16 \
  --max-model-len 8192 --gpu-memory-utilization 0.90 --enforce-eager
```

Manifest: `results/mistral-v03/f4-retest/f4_isolation_manifest.json`

## Protocol

- Isolated F4: official Mistral v0.3 weights + tokenizer; wrong template injected via vLLM `--chat-template` only
- Fault class: realistic ops mistake — accidental deletion of `[/INST]` suffixes on user turns (parallel to Qwen F4 removing `add_generation_prompt`)
- 120 core canaries (SFC-001 … SFC-120), catalog order, temp=0, seed=0
- Preflight: one deterministic pass before campaign
- Run 1: 5 warmup requests discarded, then 120 measured
- Runs 2–5: 120 measured each (no warmup)
- API health check before each run; GPU sampled every 2s **during** inference

## Preflight gate

**Run id:** `F4-chat-template-mismatch-20260815T170814Z-e06151e1`
**Note:** Directional degradation observed in preflight
**Recommend campaign:** True

| | |
|---|---|
| Strict pass rate | **44.2%** |
| Tolerant pass rate | 52.5% |
| HTTP 200 | 120/120 |
| Wall time | 283 s |
| Healthy baseline | 79.2% |
| delta_F4 (healthy − F4) | **+35.0 pp** |
| Regressions vs healthy | 46 |
| Recoveries | 4 |

**Capability breakdown (preflight strict):**

| Capability | Score |
|---|---|
| Instruction-following | 19/30 |
| Structured-output | 14/30 |
| Factual/Knowledge | 3/30 |
| Safety/Alignment | 17/30 |

## Campaign summary (3 completed runs)

| | |
|---|---|
| Runs completed | 3 / 5 |
| Strict pass rate (mean) | **43.3%** |
| Strict pass rate (min–max) | 43.3% – 43.3% |
| Tolerant pass rate (mean) | 52.5% |
| Stability gate (completed runs) | **PASS** (0 pp spread) |
| Healthy baseline | 79.2% |
| Delta vs healthy | **−35.8 pp** |

### F4 vs healthy (preflight regressions — headline swaps)

| Direction | Count | Examples |
|---|---:|---|
| Regressions (healthy PASS → F4 FAIL) | 46 | SFC-005, SFC-016, SFC-033–034, SFC-061–083, SFC-095, SFC-100, … |
| Recoveries (healthy FAIL → F4 PASS) | 4 | SFC-002, SFC-006, SFC-023, SFC-088 |
| Stable strict failures (both) | 21 | SFC-001, SFC-004, SFC-007, SFC-010, SFC-018, SFC-026, … |

Dominant failure modes under F4: **JSON/schema canaries** (`no_json`), **numerical/entity fact recall**, **structural formatting**, and **refusal miscalibration** (`comply` where refusal expected).

### Per-run pass rates

| Run | Run id | Strict | Tolerant | HTTP | Wall s | p50 ms | p95 ms | GPU util max % | GPU mem MiB | Power max W |
|---|---|---|---|---|---:|---:|---:|---:|---:|---:|
| 01 | `F4-chat-template-mismatch-20260815T171432Z-2a370592` | 43.3% | 52.5% | 120/120 | 252 | 2470 | 2956 | 97.0 | 29506 | 482.16 |
| 02 | `F4-chat-template-mismatch-20260815T171846Z-e932ad63` | 43.3% | 52.5% | 120/120 | 236 | 2413 | 2925 | 97.0 | 29506 | 484.08 |
| 03 | `F4-chat-template-mismatch-20260815T172245Z-1d887d11` | 43.3% | 52.5% | 120/120 | 236 | 2420 | 2936 | 97.0 | 29506 | 483.72 |
| 04 | — | — | — | — | — | — | — | — | — | **Interrupted (pod outage)** |
| 05 | — | — | — | — | — | — | — | — | — | Not started |

### Per-run capability breakdown (strict)

All three completed runs identical:

| Capability | Score |
|---|---|
| Instruction-following | 19/30 |
| Structured-output | 14/30 |
| Factual/Knowledge | 3/30 |
| Safety/Alignment | 16/30 |

## Canary stability across completed runs

_None — all 120 canaries had identical strict outcomes across runs 1–3._

## Resume after pod restore

```bash
bash scripts/gpu/bootstrap_f4.sh
bash scripts/gpu/tunnel.sh   # separate terminal
python3 scripts/run_fault_f4_stability.py \
  --repeats 5 --start-run 4 --skip-preflight \
  --out-dir results/mistral-v03/f4-retest
```

## Related artifacts

| Artifact | Path |
|---|---|
| Isolation manifest | `results/mistral-v03/f4-retest/f4_isolation_manifest.json` |
| Preflight manifest | `results/mistral-v03/f4-retest/preflight_manifest.json` |
| Campaign manifest | `results/mistral-v03/f4-retest/campaign_manifest.json` |
| Wrong template (repo) | `configs/mistral/f4_wrong_chat_template_no_gen_prompt.jinja` |
| Serving config | `configs/mistral/serving_f4.yaml` |
