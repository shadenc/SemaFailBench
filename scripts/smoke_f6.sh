#!/usr/bin/env bash
# F6 smoke: bootstrap + isolation gate + preflight (120 canaries, wrong LoRA adapter).
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"
mkdir -p results/f6-retest

echo "== F6 bootstrap =="
bash scripts/gpu/bootstrap_f6.sh

echo "== verify healthy restore manifest =="
if [[ ! -f results/f6-retest/healthy_restore_manifest.json ]]; then
  cp results/n1c8ialve3lv6f/healthy_restore_manifest.json results/f6-retest/healthy_restore_manifest.json 2>/dev/null || \
  cp results/f5-retest/healthy_restore_manifest.json results/f6-retest/healthy_restore_manifest.json 2>/dev/null || true
fi
.venv/bin/python scripts/verify_healthy_restore.py --out results/f6-retest/healthy_restore_manifest.json || true

echo "== F6 isolation gate =="
.venv/bin/python scripts/verify_f6_isolation.py --out results/f6-retest/f6_isolation_manifest.json

echo "== F6 preflight =="
.venv/bin/python scripts/run_fault_f6_stability.py --preflight-only --out-dir results/f6-retest

echo "F6 smoke complete. See results/f6-retest/preflight_manifest.json"
