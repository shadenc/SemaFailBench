# Handoff — testing a new model (F1–F6)

Simple checklist for continuing SemaFailBench on a **new base model**. Start from the latest F6 branch, update the model everywhere, then run **healthy → each fault** using the same injection method and campaign protocol already in the repo.

**Reference branch (has F1–F6 tooling + F6 results):**  
`retaj/fault-f6-lora-adapter-120x20`  
https://github.com/shadenc/SemaFailBench/tree/retaj/fault-f6-lora-adapter-120x20

---

## 0) One-time setup on your laptop

```bash
git clone https://github.com/shadenc/SemaFailBench.git
cd SemaFailBench
git checkout retaj/fault-f6-lora-adapter-120x20

python3.11 -m venv .venv
source .venv/bin/activate
pip install -U pip && pip install -e ".[dev]"
python scripts/compile_catalog.py
pytest   # expect 18 passed
```

### SSH key (your own — do not copy someone else's)

```bash
ssh-keygen -t ed25519 -f "$HOME/.ssh/sfb_runpod" -N "" -C "semafailbench-runpod-$(whoami)"
cat "$HOME/.ssh/sfb_runpod.pub"
```

Add the **public** line to RunPod → **Settings → SSH Public Keys**.  
If the pod was already running, **Stop → Start** so the key is injected.

### `.env` (copy from `.env.example`)

```bash
cp .env.example .env
```

Fill in **your** pod from RunPod **Connect** tab:

| Variable | What to set |
|---|---|
| `SFB_RUNPOD_SSH` | e.g. `PODID-xxxxx@ssh.runpod.io` |
| `SFB_RUNPOD_KEY` | `~/.ssh/sfb_runpod` |
| `SFB_RUNPOD_TCP_HOST` | TCP IP from Connect tab |
| `SFB_RUNPOD_TCP_PORT` | TCP port from Connect tab |
| `SFB_BASE_URL` | `http://127.0.0.1:8000/v1` |

**Important:** `SFB_RUNPOD_TCP_HOST` is required for GPU metrics during runs.

---

## 1) Change the model (before any runs)

Replace **Qwen/Qwen2.5-7B-Instruct** with your new model in these places:

| File | What to update |
|---|---|
| `configs/serving.yaml` | `model.repo`, `model.revision`, tokenizer fields |
| `.env` | `SFB_MODEL`, `SFB_HEALTHY_REVISION`, and every `SFB_F*_MODEL` / revision var |
| `configs/serving_f2.yaml` … `serving_f6.yaml` | base model + revision in each fault config |
| Fault-specific choices | see below |

After the first healthy bootstrap, copy the **actual Hub revision** from the pod (`/workspace/semafailbench/pins.json`) into `configs/serving.yaml` and `.env` — do not guess commit hashes.

### Fault-specific notes (same *kind* of fault, new model)

| Fault | What changes for a new model |
|---|---|
| **F1** AWQ | Pick an AWQ quant of **your** instruct model (`SFB_F1_MODEL`) |
| **F2** wrong checkpoint | Pick a **wrong version from the same family** (e.g. older gen instruct model). Update `SFB_F2_ACTUAL_MODEL` + `SFB_F2_REVISION` |
| **F3** tokenizer mismatch | Point `SFB_F3_BPE_SOURCE` at a tokenizer that does **not** match your base weights |
| **F4** chat template | Keep using `configs/f4_wrong_chat_template_no_gen_prompt.jinja` unless the new model needs a different wrong template |
| **F5** decoding drift | Keep `configs/f5_wrong_generation_config.json` (server-side generation defaults) |
| **F6** stale LoRA | Pick a **wrong-task LoRA built for your base model** on Hugging Face. Update `SFB_F6_LORA_REPO` and `configs/serving_f6.yaml` |

Read the short doc per fault before bootstrapping: `docs/F1_QUANTIZATION.md` … `docs/F6_LORA_ADAPTER_MISMATCH.md`.

---

## 2) Architecture (one GPU pod)

