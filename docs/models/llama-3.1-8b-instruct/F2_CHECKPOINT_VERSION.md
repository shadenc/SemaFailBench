# F2 — Model / checkpoint version regression

Deploy a **wrong model-version artifact** from the same family: serve Llama 3 8B Instruct where Llama 3.1 8B Instruct is intended. The API exposes the expected logical model id via vLLM `--served-model-name`. Infra should stay flat (HTTP 200, GPU loaded); semantic drift vs the frozen healthy baseline is the fault signal.

**Healthy baseline:** `results/healthy-stability-120x5-llama31/` (96.7% strict, 5× locked)

**Fault spec:** `configs/faults.yaml` → F2  
**F2 serving config:** `configs/serving_f2.yaml`

| | Healthy | F2 fault |
|---|---|---|
| Expected logical model | `meta-llama/Llama-3.1-8B-Instruct` | same (API id) |
| Actual loaded model | `meta-llama/Llama-3.1-8B-Instruct` | `NousResearch/Meta-Llama-3-8B-Instruct` |
| Hub revision (actual) | `0e9e39f…` | `53346005…` |
| Precision | bf16 | bf16 |
| Fault kind | — | wrong model-version artifact |
| F3 (tokenizer mismatch) | — | not this fault |
| F4 (chat-template mismatch) | — | not this fault |

---

The actual weights come from a pinned public mirror of the upstream
`meta-llama/Meta-Llama-3-8B-Instruct` checkpoint because access to that
upstream repo is gated separately from Llama 3.1.

---

## Prerequisites

1. Frozen healthy baseline recorded
2. RunPod pod with vLLM
3. `~/.ssh/sfb_runpod` on pod

`.env` entries (defaults in `configs/serving_f2.yaml`):

```bash
SFB_F2_EXPECTED_MODEL=meta-llama/Llama-3.1-8B-Instruct
SFB_F2_ACTUAL_MODEL=NousResearch/Meta-Llama-3-8B-Instruct
SFB_F2_REVISION=53346005fb0ef11d3b6a83b12c895cca40156b6c
SFB_F2_SERVED_MODEL_NAME=meta-llama/Llama-3.1-8B-Instruct
```

---

## Step 1 — Restore healthy (if coming from another fault)

```bash
bash scripts/gpu/restore_healthy.sh
bash scripts/gpu/tunnel.sh
curl http://127.0.0.1:8000/v1/models
```

---

## Step 2 — Inject F2

```bash
bash scripts/gpu/bootstrap_f2.sh
```

On the pod this:

1. Stops healthy / F1 / F2 vLLM
2. Downloads the pinned Llama 3 8B Instruct checkpoint
3. Starts vLLM with `--served-model-name meta-llama/Llama-3.1-8B-Instruct`
4. Writes `pins_f2.json` with `expected_model` and `actual_model`

---

## Step 3 — Smoke test

```bash
source .venv/bin/activate
bash scripts/smoke_f2.sh
```

---

## Step 4 — Preflight (required before 5×)

One deterministic 120-canary pass. Computes `delta_F2 = healthy_pass_rate − F2_pass_rate` and per-canary swaps vs Llama healthy run 1.

```bash
python3 scripts/run_fault_f2_stability.py --preflight-only --limit 120
```

**Effective** if `|delta_F2| ≥ 1%` **or** ≥1 canary regression/recovery vs healthy.

**Ineffective** → script exits 4 and **does not** start the 5-repeat campaign.

---

## Step 5 — Full stability campaign (120 × 5)

```bash
python3 scripts/run_fault_f2_stability.py --repeats 5 --limit 120 \
  --out-dir results/f2-llama31-stability-120x5
```

Preflight runs automatically unless `preflight_manifest.json` already exists in `--out-dir`. Use `--skip-preflight` only for debugging.

Outputs:

- `results/f2-llama31-stability-120x5/`
- `docs/F2_CHECKPOINT_VERSION_STABILITY_120x5.md`

---

## Step 6 — Restore healthy

```bash
bash scripts/gpu/restore_healthy.sh
```

Copy pins: `/workspace/semafailbench/pins_f2.json`

---

## Scripts reference

| Script | Purpose |
|--------|---------|
| `scripts/gpu/bootstrap_f2.sh` | Inject F2 wrong-version artifact |
| `scripts/gpu/restore_healthy.sh` | Restore Llama 3.1 healthy |
| `scripts/smoke_f2.sh` | API + 3-canary smoke |
| `scripts/run_fault_f2_stability.py` | Preflight + 120×N campaign |
