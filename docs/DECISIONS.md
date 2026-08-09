# SemaFailBench — frozen implementation decisions

Recorded 2026-08-09 before code was written. If a later document conflicts with this file, stop and update this file first.

## Catalog of record

**Frozen Excel v3** in this folder:

`SemaFailBench_Final_Canary_Dataset_v3_FROZEN.xlsx`

Machine-readable export (every sheet):

`docs/source_csv/SemaFailBench_Final_Canary_Dataset_v3_FROZEN/`

| Sheet | Role |
|---|---|
| README | Freeze determination, 5×24 taxonomy |
| Core_Canaries | 150 `SFC-*` items — monitoring suite |
| Held_Out_Generalization | 24 `SFH-*` items — 1 per subtype, Week 3–4 |
| Prompt_Audit | v1→v2 history |
| Final_Peer_Review_Audit | v3 keep/modify/replace |
| Coverage_Summary | counts |
| Removed_Replaced | why items were replaced |

**Not used as the executable catalog**

- Week-1 26-canary `CAN-C*` / C1–C9 suite
- SFB2 redesign 162 `SFB2-*` / 20-subtype suite (parent `research/` scaffold)

Those remain historical sources. Prompts, expected behaviors, and subtype names for code come only from v3 CSV.

## Fault IDs (pptx numbering)

| ID | Fault | This milestone |
|---|---|---|
| F1 | Quantization regression | core |
| F2 | Checkpoint / revision drift | core |
| F3 | Tokenizer–checkpoint mismatch | core |
| F4 | Chat-template mismatch | core |
| F5 | Decoding-config drift | core |
| F6 | Wrong / stale LoRA adapter | core |

**Deleted:** F7 stale retrieval snapshot + F8 embedding↔index mismatch. No live RAG. Cap 5 canaries stay (context in the prompt). Week-1 F01–F11 numbering is **not** used in code.

Excel `Faults Potentially Sensitive To` used older v2 IDs (LoRA as F8). Compile remaps that metadata to pptx IDs (LoRA → F6) and drops F7/F8.

## Capabilities / subtypes (v3)

1. Instruction-following Fidelity — Quantitative Constraint, Keyword Inclusion, Keyword Exclusion, Structural Formatting, Response Language, Ordering
2. Structured-output Validity & Value Accuracy — Flat Schema, Nested Schema, Type Strictness, Enum Constraint, Value Accuracy, Array Structure
3. Factual / Knowledge Recall — Common Fact, Numerical Fact, Entity Relation, Negative Fact/Misconception
4. Safety / Alignment Stability — Refusal Calibration, Safe Assistance, Context-sensitive Safety
5. Retrieval-grounded Response Fidelity — Single-Fact, Multi-Fact, Distractor Rejection, Missing Evidence, Evidence Fidelity

Cap 5 v3 items **embed context in the prompt**. They do not require a live retriever to score. Retrieval faults were deleted from `configs/faults.yaml`.

## Protocol (Week-1 deliverables, still binding)

- Model: `Qwen/Qwen2.5-7B-Instruct`, TP=1, Hub commit pinned at download
- Healthy: no LoRA, matching tokenizer, official chat template
- Warm-up: 5 discarded requests
- Deterministic: 20× temp=0, concurrency=1, shuffled order
- Stochastic: 10× temp=0.7 / top_p=0.9, seeds 0–9, separate regime
- Stability gate: ≥95% strict agreement; safety canaries 100%
- GPU 0 = healthy, GPU 1 = faulty; exactly one artifact hash per fault run
- Deterministic scorers only on the strict path (no LLM-as-judge)
- CUDA / vLLM point releases are **not invented**; pin on the 5090 host

## Scoring honesty

Difficulty labels are **not empirically calibrated**. Cap 3 difficulty is explicitly provisional.

Safe Assistance concept checklists use synonym families, not a single gold sentence. False negatives on unusual paraphrases are expected and documented in scorer details.

Language-ID uses `langdetect` (pinned). Short replies can be unstable; that is a known scorer limitation, not a silent fallback.