```
Your laptop (sfb / python scripts)
        │  SSH tunnel :8000
        ▼
RunPod — one vLLM at a time (healthy OR one fault)
```

- Only **one** server runs on the pod at a time.
- **Always restore healthy** before switching to another fault.
- Use a **new results folder** per model, e.g. `results/<model-slug>-f6-retest/`.

---

## 3) Commands you use every session

**Terminal 1 — keep this open:**

```bash
bash scripts/gpu/tunnel.sh
```

**Terminal 2 — all commands below:**

```bash
cd SemaFailBench
source .venv/bin/activate
set -a && source .env && set +a
```

Quick API check:

```bash
curl -s http://127.0.0.1:8000/v1/models | python3 -m json.tool
```

---

## 4) Healthy baseline (do this first on the new model)

```bash
# Start healthy vLLM on the pod
bash scripts/gpu/bootstrap_healthy.sh

# Verify API + record manifest
.venv/bin/python scripts/verify_healthy_restore.py --out results/<model-slug>/healthy_restore_manifest.json
```

Optional smoke (3 canaries):

```bash
sfb run --condition healthy --temperature 0 --split core --limit 3 --warmup
```

Optional full healthy 20×120 (needed as comparison baseline for faults):

```bash
.venv/bin/python scripts/run_healthy_stability.py --repeats 20 --out-dir results/<model-slug>/healthy-stability-120x20
```

---

## 5) Standard protocol for **each fault** (F1–F6)

Same order every time. **Do not skip preflight.**

```
restore healthy → bootstrap fault → isolation gate → preflight → (if OK) 20×120 campaign → restore healthy
```

### Step A — Restore healthy (start here if another fault was running)

```bash
bash scripts/gpu/restore_healthy.sh
.venv/bin/python scripts/verify_healthy_restore.py --out results/<model-slug>/healthy_restore_manifest.json
```

### Step B — Inject the fault (one script per fault)

| Fault | Bootstrap |
|---|---|
| F1 | `bash scripts/gpu/bootstrap_f1.sh` |
| F2 | `bash scripts/gpu/bootstrap_f2.sh` |
| F3 | `bash scripts/gpu/bootstrap_f3.sh` |
| F4 | `bash scripts/gpu/bootstrap_f4.sh` |
| F5 | `bash scripts/gpu/bootstrap_f5.sh` |
| F6 | `bash scripts/gpu/bootstrap_f6.sh` |

Confirm the fault is loaded:

```bash
curl -s http://127.0.0.1:8000/v1/models | python3 -c "import json,sys; print([m['id'] for m in json.load(sys.stdin)['data']])"
```

### Step C — Isolation gate (proves only the intended layer changed)

```bash
OUT=results/<model-slug>/f6-retest   # use f1-retest, f2-retest, etc.

.venv/bin/python scripts/verify_f<N>_isolation.py --out "$OUT/f<N>_isolation_manifest.json"
```

Check `"isolated": true` in the manifest. **If false, stop — do not run 20×.**

(F1 uses a different verification path — see `docs/F1_QUANTIZATION.md`.)

### Step D — Preflight (one full 120-canary pass)

```bash
.venv/bin/python scripts/run_fault_f<N>_stability.py --preflight-only --out-dir "$OUT"
```

Open `results/.../preflight_manifest.json`. Proceed to 20× **only if**:

- `"proceed_to_campaign_recommended": true`
- directional degradation vs healthy is clear
- HTTP 120/120

### Step E — Full campaign (20 × 120 canaries)

```bash
.venv/bin/python scripts/run_fault_f<N>_stability.py --repeats 20 --out-dir "$OUT"
```

**Campaign protocol (all stability runners):**

| Step | What happens |
|---|---|
| Warmup | **5 requests discarded** (global warmup before run 1 for F6; run 1 warmup for F1–F5) |
| Runs 1–20 | **120 core canaries** each (SFC-001 … SFC-120), temp=0, catalog order |
| GPU | Sampled every **2s during each run** + post-run snapshot |
| Output | `run_01_manifest.json` … `run_20_manifest.json`, `campaign_manifest.json`, `docs/F<N>_..._STABILITY_120x20.md` |

