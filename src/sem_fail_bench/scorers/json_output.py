from __future__ import annotations

import re
from typing import Any

import jsonschema

from sem_fail_bench.text_utils import dotted_get, extract_json, lowercase


def _is_int(value: Any) -> bool:
    return isinstance(value, int) and not isinstance(value, bool)


def _value_matches(observed: Any, expected: Any, spec: dict[str, Any]) -> bool:
    if expected is None:
        return observed is None
    if isinstance(expected, bool) or isinstance(observed, bool):
        return observed is expected or observed == expected
    if isinstance(expected, (int, float)) and isinstance(observed, (int, float)) and not isinstance(
        observed, bool
    ):
        return abs(float(observed) - float(expected)) <= float(spec.get("numeric_tolerance", 0))
    if isinstance(expected, str):
        obs = lowercase(str(observed))
        exp = lowercase(expected)
        aliases = [lowercase(a) for a in (spec.get("aliases") or {}).get(expected, [])]
        return obs == exp or any(a == obs or a in obs for a in aliases)
    if isinstance(expected, list):
        if not isinstance(observed, list) or len(observed) != len(expected):
            return False
        return all(_value_matches(o, e, spec) for o, e in zip(observed, expected))
    if isinstance(expected, dict):
        if not isinstance(observed, dict):
            return False
        return all(_value_matches(observed.get(k), v, spec) for k, v in expected.items())
    return observed == expected


def score_json(response: str, spec: dict[str, Any], **_: Any) -> dict[str, Any]:
    parsed = extract_json(response)
    details: dict[str, Any] = {"parsed": parsed}
    if parsed is None:
        return {
            "strict_pass": False,
            "tolerant_pass": False,
            "semantic_score": 0.0,
            "details": {**details, "error": "no_json"},
        }
    schema = spec.get("schema")
    schema_ok = True
    if schema:
        try:
            jsonschema.validate(parsed, schema)
        except jsonschema.ValidationError as exc:
            schema_ok = False
            details["schema_error"] = exc.message
    expected = spec.get("expected")
    values_ok = True
    if expected is not None:
        values_ok = _value_matches(parsed, expected, spec)
        details["values_ok"] = values_ok
    integer_fields = spec.get("integer_fields") or []
    integers_ok = True
    for path in integer_fields:
        try:
            value = dotted_get(parsed, path)
        except (KeyError, TypeError):
            integers_ok = False
            details["integer_missing"] = path
            break
        if not _is_int(value):
            integers_ok = False
            details["integer_failed"] = {"path": path, "value": value, "python_type": type(value).__name__}
            break
    date_fields = spec.get("date_fields") or {}
    dates_ok = True
    for path, pattern in date_fields.items():
        try:
            value = dotted_get(parsed, path)
        except (KeyError, TypeError):
            dates_ok = False
            break
        dates_ok = dates_ok and isinstance(value, str) and bool(re.fullmatch(pattern, value))
    details["dates_ok"] = dates_ok
    unique_arrays = spec.get("unique_arrays") or []
    unique_ok = True
    for path in unique_arrays:
        try:
            value = dotted_get(parsed, path)
        except (KeyError, TypeError):
            unique_ok = False
            break
        unique_ok = unique_ok and isinstance(value, list) and len(value) == len(set(map(str, value)))
    strict = schema_ok and values_ok and integers_ok and dates_ok and unique_ok
    tolerant = schema_ok if spec.get("schema_only_tolerant", True) else strict
    return {
        "strict_pass": strict,
        "tolerant_pass": tolerant,
        "semantic_score": float(strict),
        "details": details,
    }
