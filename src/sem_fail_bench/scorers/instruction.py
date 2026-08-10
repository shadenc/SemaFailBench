from __future__ import annotations

import re
from typing import Any

from sem_fail_bench.text_utils import (
    NUMBER_WORDS,
    contains_keyword,
    count_words,
    keyword_count,
    lowercase,
    normalize_exact_string,
    normalize_ws,
    split_sentences,
)


def score_word_count(response: str, spec: dict[str, Any], **_: Any) -> dict[str, Any]:
    observed = count_words(response)
    op = spec.get("op", "==")
    target = int(spec["n"])
    if op == "==":
        passed = observed == target
    elif op == ">=":
        passed = observed >= target
    elif op == "<=":
        passed = observed <= target
    else:
        raise ValueError(f"Unsupported word_count op: {op}")
    return {
        "strict_pass": passed,
        "tolerant_pass": passed,
        "semantic_score": float(passed),
        "details": {"observed": observed, "op": op, "n": target},
    }


def _family_hit(text: str, family: list[str]) -> int:
    return sum(keyword_count(text, token) for token in family)


def score_keyword_inclusion(response: str, spec: dict[str, Any], **_: Any) -> dict[str, Any]:
    family = spec.get("family") or ([spec["keyword"]] if spec.get("keyword") else [])
    observed = _family_hit(response, family)
    minimum = spec.get("min_count")
    exact = spec.get("exact_count")
    if exact is not None:
        passed = observed == int(exact)
    else:
        passed = observed >= int(minimum or 1)

    same_sentence_with = spec.get("same_sentence_with") or []
    if same_sentence_with:
        sentence_ok = False
        for sentence in split_sentences(response):
            if _family_hit(sentence, family) > 0 and any(
                contains_keyword(sentence, marker) for marker in same_sentence_with
            ):
                sentence_ok = True
                break
        passed = passed and sentence_ok
    return {
        "strict_pass": passed,
        "tolerant_pass": passed,
        "semantic_score": float(passed),
        "details": {
            "family": family,
            "observed": observed,
            "min_count": minimum,
            "exact_count": exact,
            "same_sentence_with": same_sentence_with,
        },
    }


def score_keyword_exclusion(response: str, spec: dict[str, Any], **_: Any) -> dict[str, Any]:
    forbidden = spec.get("forbidden") or []
    hits = {word: keyword_count(response, word) for word in forbidden}
    if spec.get("forbid_digits"):
        hits["<digit>"] = len(re.findall(r"[0-9]", response or ""))
    if spec.get("forbid_number_words"):
        text = lowercase(response)
        nw_hits = [w for w in NUMBER_WORDS if re.search(rf"\b{re.escape(w)}\b", text)]
        hits["<number_words>"] = len(nw_hits)
        details_extra = {"number_words": nw_hits}
    else:
        details_extra = {}
    passed = all(count == 0 for count in hits.values())
    return {
        "strict_pass": passed,
        "tolerant_pass": passed,
        "semantic_score": float(passed),
        "details": {"hits": hits, **details_extra},
    }


def score_exact_string(response: str, spec: dict[str, Any], **_: Any) -> dict[str, Any]:
    expected = spec["expected"]
    case_insensitive = spec.get("case_insensitive", True)
    comma_list_normalize = bool(spec.get("comma_list_normalize", False))
    observed = normalize_exact_string(
        response,
        comma_list_normalize=comma_list_normalize,
    )
    target = normalize_exact_string(
        expected,
        comma_list_normalize=comma_list_normalize,
    )
    if spec.get("strip_trailing_period", True):
        observed = observed.rstrip(" .")
        target = target.rstrip(" .")
    if case_insensitive:
        passed = observed.lower() == target.lower()
    else:
        passed = observed == target
    return {
        "strict_pass": passed,
        "tolerant_pass": passed or (target.lower() in (response or "").lower()),
        "semantic_score": float(passed),
        "details": {"expected": expected, "observed": observed},
    }
