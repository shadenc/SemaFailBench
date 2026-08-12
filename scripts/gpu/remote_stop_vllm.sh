#!/usr/bin/env bash
# Stop any vLLM api_server on the pod (healthy or F1).
set +e
WORKDIR="${SFB_POD_WORKDIR:-/workspace/semafailbench}"
for pidfile in "$WORKDIR/vllm_healthy.pid" "$WORKDIR/vllm_f1.pid" "$WORKDIR/vllm_f2.pid" "$WORKDIR/vllm_f3.pid" "$WORKDIR/vllm_f4.pid" "$WORKDIR/vllm_f5.pid"; do
  if [[ -f "$pidfile" ]]; then
    pid="$(cat "$pidfile")"
    if kill -0 "$pid" 2>/dev/null; then
      echo "Stopping vLLM pid=$pid ($pidfile)"
      kill "$pid" 2>/dev/null
      sleep 3
      kill -9 "$pid" 2>/dev/null || true
    fi
    rm -f "$pidfile"
  fi
done
pkill -f 'vllm.entrypoints.openai.api_server' 2>/dev/null || true
sleep 2
pgrep -af vllm || echo "No vLLM processes"
