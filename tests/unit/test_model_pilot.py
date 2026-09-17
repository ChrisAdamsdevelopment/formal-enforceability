import hashlib
import json
import shutil

import pytest

from enforceability.model_pilot import (
    ADAPTER,
    ARTIFACT_DIRECTORY,
    FORMAT_ONLY_MESSAGE,
    HISTORICAL_ARTIFACT_DIRECTORY,
    OUTPUT_TOKEN_LIMIT,
    ProviderIncompleteResponse,
    ProviderNoncompletedResponse,
    ROOT,
    TRACK_A,
    TRACK_B,
    _error_types,
    aggregate_reports,
    build_artifacts,
    build_format_repair_payload,
    build_initial_payload,
    build_requests,
    cross_domain_ids,
    extract_openai_responses,
    pilot_plan,
    run,
    score,
    selected_instances,
    strict_parse,
    validate_configurations,
    verify,
    write_artifacts,
)


def configurations():
    common = {"provider_adapter": ADAPTER, "endpoint": "https://example.test/v1/responses", "temperature": 0, "seed": None,
              "max_output_tokens": OUTPUT_TOKEN_LIMIT, "unsupported_parameters": []}
    return [common | {"id": "standard", "role": "standard/default reasoning", "credential_env": "TEST_STANDARD_KEY", "model": "m", "reasoning_effort": "medium"},
            common | {"id": "strong", "role": "stronger reasoning", "credential_env": "TEST_STRONG_KEY", "model": "m", "reasoning_effort": "high"}]


def provider_response(text="{}", request_id="resp_1"):
    return {"id": request_id, "status": "completed", "usage": {"input_tokens": 2, "output_tokens": 3},
            "output": [{"type": "message", "content": [{"type": "output_text", "text": text}]}]}


ANALYSIS_FILES = ("scored-responses.jsonl", "aggregate-report.json", "repair-sensitivity-report.json",
                  "cross-domain-report.json", "condition-transition-report.json", "pilot-freeze.json")


def assert_scoring_rejected_without_mutation(directory):
    before = {name: (directory / name).read_bytes() for name in ANALYSIS_FILES}
    assert not (directory / "execution-freeze.json").exists()
    with pytest.raises(ValueError, match="EXECUTION_INCOMPLETE: scoring prohibited"):
        score(directory)
    assert before == {name: (directory / name).read_bytes() for name in ANALYSIS_FILES}
    assert not (directory / "execution-freeze.json").exists()


@pytest.fixture
def artifact_copy(tmp_path):
    destination = tmp_path / "pilot"
    shutil.copytree(ARTIFACT_DIRECTORY, destination)
    return destination


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


def test_plan_revision_and_artifacts_are_frozen_before_execution():
    plan = pilot_plan()
    assert plan["previous_plan_sha256"] == "ab393f32b9da8f8b27f1d45cdd1795a88b35073ce9eef948811e5205a4dee2f5"
    assert plan["decoding"]["max_output_tokens"] == 25_000
    assert plan["zero_real_responses_before_revision"] is True
    assert plan["sample_sizes"] == {"unique_formal_instances": 18, "primary_calls_per_model": 54, "cross_domain_additional_calls_per_model": 16, "total_calls_per_model": 70}
    expected = build_artifacts()
    assert set(expected) == {path.name for path in ARTIFACT_DIRECTORY.iterdir()}
    assert all((ARTIFACT_DIRECTORY / name).read_bytes() == value for name, value in expected.items())
    assert verify()["status"] == "READY_FOR_PROVIDER_EXECUTION"
    assert (HISTORICAL_ARTIFACT_DIRECTORY / "pilot-plan.json").read_bytes() != (ARTIFACT_DIRECTORY / "pilot-plan.json").read_bytes()


def test_baselines_use_one_natural_abstract_render_per_formal_instance():
    report = json.loads((ARTIFACT_DIRECTORY / "aggregate-report.json").read_text())["baselines"]
    assert report["oracle"] == {"accuracy": 1.0, "all_cases_have_mechanically_certifiable_consistent_action": True,
                                "n": 18, "not_an_ai_model": True, "proposition_correct": 18}
    ignorant = report["deliberately_ignorant_majority_by_track"]
    assert ignorant[TRACK_A]["n"] == 12 and ignorant[TRACK_A]["correct"] == 4 and ignorant[TRACK_A]["accuracy"] == 1 / 3
    assert ignorant[TRACK_B]["n"] == 6 and ignorant[TRACK_B]["correct"] == 3 and ignorant[TRACK_B]["accuracy"] == 1 / 2


