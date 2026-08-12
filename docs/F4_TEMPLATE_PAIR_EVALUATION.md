# F4 template pair evaluation (2026-08-12)

Goal: **realistic deployment fault** + **silent infra** + **measurable semantic drift** on v3 canaries.

## Isolation contract (all variants)

F4 requires: matched Qwen2.5 weights + tokenizer; only vLLM `--chat-template` differs. All tested variants passed `verify_f4_isolation.py`.

## Candidates tested

| Template | Realistic? | Infra silent? | Output silent? | Preflight strict | delta_F4 | Swaps | Verdict |
|---|---|:---:|:---:|---:|---:|---:|---|
| **Mistral v0.3** `[INST]` | Low (cross-family) | Yes | Partial (`[INST]` in ~52% outputs) | 58.3% | +34.2% | 45 | Strong signal; **not realistic** |
| **Zephyr ChatML** (shared default) | High | Yes | Yes | 95.0% | +2.5% | 5 | Realistic; **flat signal** |
| **Phi-3 mini** (shared gateway) | Medium | Yes | Mostly | 92.5% | 0.0% | 6 | Realistic; **flat signal** |
| **Qwen2 official** on Qwen2.5 tok | Highest (stale after upgrade) | Yes | Yes | — | — | — | **Identical token IDs** (no runtime drift) |
| **No assistant gen prompt** (official Qwen2.5 minus final block) | High | Yes | Yes | **61.7%** | **+30.8%** | 41 | **Best realistic candidate** |
| System-stripped ChatML | High | Yes | Yes | 92.5% | 0.0% | 10 | Flat |

Artifacts:
- Mistral: `results/f4-retest/mistral-cross-family-ablation/`
- Zephyr: `results/f4-retest/zephyr-generic-chatml-ablation/`
- Phi-3: `results/f4-retest/phi3-shared-gateway-ablation/`
- **Canonical realistic (current):** `configs/f4_wrong_chat_template_no_gen_prompt.jinja` → `results/f4-retest/`

## Interpretation

1. **Most likely real ops mistakes** (stale Qwen2 template, generic ChatML, missing system role) are **infra-silent** but often **benchmark-flat** on English v3 canaries — same bimodal pattern as F3 same-family tokenizers.

2. **Cross-family templates (Mistral)** move canaries strongly but produce visible delimiter leakage and are **unlikely** in a Qwen-only production line.

3. **Silent failure** should be split:
   - **Deployment/infra silent:** all variants qualify (HTTP 200, GPU loaded, same `/v1/models` id).
   - **Output silent:** realistic variants yes; Mistral partial.

## Recommendation

- **Paper narrative:** F4 realistic = **missing assistant generation header** (edited official Qwen2.5 jinja); strong silent semantic drift (+30.8% preflight).
- **Stress ablation:** keep Mistral run as upper-bound “wrong-family template” (not canonical).
- **Do not** claim Mistral F4 as a typical production regression.

## Canonical config

```yaml
# configs/serving_f4.yaml
wrong_chat_template:
  kind: local
  path: configs/f4_wrong_chat_template_no_gen_prompt.jinja
```

```bash
SFB_F4_TEMPLATE_FILE=configs/f4_wrong_chat_template_no_gen_prompt.jinja
SFB_F4_TEMPLATE_SOURCE=local:no_assistant_gen_prompt
```
