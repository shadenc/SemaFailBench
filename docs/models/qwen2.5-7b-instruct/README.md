# Qwen2.5-7B-Instruct

Leader protocol. **120 core canaries × 20** deterministic passes. Scorer `calibrated-2026-08-10`.

Healthy strict mean: **92.5%**. Raw jsonl: `results/healthy-stability-120x20-v2/`, `results/fault-f1-stability-120x20/`, `results/f2-retest/`, `results/f4-retest/`, `results/f5-retest/`, `results/f6-retest/`.

| Campaign | Strict mean | Δ vs healthy | Report |
|---|---:|---:|---|
| Healthy | 92.5% | — | [HEALTHY_STABILITY_120x20.md](HEALTHY_STABILITY_120x20.md) |
| F1 quantization | 92.5% | 0.0 | [F1_QUANTIZATION_STABILITY_120x20.md](F1_QUANTIZATION_STABILITY_120x20.md) · [protocol](F1_QUANTIZATION.md) |
| F2 checkpoint | 90.8% | −1.7 | [F2_CHECKPOINT_VERSION_STABILITY_120x20.md](F2_CHECKPOINT_VERSION_STABILITY_120x20.md) · [protocol](F2_CHECKPOINT_VERSION.md) |
| F4 chat template | 61.7% | −30.8 | [F4_CHAT_TEMPLATE_MISMATCH_STABILITY_120x20.md](F4_CHAT_TEMPLATE_MISMATCH_STABILITY_120x20.md) · [protocol](F4_CHAT_TEMPLATE_MISMATCH.md) · [template pair eval](F4_TEMPLATE_PAIR_EVALUATION.md) |
| F5 decoding | 90.8% | −1.7 REVIEW | [F5_DECODING_CONFIG_DRIFT_STABILITY_120x20.md](F5_DECODING_CONFIG_DRIFT_STABILITY_120x20.md) · [protocol](F5_DECODING_CONFIG_DRIFT.md) |
| F6 stale LoRA | 86.7% | −5.8 | [F6_LORA_ADAPTER_STABILITY_120x20.md](F6_LORA_ADAPTER_STABILITY_120x20.md) · [protocol](F6_LORA_ADAPTER_MISMATCH.md) |

Back to [all models](../README.md).
