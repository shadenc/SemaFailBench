# F6 — Wrong / stale LoRA adapter (Gemma-2-9B-it)

Mount a **wrong-task LoRA** on the correct Gemma 2 9B IT base. Same mechanism as Qwen (tool-call LoRA) and Llama (topic-control LoRA): base weights/tokenizer/template/generation stay healthy; only the adapter is mounted and the client is routed to the module alias.

**Healthy baseline:** `results/healthy-stability-120x5-gemma2/` (88.5% strict, 5× locked)

**Fault spec:** `configs/faults.yaml` → F6  
**F6 serving config:** `configs/serving_f6.yaml`

| | Healthy | F6 fault |
|---|---|---|
| Weights | `google/gemma-2-9b-it` @ `11c9b309…` | same |
| Tokenizer / chat template | official IT | same |
| Generation defaults | model defaults | same |
| LoRA | none | `AdamLucek/gemma-2-9b-it-lora-yt-titles` (YouTube-title LoRA, rank 16) |
| Client route | `google/gemma-2-9b-it` | `stale-yt-lora` |

Not used: Llama NemoGuard topic-control, Qwen tool-call LoRA, or any adapter whose `base_model_name_or_path` is not `google/gemma-2-9b-it`.

---

## Env

```bash
SFB_F6_MODEL=google/gemma-2-9b-it
SFB_F6_MODEL_REVISION=11c9b309abf73637e4b6f9a3fa1e92e615547819
SFB_F6_LORA_REPO=AdamLucek/gemma-2-9b-it-lora-yt-titles
SFB_F6_LORA_REVISION=820f6ab60102e9c0779599e28698fb117c8607a8
SFB_F6_LORA_MODULE=stale-yt-lora
SFB_F6_MAX_LORA_RANK=16
SFB_F6_SERVED_MODEL_NAME=google/gemma-2-9b-it
```

---

## Protocol

```bash
bash scripts/gpu/restore_healthy.sh
bash scripts/gpu/tunnel.sh
python3 scripts/verify_healthy_restore.py \
  --out results/f6-gemma2-stability-120x5/healthy_restore_manifest.json

bash scripts/gpu/bootstrap_f6.sh
python3 scripts/verify_f6_isolation.py \
  --healthy-manifest results/f6-gemma2-stability-120x5/healthy_restore_manifest.json \
  --out results/f6-gemma2-stability-120x5/f6_isolation_manifest.json

python3 scripts/run_fault_f6_stability.py \
  --repeats 5 --limit 120 --split core \
  --out-dir results/f6-gemma2-stability-120x5
```

Outputs:
- `results/f6-gemma2-stability-120x5/`
- `docs/F6_LORA_ADAPTER_STABILITY_120x5_GEMMA2.md`

Compare vs **88.5%**.
