# F1 — Quantization regression (Gemma-2-9B-it)

Inject an **aggressively quantized** checkpoint (AWQ 4-bit) while keeping the same model architecture as healthy. The server should remain **HTTP-healthy** (200 responses, GPU loaded, no restart) but may show **semantic degradation** on some canaries vs the bf16 baseline.

**Healthy baseline to compare against:** `results/healthy-stability-120x5-gemma2/` (88.5% strict, 5× locked)

**Fault spec:** `configs/faults.yaml` → F1  
**F1 serving config:** `configs/serving_f1.yaml`

| | Healthy | F1 fault |
|---|---|---|
| Model | `google/gemma-2-9b-it` | `hugging-quants/gemma-2-9b-it-AWQ-INT4` |
| Precision | bf16 | AWQ 4-bit |
| vLLM flag | `--dtype bfloat16` | `--quantization awq_marlin` |
| Expected VRAM | ~30 GiB loaded | flat or lower |
| Expected HTTP | 120/120 × 200 | 120/120 × 200 |

---

## Prerequisites

1. RunPod pod running (update `.env` with SSH + TCP host/port)
2. Healthy Gemma baseline already recorded (`results/healthy-stability-120x5-gemma2`)
3. `~/.ssh/sfb_runpod` key on RunPod

**Local preflight (no pod):**

```bash
bash scripts/verify_f1_prep.sh
```

Optional `.env` entries (defaults work):

```bash
SFB_F1_MODEL=hugging-quants/gemma-2-9b-it-AWQ-INT4
SFB_F1_REVISION=6e62725da8e92309167814dad7aacc0ed8cb2484
SFB_F1_QUANTIZATION=awq_marlin
```

---

## Step 1 — Start pod & healthy server (if fresh pod)

```bash
bash scripts/gpu/bootstrap_healthy.sh
bash scripts/gpu/tunnel.sh          # keep open
curl http://127.0.0.1:8000/v1/models
```

Quick sanity: `sfb run --condition healthy --limit 3 --warmup`

---

## Step 2 — Inject F1 (stops healthy, starts AWQ)

```bash
bash scripts/gpu/bootstrap_f1.sh
```

This will:
- Stop the healthy bf16 vLLM process
- Download the pinned Gemma 2 9B IT AWQ INT4 checkpoint
- Reuse the pinned healthy Gemma tokenizer to prevent F3/F4 confounding
- Start vLLM with `--quantization awq_marlin` (RTX 5090-compatible AWQ kernel)
- Write `pins_f1.json` on the pod (`/workspace/semafailbench/`)

**Tunnel:** if already open, it keeps working (same port 8000).

Update Mac client model for F1 runs:

```bash
export SFB_MODEL=hugging-quants/gemma-2-9b-it-AWQ-INT4
```

Or rely on `run_fault_f1.py` / `smoke_f1.sh` which set this automatically.

---

## Step 3 — Smoke test (server + infra + 3 canaries)

```bash
source .venv/bin/activate
bash scripts/smoke_f1.sh
```

**Pass criteria:**
- `GET /v1/models` → HTTP 200, model id includes AWQ
- 3 canaries → HTTP 200, scored
- GPU snapshot shows vLLM running; memory used may differ from healthy ~30 GiB

---

## Step 4 — Preflight, then 5×120 campaign

```bash
python3 scripts/run_fault_f1_stability.py \
  --repeats 5 --limit 120 --split core \
  --out-dir results/f1-gemma2-stability-120x5
```

Outputs:
- `results/f1-gemma2-stability-120x5/`
- `docs/F1_QUANTIZATION_STABILITY_120x5_GEMMA2.md`

Compare:
- Overall strict rate vs **88.5%**
- Capability breakdown (Cap 1–4)
- New failures vs the stable healthy failures
- Canaries tagged `hypothesized_faults: F1` in catalog

---

## Step 5 — Restore healthy (before F2)

```bash
bash scripts/gpu/restore_healthy.sh
bash scripts/gpu/tunnel.sh   # if needed
sfb run --condition healthy --limit 3 --warmup
```

Re-run should match the Gemma baseline (88.5% strict).

Copy pins off pod after each phase:

```text
/workspace/semafailbench/pins.json    → envs/runpod_healthy_pins.json
/workspace/semafailbench/pins_f1.json → envs/runpod_f1_pins.json
```

---

## What “working properly” means for F1

| Check | Expected |
|-------|----------|
| Server starts | vLLM `/v1/models` returns AWQ model id |
| Answers | All requests HTTP 200 with non-empty completions |
| Infra healthy | No 5xx, no OOM, no restart during run |
| GPU metrics | Util spikes during inference; stable memory |
| Semantic effect | Pass rate **may drop** vs 88.5% — that is the fault signal |

**Silent failure** = infra looks fine but canaries miss degradation. Compare F1 vs healthy per-canary, especially Cap 2 (structured output) and Cap 4 (safety) where F1 sensitivity is hypothesized.

---

## Troubleshooting

| Symptom | Fix |
|---------|-----|
| AWQ load fails | Check vLLM ≥ 0.6; `VLLM_USE_FLASHINFER_SAMPLER=0` |
| Wrong model in API | `export SFB_MODEL=hugging-quants/gemma-2-9b-it-AWQ-INT4` |
| Tunnel refused | Update `SFB_RUNPOD_TCP_*` in `.env`, restart tunnel |
| OOM on AWQ | Unlikely; AWQ uses less VRAM — if OOM, lower `--gpu-memory-utilization` |

---

## Scripts reference

| Script | Purpose |
|--------|---------|
| `scripts/gpu/bootstrap_f1.sh` | Inject F1 on pod |
| `scripts/gpu/restore_healthy.sh` | Stop F1, restore bf16 healthy |
| `scripts/smoke_f1.sh` | API + 3-canary smoke test |
| `scripts/run_fault_f1.py` | Full 120-canary F1 run + report |
| `scripts/start_faulty_vllm_f1.sh` | Manual F1 vLLM launcher (on pod) |