Each run manifest and the markdown report include **GPU util/mem/temp/power** and **strict failure tables** per run.

**If a campaign stops mid-way:** rerun from scratch with `--repeats 20` into a **clean** `--out-dir` (do not resume unless you know exactly which runs completed).

### Step F — Restore healthy before the next fault

```bash
bash scripts/gpu/restore_healthy.sh
.venv/bin/python scripts/verify_healthy_restore.py --out results/<model-slug>/healthy_restore_manifest.json
```

---

## 6) Quick smoke scripts (optional, before preflight)

```bash
bash scripts/smoke_f2.sh   # F2
bash scripts/smoke_f3.sh   # F3
bash scripts/smoke_f5.sh   # F5
bash scripts/smoke_f6.sh   # F6 bootstrap + isolation + preflight
```

---

## 7) Suggested order

1. Healthy baseline (verify + optional 20×)
2. F2 → restore healthy  
3. F3 → restore healthy  
4. F4 → restore healthy  
5. F5 → restore healthy  
6. F6 → restore healthy  
7. F1 (AWQ — different serving stack) last, if needed

(F7/F8 retrieval faults are **not** in this repo branch.)

---

## 8) Where results live

| Artifact | Path |
|---|---|
| Per-run scores | `results/<out-dir>/run_XX_*.jsonl` |
| Per-run GPU + failures | `results/<out-dir>/run_XX_manifest.json` |
| Campaign summary | `results/<out-dir>/campaign_manifest.json` |
| Human-readable report | `docs/F<N>_..._STABILITY_120x20.md` |
| Preflight | `results/<out-dir>/preflight_manifest.json` |
| Isolation proof | `results/<out-dir>/f<N>_isolation_manifest.json` |

---

## 9) Troubleshooting

| Problem | Fix |
|---|---|
| `API not reachable` | Restart tunnel: `bash scripts/gpu/tunnel.sh` |
| `SFB_RUNPOD_TCP_HOST not set` | Fill TCP host/port in `.env` (needed for GPU metrics) |
| vLLM won't start / FlashInfer crash | Bootstrap scripts already set `VLLM_USE_FLASHINFER_SAMPLER=0` on 5090 |
| Wrong model still showing | Run `bash scripts/gpu/restore_healthy.sh`, then bootstrap the fault again |
| Pod recreated | Update `.env` SSH + TCP from Connect tab; re-run bootstrap |
| Preflight says do not proceed | Do **not** run 20× — fix fault config or isolation first |

---

## 10) What to push to GitHub

Create a branch per model or per fault campaign:

```bash
git checkout -b retaj/<model-slug>-f6-120x20
git add configs/ .env.example results/<out-dir>/ docs/F6_*.md scripts/
git commit -m "Add <model> F6 stability campaign results."
git push -u origin HEAD
```

Never commit `.env` (secrets / pod-specific).

---

## 11) Copy-paste example — F6 on a new model

```bash
# 1. Tunnel (separate terminal)
bash scripts/gpu/tunnel.sh

# 2. Healthy
bash scripts/gpu/restore_healthy.sh
.venv/bin/python scripts/verify_healthy_restore.py --out results/my-model/healthy_restore_manifest.json

# 3. F6 fault
OUT=results/my-model/f6-retest
mkdir -p "$OUT"
bash scripts/gpu/bootstrap_f6.sh
.venv/bin/python scripts/verify_f6_isolation.py --out "$OUT/f6_isolation_manifest.json"
.venv/bin/python scripts/run_fault_f6_stability.py --preflight-only --out-dir "$OUT"
.venv/bin/python scripts/run_fault_f6_stability.py --repeats 20 --out-dir "$OUT"

# 4. Back to healthy
bash scripts/gpu/restore_healthy.sh
```

Replace `my-model` with a short slug (e.g. `llama-3-8b-instruct`).
