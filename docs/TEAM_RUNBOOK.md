# SemaFailBench — team runbook

How to run this repo and how to repeat the RunPod GPU setup from 9 August 2026.

**Results (pass 1):** see the GitHub README → *Where to check results*.  
**Executable catalog:** frozen Excel v3 in this folder (`SFC-*` + `SFH-*`), not the old SFB2-162 suite.

Design freeze: `docs/DECISIONS.md`  
Scorer contract: `docs/SCORER_CONTRACT.md`  
GPU host notes: `docs/GPU_HOST.md`  
Implementation log: `docs/IMPLEMENTATION_LOG.md`

---

## 1) Architecture

Your laptop is the **scoring client** (`sfb`).  
RunPod is the **serving host** (vLLM + Qwen2.5-7B-Instruct).

```
Your machine (Coding_part / sfb)
        │  SSH tunnel  :8000
        ▼
RunPod GPU 0  →  vLLM healthy   http://127.0.0.1:8000/v1
RunPod GPU 1  →  vLLM faulty    (later; the current pod has only one GPU)
```

Do not run vLLM on the laptop. Do not invent CUDA / vLLM / Hub commit numbers. Record whatever the pod actually installs.

---

## 2) Local setup (no GPU)

```bash
git clone https://github.com/shadenc/SemaFailBench.git
cd SemaFailBench
python3.11 -m venv .venv
source .venv/bin/activate
pip install -U pip
pip install -e ".[dev]"
python scripts/compile_catalog.py
pytest
sfb summary
```

Expected:

- `pytest`: 18 passed
- `sfb summary`: suite `v3-frozen`, **174** items (150 core + 24 held-out)

Offline score without a server:

```bash
sfb score --canary-id SFC-061 --response "Paris"
```

---

## 3) Create your own SSH key (required)

**Each teammate must generate their own key.** Do not copy someone else’s private key (`sfb_runpod` without `.pub`). Do not commit private keys to git.

### 3.1 Generate the key on your machine

```bash
ssh-keygen -t ed25519 -f "$HOME/.ssh/sfb_runpod" -N "" -C "semafailbench-runpod-$(whoami)"
chmod 600 "$HOME/.ssh/sfb_runpod"
cat "$HOME/.ssh/sfb_runpod.pub"
```

That prints **one line** starting with `ssh-ed25519 ...`. That is the **public** key.

### 3.2 Add the public key to RunPod

