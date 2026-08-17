# Mistral 7B Instruct v0.3

Same Qwen report layout. **120 × 5** (F4 report is 3×120). Scorer `calibrated-2026-08-10`.

Healthy strict mean: **79.2%**. Original branches: `retaj/mistral-v03-healthy-5x` … `retaj/mistral-v03-f6-5x`. Raw jsonl lives on those branches under `results/mistral-v03/`.

| Campaign | Strict mean | Δ vs healthy | Report |
|---|---:|---:|---|
| Healthy | 79.2% | — | [HEALTHY_STABILITY_120x5.md](HEALTHY_STABILITY_120x5.md) |
| F1 quantization | 76.7% | −2.5 | [F1_QUANTIZATION_STABILITY_120x5.md](F1_QUANTIZATION_STABILITY_120x5.md) |
| F2 checkpoint | 13.3% | −65.9 | [F2_CHECKPOINT_VERSION_STABILITY_120x5.md](F2_CHECKPOINT_VERSION_STABILITY_120x5.md) |
| F4 chat template | 43.3% | −35.9 | [F4_CHAT_TEMPLATE_MISMATCH_STABILITY_120x5.md](F4_CHAT_TEMPLATE_MISMATCH_STABILITY_120x5.md) |
| F5 decoding | 76.3% | −2.9 | [F5_DECODING_CONFIG_DRIFT_STABILITY_120x5.md](F5_DECODING_CONFIG_DRIFT_STABILITY_120x5.md) |
| F6 stale LoRA | 46.3% | −32.9 | [F6_LORA_ADAPTER_STABILITY_120x5.md](F6_LORA_ADAPTER_STABILITY_120x5.md) |

Notes: [MISTRAL_V03_TESTING.md](MISTRAL_V03_TESTING.md). F2 = base `Mistral-7B-v0.3` + frozen v0.3 Instruct tokenizer. F4 = delete `[/INST]` closers, keep generation.

Back to [all models](../README.md).
