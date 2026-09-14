import json

import pytest

from enforceability.model_pilot import (
    ARTIFACT_DIRECTORY,
    TRACK_A,
    TRACK_B,
    build_artifacts,
    build_requests,
    cross_domain_ids,
    pilot_plan,
    selected_instances,
    strict_parse,
    verify,
)


def test_frozen_selection_and_request_counts():
    selected = selected_instances()
    assert len(selected[TRACK_A]) == 12
    assert len(selected[TRACK_B]) == 6
    assert len({item["formal_instance_id"] for values in selected.values() for item in values}) == 18
    requests, _ = build_requests()
    assert len(requests) == 70
    assert len(cross_domain_ids()) == 8
    assert sum(row["domain"] == "abstract" for row in requests) == 54
    assert all("solver_context" in row["prompt"] for row in requests if row["condition"] == "tool_assisted")
    assert all("solver_context" not in row["prompt"] for row in requests if row["condition"] != "tool_assisted")


def test_plan_and_artifacts_are_frozen_before_execution():
    plan = pilot_plan()
    assert plan["repository_sha"] == "7abe966c79a461073153fa178eb394ad9406263b"
    assert plan["sample_sizes"]["total_calls_per_model"] == 70
    assert plan["metrics"]["high_confidence_threshold"] == 0.8
    expected = build_artifacts()
    assert set(expected) == {path.name for path in ARTIFACT_DIRECTORY.iterdir()}
    assert all((ARTIFACT_DIRECTORY / name).read_bytes() == value for name, value in expected.items())
    assert verify()["status"] == "READY_FOR_PROVIDER_EXECUTION"


def test_strict_parser_accepts_only_neutral_schema():
    requests, keys = build_requests()
    key = keys[requests[0]["render_id"]]
    valid = {"answer_id": next(iter(key["answer_id_to_semantic"])), "action_id": next(iter(key["action_id_to_semantic"])), "confidence": 0.8}
    assert strict_parse(json.dumps(valid), key) == valid
    with pytest.raises(ValueError):
        strict_parse(json.dumps(valid | {"analysis": "private reasoning"}), key)
    with pytest.raises(ValueError):
        strict_parse(json.dumps(valid | {"confidence": 1.1}), key)