1. Open [RunPod](https://console.runpod.io) → **Settings → SSH Public Keys**.
2. Paste the full public-key line and save.
3. If the pod was already running, **Stop then Start** it. RunPod injects keys into the pod only at boot.
4. After restart, open the pod **Connect** tab and copy the new SSH target if the pod id or TCP port changed.

You can add several public keys on the same RunPod account. Each laptop should have its own.

### 3.3 Check that SSH works

```bash
export SFB_RUNPOD_SSH='qp386qvf6p72gg-64411ac1@ssh.runpod.io'
export SFB_RUNPOD_KEY="$HOME/.ssh/sfb_runpod"
# Direct TCP (changes after restart — copy from Connect):
export SFB_RUNPOD_TCP_HOST='213.173.111.179'
export SFB_RUNPOD_TCP_PORT=29086

bash scripts/gpu/probe.sh
```

`Permission denied (publickey)` means the public key is missing from Settings, or the pod was not restarted after you added it.

The RunPod proxy (`*.ssh.runpod.io`) **requires a PTY**. Use `scripts/gpu/probe.sh` / `scripts/gpu/ssh_run.py`. A bare `ssh host 'command'` often returns:

`Error: Your SSH client doesn't support PTY`

---

## 4) Start the healthy vLLM server

```bash
bash scripts/gpu/bootstrap_healthy.sh
```

On the pod this script:

1. Creates `/workspace/semafailbench/`
2. Appends **your** public key to `/root/.ssh/authorized_keys` (so the TCP tunnel works without a PTY)
3. Installs `vllm` only if missing (`pip install vllm` — whatever pip resolves for that CUDA)
4. Downloads `Qwen/Qwen2.5-7B-Instruct` and records the Hub commit
5. Writes `pins.json` + `pip_freeze.txt`
6. Starts vLLM on **GPU 0**, port **8000**, TP=1, bf16, with `VLLM_USE_FLASHINFER_SAMPLER=0`

### Why FlashInfer is off

On RTX 5090 (sm_120) + CUDA toolkit 12.8, FlashInfer JIT dies during warmup with a misleading:

`RuntimeError: FlashInfer requires GPUs with sm75 or higher`

This is a known vLLM 0.26 issue. The documented workaround is `VLLM_USE_FLASHINFER_SAMPLER=0` (native sampler). Do not upgrade CUDA to a blog-post version. See:  
https://github.com/vllm-project/vllm/issues/50705

The RunPod template also sets `NVIDIA_VISIBLE_DEVICES=void`. The script unsets that and sets `0`.

---

## 5) Tunnel + smoke test from your laptop

Terminal 1 (leave it open):

```bash
bash scripts/gpu/tunnel.sh
```

Terminal 2:

```bash
source .venv/bin/activate
cp -n .env.example .env
# SFB_BASE_URL=http://127.0.0.1:8000/v1
curl -sS http://127.0.0.1:8000/v1/models
sfb run --condition healthy --temperature 0 --split core --limit 3 --warmup
```

Expected: `strict_pass_rate` near 1.0 and a file under `outputs/runs/`.

First smoke test that passed (9 August 2026):

| Canary | Result |
|---|---|
| SFC-028 season order | pass |
| SFC-051 `total == 12` | pass |
| SFC-054 `sale_price == 60` | pass |

Run id: `healthy-20260809T181136Z-39a7f8da`

---

## 6) Full healthy protocol (before any fault)

From the Week-1 docs. Do not start F1–F5 / F8 until this gate passes. Retrieval faults were deleted.

1. 5 discarded warmup requests
2. **20** deterministic suite runs: `temperature=0`, concurrency=1
3. **10** stochastic runs: `temperature=0.7`, `top_p=0.9`, seeds `0..9`
4. Stability gate: ≥95% strict agreement on ordinary canaries; safety 100%

One deterministic pass over all 150 core canaries:

```bash
sfb run --condition healthy --temperature 0 --split core --warmup
```

Results: `outputs/runs/<run_id>.jsonl` + `.meta.json`

Copy from the pod into this repo (no secrets):

```text
/workspace/semafailbench/pins.json      →  envs/runpod_healthy_pins.json
/workspace/semafailbench/pip_freeze.txt →  envs/runpod_pip_freeze.txt
```

Update `configs/serving.yaml` `model.revision` and `tokenizer_revision` from `pins.json`.

---

## 7) Pins recorded on pod `qp386qvf6p72gg`

These numbers were **observed**, not chosen in advance. Re-measure on a new pod.

| Item | Value |
|---|---|
| Pod | `key_fuchsia_hare` / `qp386qvf6p72gg` |
| GPU | **1× RTX 5090** (32607 MiB) — design target was 2× |
| Driver | 580.159.03 |
| CUDA (image) | 12.8.1 |
| Python on pod | 3.12.3 |
| vLLM | 0.26.0 |
| torch after `pip install vllm` | 2.11.0+cu130 |
| Model | `Qwen/Qwen2.5-7B-Instruct` |
| Hub revision | `a09a35458c702b33eeacc393d103063234e8bc28` |
| dtype / TP / max_model_len | bf16 / 1 / 8192 |
| Sampler | `VLLM_USE_FLASHINFER_SAMPLER=0` |
| Attention | FLASH_ATTN v2 |

**Scientific honesty:** this pod has one GPU. Do not write “2× RTX 5090” for this session. The faulty twin needs a second pod or a later swap on the same card.

---

## 8) Problems we hit

| Symptom | Cause | Fix |
|---|---|---|
| `set: pipefail: invalid option name` | CRLF in shell scripts | `.gitattributes` + LF; do not save `.sh` with Windows endings |
| `Permission denied (publickey)` | Your public key is not on RunPod, or the pod was not restarted | Add **your** key, then Stop/Start |
| `Your SSH client doesn't support PTY` | RunPod proxy without a TTY | Use `scripts/gpu/probe.sh` / `ssh_run.py` |
| FlashInfer `sm75 or higher` | 5090 + CUDA 12.8 JIT | `VLLM_USE_FLASHINFER_SAMPLER=0` |
| `NVIDIA_VISIBLE_DEVICES=void` | RunPod template | Script sets it to `0` |
| pip moved torch from cu128 to cu130 | vLLM 0.26 dependency | Record the new version in `pins.json`; do not revert without a reason |

---

## 9) Layout that matters

```
Coding_part/
  configs/canaries_v3.yaml     ← executable catalog (from CSV)
  configs/serving.yaml         ← serving envelope + pins
  configs/faults.yaml          ← F1–F5 + F8 only
  docs/source_csv/             ← every Excel sheet
  docs/TEAM_RUNBOOK.md         ← this file
  scripts/gpu/                 ← probe / bootstrap / tunnel / ssh_run
  outputs/runs/                ← sfb run results (gitignored)
  envs/                        ← pins copied off the pod
```

If the frozen Excel workbook changes:

```bash
python scripts/export_excel_to_csv.py
python scripts/compile_catalog.py
pytest
```

---

## 10) Do not do this yet

- Do not expose port 8000 on the public internet without a tunnel or auth.
- Do not start F1–F5 / F8 before the healthy baseline and stability gate.
- Do not use the Week-1 `CAN-C*` catalog or SFB2-162 as the running suite.
- Do not invent a CUDA version “that supports Blackwell” from social media.
- Do not share or commit `~/.ssh/sfb_runpod` (private key).

---

## 11) Daily commands once the pod is up

```bash
# 1) Keep the tunnel open
bash scripts/gpu/tunnel.sh

# 2) From a second terminal
source .venv/bin/activate
curl -sS http://127.0.0.1:8000/v1/models
sfb run --condition healthy --temperature 0 --split core --limit 3
```

If vLLM died (a pod restart clears RAM; weights stay under `/workspace/.cache`):

```bash
bash scripts/gpu/bootstrap_healthy.sh
```

Weights stay cached; `pip install vllm` is skipped if `import vllm` already works.
