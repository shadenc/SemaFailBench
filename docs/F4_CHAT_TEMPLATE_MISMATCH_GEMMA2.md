# F4 — Chat-template mismatch (Gemma-2-9B-it)

Deploy a **wrong chat template** on the correct Gemma 2 9B IT checkpoint: keep `google/gemma-2-9b-it` weights and tokenizer, and serve the official Gemma IT jinja with the `add_generation_prompt` block deleted. Same mechanism as Qwen and Llama F4 (official family template minus generation header). Not a Mistral `[INST]` template and not a Llama header template.

**Healthy baseline:** `results/healthy-stability-120x5-gemma2/` (88.5% strict, 5× locked)

**Fault spec:** `configs/faults.yaml` → F4  
**F4 serving config:** `configs/serving_f4.yaml`

| | Healthy | F4 fault |
|---|---|---|
| Weights | `google/gemma-2-9b-it` @ `11c9b309…` | same |
| Tokenizer files | same repo @ `11c9b309…` | same |
| Chat template at serve | Official Gemma IT template | Official template minus `add_generation_prompt` (`<start_of_turn>model`) |
| Quantization / LoRA / dtype | none / none / bf16 | unchanged |

Wrong template: `configs/f4_wrong_chat_template_no_gen_prompt.jinja`  
(generated from the official Gemma 2 IT `tokenizer_config.json` by deleting the final assistant generation header).

---

## Prerequisites

```bash
SFB_F4_MODEL=google/gemma-2-9b-it
SFB_F4_MODEL_REVISION=11c9b309abf73637e4b6f9a3fa1e92e615547819
SFB_F4_TOKENIZER=google/gemma-2-9b-it
SFB_F4_TOKENIZER_REVISION=11c9b309abf73637e4b6f9a3fa1e92e615547819
SFB_F4_TEMPLATE_FILE=configs/f4_wrong_chat_template_no_gen_prompt.jinja
SFB_F4_TEMPLATE_SOURCE=local:no_assistant_gen_prompt
SFB_F4_SERVED_MODEL_NAME=google/gemma-2-9b-it
```

Rebuild the faulty jinja from the healthy Gemma template (do not reuse Llama/Mistral jinja):

```bash
python3 scripts/gen_f4_no_gen_prompt_template.py
```

---

## Step 1 — Restore healthy (if coming from another fault)

```bash
bash scripts/gpu/restore_healthy.sh
bash scripts/gpu/tunnel.sh
python3 scripts/verify_healthy_restore.py \
  --out results/f4-gemma2-stability-120x5/healthy_restore_manifest.json
```

---

## Step 2 — Inject F4

```bash
bash scripts/gpu/bootstrap_f4.sh
python3 scripts/verify_f4_isolation.py \
  --healthy-manifest results/f4-gemma2-stability-120x5/healthy_restore_manifest.json \
  --out results/f4-gemma2-stability-120x5/f4_isolation_manifest.json
```

Gate must show `"isolated": true`:
- weights/tokenizer files identical to healthy
- `--chat-template` → `f4_wrong_chat_template.jinja`
- served token IDs differ from healthy template
- isolation probe does **not** send `role=system` on templates that reject it

---

## Step 3 — Preflight, then 5×120 campaign

```bash
python3 scripts/run_fault_f4_stability.py \
  --repeats 5 --limit 120 --split core \
  --out-dir results/f4-gemma2-stability-120x5
```

Outputs:
- `results/f4-gemma2-stability-120x5/`
- `docs/F4_CHAT_TEMPLATE_MISMATCH_STABILITY_120x5_GEMMA2.md`

Compare overall strict rate vs **88.5%**.
