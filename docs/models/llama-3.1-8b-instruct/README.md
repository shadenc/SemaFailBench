# Llama 3.1 8B Instruct

Same Qwen report layout. **120 × 5** (not 20). Scorer `calibrated-2026-08-10`.

Healthy strict mean: **96.7%**. Raw jsonl: `results/healthy-stability-120x5-llama31/`, `results/f1-llama31-stability-120x5/`, `results/f2-llama31-stability-120x5/`, `results/f4-llama31-stability-120x5/`, `results/f5-llama31-stability-120x5/`, `results/f6-llama31-stability-120x5/`.

| Campaign | Strict mean | Δ vs healthy | Report |
|---|---:|---:|---|
| Healthy | 96.7% | — | [HEALTHY_STABILITY_120x5.md](HEALTHY_STABILITY_120x5.md) |
| F1 quantization | 95.0% | −1.7 | [F1_QUANTIZATION_STABILITY_120x5.md](F1_QUANTIZATION_STABILITY_120x5.md) · [protocol](F1_QUANTIZATION.md) |
| F2 checkpoint | 92.5% | −4.2 | [F2_CHECKPOINT_VERSION_STABILITY_120x5.md](F2_CHECKPOINT_VERSION_STABILITY_120x5.md) · [protocol](F2_CHECKPOINT_VERSION.md) |
| F4 chat template | 76.7% | −20.0 | [F4_CHAT_TEMPLATE_MISMATCH_STABILITY_120x5.md](F4_CHAT_TEMPLATE_MISMATCH_STABILITY_120x5.md) · [protocol](F4_CHAT_TEMPLATE_MISMATCH.md) |
| F5 decoding | 87.2% | −9.5 REVIEW | [F5_DECODING_CONFIG_DRIFT_STABILITY_120x5.md](F5_DECODING_CONFIG_DRIFT_STABILITY_120x5.md) · [protocol](F5_DECODING_CONFIG_DRIFT.md) |
| F6 stale LoRA | 75.0% | −21.7 | [F6_LORA_ADAPTER_STABILITY_120x5.md](F6_LORA_ADAPTER_STABILITY_120x5.md) · [protocol](F6_LORA_ADAPTER_MISMATCH.md) |

F2 = Llama 3 Instruct weights, frozen Llama 3.1 tokenizer. F4 = official template minus generation header (same idea as Qwen).

Back to [all models](../README.md).
