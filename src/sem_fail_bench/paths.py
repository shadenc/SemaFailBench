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


def serving_path() -> Path:
    return CONFIGS / "serving.yaml"


def monitoring_path() -> Path:
    return CONFIGS / "monitoring.yaml"


def run_record_schema_path() -> Path:
    return SCHEMAS / "run_record.schema.json"


def core_canaries_csv() -> Path:
    return SOURCE_CSV / "Core_Canaries.csv"


def held_out_csv() -> Path:
    return SOURCE_CSV / "Held_Out_Generalization.csv"
