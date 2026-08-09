"""Artifact hashing for attributable silent-failure claims."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from sem_fail_bench.hash_utils import sha256_file, sha256_json, sha256_text
from sem_fail_bench.paths import canaries_path, faults_path, serving_path


def snapshot_hashes(
    *,
    extra_files: list[str | Path] | None = None,
    extra_objects: dict[str, Any] | None = None,
) -> dict[str, str]:
    hashes = {
        "canaries_yaml": sha256_file(canaries_path()),
        "faults_yaml": sha256_file(faults_path()),
        "serving_yaml": sha256_file(serving_path()),
    }
    for path in extra_files or []:
        hashes[f"file:{Path(path).name}"] = sha256_file(path)
    if extra_objects:
        hashes["extra_objects"] = sha256_json(extra_objects)
    hashes["bundle"] = sha256_text("".join(f"{k}={v};" for k, v in sorted(hashes.items())))
    return hashes
