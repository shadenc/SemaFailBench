# Mistral-7B-Instruct-v0.3 — same fault protocol as Qwen, **5 runs** each

Same injection **shape** as the Qwen campaign. Only the model artifacts differ.  
**F3 skipped** (same as your Qwen run).

Configs live in `configs/mistral/`. Activate with:

```bash
source scripts/activate_mistral_profile.sh
# or set SFB_CONFIG_PROFILE=mistral in .env
```

Results directory: `results/mistral-v03/`

---

## What changed per fault (Mistral vs healthy)

| Fault | Only layer changed | Mistral artifact |
|---|---|---|
| **Healthy** | — | `mistralai/Mistral-7B-Instruct-v0.3` bf16 |
| **F1** | Weight format | `solidrust/Mistral-7B-Instruct-v0.3-AWQ` + `--quantization awq` |
| **F2** | Weights only | Load **`Mistral-7B-Instruct-v0.2`** weights; keep **v0.3 tokenizer + template**; API id stays **v0.3** |
| **F3** | *(skipped)* | — |
| **F4** | Chat template only | `configs/mistral/f4_wrong_chat_template_no_gen_prompt.jinja` — **missing trailing ` [INST] ` opener** |
| **F5** | Server generation defaults | Same `configs/f5_wrong_generation_config.json` (temp 1.4, top_p 0.95); client omits decoding params |
| **F6** | LoRA adapter only | `dpevzner/CyberOps_Mistral_7B_LoRA` as **`stale-cyber-lora`**; client uses `model=stale-cyber-lora` |

---

## Protocol (every fault)

```
restore healthy → bootstrap fault → isolation gate → preflight → 5×120 campaign → restore healthy
```

| Step | Command |
|---|---|
| Tunnel | `bash scripts/gpu/tunnel.sh` |
| Restore healthy | `bash scripts/gpu/restore_healthy.sh` |
| Verify healthy | `python scripts/verify_healthy_restore.py --out results/mistral-v03/healthy_restore_manifest.json` |
| Bootstrap fault | `bash scripts/gpu/bootstrap_fN.sh` |
| Isolation | `python scripts/verify_fN_isolation.py --out results/mistral-v03/fN-retest/fN_isolation_manifest.json` |
| Preflight | `python scripts/run_fault_fN_stability.py --preflight-only --out-dir results/mistral-v03/fN-retest` |
| Campaign **5×** | `python scripts/run_fault_fN_stability.py --repeats 5 --out-dir results/mistral-v03/fN-retest` |

**Campaign rules (same as Qwen):**
- 5 global warmup requests discarded once before run 1
- **5 scored runs** × **120 core canaries** (SFC-001…120), temp=0
- GPU sampled every 2s during each run
- Only proceed to 5× if preflight says `"proceed_to_campaign_recommended": true`

---

## Suggested order

1. **Healthy 5×** (optional baseline for comparison):
   ```bash
   source scripts/activate_mistral_profile.sh
   bash scripts/gpu/bootstrap_healthy.sh
   python scripts/run_healthy_stability.py --repeats 5 --out-dir results/mistral-v03/healthy-stability-5x
   ```
2. **F2** → restore healthy  
3. **F4** → restore healthy  
4. **F5** → restore healthy  
5. **F6** → restore healthy  
6. **F1** (AWQ) last → restore healthy  

---

## Per-fault bootstrap + campaign

Replace `fN` and paths as needed. Always `source scripts/activate_mistral_profile.sh` first.

```bash
OUT=results/mistral-v03/f6-retest
mkdir -p "$OUT"

bash scripts/gpu/restore_healthy.sh
python scripts/verify_healthy_restore.py --out results/mistral-v03/healthy_restore_manifest.json

bash scripts/gpu/bootstrap_f6.sh
python scripts/verify_f6_isolation.py --out "$OUT/f6_isolation_manifest.json"
python scripts/run_fault_f6_stability.py --preflight-only --out-dir "$OUT"
python scripts/run_fault_f6_stability.py --repeats 5 --out-dir "$OUT"

bash scripts/gpu/restore_healthy.sh
```

Swap `bootstrap_f6.sh` → `bootstrap_f2.sh`, `f4`, `f5`, `f1` for other faults.

---

## After first healthy bootstrap

Update revision in `configs/mistral/serving.yaml` from pod `/workspace/semafailbench/pins.json` if it differs from `c170c708…`.

---

## Switch back to Qwen

```bash
unset SFB_CONFIG_PROFILE
export SFB_MODEL=Qwen/Qwen2.5-7B-Instruct
export SFB_HEALTHY_REVISION=a09a35458c702b33eeacc393d103063234e8bc28
# restore Qwen .env values …
```
