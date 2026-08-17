# F6 — Wrong / stale LoRA adapter

## Fault summary

**F6** mounts a **wrong-task LoRA adapter** on the correct Llama 3.1 8B Instruct base. Weights, tokenizer, chat template, and generation defaults stay healthy; only the adapter differs.

| Layer | Healthy | F6 (fault) |
|---|---|---|
| Base weights | `meta-llama/Llama-3.1-8B-Instruct` @ `0e9e39f…` | Same |
| Tokenizer | Matched | Same |
| Chat template | Official from model | Same |
| Generation defaults | Model defaults | Same |
| **LoRA adapter** | **None** | **`nvidia/llama-3.1-nemoguard-8b-topic-control`** (topic-control LoRA, rank 8) |
| **Client route** | `model=meta-llama/Llama-3.1-8B-Instruct` | **`model=stale-topic-lora`** (misconfigured gateway) |

Realistic scenario: a domain-specific adapter from an old product line stays mounted on the general instruct endpoint; production traffic is routed to the stale adapter slot. HTTP stays 200, GPU stays loaded, but outputs shift semantically.

## Isolation contract

Only vLLM `--enable-lora` + `--lora-modules stale-topic-lora=…` differs. Verified by `scripts/verify_f6_isolation.py` → `f6_isolation_manifest.json`.

## Quick start (RunPod — one pod)

```bash
# Tunnel (if not already up)
bash scripts/gpu/tunnel.sh

# Bootstrap F6 on pod (same pod as healthy/F1–F5)
bash scripts/gpu/bootstrap_f6.sh

# Isolation gate (requires prior healthy restore manifest)
.venv/bin/python scripts/verify_healthy_restore.py --out results/f6-llama31-stability-120x5/healthy_restore_manifest.json
.venv/bin/python scripts/verify_f6_isolation.py \
  --healthy-manifest results/f6-llama31-stability-120x5/healthy_restore_manifest.json \
  --out results/f6-llama31-stability-120x5/f6_isolation_manifest.json

# Preflight (120 canaries, temp=0)
.venv/bin/python scripts/run_fault_f6_stability.py --preflight-only --out-dir results/f6-llama31-stability-120x5

# Full 5×120 campaign (after preflight recommends)
.venv/bin/python scripts/run_fault_f6_stability.py --repeats 5 --out-dir results/f6-llama31-stability-120x5
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
| `scripts/run_fault_f6_stability.py` | Preflight + 5×120 campaign |

## Restore healthy

```bash
bash scripts/gpu/restore_healthy.sh
.venv/bin/python scripts/verify_healthy_restore.py --out results/f6-llama31-stability-120x5/healthy_restore_manifest.json
```

## Expected behavior

| Signal | Expected |
|---|---|
| HTTP | 120/120 × 200 |
| GPU | Loaded (~30 GiB base + LoRA overhead) |
| vLLM | Running with `--enable-lora` |
| Strict pass rate | Below healthy 96.7% if adapter shifts behavior |
| Infra alerts | None (infra-silent) |

Compare vs Llama healthy: `results/healthy-stability-120x5-llama31/`

## Pinned adapter provenance

- Repo: `nvidia/llama-3.1-nemoguard-8b-topic-control`
- Revision: `5ce438e7119061c809e9da819beb5b9287104230`
- Declared base: `meta-llama/Llama-3.1-8B-Instruct`
- LoRA rank: 8 (`--max-lora-rank 16`)
