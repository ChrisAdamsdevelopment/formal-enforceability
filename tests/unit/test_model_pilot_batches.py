"""Offline-only bounded batch regressions; no provider calls or frozen writes."""
import json
import shutil

import pytest

from enforceability import model_pilot as pilot
from test_model_pilot import configurations, provider_response, render_for_payload


@pytest.fixture
def pilot_copy(tmp_path):
    directory = tmp_path / "pilot"
    shutil.copytree(pilot.ARTIFACT_DIRECTORY, directory)
    return directory


@pytest.fixture
def setup_config(tmp_path, monkeypatch):
    configs = configurations()
    for config in configs:
        monkeypatch.setenv(config["credential_env"], "fake-test-credential")
    path = tmp_path / "config.json"
    path.write_text(json.dumps({"configurations": configs}), encoding="utf-8")
    return path


def _valid_response(payload):
    private = pilot.build_requests()[1][render_for_payload(payload)]
    return json.dumps({
        "answer_id": next(iter(private["answer_id_to_semantic"])),
        "action_id": next(iter(private["action_id_to_semantic"])),
        "confidence": 0.5,
    })


@pytest.mark.parametrize("limit", [0, -1, 141, True, 2.5, "2"])
def test_bad_batch_limit_rejected_without_writing(pilot_copy, setup_config, limit):
    before = {path.name: path.read_bytes() for path in pilot_copy.iterdir()}
    with pytest.raises(ValueError, match="max_initial_requests"):
        pilot.run(setup_config, pilot_copy, lambda *_: pytest.fail("transport called"),
                  max_initial_requests=limit)
    assert before == {path.name: path.read_bytes() for path in pilot_copy.iterdir()}


def test_bounded_batches_resume_without_repeating_keys(pilot_copy, setup_config):
    seen = []
    def transport(config, payload, credential):
        seen.append((config["id"], render_for_payload(payload)))
        return provider_response(_valid_response(payload), f"resp-{len(seen)}")

    first = pilot.run(setup_config, pilot_copy, transport, max_initial_requests=2)
    assert first["end_status"] == "BATCH_LIMIT_REACHED"
    assert first["initial_requests_started"] == first["completed_during_session"] == 2
    assert first["transport_attempts"] == 2
    assert pilot.verify(pilot_copy)["status"] == "EXECUTION_INCOMPLETE"

    second = pilot.run(setup_config, pilot_copy, transport, max_initial_requests=3)
    assert second["end_status"] == "BATCH_LIMIT_REACHED"
    assert second["completed_before_session"] == 2
    assert second["initial_requests_started"] == second["completed_during_session"] == 3
    assert len(seen) == len(set(seen)) == 5
    assert len((pilot_copy / "raw-responses.jsonl").read_text().splitlines()) == 5
    assert len((pilot_copy / "execution-sessions.jsonl").read_text().splitlines()) == 2
    with pytest.raises(ValueError, match="EXECUTION_INCOMPLETE"):
        pilot.score(pilot_copy)


def test_batch_does_not_split_one_allowed_format_repair(pilot_copy, setup_config):
    requests, privates = pilot.build_requests()
    first_private = privates[requests[0]["render_id"]]
    valid = json.dumps({
        "answer_id": next(iter(first_private["answer_id_to_semantic"])),
        "action_id": next(iter(first_private["action_id_to_semantic"])),
        "confidence": 0.5,
    })
    calls = []
    def transport(config, payload, credential):
        calls.append(json.loads(payload["input"]))
        if len(calls) == 1:
            return provider_response("not json", "initial-malformed")
        if len(calls) == 2:
            return provider_response(valid, "repair-completed")
        return provider_response(_valid_response(payload), "later-completed")

    result = pilot.run(setup_config, pilot_copy, transport, max_initial_requests=1)
    assert result["end_status"] == "BATCH_LIMIT_REACHED"
    assert result["initial_requests_started"] == 1
    assert result["transport_attempts"] == 2
    assert len(calls) == 2
    raw = [json.loads(line) for line in (pilot_copy / "raw-responses.jsonl").read_text().splitlines()]
    assert len(raw) == 1
    assert raw[0]["repair_attempted"] is True
    assert raw[0]["repair_raw_response"] == valid
    next_batch = pilot.run(setup_config, pilot_copy, transport, max_initial_requests=1)
    assert next_batch["completed_before_session"] == 1
    assert next_batch["initial_requests_started"] == 1
    assert len(calls) == 3
    assert pilot.verify(pilot_copy)["status"] == "EXECUTION_INCOMPLETE"


def test_batch_crosses_configuration_boundary_without_replay(pilot_copy, setup_config):
    calls = []
    def transport(config, payload, credential):
        calls.append(config["id"])
        return provider_response(_valid_response(payload), f"id-{len(calls)}")

    first = pilot.run(setup_config, pilot_copy, transport, max_initial_requests=70)
    assert first["end_status"] == "BATCH_LIMIT_REACHED"
    assert len(calls) == 70 and set(calls) == {"standard"}
    second = pilot.run(setup_config, pilot_copy, transport, max_initial_requests=1)
    assert second["end_status"] == "BATCH_LIMIT_REACHED"
    assert len(calls) == 71 and calls[-1] == "strong"
    assert pilot.verify(pilot_copy)["completed"] == 71
