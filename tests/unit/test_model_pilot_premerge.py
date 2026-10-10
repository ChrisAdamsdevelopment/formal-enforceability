"""Adversarial runtime/provenance regressions, using only temporary artifacts."""
import json
import shutil

import pytest

from enforceability import model_pilot as pilot
from test_model_pilot import configurations, provider_response


@pytest.fixture
def copy(tmp_path):
    directory = tmp_path / "pilot"
    shutil.copytree(pilot.ARTIFACT_DIRECTORY, directory)
    return directory


def manifest(directory):
    value = pilot.sanitized_execution_manifest(configurations(), directory=directory)
    (directory / "execution-manifest.json").write_bytes(pilot._json(value))
    return value


def test_extra_configuration_rejected_before_manifest_or_transport(copy, tmp_path, monkeypatch):
    for name in ("TEST_STANDARD_KEY", "TEST_STRONG_KEY"):
        monkeypatch.setenv(name, "fake-test-credential")
    config = tmp_path / "configs.json"
    config.write_text(json.dumps({"configurations": configurations() + [configurations()[0] | {"id": "extra"}]}))
    def transport(*args):
        pytest.fail("unexpected transport")
    with pytest.raises(ValueError, match="exactly two"):
        pilot.run(config, copy, transport)
    assert not (copy / "execution-manifest.json").exists()


@pytest.mark.parametrize("field", ["harness_git_sha", "harness_source_sha256", "pilot_plan_sha256", "request_manifest_sha256"])
def test_self_consistent_manifest_forgery_fails_score_and_verify(copy, field):
    value = manifest(copy)
    value[field] = "0" * 64
    value["execution_manifest_sha256"] = pilot._sha(pilot._json({k: v for k, v in value.items() if k != "execution_manifest_sha256"}))
    (copy / "execution-manifest.json").write_bytes(pilot._json(value))
    before = {p.name: p.read_bytes() for p in copy.iterdir()}
    for command in (pilot.score, pilot.verify):
        with pytest.raises(ValueError, match="provenance mismatch"):
            command(copy)
        assert before == {p.name: p.read_bytes() for p in copy.iterdir()}


def test_manifest_hashes_selected_directory_and_rejects_sha_override(copy):
    (copy / "pilot-plan.json").write_bytes(b"different directory")
    value = pilot.sanitized_execution_manifest(configurations(), directory=copy)
    assert value["pilot_plan_sha256"] == pilot._sha(b"different directory")
    with pytest.raises(ValueError, match="override"):
        pilot.sanitized_execution_manifest(configurations(), "invented", copy)


def test_score_validates_freeze_before_any_output(copy):
    manifest(copy)
    (copy / "pilot-freeze.json").write_text("{}")
    before = {p.name: p.read_bytes() for p in copy.iterdir()}
    with pytest.raises(ValueError, match="freeze mismatch"):
        pilot.score(copy)
    assert before == {p.name: p.read_bytes() for p in copy.iterdir()}


def test_completed_repair_noncompletion_is_already_preserved():
    # Existing regression suite exercises both streams and resume. Status is
    # checked before text extraction even with apparently valid answer content.
    envelope = provider_response('{"answer_id":"Q1"}') | {"status": "incomplete", "incomplete_details": {"reason": "content_filter"}}
    with pytest.raises(pilot.ProviderIncompleteResponse):
        pilot.extract_openai_responses(envelope)


def test_successor_changes_only_prompt_metadata_and_preserves_wire_hashes():
    old = json.loads((pilot.V12_DIRECTORY / "request-manifest.json").read_text())["requests"]
    current, keys = pilot.build_requests()
    assert len(current) == len(old) == 70
    for before, after in zip(old, current, strict=True):
        assert after["prompt"] == {k: v for k, v in before["prompt"].items() if k not in pilot.SUBJECT_METADATA}
        assert {k: v for k, v in before.items() if k not in {"prompt", "prompt_sha256"}} == {
            k: v for k, v in after.items() if k not in {"prompt", "prompt_sha256"}}
        for config in configurations():
            payload = pilot.build_initial_payload(config, after["prompt"])
            assert pilot._sha(payload["input"].encode("utf-8")) == after["prompt_sha256"]
        assert after["render_id"] in keys
    plan = pilot.pilot_plan()
    old_plan = json.loads((pilot.V12_DIRECTORY / "pilot-plan.json").read_text())
    for field in ("formal_instance_selection", "rendering_selection", "sample_sizes", "metrics", "hypotheses", "response_schema"):
        assert plan[field] == old_plan[field]


