# Implementation log

Append-only. Newest entry at the bottom.

## 2026-08-09 — Step 0: read sources, do not code yet

Read Week-1 deliverables (threat model, fault catalog, taxonomy, matrix, canaries, eval spec, healthy baseline, infra envelope, experiment protocol, traceability), pptx, presenting.docx, Shaden notes, canary redesign docx, literature workbook, and parent `research/` scaffold.

Identified catalog/fault-ID conflicts. Did not start implementation until Excel v3 was treated as source of truth.

## 2026-08-09 — Step 1: Excel → CSV (all sheets)

Converted every sheet of:

- `Coding_part/SemaFailBench_Final_Canary_Dataset_v3_FROZEN.xlsx` (7 sheets)
- `research/Corrected_SemaFailBench_Literature_Review (1).xlsx` (8 sheets)

to UTF-8 CSV under `docs/source_csv/`. Manifest: `docs/source_csv/_manifest.csv`.

Re-export script: `scripts/export_excel_to_csv.py`.

Verified Core_Canaries = 150 unique `SFC-*` IDs, Held_Out = 24 unique `SFH-*` IDs, 5 capabilities × 30, 24 subtypes.

## 2026-08-09 — Step 2: freeze decisions

Wrote `docs/DECISIONS.md`. Executable catalog = v3 CSV. Fault IDs = v2 F1–F8. Protocol = Week-1 baseline/envelope/experiment docs.

## 2026-08-09 — Step 3: publication scaffold in Coding_part

Created package `sem-fail-bench`, configs, schemas, catalog compiler (CSV → YAML + explicit scorer specs), deterministic scorers, OpenAI-compatible runner, provenance hashes, unit tests (no GPU).

## 2026-08-09 — Step 4: compile catalog + unit tests

`scripts/compile_catalog.py` reads Core_Canaries (150) + Held_Out (24) and attaches `SCORER_SPECS` for every ID. Output: `configs/canaries_v3.yaml`.

Scorer types cover all 24 subtypes. Known limitations in `docs/SCORER_CONTRACT.md`. Cap 5 scores in-prompt context (no live retriever). CUDA/vLLM point releases still unpinned until GPU-host install.

`pytest`: 18 passed (catalog invariants, scorer pass/fail pairs, run-record schema, detector metrics). `sfb summary`: 174 items (150 core + 24 held-out). Dedicated `.venv` in this folder so the parent SFB2-162 install is untouched.

## 2026-08-09 — Step 5: RunPod GPU path (blocked on SSH key)

This Mac is M2 Max — no NVIDIA. Target pod from console: `key_fuchsia_hare` / `qp386qvf6p72gg`. Screenshot SSH used `~/.ssh/id_ed25519`, which does not exist on this Mac (`~/.ssh/` had only `known_hosts`).

Generated dedicated key `~/.ssh/sfb_runpod`. User must paste the public key into RunPod Settings and restart the pod. Then: `scripts/gpu/probe.sh` → `bootstrap_healthy.sh` → `tunnel.sh` → local `sfb run`. Docs: `docs/GPU_HOST.md`. CUDA/vLLM still unpinned until probe+bootstrap succeed.

Shell scripts written from this environment had CRLF (`set: pipefail: invalid option name`). Converted repo text to LF and added `.gitattributes` so bash on the Mac/pod does not break again.

## 2026-08-09 — Step 6: RunPod SSH works; healthy vLLM up on 1× 5090

- Key `sfb_runpod` accepted after user added it. RunPod proxy requires a real PTY; added `scripts/gpu/ssh_run.py`.
- Observed hardware (honest, not the 2× design target): **1× RTX 5090**, 32607 MiB, driver **580.159.03**, image CUDA **12.8.1**, Python 3.12.3.
- `pip install vllm` resolved **vLLM 0.26.0** and upgraded torch to **2.11.0+cu130** (recorded, not pre-chosen).
- Hub commit: `a09a35458c702b33eeacc393d103063234e8bc28`.
- First vLLM start died in FlashInfer warmup (`sm75 or higher` — known sm_120 + CUDA 12.8 JIT bug). Restart with `VLLM_USE_FLASHINFER_SAMPLER=0`; attention backend FLASH_ATTN v2. `/v1/models` → 200.
- TCP sshd (`root@213.173.111.179:29086`) works after writing pubkey into container `authorized_keys`. Tunnel: `scripts/gpu/tunnel.sh`.
- Smoke test from Mac: `sfb run --condition healthy --limit 3 --warmup` → **strict_pass_rate 1.0** (SFC-028 seasons order, SFC-051 total=12, SFC-054 sale_price=60). Run id `healthy-20260809T181136Z-39a7f8da`.

## 2026-08-09 — Step 7: team runbook

Wrote `docs/TEAM_RUNBOOK.md` (English) so the rest of the team can reproduce local scoring + RunPod healthy serving. Each teammate generates their own SSH key; CUDA/vLLM pins are not invented.

## 2026-08-09 — Step 8: one healthy deterministic pass (150 core)

Team instruction: one full pass only; no 20× repeats; no fault injection.

- Run id `healthy-20260809T181649Z-a61fb8bf`, ~128 s, warmup=5, temp=0, split=core
- Completeness: 150/150 unique SFC IDs, HTTP 200 all, no empty responses, jsonl + meta + artifact hashes written
- Strict 129/150 = **86.0%**; tolerant 86.7%
- Cap2 30/30; Cap3 29/30; Cap4 26/30; Cap1 23/30; Cap5 21/30
- Summary: `docs/HEALTHY_PASS1.md`

Did not start 20×, stochastic, or F1–F8.

## 2026-08-09 — Step 9: README status for the team

Recorded the above work in `README.md` § Status so teammates see catalog freeze, RunPod pins, pass-1 metrics, and what is still pending without reading the full implementation log.

## 2026-08-09 — Step 10: README operational steps (warmup, etc.)

Expanded `README.md` § Status into the actual run order: catalog freeze → probe → bootstrap → FlashInfer flag → tunnel → 3-canary smoke + 5 discarded warmups → one 150-core deterministic pass (warmup then measure) → what is still not done. Same sequence added at the top of `docs/HEALTHY_PASS1.md` so pass-1 readers see warmup vs measured clearly.

## 2026-08-09 — Step 11: pass-1 canary/scorer review (Word, team share)

Wrote `docs/PASS1_CANARY_FIX_REVIEW.docx`. Classifies all 21 strict fails: A scorer, B design/expected, C true fail keep. Does not start 20× or faults. Flags SFC-097 as the safety-gate blocker.

## 2026-08-09 — Step 12: drop retrieval faults F7 and F8

Pptx numbering: delete **F7** (stale retrieval snapshot) and **F8** (embedding↔index). Keep **F6** LoRA. Cap 5 canaries stay. `configs/faults.yaml` is F1–F6 only.
