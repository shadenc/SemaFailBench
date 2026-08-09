from __future__ import annotations

from collections import Counter

from sem_fail_bench.catalog import load_canaries, load_faults, load_serving_config
from sem_fail_bench.scorer_specs import SCORER_SPECS, SUBTYPE_SLUG
from sem_fail_bench.scorers import score_canary


def test_catalog_counts():
    catalog = load_canaries()
    canaries = catalog["canaries"]
    assert catalog["suite_version"] == "v3-frozen"
    assert len(canaries) == 174
    assert sum(1 for c in canaries if c["split"] == "core") == 150
    assert sum(1 for c in canaries if c["split"] == "held_out") == 24
    ids = [c["id"] for c in canaries]
    assert ids[:150] == [f"SFC-{i:03d}" for i in range(1, 151)]
    assert ids[150:] == [f"SFH-{i:03d}" for i in range(1, 25)]
    assert len(set(ids)) == 174


def test_capability_and_subtype_coverage():
    canaries = [c for c in load_canaries()["canaries"] if c["split"] == "core"]
    by_cap = Counter(c["capability_code"] for c in canaries)
    assert by_cap == {"IF": 30, "SO": 30, "FA": 30, "SA": 30, "RG": 30}
    by_subtype = Counter(c["subtype"] for c in canaries)
    assert by_subtype["Quantitative Constraint Compliance"] == 5
    assert by_subtype["Numerical Fact Recall"] == 11
    assert by_subtype["Refusal Calibration"] == 10
    assert by_subtype["Single-Fact Grounding"] == 6
    assert set(by_subtype) == set(SUBTYPE_SLUG)
    held = [c for c in load_canaries()["canaries"] if c["split"] == "held_out"]
    assert {c["subtype"] for c in held} == set(SUBTYPE_SLUG)
    assert len(held) == 24


def test_every_item_has_explicit_scorer():
    for canary in load_canaries()["canaries"]:
        assert canary["id"] in SCORER_SPECS
        assert canary["scorer"]["type"]
        assert canary["prompt"].strip()
        assert canary["expected_behavior"].strip()


def test_hypothesized_faults_are_metadata_only():
    core = [c for c in load_canaries()["canaries"] if c["split"] == "core"]
    assert all(isinstance(c["hypothesized_faults"], list) for c in core)
    assert any(c["hypothesized_faults"] for c in core)
    held = [c for c in load_canaries()["canaries"] if c["split"] == "held_out"]
    assert all(c["hypothesized_faults"] == [] for c in held)


def test_fault_and_serving_configs():
    faults = load_faults()["faults"]
    assert set(faults) == {"F1", "F2", "F3", "F4", "F5", "F8"}
    serving = load_serving_config()
    assert serving["model"]["repo"] == "Qwen/Qwen2.5-7B-Instruct"
    assert serving["tensor_parallel_size"] == 1


def test_score_canary_roundtrip_on_goldish_examples():
    catalog = {c["id"]: c for c in load_canaries()["canaries"]}
    assert score_canary(catalog["SFC-001"], " ".join(["word"] * 25))["strict_pass"] is True
    assert score_canary(catalog["SFC-001"], " ".join(["word"] * 24))["strict_pass"] is False
    assert score_canary(catalog["SFC-061"], "Paris")["strict_pass"] is True
    assert score_canary(catalog["SFC-084"], "No")["strict_pass"] is True
    assert score_canary(catalog["SFH-001"], " ".join(["word"] * 15))["strict_pass"] is True
