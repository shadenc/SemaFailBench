# F5 — Decoding / generation configuration drift (Gemma-2-9B-it)

Inject **server-side generation default drift** while keeping Gemma 2 9B IT weights, tokenizer, and chat template identical to healthy. Same mechanism as Qwen and Llama F5: `--override-generation-config` with temperature 1.4 / top_p 0.95 / do_sample, and the client omits decoding params.

**Healthy baseline:** `results/healthy-stability-120x5-gemma2/` (88.5% strict, 5× locked)

**Fault spec:** `configs/faults.yaml` → F5  
**F5 serving config:** `configs/serving_f5.yaml`

| | Healthy | F5 fault |
|---|---|---|
| Weights | `google/gemma-2-9b-it` @ `11c9b309…` | same |
| Tokenizer / chat template | official IT | same |
| Generation defaults | model `generation_config.json` | `--override-generation-config` → temp 1.4, top_p 0.95 |
| Client requests | explicit `temperature=0`, `seed=0` | omits temperature/top_p/seed (`trust_server_decoding`) |

---

## Env

```bash
SFB_F5_MODEL=google/gemma-2-9b-it
SFB_F5_MODEL_REVISION=11c9b309abf73637e4b6f9a3fa1e92e615547819
SFB_F5_OVERRIDE_FILE=configs/f5_wrong_generation_config.json
SFB_F5_SERVED_MODEL_NAME=google/gemma-2-9b-it
```

---

## Protocol

```bash
bash scripts/gpu/restore_healthy.sh
bash scripts/gpu/tunnel.sh
python3 scripts/verify_healthy_restore.py \
  --out results/f5-gemma2-stability-120x5/healthy_restore_manifest.json

bash scripts/gpu/bootstrap_f5.sh
python3 scripts/verify_f5_isolation.py \
  --healthy-manifest results/f5-gemma2-stability-120x5/healthy_restore_manifest.json \
  --out results/f5-gemma2-stability-120x5/f5_isolation_manifest.json

python3 scripts/run_fault_f5_stability.py \
  --repeats 5 --limit 120 --split core \
  --out-dir results/f5-gemma2-stability-120x5
```

Outputs:
- `results/f5-gemma2-stability-120x5/`
- `docs/F5_DECODING_CONFIG_DRIFT_STABILITY_120x5_GEMMA2.md`

Compare vs **88.5%**. F5 is stochastic under thin-client decoding; run-to-run variance is expected.
