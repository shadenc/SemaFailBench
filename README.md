# SemaFailBench

Silent semantic failures in LLM serving: the API stays up, GPU/latency look healthy, but answers quietly get worse.

**Catalog:** 150 core canaries (`SFC-*`) + 24 held-out (`SFH-*`).  
**Model:** Qwen2.5-7B-Instruct. **This pod:** 1× RTX 5090 (not 2×).

---

## Where to check results (start here)

| What | Open this |
|---|---|
| **Pass 1 summary** (150 canaries, 86% strict) | [docs/HEALTHY_PASS1.md](docs/HEALTHY_PASS1.md) |
| **Which canaries need a fix** (Word — share this) | [docs/PASS1_CANARY_FIX_REVIEW.docx](docs/PASS1_CANARY_FIX_REVIEW.docx) |
| **Raw scores** (one JSON line per canary) | [results/healthy-pass1/](results/healthy-pass1/) |

Pass 1 = **one** healthy deterministic run (warmup 5 discarded + 150 measured).  
**Not done yet:** 20× repeats, stochastic runs, or any fault injection. Review the 21 fails first.

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
