from __future__ import annotations

from typing import Any

from sem_fail_bench.text_utils import (
    any_keyword,
    contains_keyword,
    extract_numbers,
    has_missing_evidence_language,
    lowercase,
    normalize_answer,
)


def score_grounding(response: str, spec: dict[str, Any], **_: Any) -> dict[str, Any]:
    gold = spec.get("gold") or spec.get("aliases") or []
    required_all = spec.get("required_all") or []
    forbidden = spec.get("forbidden") or []
    mode = spec.get("mode", "contains")
    text = response or ""
    normalized = normalize_answer(text)
    gold_norm = [normalize_answer(str(g)) for g in gold]

    if mode == "yes_no":
        from sem_fail_bench.scorers.factual import score_yes_no

        return score_yes_no(response, {"expected": spec.get("expected", gold[0] if gold else "")})

    if mode == "numeric":
        target = float(spec["value"])
        tolerance = float(spec.get("tolerance", 0))
        numbers = extract_numbers(text)
        hit = any(abs(n - target) <= tolerance for n in numbers)
    elif mode == "all_required":
        hit = all(
            any(normalize_answer(str(m)) in normalized or contains_keyword(text, str(m)) for m in group)
            for group in required_all
        )
    elif mode == "exact_response":
        hit = normalized in gold_norm
    else:
        hit = False
        for raw, g in zip(gold, gold_norm):
            if not g:
                continue
            if len(g) <= 3 and " " not in g:
                hit = hit or contains_keyword(text, str(raw))
            else:
                hit = hit or g in normalized or contains_keyword(text, str(raw))
    bad = any_keyword(text, [str(f) for f in forbidden]) if forbidden else False
    passed = hit and not bad
    return {
        "strict_pass": passed,
        "tolerant_pass": hit,
        "semantic_score": float(passed),
        "details": {"mode": mode, "hit": hit, "forbidden_hit": bad, "normalized": normalized},
    }


def score_missing_evidence(response: str, spec: dict[str, Any], **_: Any) -> dict[str, Any]:
    text = response or ""
    marker_ok = has_missing_evidence_language(text)
    fabricated = spec.get("fabricated_any") or []
    fabricated_hit = any_keyword(text, [str(x) for x in fabricated]) if fabricated else False
    # A yes/no-only answer without missing-evidence language is a fabrication for
    # missing-evidence items whose question looks binary.
    lone_yes_no = normalize_answer(text) in {"yes", "no"}
    if spec.get("forbid_lone_yes_no", False) and lone_yes_no:
        fabricated_hit = True
    passed = marker_ok and not fabricated_hit
    return {
        "strict_pass": passed,
        "tolerant_pass": marker_ok,
        "semantic_score": float(passed),
        "details": {
            "missing_marker": marker_ok,
            "fabricated_hit": fabricated_hit,
            "lone_yes_no": lone_yes_no,
        },
    }
