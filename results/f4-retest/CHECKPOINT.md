# F4 retest checkpoint — paused for pod recharge

**Date:** 2026-08-12 (updated after recharge)  
**Pod:** `2pr0ssumaq3ue4` — `key_fuchsia_hare-migration-migration-migration`  
**TCP:** `root@213.173.111.174:44748`  
**Proxy SSH:** `2pr0ssumaq3ue4-64411ab9@ssh.runpod.io`  
**Status:** Pod running; SSH blocked until `sfb_runpod.pub` is added to RunPod account keys.

## Completed locally

- [x] F4 config: `configs/serving_f4.yaml`
- [x] Bootstrap: `scripts/gpu/bootstrap_f4.sh`, `remote_bootstrap_f4.sh`
- [x] Isolation verifier: `scripts/verify_f4_isolation.py`
- [x] Runner: `scripts/run_fault_f4_stability.py` (compiles OK)
- [x] `remote_stop_vllm.sh` updated for `vllm_f4.pid`
- [x] Resume doc: `docs/F4_CHAT_TEMPLATE_MISMATCH.md`

## Completed on pod (may be lost if pod terminated)

- [x] `restore_healthy.sh` ran — Qwen2.5 @ `a09a354…`, vLLM pid 9706 started
- [ ] Healthy verify manifest **not written** (tunnel never connected)
- [ ] F4 bootstrap **not run**
- [ ] Preflight **not run**

## Next session (in order)

1. Recharge pod / confirm same pod or update `.env` TCP host+port
2. `bash scripts/gpu/restore_healthy.sh`
3. `bash scripts/gpu/tunnel.sh` → confirm `curl localhost:8000/v1/models`
4. `python3 scripts/verify_healthy_restore.py --out results/f4-retest/healthy_restore_manifest.json`
5. `bash scripts/gpu/bootstrap_f4.sh`
6. `python3 scripts/verify_f4_isolation.py`
7. `python3 scripts/run_fault_f4_stability.py --preflight-only`

## Git status (uncommitted — save before switching machines)

Untracked/modified F4-related + F3 (skipped) work — run `git status` and commit when ready.

## Baselines (unchanged)

| Condition | Strict mean | Location |
|---|---:|---|
| Healthy v2 | 92.5% | `results/healthy-stability-120x20-v2/` |
| F2 retest | 90.8% | `results/f2-retest/` |
| F3 | skipped | — |
| F4 | pending | this directory |
