# F4 — Chat-Template Mismatch

**Fault:** Incorrect conversation template applied at serving time. Weights and tokenizer stay matched to healthy Qwen2.5; only vLLM `--chat-template` points at a wrong-family template.

**Distinct from:**
- **F2** — checkpoint/weights change
- **F3** — tokenizer files change (skipped for now)

## Isolation design

| Artifact | Healthy | F4 |
|---|---|---|
| Model weights | Qwen2.5-7B-Instruct @ `a09a354…` | Same |
| Tokenizer files | Qwen2.5 @ `a09a354…` | Same |
| Chat template at serve | Bundled Qwen ChatML | **Mistral [INST] template** via `--chat-template` |

Wrong template source (default): `mistralai/Mistral-7B-Instruct-v0.3` — tokenizer-only download on pod (`allow_patterns` for `tokenizer_config.json`).

## Local files (ready before pod recharge)

| Path | Purpose |
|---|---|
| `configs/serving_f4.yaml` | F4 serving envelope + preflight gates |
| `scripts/gpu/bootstrap_f4.sh` | Mac → pod inject |
| `scripts/gpu/remote_bootstrap_f4.sh` | Pod-side stop + F4 vLLM |
| `scripts/verify_f4_isolation.py` | Isolation gate → `f4_isolation_manifest.json` |
| `scripts/run_fault_f4_stability.py` | Preflight + 120×20 campaign |
| `results/f4-retest/` | Output dir (empty until runs complete) |

## Pod state at pause (2026-08-12)

- **Pod:** `e0062jv6mdqq7w` — **stopped / needs recharge**
- Last successful step: `restore_healthy.sh` started vLLM (pid 9706) but local tunnel never saw `/v1/models` before pod died
- **F4 not injected yet** — no `pins_f4.json`, no preflight, no isolation manifest
- **F3 skipped** — artifacts kept locally for reference only

## Resume after recharge

### 1. Update `.env` if pod was recreated

From RunPod Connect tab, set:

```bash
SFB_RUNPOD_SSH=<pod-id>@ssh.runpod.io
SFB_RUNPOD_TCP_HOST=<ip>
SFB_RUNPOD_TCP_PORT=<port>
```

Current values (last working session):

```
SFB_RUNPOD_SSH=e0062jv6mdqq7w-644120e5@ssh.runpod.io
SFB_RUNPOD_TCP_HOST=213.173.103.226
SFB_RUNPOD_TCP_PORT=27001
```

### 2. Restore healthy + verify

```bash
bash scripts/gpu/restore_healthy.sh          # ~2–5 min model load
bash scripts/gpu/tunnel.sh                   # separate terminal, keep open
python3 scripts/verify_healthy_restore.py \
  --out results/f4-retest/healthy_restore_manifest.json
```

Wait until `curl -s http://127.0.0.1:8000/v1/models` returns JSON.

### 3. Inject F4

```bash
bash scripts/gpu/bootstrap_f4.sh             # ~3–8 min (Mistral template download + load)
python3 scripts/verify_f4_isolation.py \
  --out results/f4-retest/f4_isolation_manifest.json
```

Gate must show `"isolated": true`:
- tokenizer files identical to healthy
- `--chat-template` → `f4_wrong_chat_template.jinja`
- served token IDs differ from healthy template

### 4. Preflight (120 canaries, one pass)

```bash
python3 scripts/run_fault_f4_stability.py --preflight-only
```

Proceed to 20× only if preflight shows directional degradation + `delta_F4 ≥ 1%` or canary swaps.

### 5. Full campaign (optional)

```bash
python3 scripts/run_fault_f4_stability.py --repeats 20
```

## Env vars (F4)

```bash
SFB_F4_MODEL=Qwen/Qwen2.5-7B-Instruct
SFB_F4_MODEL_REVISION=a09a35458c702b33eeacc393d103063234e8bc28
SFB_F4_TOKENIZER=Qwen/Qwen2.5-7B-Instruct
SFB_F4_TOKENIZER_REVISION=a09a35458c702b33eeacc393d103063234e8bc28
SFB_F4_TEMPLATE_SOURCE=mistralai/Mistral-7B-Instruct-v0.3
SFB_F4_SERVED_MODEL_NAME=Qwen/Qwen2.5-7B-Instruct
```

## Healthy baseline reference

- `results/healthy-stability-120x20-v2/` — **92.5% strict** mean (20× locked)
- Compare `delta_F4 = healthy_mean − f4_mean`

## Notes

- Use **direct TCP SSH** (`SFB_RUNPOD_TCP_*`) for bootstrap; proxy SSH can drop on long installs.
- Pod disk: prefer `/workspace` cache; Mistral bootstrap uses tokenizer-only snapshot.
- Do not commit `.env` (secrets/pod-specific).