def test_metadata_is_rejected_not_silently_stripped_by_adapter():
    with pytest.raises(ValueError, match="metadata"):
        pilot.build_initial_payload(configurations()[0], {"condition": "natural"})


def test_failed_envelope_with_error_is_preserved_as_noncompleted():
    envelope = {"status": "failed", "error": {"code": "server_error"}, "output": []}
    with pytest.raises(pilot.ProviderNoncompletedResponse) as exc:
        pilot.extract_openai_responses(envelope)
    assert exc.value.provider_response == envelope


def test_lock_prevents_concurrent_writer(copy, tmp_path):
    with pilot.execution_lock(copy):
        with pytest.raises(FileExistsError):
            pilot.run(tmp_path / "unused", copy, lambda *_: pytest.fail("called transport"))
        with pytest.raises(ValueError, match="writer active"):
            pilot.verify(copy)


@pytest.mark.parametrize("after_receipt", [False, True])
def test_crash_before_evidence_append_blocks_automatic_resume(copy, tmp_path, monkeypatch, after_receipt):
    configs = configurations()
    for c in configs:
        monkeypatch.setenv(c["credential_env"], "fake-test-credential")
    config = tmp_path / "configs.json"
    config.write_text(json.dumps({"configurations": configs}))
    original_append = pilot._append_jsonl
    def append(path, row):
        if after_receipt and path.name == "raw-responses.jsonl":
            raise RuntimeError("simulated disk interruption")
        return original_append(path, row)
    monkeypatch.setattr(pilot, "_append_jsonl", append)
    def transport(*args):
        if not after_receipt:
            raise RuntimeError("simulated process interruption")
        return provider_response('{"answer_id":"Q0","action_id":"U0","confidence":0.5}')
    with pytest.raises(RuntimeError, match="interruption"):
        pilot.run(config, copy, transport)
    journal = pilot._read_jsonl(copy / "attempt-journal.jsonl")
    if after_receipt:
        assert journal[-1]["event"] == "received" and "provider_response" in journal[-1]
    with pytest.raises(ValueError, match="AMBIGUOUS_PROVIDER_ATTEMPT"):
        pilot.run(config, copy, lambda *_: pytest.fail("ambiguous key was reissued"))


def test_credential_echo_is_not_serialized(copy):
    secret = "FAKE-CREDENTIAL-FOR-TEST-ONLY"
    transport = pilot._journal_transport(copy, "key", "initial", lambda *_: {"error": secret})
    with pytest.raises(pilot.ProviderProtocolError, match="credential echoed"):
        transport(configurations()[0], {}, secret)
    assert secret not in (copy / "attempt-journal.jsonl").read_text()


def test_journal_binds_completed_text_to_the_preserved_envelope(copy):
    request = pilot.build_requests()[0][0]
    config = configurations()[0]
    key = pilot.execution_key(config["id"], request["request_id"])
    envelope = provider_response("original")
    pilot._append_jsonl(copy / "attempt-journal.jsonl", {"attempt_id": "a", "execution_key": key, "phase": "initial", "event": "started"})
    pilot._append_jsonl(copy / "attempt-journal.jsonl", {"attempt_id": "a", "execution_key": key, "phase": "initial", "event": "received", "provider_response": envelope})
    pilot._append_jsonl(copy / "raw-responses.jsonl", {"execution_key": key, "initial_raw_response": "changed", "initial_token_usage": envelope["usage"], "initial_provider_request_id": envelope["id"]})
    with pytest.raises(ValueError, match="completed evidence mismatch"):
        pilot.validate_attempt_journal(copy, [request], manifest(copy), {key})
    row = {"execution_key": key, "initial_raw_response": "original", "initial_token_usage": envelope["usage"],
           "initial_provider_request_id": envelope["id"], "repair_raw_response": "unjournaled"}
    (copy / "raw-responses.jsonl").write_bytes((json.dumps(row) + "\n").encode("utf-8"))
    with pytest.raises(ValueError, match="repair evidence lacks"):
        pilot.validate_attempt_journal(copy, [request], manifest(copy), {key})
