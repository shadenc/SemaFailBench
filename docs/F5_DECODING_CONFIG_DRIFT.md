# F5 — Decoding / generation configuration drift

## Fault summary

**F5** injects **server-side generation default drift** while keeping Llama 3.1 weights, tokenizer, and chat template identical to healthy.

| Layer | Healthy | F5 (fault) |
|---|---|---|
| Weights | `meta-llama/Llama-3.1-8B-Instruct` @ `0e9e39f…` | Same |
| Tokenizer | Matched | Same |
| Chat template | Official from model | Same |
| **Generation defaults** | Model `generation_config.json` | **`--override-generation-config`** → temp 1.4, top_p 0.95 |
| **Client requests** | Explicit `temperature=0`, `seed=0` | **Omits** temperature/top_p/seed (`trust_server_decoding`) |

Realistic scenario: ops bumps server sampling defaults in a deployment manifest; thin API clients omit decoding params and inherit the drift.

## Isolation contract

Only vLLM `--override-generation-config` differs. Verified by `scripts/verify_f5_isolation.py` → `f5_isolation_manifest.json`.

## Quick start (RunPod)

```bash
# Tunnel (if not already up)
bash scripts/gpu/tunnel.sh

# Bootstrap F5 on pod
bash scripts/gpu/bootstrap_f5.sh

# Isolation gate (requires prior healthy restore manifest)
.venv/bin/python scripts/verify_healthy_restore.py --out results/f5-llama31-stability-120x5/healthy_restore_manifest.json
.venv/bin/python scripts/verify_f5_isolation.py \
  --healthy-manifest results/f5-llama31-stability-120x5/healthy_restore_manifest.json \
  --out results/f5-llama31-stability-120x5/f5_isolation_manifest.json

# Preflight (120 canaries, server-default decoding)
.venv/bin/python scripts/run_fault_f5_stability.py --preflight-only --out-dir results/f5-llama31-stability-120x5

# Full 5×120 campaign (after preflight recommends)
.venv/bin/python scripts/run_fault_f5_stability.py --repeats 5 --out-dir results/f5-llama31-stability-120x5
```

Or run the full smoke path:

```bash
bash scripts/smoke_f5.sh
```

## Config files

| Path | Purpose |
|---|---|
| `configs/serving_f5.yaml` | F5 envelope + preflight gates |
| `configs/f5_wrong_generation_config.json` | Server override JSON (temp 1.4) |
| `scripts/gpu/bootstrap_f5.sh` | Mac → pod inject |
| `scripts/run_fault_f5_stability.py` | Preflight + 5×120 campaign |

## Restore healthy

```bash
bash scripts/gpu/restore_healthy.sh
.venv/bin/python scripts/verify_healthy_restore.py --out results/f5-llama31-stability-120x5/healthy_restore_manifest.json
```

## Results

Active dir: `results/f5-llama31-stability-120x5/`

Detailed campaign report: `docs/F5_DECODING_CONFIG_DRIFT_STABILITY_120x5.md`

Compare vs Llama healthy: `results/healthy-stability-120x5-llama31/`

**Note:** Healthy baseline (96.7%) used explicit client `temp=0`. F5 runs use server-trust mode intentionally — compare as **deployment regression under thin clients**, not apples-to-apples with explicit deterministic client overrides. Run-to-run variance is expected because F5 is stochastic (`temperature=1.4`).