@pytest.mark.parametrize("marker", ["raw", "incomplete", "transport", "sessions", "manifest", "freeze", "scored"])
def test_build_never_erases_execution_evidence(artifact_copy, marker):
    markers = {
        "raw": ("raw-responses.jsonl", b'{"completed":"response"}\n'),
        "incomplete": ("incomplete-responses.jsonl", b'{"status":"incomplete"}\n'),
        "transport": ("transport-events.jsonl", b'{"transport":"failure"}\n'),
        "sessions": ("execution-sessions.jsonl", b'{"session":"started"}\n'),
        "manifest": ("execution-manifest.json", b'{"frozen":"configuration"}\n'),
        "freeze": ("execution-freeze.json", b'{"frozen":"results"}\n'),
        "scored": ("scored-responses.jsonl", b'{"scored":"response"}\n'),
    }
    name, evidence = markers[marker]
    (artifact_copy / name).write_bytes(evidence)
    if marker == "raw":
        (artifact_copy / "execution-manifest.json").write_bytes(b'{"frozen":"configuration"}\n')
    before = {path.name: path.read_bytes() for path in artifact_copy.iterdir() if path.is_file()}
    with pytest.raises(RuntimeError, match="after execution has begun"):
        write_artifacts(artifact_copy)
    assert {path.name: path.read_bytes() for path in artifact_copy.iterdir() if path.is_file()} == before


def test_build_is_idempotent_for_exact_pre_execution_freeze(artifact_copy):
    before = {path.name: path.read_bytes() for path in artifact_copy.iterdir() if path.is_file()}
    write_artifacts(artifact_copy)
    assert {path.name: path.read_bytes() for path in artifact_copy.iterdir() if path.is_file()} == before


def test_build_creates_pre_execution_freeze_in_empty_directory(tmp_path):
    directory = tmp_path / "empty-pilot"
    directory.mkdir()
    write_artifacts(directory)
    assert {path.name: path.read_bytes() for path in directory.iterdir()} == build_artifacts()


def test_strict_parser_accepts_only_neutral_schema():
    requests, keys = build_requests(); key = keys[requests[0]["render_id"]]
    valid = {"answer_id": next(iter(key["answer_id_to_semantic"])), "action_id": next(iter(key["action_id_to_semantic"])), "confidence": 0.8}
    assert strict_parse(json.dumps(valid), key) == valid
    with pytest.raises(ValueError): strict_parse(json.dumps(valid | {"analysis": "private"}), key)
    with pytest.raises(ValueError): strict_parse(json.dumps(valid | {"confidence": 1.1}), key)


def test_format_repair_payload_is_semantics_preserving_and_omits_unsupported_parameters():
    config = configurations()[0] | {"unsupported_parameters": ["temperature", "seed", "reasoning_effort"]}
    payload = build_format_repair_payload(config, {"answer_id": "Q"}, "malformed Q2 U1 0.7")
    context = json.loads(payload["input"])
    assert context["malformed_response"] == "malformed Q2 U1 0.7"
    assert context["format_only_message"] == FORMAT_ONLY_MESSAGE
    assert "Do not solve" in context["format_only_message"] and "Do not reconsider" in context["format_only_message"]
    assert not {"temperature", "seed", "reasoning"} & payload.keys()
    initial = build_initial_payload(configurations()[0], {})
    assert initial["temperature"] == 0 and initial["store"] is False


