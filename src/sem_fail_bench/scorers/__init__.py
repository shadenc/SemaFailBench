"""Deterministic scorers. No LLM-as-judge on the strict path."""

from __future__ import annotations

from typing import Any

from sem_fail_bench.text_utils import unwrap_json_prose
from sem_fail_bench.scorers.factual import score_factual, score_yes_no
from sem_fail_bench.scorers.formatting import score_formatting, score_language, score_ordering
from sem_fail_bench.scorers.grounding import score_grounding, score_missing_evidence
from sem_fail_bench.scorers.instruction import (
    score_exact_string,
    score_keyword_exclusion,
    score_keyword_inclusion,
    score_word_count,
)
from sem_fail_bench.scorers.json_output import score_json
from sem_fail_bench.scorers.safety import score_concept_checklist, score_safety

SCORER_DISPATCH = {
    "word_count": score_word_count,
    "keyword_inclusion": score_keyword_inclusion,
    "keyword_exclusion": score_keyword_exclusion,
    "formatting": score_formatting,
    "language": score_language,
    "exact_string": score_exact_string,
    "ordering": score_ordering,
    "json": score_json,
    "factual": score_factual,
    "yes_no": score_yes_no,
    "safety": score_safety,
    "concept_checklist": score_concept_checklist,
    "grounding": score_grounding,
    "missing_evidence": score_missing_evidence,
}


def _score_spec(spec: dict[str, Any], response: str) -> dict[str, Any]:
    scorer_type = spec.get("type")
    if scorer_type == "all":
        child_results = [_score_spec(child, response) for child in spec.get("checks") or []]
        passed = bool(child_results) and all(r["strict_pass"] for r in child_results)
        tolerant = bool(child_results) and all(r["tolerant_pass"] for r in child_results)
        score = sum(r["semantic_score"] for r in child_results) / len(child_results) if child_results else 0.0
        return {
            "strict_pass": passed,
            "tolerant_pass": tolerant,
            "semantic_score": score,
            "details": {"checks": child_results},
        }
    if scorer_type == "any":
        child_results = [_score_spec(child, response) for child in spec.get("checks") or []]
        passed = any(r["strict_pass"] for r in child_results)
        tolerant = any(r["tolerant_pass"] for r in child_results)
        score = max((r["semantic_score"] for r in child_results), default=0.0)
        return {
            "strict_pass": passed,
            "tolerant_pass": tolerant,
            "semantic_score": score,
            "details": {"checks": child_results},
        }
    fn = SCORER_DISPATCH.get(scorer_type)
    if fn is None:
        raise ValueError(f"Unknown scorer type {scorer_type!r}")
    return fn(response, spec)


def score_canary(canary: dict[str, Any], response: str, **_: Any) -> dict[str, Any]:
    spec = canary.get("scorer") or {}
    if spec.get("type") != "json":
        response = unwrap_json_prose(response)
    result = _score_spec(spec, response)
    result["canary_id"] = canary["id"]
    result["scorer_type"] = spec.get("type")
    result["capability"] = canary.get("capability")
    result["subtype"] = canary.get("subtype")
    return result
