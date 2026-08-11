# F2 — Model / checkpoint version regression

Serve a **different Hub revision** of the same model id while keeping architecture and API surface unchanged. The server should remain **HTTP-healthy** (200 responses, GPU loaded, no restart) but may show **semantic drift** on some canaries vs the hash-pinned healthy baseline.

**Healthy baseline to compare against:** `results/healthy-stability-120x20-v2/` (92.5% strict, 20× locked)

**Fault spec:** `configs/faults.yaml` → F2  
**F2 serving config:** `configs/serving_f2.yaml`

| | Healthy | F2 fault |
|---|---|---|
| Model id | `Qwen/Qwen2.5-7B-Instruct` | same |
| Revision | `a09a35458c702b33eeacc393d103063234e8bc28` | `52e20a6f5f475e5c8f6a8ebda4ae5fa6b1ea22ac` |
| Precision | bf16 | bf16 |
| vLLM | `--revision a09a354…` | `--revision 52e20a6…` |
| API exposes revision? | no | no |
| Expected VRAM | ~29.6 GiB | flat |
| Expected HTTP | 120/120 × 200 | 120/120 × 200 |

---

## Prerequisites

1. RunPod pod with vLLM + healthy baseline recorded
2. Prior fault restored to healthy (or fresh healthy bootstrap)
3. `~/.ssh/sfb_runpod` key on pod

Optional `.env` entries (defaults in `configs/serving_f2.yaml`):

```bash
SFB_F2_MODEL=Qwen/Qwen2.5-7B-Instruct
SFB_F2_REVISION=52e20a6f5f475e5c8f6a8ebda4ae5fa6b1ea22ac
SFB_HEALTHY_REVISION=a09a35458c702b33eeacc393d103063234e8bc28
```

---

## Step 1 — Restore healthy (if coming from F1 or fresh pod)

```bash
bash scripts/gpu/restore_healthy.sh
bash scripts/gpu/tunnel.sh          # keep open
curl http://127.0.0.1:8000/v1/models
```

Verify a few healthy passes before injecting F2:

```bash
python3 scripts/run_healthy_stability.py --repeats 3 --limit 120 --out-dir results/healthy-restore-verify-120x3
```

---

## Step 2 — Inject F2 (stops healthy/F1, starts stale revision)

```bash
bash scripts/gpu/bootstrap_f2.sh
```

This will:
- Stop prior vLLM (healthy, F1, F2)
- Download revision `52e20a6…` of `Qwen/Qwen2.5-7B-Instruct`
- Start vLLM with `--revision 52e20a6… --dtype bfloat16`
- Write `pins_f2.json` on the pod (`/workspace/semafailbench/`)

**Tunnel:** same port 8000 if already open.

---

## Step 3 — Smoke test

```bash
source .venv/bin/activate
bash scripts/smoke_f2.sh
```

**Pass criteria:**
- `GET /v1/models` → HTTP 200, model id `Qwen/Qwen2.5-7B-Instruct`
- 3 canaries → HTTP 200, scored under condition `F2-checkpoint-version`
- GPU snapshot shows vLLM running (~29.6 GiB)

---

## Step 4 — Stability campaign (120 × 20)

```bash
python3 scripts/run_fault_f2_stability.py --repeats 20 --limit 120
```

Outputs:
- `results/fault-f2-stability-120x20/`
- `docs/F2_CHECKPOINT_VERSION_STABILITY_120x20.md`

Compare per-canary vs healthy v2, not just headline pass rate.

---

## Step 5 — Restore healthy (before next fault)

```bash
bash scripts/gpu/restore_healthy.sh
sfb run --condition healthy --limit 3 --warmup
```

Copy pins off pod:

```text
/workspace/semafailbench/pins_f2.json → envs/runpod_f2_pins.json
```

---

## Scripts reference

| Script | Purpose |
|--------|---------|
| `scripts/gpu/bootstrap_f2.sh` | Inject F2 on pod |
| `scripts/gpu/restore_healthy.sh` | Stop F2/F1, restore bf16 healthy |
| `scripts/smoke_f2.sh` | API + 3-canary smoke test |
| `scripts/run_fault_f2_stability.py` | 120×N stability campaign + report |