def test_openai_responses_adapter_extractor_fixtures():
    text, usage, request_id = extract_openai_responses(provider_response('{"answer_id":"Q0"}', "resp_ok"))
    assert text == '{"answer_id":"Q0"}' and usage == {"input_tokens": 2, "output_tokens": 3} and request_id == "resp_ok"
    with pytest.raises(ValueError, match="no output_text"): extract_openai_responses({"id": "x", "status": "completed", "output": []})
    with pytest.raises(ValueError, match="must be an object"): extract_openai_responses([])
    with pytest.raises(ValueError, match="provider error"): extract_openai_responses({"error": {"code": "bad_request"}})
    with pytest.raises(ValueError, match="malformed"): extract_openai_responses({"status": "completed", "output": [{"type": "message", "content": {}}]})
    with pytest.raises(ProviderIncompleteResponse) as exc:
        extract_openai_responses({"id": "resp_incomplete", "status": "incomplete", "usage": {"output_tokens": 25000},
                                  "incomplete_details": {"reason": "max_output_tokens"}, "output": []})
    assert exc.value.reason == "max_output_tokens"
    for status in ("failed", "in_progress", "cancelled", "queued"):
        with pytest.raises(ProviderNoncompletedResponse) as exc:
            extract_openai_responses({"id": "not_done", "status": status, "output": provider_response()["output"]})
        assert exc.value.status == status
    with pytest.raises(ValueError, match="top-level status"):
        extract_openai_responses({"id": "missing_status", "output": provider_response()["output"]})


def test_configuration_validation_rejects_duplicates_roles_and_adapter(monkeypatch):
    monkeypatch.setenv("TEST_STANDARD_KEY", "secret"); monkeypatch.setenv("TEST_STRONG_KEY", "secret")
    assert len(validate_configurations(configurations())) == 2
    with pytest.raises(ValueError, match="IDs"): validate_configurations([configurations()[0], configurations()[1] | {"id": "standard"}])
    with pytest.raises(ValueError, match="required model role"): validate_configurations([configurations()[0], configurations()[1] | {"role": "standard/default reasoning"}])
    with pytest.raises(ValueError, match="adapter"): validate_configurations([configurations()[0] | {"provider_adapter": "arbitrary"}, configurations()[1]])


@pytest.mark.parametrize(("index", "change"), [
    (0, {"reasoning_effort": "low"}), (1, {"reasoning_effort": "xhigh"}),
    (0, {"reasoning_effort": "high"}), (1, {"reasoning_effort": "medium"}),
    (1, {"endpoint": "https://other.example/v1/responses"}), (1, {"model": "other-model"}),
    (1, {"temperature": 0.2}), (1, {"seed": 7}),
    (1, {"unsupported_parameters": ["temperature"]}),
])
def test_configuration_validation_enforces_exact_medium_high_treatment(monkeypatch, index, change):
    monkeypatch.setenv("TEST_STANDARD_KEY", "secret"); monkeypatch.setenv("TEST_STRONG_KEY", "secret")
    changed = configurations(); changed[index] = changed[index] | change
    with pytest.raises(ValueError, match="treatment|generation-treatment"):
        validate_configurations(changed)


def test_configuration_validation_rejects_output_cap_drift(monkeypatch):
    monkeypatch.setenv("TEST_STANDARD_KEY", "secret"); monkeypatch.setenv("TEST_STRONG_KEY", "secret")
    changed = configurations(); changed[1] = changed[1] | {"max_output_tokens": 24_999}
    with pytest.raises(ValueError, match="frozen limit"):
        validate_configurations(changed)


@pytest.mark.parametrize("unsupported_reasoning_name", ["reasoning", "reasoning_effort"])
def test_required_roles_cannot_mark_reasoning_unsupported(monkeypatch, unsupported_reasoning_name):
    monkeypatch.setenv("TEST_STANDARD_KEY", "secret"); monkeypatch.setenv("TEST_STRONG_KEY", "secret")
    changed = [config | {"unsupported_parameters": [unsupported_reasoning_name]} for config in configurations()]
    with pytest.raises(ValueError, match="reasoning cannot be marked unsupported"):
        validate_configurations(changed)


def test_frozen_example_emits_exact_required_reasoning_payloads():
    example = json.loads((ROOT / "configs" / "stage6a-models.example.json").read_text())["configurations"]
    validated = validate_configurations(example, require_credentials=False)
    by_role = {config["role"]: config for config in validated}
    standard = build_initial_payload(by_role["standard/default reasoning"], {})
    stronger = build_initial_payload(by_role["stronger reasoning"], {})
    assert standard["reasoning"] == {"effort": "medium"}
    assert stronger["reasoning"] == {"effort": "high"}
    for payload in (standard, stronger):
        assert "temperature" not in payload and "seed" not in payload
        assert payload["store"] is False
        assert payload["max_output_tokens"] == 25_000


