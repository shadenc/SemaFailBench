"""SemaFailBench: silent semantic-failure detection for LLM serving."""

__version__ = "0.3.0"

from sem_fail_bench.catalog import load_canaries, load_faults, load_serving_config
from sem_fail_bench.scorers import score_canary

__all__ = [
    "__version__",
    "load_canaries",
    "load_faults",
    "load_serving_config",
    "score_canary",
]
