# F2 — Model / checkpoint version regression

Deploy a **wrong model-version artifact** from the same family: serve `Qwen/Qwen2-7B-Instruct` where `Qwen/Qwen2.5-7B-Instruct` is intended. The API exposes the expected logical model id via vLLM `--served-model-name`. Infra should stay flat (HTTP 200, GPU loaded); semantic drift vs the frozen healthy baseline is the fault signal.

**Healthy baseline:** `results/healthy-stability-120x20-v2/` (92.5% strict, 20× locked)

**Fault spec:** `configs/faults.yaml` → F2  
**F2 serving config:** `configs/serving_f2.yaml`

| | Healthy | F2 fault |
|---|---|---|
| Expected logical model | `Qwen/Qwen2.5-7B-Instruct` | same (API id) |
| Actual loaded model | `Qwen/Qwen2.5-7B-Instruct` | `Qwen/Qwen2-7B-Instruct` |
| Hub revision (actual) | `a09a354…` | `f2826a00…` |
| Precision | bf16 | bf16 |
| Fault kind | — | wrong model-version artifact |
| F3 (tokenizer mismatch) | — | not this fault |
| F4 (chat-template mismatch) | — | not this fault |

---

## Invalid prior attempt (do not use as F2 evidence)

The first F2 campaign (`results/fault-f2-stability-120x20/`, Aug 2026) pinned an **older git revision inside the same `Qwen/Qwen2.5-7B-Instruct` repo** (`52e20a6…`). That commit only changed README/LICENSE — **not model weights**. It was a **weak/invalid artifact selection**, not proof that checkpoint-version regression has no semantic effect.

---

## Prerequisites

1. Frozen healthy baseline recorded
2. RunPod pod with vLLM
3. `~/.ssh/sfb_runpod` on pod

`.env` entries (defaults in `configs/serving_f2.yaml`):

```bash
SFB_F2_EXPECTED_MODEL=Qwen/Qwen2.5-7B-Instruct
SFB_F2_ACTUAL_MODEL=Qwen/Qwen2-7B-Instruct
SFB_F2_REVISION=f2826a00ceef68f0f2b946d945ecc0477ce4450c
SFB_F2_SERVED_MODEL_NAME=Qwen/Qwen2.5-7B-Instruct
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
2. Downloads `Qwen/Qwen2-7B-Instruct` @ pinned revision to `/workspace/.cache/huggingface`
3. Starts vLLM with `--served-model-name Qwen/Qwen2.5-7B-Instruct`
4. Writes `pins_f2.json` with `expected_model` and `actual_model`

---

## Step 3 — Smoke test

```bash
source .venv/bin/activate
bash scripts/smoke_f2.sh
```

---

## Step 4 — Preflight (required before 20×)

One deterministic 120-canary pass. Computes `delta_F2 = healthy_pass_rate − F2_pass_rate` and per-canary swaps vs healthy v2 run 1.

```bash
python3 scripts/run_fault_f2_stability.py --preflight-only --limit 120
```

**Effective** if `|delta_F2| ≥ 1%` **or** ≥1 canary regression/recovery vs healthy.

**Ineffective** → script exits 4 and **does not** start the 20-repeat campaign. Do not silently swap to a stronger fault.

---

## Step 5 — Full stability campaign (120 × 20)

```bash
python3 scripts/run_fault_f2_stability.py --repeats 20 --limit 120 \
  --out-dir results/fault-f2-stability-120x20
```

Preflight runs automatically unless `preflight_manifest.json` already exists in `--out-dir`. Use `--skip-preflight` only for debugging.

Outputs:

- `results/fault-f2-stability-120x20/`
- `docs/F2_CHECKPOINT_VERSION_STABILITY_120x20.md` (overwritten on finalize)

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
| `scripts/gpu/restore_healthy.sh` | Restore Qwen2.5 healthy |
| `scripts/smoke_f2.sh` | API + 3-canary smoke |
| `scripts/run_fault_f2_stability.py` | Preflight + 120×N campaign |