def test_repair_preserves_both_calls_metadata_and_occurs_once(artifact_copy, tmp_path, monkeypatch):
    monkeypatch.setenv("TEST_STANDARD_KEY", "x"); monkeypatch.setenv("TEST_STRONG_KEY", "x")
    config_path = tmp_path / "config.json"; config_path.write_text(json.dumps({"configurations": configurations()}))
    requests, keys = build_requests(); private = keys[requests[0]["render_id"]]
    valid = json.dumps({"answer_id": next(iter(private["answer_id_to_semantic"])), "action_id": next(iter(private["action_id_to_semantic"])), "confidence": 0.5})
    calls = []
    def transport(config, payload, credential):
        calls.append(json.loads(payload["input"]))
        if len(calls) == 1: return provider_response("not json", "initial-id")
        if len(calls) == 2: return provider_response(valid, "repair-id")
        raise OSError("stop after first completed request")
    with pytest.raises(OSError): run(config_path, artifact_copy, transport, harness_sha="test-sha")
    rows = [json.loads(x) for x in (artifact_copy / "raw-responses.jsonl").read_text().splitlines()]
    assert len(rows) == 1 and rows[0]["repair_attempted"]
    assert rows[0]["initial_raw_response"] == "not json" and rows[0]["initial_provider_request_id"] == "initial-id"
    assert rows[0]["repair_raw_response"] == valid and rows[0]["repair_provider_request_id"] == "repair-id"
    assert calls[1]["malformed_response"] == "not json"
    assert "original_request" not in calls[1]


@pytest.mark.parametrize("reason", ["max_output_tokens", "content_filter"])
def test_incomplete_response_is_preserved_without_parse_repair_or_completion(artifact_copy, tmp_path, monkeypatch, reason):
    monkeypatch.setenv("TEST_STANDARD_KEY", "x"); monkeypatch.setenv("TEST_STRONG_KEY", "x")
    config_path = tmp_path / "config.json"; config_path.write_text(json.dumps({"configurations": configurations()}))
    calls = 0
    envelope = {"id": "resp_incomplete", "status": "incomplete", "incomplete_details": {"reason": reason},
                "usage": {"input_tokens": 2, "output_tokens": 25000}, "output": []}
    def transport(config, payload, credential):
        nonlocal calls; calls += 1
        assert payload["store"] is False
        if calls == 1:
            return envelope
        raise OSError("stop after incomplete evidence")
    with pytest.raises(OSError):
        run(config_path, artifact_copy, transport, harness_sha="test-sha")
    assert (artifact_copy / "raw-responses.jsonl").read_text() == ""
    rows = [json.loads(line) for line in (artifact_copy / "incomplete-responses.jsonl").read_text().splitlines()]
    assert len(rows) == 1 and rows[0]["provider_response"] == envelope
    assert rows[0]["provider_request_id"] == "resp_incomplete" and rows[0]["token_usage"] == envelope["usage"]
    assert rows[0]["incomplete_reason"] == reason and rows[0]["repair_attempted"] is False
    assert rows[0]["phase"] == "initial"
    result = verify(artifact_copy)
    assert result["status"] == "EXECUTION_INCOMPLETE" and result["completed"] == 0
    assert result["provider_incomplete"] == 1
    assert_scoring_rejected_without_mutation(artifact_copy)

    resumed = []
    def resumed_transport(config, payload, credential):
        resumed.append(json.loads(payload["input"])["render_id"])
        raise OSError("stop resumed session")
    with pytest.raises(OSError):
        run(config_path, artifact_copy, resumed_transport, harness_sha="test-sha")
    requests, _ = build_requests()
    assert resumed == [requests[1]["render_id"]]


