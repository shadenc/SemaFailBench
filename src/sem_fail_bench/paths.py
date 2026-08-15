from __future__ import annotations

import os
from pathlib import Path

REPO_ROOT = Path(os.getenv("SFB_ROOT") or Path(__file__).resolve().parents[2])
CONFIGS = REPO_ROOT / "configs"
DATA = REPO_ROOT / "data"
SCHEMAS = REPO_ROOT / "schemas"
DOCS = REPO_ROOT / "docs"
OUTPUTS = REPO_ROOT / "outputs"
SOURCE_CSV = DOCS / "source_csv" / "SemaFailBench_Final_Canary_Dataset_v3_FROZEN"


def canaries_path() -> Path:
    return CONFIGS / "canaries_v3.yaml"


def faults_path() -> Path:
    return CONFIGS / "faults.yaml"


def configs_dir() -> Path:
    profile = os.getenv("SFB_CONFIG_PROFILE", "").strip()
    if profile:
        return CONFIGS / profile
    return CONFIGS


def serving_path() -> Path:
    return configs_dir() / "serving.yaml"


def fault_serving_path(fault_id: str) -> Path:
    fault = fault_id.lower().strip()
    if fault.startswith("f") and fault[1:].isdigit():
        return configs_dir() / f"serving_{fault}.yaml"
    raise ValueError(f"Unknown fault id: {fault_id!r}")


def monitoring_path() -> Path:
    return CONFIGS / "monitoring.yaml"


def run_record_schema_path() -> Path:
    return SCHEMAS / "run_record.schema.json"


def core_canaries_csv() -> Path:
    return SOURCE_CSV / "Core_Canaries.csv"


def held_out_csv() -> Path:
    return SOURCE_CSV / "Held_Out_Generalization.csv"
