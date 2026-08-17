# SemaFailBench

Silent semantic failures in LLM serving: the API stays up, GPU/latency look healthy, but answers quietly get worse.

**Catalog:** 150 core canaries (`SFC-*`) + 24 held-out (`SFH-*`).  
**Model:** Qwen2.5-7B-Instruct. **This pod:** 1× RTX 5090 (not 2×).  
**Faults later:** F1–F6 only (F6 = LoRA). **Deleted:** F7 and F8 (retrieval). Cap 5 canaries stay.

---

## Where to check results (start here)

| What | Open this |
|---|---|
| **All models (comparison + folders)** | [docs/models/README.md](docs/models/README.md) |
| Qwen 120×20 | [docs/models/qwen2.5-7b-instruct/](docs/models/qwen2.5-7b-instruct/) |
| Llama 120×5 | [docs/models/llama-3.1-8b-instruct/](docs/models/llama-3.1-8b-instruct/) |
| Gemma 120×5 | [docs/models/gemma-2-9b-it/](docs/models/gemma-2-9b-it/) |
| Mistral 120×5 | [docs/models/mistral-7b-instruct-v0.3/](docs/models/mistral-7b-instruct-v0.3/) |

Same MD design as the original Qwen reports (summary → per-run table → GPU → canary details). Pass 1 / early Qwen baselines remain at [docs/HEALTHY_PASS1.md](docs/HEALTHY_PASS1.md).

---

## First-time setup (laptop, no GPU)

```bash
git clone https://github.com/shadenc/SemaFailBench.git
cd SemaFailBench
python3.11 -m venv .venv
source .venv/bin/activate
pip install -U pip && pip install -e ".[dev]"
pytest          # expect 18 passed
sfb summary     # expect 174 items
```

---

## GPU / RunPod

Each person creates **their own SSH key**. Do not copy a teammate’s private key.

Full beginner steps: **[docs/TEAM_RUNBOOK.md](docs/TEAM_RUNBOOK.md)**

---

## Other docs

| File | What it is |
|---|---|
| [docs/TEAM_RUNBOOK.md](docs/TEAM_RUNBOOK.md) | How to run locally + RunPod |
| [docs/SCORER_CONTRACT.md](docs/SCORER_CONTRACT.md) | How scoring works |
| [docs/DECISIONS.md](docs/DECISIONS.md) | Frozen catalog decisions |
| [docs/IMPLEMENTATION_LOG.md](docs/IMPLEMENTATION_LOG.md) | What we already did, in order |
| [docs/GPU_HOST.md](docs/GPU_HOST.md) | GPU pin notes |
