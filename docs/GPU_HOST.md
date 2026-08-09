# GPU host (RunPod) — how SemaFailBench uses the 5090s

This Mac is the **scoring client**. The RunPod pod is the **serving host**.
vLLM never runs on the Mac.

```
Mac (Coding_part / sfb)  --SSH tunnel :8000-->  RunPod GPU 0  vLLM healthy
                                              RunPod GPU 1  vLLM faulty (later)
```

Do **not** invent CUDA / vLLM / Hub commit numbers. Record whatever the pod actually has after install.

## 0. SSH key (this Mac)

A dedicated key was generated:

- private: `~/.ssh/sfb_runpod`
- public: `~/.ssh/sfb_runpod.pub`

Add the **public** key in RunPod → Settings → SSH Public Keys:

```
ssh-ed25519 AAAAC3NzaC1lZDI1NTE5AAAAIILi1cLU3VpJxpskh5XLBM/4cg+64sEFRfl/dtz2fjyc semafailbench-runpod
```

If the pod was already running when you added the key, **Stop then Start** the pod so `authorized_keys` is injected. Then update the SSH target if the pod id / TCP port changed.

Current pod from the console (update if it changes):

```bash
export SFB_RUNPOD_SSH='qp386qvf6p72gg-64411ac1@ssh.runpod.io'
export SFB_RUNPOD_KEY="$HOME/.ssh/sfb_runpod"
# fallback TCP (also changes on restart):
# export SFB_RUNPOD_SSH='root@213.173.111.179'
# export SFB_RUNPOD_PORT=29086
```

## 1. Probe (from this Mac)

```bash
cd "/Users/alangari/Desktop/SAMA_@/To be Removed/research/Coding_part"
bash scripts/gpu/probe.sh
```

Expected on the **design** target: 2× RTX 5090. Observed on pod `qp386qvf6p72gg`: **1× RTX 5090**. Update `configs/serving.yaml` if the pod changes. Do not claim 2× when only one card is present.

## 2. Bootstrap healthy server (on the pod, via SSH)

```bash
bash scripts/gpu/bootstrap_healthy.sh
```

That script, on the pod:

1. Creates `/workspace/semafailbench/`
2. `pip install vllm` **only if missing** (uses whatever pip resolves for that CUDA)
3. Writes pins: driver, `nvidia-smi`, `pip freeze`, torch/vllm versions
4. Downloads `Qwen/Qwen2.5-7B-Instruct` and records the Hub commit
5. Starts vLLM on **GPU 0**, port **8000**, TP=1, bf16, with `VLLM_USE_FLASHINFER_SAMPLER=0` (required on this 5090 + CUDA 12.8 image; FlashInfer JIT otherwise crashes warmup).

Healthy server stays on GPU 0. GPU 1 is reserved for the faulty twin later.

## 3. Tunnel + smoke test (from this Mac)

Leave bootstrap running on the pod. In another local terminal:

```bash
bash scripts/gpu/tunnel.sh
```

Then:

```bash
source .venv/bin/activate
cp -n .env.example .env
# SFB_BASE_URL=http://127.0.0.1:8000/v1
sfb run --condition healthy --temperature 0 --split core --limit 3 --warmup
```

If 3 canaries return HTTP 200 and scores, run the full healthy protocol (20× temp=0, then 10× stochastic). Do not start fault injection until the stability gate passes.

## 4. Where pins go

On the pod: `/workspace/semafailbench/pins.json`  
Copy that file into this repo as `envs/runpod_healthy_pins.json` (not secrets). Update `configs/serving.yaml` `model.revision` / `tokenizer_revision` from it.

## 5. What not to do yet

- Do not expose vLLM to the public internet without a tunnel or auth.
- Do not install a random “CUDA 12.x” wheel from a blog post. Use the pod’s existing driver + `pip install vllm`.
- Do not start F1–F5 / F8 until the healthy baseline is recorded.
