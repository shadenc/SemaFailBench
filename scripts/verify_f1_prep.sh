#!/usr/bin/env bash
# Local preflight for F1 injection (no pod required). Run from repo root.
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"
FAIL=0

check() {
  if "$@"; then
    echo "OK  $*"
  else
    echo "FAIL $*"
    FAIL=1
  fi
}

echo "=== F1 prep verification ==="

check test -f configs/serving_f1.yaml
check test -f configs/faults.yaml
check test -f docs/F1_QUANTIZATION.md
check test -f scripts/gpu/bootstrap_f1.sh
check test -f scripts/gpu/remote_bootstrap_f1.sh
check test -f scripts/gpu/restore_healthy.sh
check test -f scripts/smoke_f1.sh
check test -f scripts/run_fault_f1.py

for s in scripts/gpu/bootstrap_f1.sh scripts/gpu/remote_bootstrap_f1.sh \
         scripts/gpu/restore_healthy.sh scripts/smoke_f1.sh; do
  check bash -n "$s"
done

source .venv/bin/activate 2>/dev/null || true
check python3 -c "
import yaml
from pathlib import Path
cfg = yaml.safe_load(Path('configs/serving_f1.yaml').read_text())
assert cfg['fault_id'] == 'F1'
assert cfg['model']['quantization'] in {'awq', 'awq_marlin'}
assert 'AWQ' in cfg['model']['repo']
"

check python3 -c "
import importlib.util
from pathlib import Path
spec = importlib.util.spec_from_file_location('run_fault_f1', Path('scripts/run_fault_f1.py'))
mod = importlib.util.module_from_spec(spec)
# import-only smoke (does not call main)
assert spec.loader is not None
"

if [[ -f .env ]]; then
  set -a; source .env; set +a
  echo "env SFB_F1_MODEL=${SFB_F1_MODEL:-<unset>}"
  echo "env SFB_RUNPOD_SSH=${SFB_RUNPOD_SSH:-<unset>}"
  echo "env SFB_RUNPOD_TCP_HOST=${SFB_RUNPOD_TCP_HOST:-<unset>}"
else
  echo "WARN .env missing — copy .env.example and set RunPod credentials"
fi

code="000"
if curl -s -o /dev/null -w "%{http_code}" --connect-timeout 2 http://127.0.0.1:8000/v1/models >/tmp/sfb_verify_http 2>/dev/null; then
  code="$(cat /tmp/sfb_verify_http)"
fi
if [[ "$code" == "200" ]]; then
  echo "OK  tunnel/API reachable (HTTP 200) — run: bash scripts/smoke_f1.sh"
else
  echo "SKIP tunnel/API not up (HTTP $code) — start pod + tunnel before smoke"
fi

check test -f results/healthy-stability-120x5-llama31/campaign_manifest.json

echo "=== done ==="
exit "$FAIL"
