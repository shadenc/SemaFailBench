#!/usr/bin/env bash
# Forward local :8000 to the pod vLLM. Prefer direct TCP sshd (no PTY needed).
set -euo pipefail

SSH_KEY="${SFB_RUNPOD_KEY:-$HOME/.ssh/sfb_runpod}"
LOCAL_PORT="${SFB_LOCAL_PORT:-8000}"
REMOTE_PORT="${SFB_REMOTE_PORT:-8000}"

if [[ -n "${SFB_RUNPOD_TCP_HOST:-}" ]]; then
  HOST="$SFB_RUNPOD_TCP_HOST"
  PORT="${SFB_RUNPOD_TCP_PORT:-22}"
else
  # Observed on pod qp386qvf6p72gg; override if Connect tab changes.
  HOST="${SFB_RUNPOD_TCP_HOST:-213.173.111.179}"
  PORT="${SFB_RUNPOD_TCP_PORT:-29086}"
fi

echo "Tunnel: localhost:${LOCAL_PORT} -> root@${HOST}:${PORT} -> 127.0.0.1:${REMOTE_PORT}"
echo "Keep this terminal open."
exec ssh -N \
  -o ExitOnForwardFailure=yes \
  -o ServerAliveInterval=30 \
  -o StrictHostKeyChecking=accept-new \
  -i "$SSH_KEY" \
  -p "$PORT" \
  -L "${LOCAL_PORT}:127.0.0.1:${REMOTE_PORT}" \
  "root@${HOST}"