def test_repair_incomplete_preserves_both_evidence_streams_and_resume_skips_key(artifact_copy, tmp_path, monkeypatch):
    monkeypatch.setenv("TEST_STANDARD_KEY", "x"); monkeypatch.setenv("TEST_STRONG_KEY", "x")
    config_path = tmp_path / "config.json"; config_path.write_text(json.dumps({"configurations": configurations()}))
    calls = []
    repair_envelope = {"id": "repair_incomplete", "status": "incomplete",
                       "incomplete_details": {"reason": "max_output_tokens"},
                       "usage": {"input_tokens": 4, "output_tokens": 25000}, "output": []}
    def transport(config, payload, credential):
        calls.append(json.loads(payload["input"]))
        if len(calls) == 1:
            return provider_response("malformed initial", "initial_completed")
        if len(calls) == 2:
            return repair_envelope
        raise OSError("stop on next scientific key")
    with pytest.raises(OSError):
        run(config_path, artifact_copy, transport, harness_sha="test-sha")
    assert len(calls) == 3  # initial, its one repair, then the next scientific key
    raw = [json.loads(line) for line in (artifact_copy / "raw-responses.jsonl").read_text().splitlines()]
    incomplete = [json.loads(line) for line in (artifact_copy / "incomplete-responses.jsonl").read_text().splitlines()]
    first_raw = next(row for row in raw if row["initial_provider_request_id"] == "initial_completed")
    first_incomplete = incomplete[0]
    assert first_raw["initial_raw_response"] == "malformed initial" and first_raw["repair_raw_response"] is None
    assert first_incomplete["initial_raw_response"] == "malformed initial"
    assert first_incomplete["provider_response"] == repair_envelope and first_incomplete["phase"] == "repair"
    assert verify(artifact_copy)["status"] == "EXECUTION_INCOMPLETE"
    assert_scoring_rejected_without_mutation(artifact_copy)
    before = ((artifact_copy / "raw-responses.jsonl").read_bytes(), (artifact_copy / "incomplete-responses.jsonl").read_bytes())
    resumed_calls = []
    def resumed(config, payload, credential):
        resumed_calls.append(json.loads(payload["input"])["render_id"])
        raise OSError("stop resumed session")
    with pytest.raises(OSError):
        run(config_path, artifact_copy, resumed, harness_sha="test-sha")
    requests, _ = build_requests()
    assert resumed_calls == [requests[1]["render_id"]]
    assert before == ((artifact_copy / "raw-responses.jsonl").read_bytes(), (artifact_copy / "incomplete-responses.jsonl").read_bytes())


def test_repair_transport_failure_preserves_initial_evidence(artifact_copy, tmp_path, monkeypatch):
    monkeypatch.setenv("TEST_STANDARD_KEY", "x"); monkeypatch.setenv("TEST_STRONG_KEY", "x")
    config_path = tmp_path / "config.json"; config_path.write_text(json.dumps({"configurations": configurations()}))
    calls = 0
    def transport(config, payload, credential):
        nonlocal calls; calls += 1
        if calls == 1:
            return provider_response("not json", "initial-preserved")
        raise OSError("repair unavailable")
    with pytest.raises(OSError):
        run(config_path, artifact_copy, transport, harness_sha="test-sha")
    rows = [json.loads(line) for line in (artifact_copy / "raw-responses.jsonl").read_text().splitlines()]
    assert len(rows) == 1
    assert rows[0]["initial_raw_response"] == "not json"
    assert rows[0]["initial_provider_request_id"] == "initial-preserved"
    assert rows[0]["repair_attempted"] is True and rows[0]["repair_raw_response"] is None
    events = [json.loads(line) for line in (artifact_copy / "transport-events.jsonl").read_text().splitlines()]
    assert events[0]["phase"] == "repair"
    verification = verify(artifact_copy)
    assert verification["status"] == "EXECUTION_INCOMPLETE"
    assert verification["completed"] == 0 and verification["missing"] == 140
    assert_scoring_rejected_without_mutation(artifact_copy)
    requests, _ = build_requests(); resumed = []
    def resume_transport(config, payload, credential):
        resumed.append(json.loads(payload["input"])["render_id"])
        raise OSError("stop resumed session")
    with pytest.raises(OSError):
        run(config_path, artifact_copy, resume_transport, harness_sha="test-sha")
    assert resumed == [requests[1]["render_id"]]


