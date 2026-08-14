# F6 — Wrong / stale LoRA adapter

## Fault summary

**F6** mounts a **wrong-task LoRA adapter** on the correct Qwen2.5-7B-Instruct base. Weights, tokenizer, chat template, and generation defaults stay healthy; only the adapter differs.

| Layer | Healthy | F6 (fault) |
|---|---|---|
| Base weights | `Qwen/Qwen2.5-7B-Instruct` @ `a09a354…` | Same |
| Tokenizer | Matched | Same |
| Chat template | Official from model | Same |
| Generation defaults | Model defaults | Same |
| **LoRA adapter** | **None** | **`arvindcr4/tool-call-lora-qwen2.5-7b`** (tool/agent LoRA) |
| **Client route** | `model=Qwen/Qwen2.5-7B-Instruct` | **`model=stale-tool-lora`** (misconfigured gateway) |

Realistic scenario: a domain-specific adapter from an old product line stays mounted on the general instruct endpoint; production traffic is routed to the stale adapter slot. HTTP stays 200, GPU stays loaded, but outputs shift semantically.

## Isolation contract

Only vLLM `--enable-lora` + `--lora-modules stale-tool-lora=…` differs. Verified by `scripts/verify_f6_isolation.py` → `f6_isolation_manifest.json`.

## Quick start (RunPod — one pod)

```bash
# Tunnel (if not already up)
bash scripts/gpu/tunnel.sh

# Bootstrap F6 on pod (same pod as healthy/F1–F5)
bash scripts/gpu/bootstrap_f6.sh

# Isolation gate (requires prior healthy restore manifest)
.venv/bin/python scripts/verify_healthy_restore.py --out results/f6-retest/healthy_restore_manifest.json
.venv/bin/python scripts/verify_f6_isolation.py --out results/f6-retest/f6_isolation_manifest.json

# Preflight (120 canaries, temp=0)
.venv/bin/python scripts/run_fault_f6_stability.py --preflight-only --out-dir results/f6-retest

# Full 20×120 campaign (after preflight recommends)
.venv/bin/python scripts/run_fault_f6_stability.py --repeats 20 --out-dir results/f6-retest
```

Or:

```bash
bash scripts/smoke_f6.sh
```

## Config files

| Path | Purpose |
|---|---|
| `configs/serving_f6.yaml` | F6 envelope + adapter choice |
| `scripts/gpu/bootstrap_f6.sh` | Mac → pod inject |
| `scripts/run_fault_f6_stability.py` | Preflight + 20× campaign |

## Restore healthy

```bash
bash scripts/gpu/restore_healthy.sh
.venv/bin/python scripts/verify_healthy_restore.py --out results/f6-retest/healthy_restore_manifest.json
```

## Expected behavior

| Signal | Expected |
|---|---|
| HTTP | 120/120 × 200 |
| GPU | Loaded (~30 GiB base + LoRA overhead) |
| vLLM | Running with `--enable-lora` |
| Strict pass rate | Below healthy 92.5% if adapter shifts behavior |
| Infra alerts | None (infra-silent) |

Compare vs healthy v2: `results/healthy-stability-120x20-v2/`
