# Gemma 2 9B IT

Same Qwen report layout. **120 × 5**. Scorer `calibrated-2026-08-10`.

Healthy strict mean: **88.5%**. Raw jsonl: `results/healthy-stability-120x5-gemma2/`, `results/f1-gemma2-stability-120x5/`, `results/f2-gemma2-stability-120x5/`, `results/f4-gemma2-stability-120x5/`, `results/f5-gemma2-stability-120x5/`, `results/f6-gemma2-stability-120x5/`.

| Campaign | Strict mean | Δ vs healthy | Report |
|---|---:|---:|---|
| Healthy | 88.5% | — | [HEALTHY_STABILITY_120x5.md](HEALTHY_STABILITY_120x5.md) |
| F1 quantization | 90.8% | +2.3 | [F1_QUANTIZATION_STABILITY_120x5.md](F1_QUANTIZATION_STABILITY_120x5.md) · [protocol](F1_QUANTIZATION.md) |
| F2 checkpoint | 15.0% | −73.5 | [F2_CHECKPOINT_VERSION_STABILITY_120x5.md](F2_CHECKPOINT_VERSION_STABILITY_120x5.md) · [protocol](F2_CHECKPOINT_VERSION.md) |
| F4 chat template | 38.3% | −50.2 | [F4_CHAT_TEMPLATE_MISMATCH_STABILITY_120x5.md](F4_CHAT_TEMPLATE_MISMATCH_STABILITY_120x5.md) · [protocol](F4_CHAT_TEMPLATE_MISMATCH.md) |
| F5 decoding | 88.8% | +0.3 REVIEW | [F5_DECODING_CONFIG_DRIFT_STABILITY_120x5.md](F5_DECODING_CONFIG_DRIFT_STABILITY_120x5.md) · [protocol](F5_DECODING_CONFIG_DRIFT.md) |
| F6 stale LoRA | 9.0% | −79.5 | [F6_LORA_ADAPTER_STABILITY_120x5.md](F6_LORA_ADAPTER_STABILITY_120x5.md) · [protocol](F6_LORA_ADAPTER_MISMATCH.md) |

Extras: [F1 120×1](F1_QUANTIZATION_STABILITY_120x1.md), [post-F1 healthy 120×2](HEALTHY_STABILITY_120x2.md).

**F2** is `gemma-2-9b` base + frozen IT tokenizer (same *kind* as Mistral F2, not Qwen/Llama Instruct→Instruct).

**F4 38.3%** is official template minus generation header. Many replies were empty with HTTP 200. Do not present that number as silent semantic failure. Closer-delete retarget is not in this published folder yet.

**F6** adapter is YouTube-titles LoRA; outputs often looped, still HTTP 200 and isolation PASS.

Back to [all models](../README.md).
