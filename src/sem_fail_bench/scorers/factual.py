from __future__ import annotations

import re
from typing import Any

from sem_fail_bench.text_utils import contains_keyword, extract_numbers, normalize_answer


def score_factual(response: str, spec: dict[str, Any], **_: Any) -> dict[str, Any]:
    gold = [str(g) for g in (spec.get("gold") or [])]
    mode = spec.get("mode", "contains")
    forbidden = [str(f) for f in (spec.get("forbidden") or [])]
    text = response or ""
    normalized = normalize_answer(text)
    gold_norm = [normalize_answer(g) for g in gold]
    hit = False
    if mode == "exact_response":
        hit = normalized in gold_norm
    elif mode == "numeric":
        target = float(spec["value"])
        tolerance = float(spec.get("tolerance", 0))
        numbers = extract_numbers(text)
        hit = any(abs(n - target) <= tolerance for n in numbers)
        if spec.get("max_words") is not None:
            from sem_fail_bench.text_utils import count_words

            hit = hit and count_words(text) <= int(spec["max_words"])
    elif mode == "partial":
        hit = any(g and g in normalized for g in gold_norm)
    else:  # contains
        hit = False
        for raw, g in zip(gold, gold_norm):
            if not g:
                continue
            if len(g) <= 3 and " " not in g:
                hit = hit or contains_keyword(text, raw)
            else:
                hit = hit or g in normalized or contains_keyword(text, raw)
    bad = any(normalize_answer(f) and normalize_answer(f) in normalized for f in forbidden)
    if spec.get("max_words") is not None and mode != "numeric":
        from sem_fail_bench.text_utils import count_words

        hit = hit and count_words(text) <= int(spec["max_words"])
    passed = hit and not bad
    return {
        "strict_pass": passed,
        "tolerant_pass": hit,
        "semantic_score": float(passed),
        "details": {"mode": mode, "gold": gold, "hit": hit, "forbidden_hit": bad, "normalized": normalized},
    }


def score_yes_no(response: str, spec: dict[str, Any], **_: Any) -> dict[str, Any]:
    expected = str(spec.get("expected", "")).strip().lower()
    normalized = normalize_answer(response)
    # Accept a lone yes/no, optionally with a period already stripped.
    token = normalized
    if token.startswith("yes ") or token == "yes":
        observed = "yes"
    elif token.startswith("no ") or token == "no":
        observed = "no"
    else:
        match = re.match(r"^(yes|no)\b", normalized)
        observed = match.group(1) if match else normalized
    passed = observed == expected
    # Strict: the whole answer should be just yes/no (plus trivial filler).
    strict = passed and observed in {"yes", "no"} and len(normalized.split()) <= 3
    return {
        "strict_pass": strict,
        "tolerant_pass": passed,
        "semantic_score": float(strict),
        "details": {"expected": expected, "observed": observed, "normalized": normalized},
    }
