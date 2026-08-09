#!/usr/bin/env python3
"""Run a remote command on RunPod's PTY-required SSH proxy.

Cursor/automation shells have no TTY. RunPod's ssh.runpod.io gateway rejects
non-PTY sessions with "Your SSH client doesn't support PTY". This helper
allocates a local pseudo-terminal, waits for the pod shell prompt, then
sends a bash snippet and waits for a sentinel.
"""

from __future__ import annotations

import argparse
import os
import pty
import re
import select
import sys
import time
from pathlib import Path

SENTINEL = "__SFB_SSH_DONE__"
PROMPT_RE = re.compile(rb"(?:root@[\w.-]+|ubuntu@[\w.-]+)[:~].*[#$] ?$")


def _read(fd: int, timeout: float) -> bytes:
    ready, _, _ = select.select([fd], [], [], timeout)
    if not ready:
        return b""
    try:
        return os.read(fd, 8192)
    except OSError:
        return b""


def run_remote(
    *,
    host: str,
    identity: Path,
    script: str,
    port: int | None = None,
    timeout: float = 180.0,
) -> int:
    ssh = [
        "ssh",
        "-tt",
        "-o",
        "BatchMode=yes",
        "-o",
        "ConnectTimeout=25",
        "-o",
        "StrictHostKeyChecking=accept-new",
        "-i",
        str(identity),
    ]
    if port:
        ssh.extend(["-p", str(port)])
    ssh.append(host)

    wrapped = (
        "set +e\n"
        f"{script.rstrip()}\n"
        f"echo {SENTINEL}:$?\n"
    )

    pid, fd = pty.fork()
    if pid == 0:
        os.execvp(ssh[0], ssh)

    buf = b""
    deadline = time.time() + 45
    prompt_seen = False
    while time.time() < deadline:
        chunk = _read(fd, 1.0)
        if chunk:
            buf += chunk
            sys.stderr.buffer.write(chunk)
            sys.stderr.buffer.flush()
            if PROMPT_RE.search(buf.split(b"\n")[-1]):
                prompt_seen = True
                break
        else:
            # child exited early?
            wpid, status = os.waitpid(pid, os.WNOHANG)
            if wpid:
                sys.stderr.write("SSH exited before prompt.\n")
                return 255

    if not prompt_seen:
        os.write(fd, b"\n")
        extra_deadline = time.time() + 10
        while time.time() < extra_deadline:
            chunk = _read(fd, 1.0)
            if chunk:
                buf += chunk
                sys.stderr.buffer.write(chunk)
                sys.stderr.buffer.flush()
                if PROMPT_RE.search(buf.split(b"\n")[-1]):
                    prompt_seen = True
                    break

    if not prompt_seen:
        sys.stderr.write("\nTimed out waiting for RunPod shell prompt.\n")
        try:
            os.kill(pid, 15)
        except OSError:
            pass
        return 2

    os.write(fd, wrapped.encode() + b"\n")
    out = b""
    deadline = time.time() + timeout
    while time.time() < deadline:
        chunk = _read(fd, 1.0)
        if chunk:
            out += chunk
            sys.stdout.buffer.write(chunk)
            sys.stdout.buffer.flush()
            if SENTINEL.encode() in out:
                break
        else:
            wpid, status = os.waitpid(pid, os.WNOHANG)
            if wpid:
                break

    os.write(fd, b"exit\n")
    time.sleep(0.4)
    try:
        os.kill(pid, 15)
    except OSError:
        pass
    try:
        os.waitpid(pid, 0)
    except OSError:
        pass

    text = out.decode("utf-8", errors="replace")
    for line in text.splitlines():
        if line.startswith(SENTINEL + ":"):
            try:
                return int(line.split(":", 1)[1].strip().split()[0])
            except ValueError:
                return 0
    return 0 if SENTINEL in text else 3


def main() -> int:
    parser = argparse.ArgumentParser(description="Run a command on RunPod via PTY SSH")
    parser.add_argument("--host", default=os.environ.get("SFB_RUNPOD_SSH", "qp386qvf6p72gg-64411ac1@ssh.runpod.io"))
    parser.add_argument("--identity", default=os.environ.get("SFB_RUNPOD_KEY", str(Path.home() / ".ssh" / "sfb_runpod")))
    parser.add_argument("--port", type=int, default=int(os.environ["SFB_RUNPOD_PORT"]) if os.environ.get("SFB_RUNPOD_PORT") else None)
    parser.add_argument("--timeout", type=float, default=300.0)
    parser.add_argument("script", nargs="?", help="bash snippet; default read stdin")
    args = parser.parse_args()
    script = args.script if args.script is not None else sys.stdin.read()
    if not script.strip():
        print("empty script", file=sys.stderr)
        return 2
    return run_remote(
        host=args.host,
        identity=Path(args.identity).expanduser(),
        script=script,
        port=args.port,
        timeout=args.timeout,
    )


if __name__ == "__main__":
    raise SystemExit(main())
