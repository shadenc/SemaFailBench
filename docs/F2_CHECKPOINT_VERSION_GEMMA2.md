# F2 — Model / checkpoint version regression (Gemma-2-9B-it)

Deploy a **wrong checkpoint artifact** from the same architecture: serve `google/gemma-2-9b` (pretrained) where `google/gemma-2-9b-it` is intended. The API exposes the expected logical model id via vLLM `--served-model-name`. Infra should stay flat (HTTP 200, GPU loaded); semantic drift vs the frozen healthy baseline is the fault signal.

This is the Gemma analog of Llama 3.1 Instruct ← Llama 3 Instruct: same family and size, frozen healthy tokenizer/chat template, only weights change. Gemma 1.1 7B IT is **not** used here because it would confound architecture and size (F2+F3).

**Healthy baseline:** `results/healthy-stability-120x5-gemma2/` (88.5% strict, 5× locked)

**Fault spec:** `configs/faults.yaml` → F2  
**F2 serving config:** `configs/serving_f2.yaml`

| | Healthy | F2 fault |
|---|---|---|
| Expected logical model | `google/gemma-2-9b-it` | same (API id) |
| Actual loaded model | `google/gemma-2-9b-it` | `google/gemma-2-9b` |
| Hub revision (actual) | `11c9b309…` | `33c19302…` |
| Precision | bf16 | bf16 |
| Fault kind | — | wrong checkpoint artifact |
| F3 (tokenizer mismatch) | — | not this fault |
| F4 (chat-template mismatch) | — | not this fault |

---

## Prerequisites

1. Frozen healthy Gemma baseline recorded
2. RunPod pod with vLLM
3. `~/.ssh/sfb_runpod` on pod

```bash
SFB_F2_EXPECTED_MODEL=google/gemma-2-9b-it
SFB_F2_ACTUAL_MODEL=google/gemma-2-9b
SFB_F2_REVISION=33c193028431c2fde6c6e51f29e6f17b60cbfac6
SFB_F2_SERVED_MODEL_NAME=google/gemma-2-9b-it
SFB_F2_TOKENIZER=google/gemma-2-9b-it
SFB_F2_TOKENIZER_REVISION=11c9b309abf73637e4b6f9a3fa1e92e615547819
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

1. Stops healthy / prior vLLM
2. Downloads the pinned Gemma 2 9B pretrained checkpoint
3. Freezes the healthy Gemma IT tokenizer + chat template
4. Starts vLLM with `--served-model-name google/gemma-2-9b-it`
5. Writes `pins_f2.json`

---

## Step 3 — Smoke test

```bash
source .venv/bin/activate
bash scripts/smoke_f2.sh
```

---

## Step 4 — Preflight, then 5×120 campaign

```bash
python3 scripts/run_fault_f2_stability.py \
  --repeats 5 --limit 120 --split core \
  --out-dir results/f2-gemma2-stability-120x5
```

Outputs:
- `results/f2-gemma2-stability-120x5/`
- `docs/F2_CHECKPOINT_VERSION_STABILITY_120x5_GEMMA2.md`

Compare overall strict rate vs **88.5%**.
