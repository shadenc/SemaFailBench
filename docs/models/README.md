# Model results — start here

Same report design as Qwen: one Markdown file per campaign, campaign summary, per-run table, GPU envelope, then per-run details. Raw jsonl stays under `results/`.

**One GitHub branch** holds this index: [`alangari/gemma2-9b-it-120x5`](https://github.com/shadenc/SemaFailBench/tree/alangari/gemma2-9b-it-120x5).

## Folders

| Model | Repeats | Open |
|---|---|---|
| Qwen2.5-7B-Instruct | 120×20 | [qwen2.5-7b-instruct/](qwen2.5-7b-instruct/) |
| Llama 3.1 8B Instruct | 120×5 | [llama-3.1-8b-instruct/](llama-3.1-8b-instruct/) |
| Gemma 2 9B IT | 120×5 | [gemma-2-9b-it/](gemma-2-9b-it/) |
| Mistral 7B Instruct v0.3 | 120×5 | [mistral-7b-instruct-v0.3/](mistral-7b-instruct-v0.3/) |

F3 skipped on every family. Scorer: `calibrated-2026-08-10`.

## How to read one report

1. **Campaign summary** — strict mean, min–max, HTTP 200, stability gate, delta vs healthy.
2. **Per-run table** — five or twenty rows; same columns as Qwen (strict, latency, GPU).
3. **GPU envelope** — util / mem / temp / power during inference (infra-silent check).
4. **Per-run details** — which canaries failed.
5. **Raw scores** — path at the top of the file (`results/…`).

To compare the same fault across models, open the same filename in two folders, e.g. `F4_CHAT_TEMPLATE_MISMATCH_STABILITY_120x5.md` vs Qwen’s `…_120x20.md`.

## Strict mean (locked campaigns)

Delta = fault − healthy, in percentage points.

| | Qwen 120×20 | Llama 120×5 | Gemma 120×5 | Mistral 120×5 |
|---|---:|---:|---:|---:|
| Healthy | **92.5%** | **96.7%** | **88.5%** | **79.2%** |
| F1 quantization | 92.5% (0.0) | 95.0% (−1.7) | 90.8% (+2.3) | 76.7% (−2.5) |
| F2 checkpoint | 90.8% (−1.7) | 92.5% (−4.2) | 15.0% (−73.5) | 13.3% (−65.9) |
| F4 chat template | 61.7% (−30.8) | 76.7% (−20.0) | 38.3% (−50.2) | 43.3% (−35.9) |
| F5 decoding config | 90.8% (−1.7) REVIEW | 87.2% (−9.5) REVIEW | 88.8% (+0.3) REVIEW | 76.3% (−2.9) |
| F6 stale LoRA | 86.7% (−5.8) | 75.0% (−21.7) | 9.0% (−79.5) | 46.3% (−32.9) |

## Do not treat every column as the same construction

| Fault | Qwen / Llama | Gemma / Mistral |
|---|---|---|
| F2 | Older **Instruct** checkpoint, frozen healthy tokenizer | **Base** (non-IT) weights, frozen IT tokenizer |
| F4 | Official template minus generation header | Family closer-delete (Mistral `[/INST]`). Gemma’s **published** 38.3% is generation-header deletion and produced many empty HTTP 200 replies — not silent semantic failure |
| F5 | Stochastic by design; stability gate may be REVIEW | Same |
| F6 | Different wrong-task adapters per family | Gemma YouTube-titles LoRA; others tool-call / NemoGuard / CyberOps |

Mistral F4 campaign is 3×120 in the report (not 5). Gemma F1 rose vs healthy; still isolated AWQ.
