from __future__ import annotations

import re
from typing import Any

from langdetect import DetectorFactory, detect_langs
from langdetect.lang_detect_exception import LangDetectException

from sem_fail_bench.text_utils import (
    first_occurrence_index,
    lowercase,
    non_empty_lines,
)

DetectorFactory.seed = 0

LANG_ALIASES = {
    "es": "es",
    "spanish": "es",
    "fr": "fr",
    "french": "fr",
    "de": "de",
    "german": "de",
    "pt": "pt",
    "portuguese": "pt",
    "it": "it",
    "italian": "it",
}

STOPWORDS = {
    "es": {"el", "la", "los", "las", "una", "unos", "unas", "es", "está", "están", "por", "para", "con", "que", "del"},
    "fr": {"le", "les", "une", "des", "est", "sont", "pour", "avec", "dans", "pas", "vous", "nous", "merci"},
    "de": {"der", "die", "das", "und", "ist", "nicht", "ein", "eine", "mit", "auf", "den", "dem", "wurde"},
    "pt": {"o", "os", "uma", "uns", "é", "está", "para", "com", "que", "não", "obrigado", "obrigada"},
    "it": {"il", "la", "le", "una", "è", "per", "con", "che", "non", "grazie", "orari"},
}


def _stopword_score(text: str, lang: str) -> int:
    tokens = set(re.findall(r"\w+", lowercase(text), flags=re.UNICODE))
    return len(tokens & STOPWORDS.get(lang, set()))


def score_formatting(response: str, spec: dict[str, Any], **_: Any) -> dict[str, Any]:
    rule = spec.get("rule")
    text = response or ""
    checks: dict[str, bool] = {}
    lines = non_empty_lines(text)

    if rule == "numbered_lines":
        n = int(spec["n"])
        checks["line_count"] = len(lines) == n
        checks["numbered"] = all(re.match(r"^\d+[.)]\s+\S", ln) for ln in lines) and len(lines) == n
        if spec.get("nothing_else", True):
            checks["nothing_else"] = len(lines) == n
    elif rule == "prefix_lines":
        prefixes = spec.get("prefixes") or []
        checks["line_count"] = len(lines) == len(prefixes)
        checks["prefixes"] = len(lines) == len(prefixes) and all(
            ln.lower().startswith(prefix.lower()) for ln, prefix in zip(lines, prefixes)
        )
    elif rule == "delimiter_wrap":
        delimiter = spec.get("delimiter", "=====")
        checks["line_count"] = len(lines) == 3
        if len(lines) == 3:
            checks["open"] = lines[0] == delimiter
            checks["close"] = lines[2] == delimiter
            checks["body"] = bool(lines[1]) and lines[1] != delimiter
        else:
            checks["open"] = checks["close"] = checks["body"] = False
    elif rule == "quoted_whole":
        stripped = text.strip()
        checks["quoted"] = bool(
            re.match(r'^["“].+["”]$', stripped, flags=re.DOTALL)
        ) and stripped[0] in {'"', "“"} and stripped[-1] in {'"', "”"}
        inner = stripped[1:-1] if len(stripped) >= 2 else ""
        checks["non_empty_inner"] = bool(inner.strip())
        checks["no_outer_text"] = stripped == text.strip()
    elif rule == "bold_headers":
        n = int(spec.get("n", 2))
        headers = list(re.finditer(r"\*\*([^*]+)\*\*", text))
        checks["header_count"] = len(headers) == n
        bodies_ok = True
        for i, match in enumerate(headers):
            start = match.end()
            end = headers[i + 1].start() if i + 1 < len(headers) else len(text)
            body = text[start:end].strip()
            if not body:
                bodies_ok = False
        checks["bodies"] = bodies_ok and bool(headers)
    else:
        raise ValueError(f"Unsupported formatting rule: {rule}")

    passed = bool(checks) and all(checks.values())
    return {
        "strict_pass": passed,
        "tolerant_pass": passed,
        "semantic_score": float(passed),
        "details": {"rule": rule, "checks": checks, "lines": lines},
    }