def test_resume_skips_first_ten_and_transport_events_are_separate(artifact_copy, tmp_path, monkeypatch):
    monkeypatch.setenv("TEST_STANDARD_KEY", "x"); monkeypatch.setenv("TEST_STRONG_KEY", "x")
    path = tmp_path / "config.json"; path.write_text(json.dumps({"configurations": configurations()}))
    requests, keys = build_requests(); valid_by_prompt = {}
    for request in requests:
        private = keys[request["render_id"]]
        valid_by_prompt[request["render_id"]] = json.dumps({"answer_id": next(iter(private["answer_id_to_semantic"])), "action_id": next(iter(private["action_id_to_semantic"])), "confidence": 0.5})
    count = 0
    def first_transport(config, payload, credential):
        nonlocal count; count += 1
        if count == 11: raise OSError("interruption")
        prompt = json.loads(payload["input"])
        return provider_response(valid_by_prompt[prompt["render_id"]], f"id-{count}")
    with pytest.raises(OSError): run(path, artifact_copy, first_transport, harness_sha="test-sha")
    assert len((artifact_copy / "raw-responses.jsonl").read_text().splitlines()) == 10
    resumed = []
    def resumed_transport(config, payload, credential):
        prompt = json.loads(payload["input"]); resumed.append(prompt["render_id"]); raise OSError("stop")
    with pytest.raises(OSError): run(path, artifact_copy, resumed_transport, harness_sha="test-sha")
    assert resumed == [requests[10]["render_id"]]
    events = [json.loads(x) for x in (artifact_copy / "transport-events.jsonl").read_text().splitlines()]
    assert len(events) == 2 and all("execution_key" in x and "error_class" in x and "safe_provider_status" in x for x in events)
    sessions = [json.loads(x) for x in (artifact_copy / "execution-sessions.jsonl").read_text().splitlines()]
    assert sessions[1]["completed_before_session"] == 10 and sessions[1]["transport_attempts"] == 1 and sessions[1]["transport_failures"] == 1


def test_duplicate_partial_and_configuration_request_drift_failures(artifact_copy, tmp_path, monkeypatch):
    monkeypatch.setenv("TEST_STANDARD_KEY", "x"); monkeypatch.setenv("TEST_STRONG_KEY", "x")
    path = tmp_path / "config.json"; path.write_text(json.dumps({"configurations": configurations()}))
    requests, keys = build_requests(); private = keys[requests[0]["render_id"]]
    valid = json.dumps({"answer_id": next(iter(private["answer_id_to_semantic"])), "action_id": next(iter(private["action_id_to_semantic"])), "confidence": 0.5})
    calls = 0
    def transport(config, payload, credential):
        nonlocal calls; calls += 1
        if calls > 1: raise OSError("stop")
        return provider_response(valid)
    with pytest.raises(OSError): run(path, artifact_copy, transport, harness_sha="test-sha")
    assert verify(artifact_copy)["status"] == "EXECUTION_INCOMPLETE"
    raw_path = artifact_copy / "raw-responses.jsonl"; one = raw_path.read_text()
    raw_path.write_text(one + one)
    with pytest.raises(ValueError, match="duplicate"): verify(artifact_copy)
    raw_path.write_text(one)
    changed = [config | {"temperature": 0.2} for config in configurations()]
    changed_path = tmp_path / "changed.json"; changed_path.write_text(json.dumps({"configurations": changed}))
    with pytest.raises(ValueError, match="manifest drift"): run(changed_path, artifact_copy, lambda *_: provider_response(valid), harness_sha="test-sha")
    row = json.loads(one); row["prompt_sha256"] = "0" * 64; raw_path.write_text(json.dumps(row) + "\n")
    with pytest.raises(ValueError, match="drift"): verify(artifact_copy)


def test_interrupted_partial_run_cannot_be_scored(artifact_copy, tmp_path, monkeypatch):
    monkeypatch.setenv("TEST_STANDARD_KEY", "x"); monkeypatch.setenv("TEST_STRONG_KEY", "x")
    path = tmp_path / "config.json"; path.write_text(json.dumps({"configurations": configurations()}))
    requests, keys = build_requests(); private = keys[requests[0]["render_id"]]
    valid = json.dumps({"answer_id": next(iter(private["answer_id_to_semantic"])), "action_id": next(iter(private["action_id_to_semantic"])), "confidence": 0.5})
    calls = 0
    def transport(config, payload, credential):
        nonlocal calls; calls += 1
        if calls == 1: return provider_response("bad")
        if calls == 2: return provider_response(valid)
        raise OSError("stop")
    with pytest.raises(OSError): run(path, artifact_copy, transport, harness_sha="test-sha")
    assert_scoring_rejected_without_mutation(artifact_copy)


