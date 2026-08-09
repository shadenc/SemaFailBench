from __future__ import annotations

from functools import lru_cache
from typing import Any

import yaml

from sem_fail_bench.paths import canaries_path, faults_path, serving_path


def _load_yaml(path) -> dict[str, Any]:
    with open(path, encoding="utf-8") as fh:
        return yaml.safe_load(fh) or {}


@lru_cache(maxsize=1)
def load_canaries() -> dict[str, Any]:
    data = _load_yaml(canaries_path())
    items = data.get("canaries") or []
    if not items:
        raise FileNotFoundError(f"No canaries found in {canaries_path()}")
    return data


@lru_cache(maxsize=1)
def load_faults() -> dict[str, Any]:
    return _load_yaml(faults_path())


@lru_cache(maxsize=1)
def load_serving_config() -> dict[str, Any]:
    return _load_yaml(serving_path())


def canary_by_id(canary_id: str) -> dict[str, Any]:
    for item in load_canaries()["canaries"]:
        if item["id"] == canary_id:
            return item
    raise KeyError(canary_id)


def canaries_for_subtype(subtype: str) -> list[dict[str, Any]]:
    return [c for c in load_canaries()["canaries"] if c["subtype"] == subtype]


def canaries_for_capability(capability: str) -> list[dict[str, Any]]:
    return [c for c in load_canaries()["canaries"] if c["capability"] == capability]


def canaries_for_split(split: str) -> list[dict[str, Any]]:
    return [c for c in load_canaries()["canaries"] if c.get("split") == split]