def score_ordering(response: str, spec: dict[str, Any], **_: Any) -> dict[str, Any]:
    sequence = spec.get("sequence") or []
    text = lowercase(response)
    indexes = []
    missing = []
    used_aliases = []
    for item in sequence:
        aliases = item if isinstance(item, list) else [item]
        found_at = -1
        used = None
        for alias in aliases:
            idx = first_occurrence_index(text, alias)
            if idx >= 0 and (found_at < 0 or idx < found_at):
                found_at = idx
                used = alias
        if found_at < 0:
            missing.append(aliases[0])
        indexes.append(found_at)
        used_aliases.append(used)
    present = not missing
    ordered = present and all(
        indexes[i] < indexes[i + 1] for i in range(len(indexes) - 1)
    )
    extra_ok = True
    max_items = spec.get("max_listed_items")
    if max_items is not None:
        listed = len(re.findall(r"(?m)^\s*(?:\d+[.)]|[-*•])\s+\S", response or ""))
        if listed:
            extra_ok = listed <= int(max_items)
    qualifier = spec.get("qualifier_any") or []
    qualifier_index = spec.get("qualifier_on_index")
    qualifier_ok = True
    if qualifier:
        q_idx = min(
            (i for i in (first_occurrence_index(text, q) for q in qualifier) if i >= 0),
            default=-1,
        )
        qualifier_ok = q_idx >= 0
        if qualifier_index is not None and present and q_idx >= 0:
            # Qualifier belongs on the named step: after the previous step and
            # before the next one (may appear just before the step mention).
            q_i = int(qualifier_index)
            prev = indexes[q_i - 1] if q_i > 0 else -1
            nxt = indexes[q_i + 1] if q_i + 1 < len(indexes) else 10**9
            qualifier_ok = prev <= q_idx < nxt
    passed = present and ordered and extra_ok and qualifier_ok
    return {
        "strict_pass": passed,
        "tolerant_pass": present,
        "semantic_score": float(passed),
        "details": {
            "indexes": indexes,
            "missing": missing,
            "ordered": ordered,
            "used_aliases": used_aliases,
            "extra_ok": extra_ok,
            "qualifier_ok": qualifier_ok,
        },
    }


def score_language(response: str, spec: dict[str, Any], **_: Any) -> dict[str, Any]:
    expected = LANG_ALIASES.get(str(spec.get("language", "")).lower(), spec.get("language"))
    min_prob = float(spec.get("min_probability", 0.50))
    details: dict[str, Any] = {"expected": expected}
    passed = False
    try:
        langs = detect_langs(response or "")
        details["detected"] = [{"lang": x.lang, "prob": x.prob} for x in langs]
        top = langs[0] if langs else None
        expected_prefix = str(expected).lower()[:2]
        if top:
            passed = top.lang.lower().startswith(expected_prefix) and top.prob >= min_prob
            if not passed and top.lang[:2] in {"ca", "it", "pt", "es", "fr", "ro"} and expected_prefix in {
                "es",
                "fr",
                "pt",
                "it",
            }:
                sw = _stopword_score(response, expected_prefix)
                details["stopwords"] = sw
                passed = sw >= 2
    except LangDetectException as exc:
        details["error"] = str(exc)
        passed = False
    if not passed and expected:
        sw = _stopword_score(response or "", str(expected)[:2])
        details["stopwords"] = sw
        if sw >= 2:
            passed = True
            details["stopword_hint"] = True
    content_any = spec.get("content_any") or []
    content_ok = True
    if content_any:
        # Stem / substring match so expédiée hits expédi, Rückerstattung hits rückerstatt.
        low = lowercase(response)
        content_ok = any(lowercase(m) in low for m in content_any if m)
        details["content_ok"] = content_ok
    passed = passed and content_ok
    return {
        "strict_pass": passed,
        "tolerant_pass": passed,
        "semantic_score": float(passed),
        "details": details,
    }