def test_complete_execution_scores_and_freezes_all_140_keys(artifact_copy, tmp_path, monkeypatch):
    monkeypatch.setenv("TEST_STANDARD_KEY", "x"); monkeypatch.setenv("TEST_STRONG_KEY", "x")
    path = tmp_path / "config.json"; path.write_text(json.dumps({"configurations": configurations()}))
    requests, keys = build_requests(); valid_by_render = {}
    for request in requests:
        private = keys[request["render_id"]]
        valid_by_render[request["render_id"]] = json.dumps({
            "answer_id": next(iter(private["answer_id_to_semantic"])),
            "action_id": next(iter(private["action_id_to_semantic"])), "confidence": 0.5,
        })
    calls = 0
    def transport(config, payload, credential):
        nonlocal calls; calls += 1
        prompt = json.loads(payload["input"])
        if calls == 1:
            return provider_response("bad", "initial-malformed")
        if "format_only_message" in prompt:
            return provider_response(valid_by_render[requests[0]["render_id"]], "repair-completed")
        return provider_response(valid_by_render[prompt["render_id"]], f"completed-{calls}")
    run(path, artifact_copy, transport, harness_sha="test-sha")
    assert calls == 141
    before = (artifact_copy / "pilot-freeze.json").read_bytes()
    freeze = score(artifact_copy)
    assert (artifact_copy / "pilot-freeze.json").read_bytes() == before
    sensitivity = json.loads((artifact_copy / "repair-sensitivity-report.json").read_text())
    assert sensitivity["parse_failure_initial"] == 1 and sensitivity["parse_failure_after_repair"] == 0
    assert sensitivity["accuracy_treating_all_repairs_as_failures"] < sensitivity["accuracy_with_allowed_format_repair"]
    assert len((artifact_copy / "scored-responses.jsonl").read_text().splitlines()) == 140
    assert set(freeze["files"]) == {"execution-manifest.json", "raw-responses.jsonl", "incomplete-responses.jsonl",
                                     "transport-events.jsonl", "execution-sessions.jsonl", "scored-responses.jsonl",
                                     "aggregate-report.json", "repair-sensitivity-report.json", "cross-domain-report.json",
                                     "condition-transition-report.json"}
    assert all(freeze["files"][name] == hashlib.sha256((artifact_copy / name).read_bytes()).hexdigest()
               for name in freeze["files"])
    assert verify(artifact_copy) == {"status": "VERIFIED_EXECUTED", "completed": 140, "expected": 140}


def test_representation_inconsistency_is_cross_render_and_generic_error_is_other():
    formal = cross_domain_ids()[0]
    rows = []
    for domain, answer in zip(("abstract", "ant_colony", "technical_system"), ("A", "B", "A"), strict=True):
        rows.append({"model_configuration_id": "m", "formal_instance_id": formal, "condition": "natural", "domain": domain,
                     "track": TRACK_A, "parse_failure_after_repair": False, "conservative_parse_failure": False,
                     "parse_failure_initial": False, "repair_attempted": False, "canonical_proposition": answer,
                     "gold_proposition": "A", "confidence": 0.5, "error_taxonomy": [],
                     "scoring": {"proposition_correct": answer == "A", "epistemically_consistent": True,
                                 "knowledge_action_dissociation": False, "unsafe_fixed_deployment_after_correct_per_world_only": False}})
    report = aggregate_reports(rows)["cross-domain-report.json"]
    assert report["representation_inconsistency_case_count"] == 1
    assert report["representation_inconsistency_formal_instance_ids"] == [{"model_configuration_id": "m", "formal_instance_id": formal}]
    assert _error_types("CERTIFIABLY_LOSING", "CERTIFIABLY_WINNING", {"proposition_correct": False,
        "unsafe_fixed_deployment_after_correct_per_world_only": False}) == ["OTHER"]
