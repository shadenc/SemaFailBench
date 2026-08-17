# F4 — Chat-Template Mismatch

**Fault:** Incorrect conversation template applied at serving time. Weights and tokenizer stay matched to healthy Llama 3.1; only vLLM `--chat-template` points at an edited Llama template with the assistant generation header removed.

**Distinct from:**
- **F2** — checkpoint/weights change
- **F3** — tokenizer files change (**skipped** — often operationally noisy and confounds template measurement)

## Isolation design

| Artifact | Healthy | F4 |
|---|---|---|
| Model weights | `meta-llama/Llama-3.1-8B-Instruct` @ `0e9e39f…` | Same |
| Tokenizer files | same repo @ `0e9e39f…` | Same |
| Chat template at serve | Official Llama header template | **Official template minus `add_generation_prompt` block** via `--chat-template` |

Wrong template source: `configs/f4_wrong_chat_template_no_gen_prompt.jinja`
(generated from the official Llama 3.1 `tokenizer_config.json` by deleting the final assistant generation header).

## Local files

| Path | Purpose |
|---|---|
| `configs/serving_f4.yaml` | F4 serving envelope + preflight gates |
| `configs/f4_wrong_chat_template_no_gen_prompt.jinja` | Exact wrong template |
| `scripts/gpu/bootstrap_f4.sh` | Mac → pod inject |
| `scripts/gpu/remote_bootstrap_f4.sh` | Pod-side stop + F4 vLLM |
| `scripts/verify_f4_isolation.py` | Isolation gate → `f4_isolation_manifest.json` |
| `scripts/run_fault_f4_stability.py` | Preflight + 120×5 campaign |
| `results/f4-llama31-stability-120x5/` | Campaign outputs |

## Protocol

### 1. Restore healthy + verify

```bash
bash scripts/gpu/restore_healthy.sh
bash scripts/gpu/tunnel.sh
python3 scripts/verify_healthy_restore.py \
  --out results/f4-llama31-stability-120x5/healthy_restore_manifest.json
```

### 2. Inject F4

```bash
bash scripts/gpu/bootstrap_f4.sh
python3 scripts/verify_f4_isolation.py \
  --healthy-manifest results/f4-llama31-stability-120x5/healthy_restore_manifest.json \
  --out results/f4-llama31-stability-120x5/f4_isolation_manifest.json
```

Gate must show `"isolated": true`:
- weights/tokenizer files identical to healthy
- `--chat-template` → `f4_wrong_chat_template.jinja`
- served token IDs differ from healthy template

### 3. Preflight (120 canaries, one pass)

```bash
python3 scripts/run_fault_f4_stability.py --preflight-only \
  --out-dir results/f4-llama31-stability-120x5
```

Proceed to 5× only if preflight shows directional degradation.

### 4. Full campaign

```bash
python3 scripts/run_fault_f4_stability.py --repeats 5 \
  --out-dir results/f4-llama31-stability-120x5
```

Outputs:
- `results/f4-llama31-stability-120x5/`
- `docs/F4_CHAT_TEMPLATE_MISMATCH_STABILITY_120x5.md`

## Env vars (F4)

```bash
SFB_F4_MODEL=meta-llama/Llama-3.1-8B-Instruct
SFB_F4_MODEL_REVISION=0e9e39f249a16976918f6564b8830bc894c89659
SFB_F4_TOKENIZER=meta-llama/Llama-3.1-8B-Instruct
SFB_F4_TOKENIZER_REVISION=0e9e39f249a16976918f6564b8830bc894c89659
SFB_F4_TEMPLATE_FILE=configs/f4_wrong_chat_template_no_gen_prompt.jinja
SFB_F4_TEMPLATE_SOURCE=local:no_assistant_gen_prompt
SFB_F4_SERVED_MODEL_NAME=meta-llama/Llama-3.1-8B-Instruct
```

## Healthy baseline reference

- `results/healthy-stability-120x5-llama31/` — **96.7% strict** mean (5× locked)
- Compare `delta_F4 = healthy_mean − f4_mean`

## Why F3 is skipped

F3 (tokenizer–checkpoint mismatch) often produces loud operational/token-id failures rather than clean silent semantic drift, and it confounds clean F4 isolation. Leader protocol skips it for this campaign set.
