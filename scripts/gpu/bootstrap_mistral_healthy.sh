#!/usr/bin/env bash
# Download Mistral-7B-Instruct-v0.3 to the pod GPU and start healthy vLLM.
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
cd "$ROOT"
if [[ -f .env ]]; then set -a; source .env; set +a; fi
# shellcheck source=/dev/null
source "$ROOT/scripts/activate_mistral_profile.sh"
echo "Bootstrapping Mistral healthy vLLM on pod (${SFB_RUNPOD_SSH:-?})"
echo "  model=$SFB_MODEL revision=${SFB_HEALTHY_REVISION:-pin-at-download}"
bash "$ROOT/scripts/gpu/bootstrap_healthy.sh"
