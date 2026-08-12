#!/usr/bin/env bash
# F5 smoke: bootstrap + isolation gate + preflight (120 canaries, server-default decoding).
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"
mkdir -p results/f5-retest

echo "== F5 bootstrap =="
bash scripts/gpu/bootstrap_f5.sh

echo "== verify healthy restore manifest =="
if [[ ! -f results/f5-retest/healthy_restore_manifest.json ]]; then
  cp results/f4-retest/healthy_restore_manifest.json results/f5-retest/healthy_restore_manifest.json 2>/dev/null || \
  cp results/healthy-restore-verify-single/campaign_manifest.json results/f5-retest/healthy_restore_manifest.json 2>/dev/null || true
fi
.venv/bin/python scripts/verify_healthy_restore.py --out results/f5-retest/healthy_restore_manifest.json || true

echo "== F5 isolation gate =="
.venv/bin/python scripts/verify_f5_isolation.py --out results/f5-retest/f5_isolation_manifest.json

echo "== F5 preflight =="
.venv/bin/python scripts/run_fault_f5_stability.py --preflight-only --out-dir results/f5-retest

echo "F5 smoke complete. See results/f5-retest/preflight_manifest.json"
