#!/usr/bin/env bash
# Source before Mistral v0.3 testing: sets config profile + model env vars.
# Usage: source scripts/activate_mistral_profile.sh

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

export SFB_CONFIG_PROFILE=mistral
export SFB_MODEL=mistralai/Mistral-7B-Instruct-v0.3
export SFB_HEALTHY_REVISION=c170c708c41dac9275d15a8fff4eca08d52bab71

# F1 AWQ (weights quantized; keep healthy v0.3 tokenizer/template)
export SFB_F1_MODEL=solidrust/Mistral-7B-Instruct-v0.3-AWQ
export SFB_F1_QUANTIZATION=awq
export SFB_F1_TOKENIZER=mistralai/Mistral-7B-Instruct-v0.3
export SFB_F1_TOKENIZER_REVISION=c170c708c41dac9275d15a8fff4eca08d52bab71

# F2 wrong weights (v0.3 base artifact), frozen instruct v0.3 tokenizer
export SFB_F2_EXPECTED_MODEL=mistralai/Mistral-7B-Instruct-v0.3
export SFB_F2_ACTUAL_MODEL=mistralai/Mistral-7B-v0.3
export SFB_F2_REVISION=caa1feb0e54d415e2df31207e5f4e273e33509b1
export SFB_F2_SERVED_MODEL_NAME=mistralai/Mistral-7B-Instruct-v0.3
export SFB_F2_TOKENIZER=mistralai/Mistral-7B-Instruct-v0.3
export SFB_F2_TOKENIZER_REVISION=c170c708c41dac9275d15a8fff4eca08d52bab71

# F4 wrong Mistral template (official v0.3 jinja with [/INST] closers deleted)
export SFB_F4_MODEL=mistralai/Mistral-7B-Instruct-v0.3
export SFB_F4_MODEL_REVISION=c170c708c41dac9275d15a8fff4eca08d52bab71
export SFB_F4_TOKENIZER=mistralai/Mistral-7B-Instruct-v0.3
export SFB_F4_TOKENIZER_REVISION=c170c708c41dac9275d15a8fff4eca08d52bab71
export SFB_F4_TEMPLATE_FILE=configs/mistral/f4_wrong_chat_template_no_gen_prompt.jinja
export SFB_F4_TEMPLATE_SOURCE=local:no_assistant_gen_prompt
export SFB_F4_SERVED_MODEL_NAME=mistralai/Mistral-7B-Instruct-v0.3

# F5 decoding drift (shared override JSON)
export SFB_F5_MODEL=mistralai/Mistral-7B-Instruct-v0.3
export SFB_F5_MODEL_REVISION=c170c708c41dac9275d15a8fff4eca08d52bab71
export SFB_F5_OVERRIDE_FILE=configs/f5_wrong_generation_config.json
export SFB_F5_OVERRIDE_SOURCE=local:f5_wrong_generation_config
export SFB_F5_SERVED_MODEL_NAME=mistralai/Mistral-7B-Instruct-v0.3

# F6 stale LoRA
export SFB_F6_MODEL=mistralai/Mistral-7B-Instruct-v0.3
export SFB_F6_MODEL_REVISION=c170c708c41dac9275d15a8fff4eca08d52bab71
export SFB_F6_LORA_REPO=dpevzner/CyberOps_Mistral_7B_LoRA
export SFB_F6_LORA_MODULE=stale-cyber-lora
export SFB_F6_MAX_LORA_RANK=16
export SFB_F6_SERVED_MODEL_NAME=mistralai/Mistral-7B-Instruct-v0.3

echo "Mistral profile active (SFB_CONFIG_PROFILE=$SFB_CONFIG_PROFILE)"
echo "Healthy model: $SFB_MODEL"
