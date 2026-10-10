import json
from pathlib import Path

import pytest

from enforceability import model_pilot as pilot
from enforceability import provider_canary as canary
from test_model_pilot import provider_response


def setup(tmp_path, monkeypatch):
    config = tmp_path / "config.json"
    config.write_bytes((pilot.ROOT / "configs/stage6a-models.example.json").read_bytes())
    monkeypatch.setenv("OPENAI_API_KEY", "FAKE-CREDENTIAL-FOR-TEST-ONLY")
    # tmp_path may be inside a checkout in CI. Isolate the path-policy root only.
    monkeypatch.setattr(canary, "_external", lambda p: p.resolve())
    return config


def test_canary_uses_adapter_fixed_input_and_external_stream_only(tmp_path, monkeypatch):
    config = setup(tmp_path, monkeypatch)
    calls = []
    before = {p: p.read_bytes() for p in pilot.ARTIFACT_DIRECTORY.iterdir()}
    def transport(configuration, payload, credential):
        calls.append(payload)
        return provider_response('{"ping":"ok"}', "canary-response")
    output = tmp_path / "canary"
    result = canary.canary(config, output, transport)
    assert result["status"] == "PASSED" and result["scientific_requests"] == 0
    assert len(calls) == 2
    assert [p["reasoning"]["effort"] for p in calls] == ["medium", "high"]
    for payload in calls:
        assert json.loads(payload["input"]) == canary.CANARY_PROMPT
        assert payload["store"] is False and payload["max_output_tokens"] == 25000
        assert not {"temperature", "seed"} & payload.keys()
    assert set(p.name for p in output.iterdir()) == {"canary-report.json", "canary-evidence.jsonl"}
    assert before == {p: p.read_bytes() for p in pilot.ARTIFACT_DIRECTORY.iterdir()}
    receipt = output / "canary-report.json"
    assert result["transport_mode"] == "mock"
    with pytest.raises(ValueError, match="transport provenance"):
        canary.verify_receipt(config, receipt)
    assert canary.verify_receipt(config, receipt, expected_transport="mock")["status"] == "PASSED"
    value = json.loads(receipt.read_text()); value["configuration_sha256"] = "bad"
    receipt.write_text(json.dumps(value))
    with pytest.raises(ValueError, match="drift"):
        canary.verify_receipt(config, receipt, expected_transport="mock")
    with pytest.raises(FileExistsError):
        canary.canary(config, output, transport)


@pytest.mark.parametrize("status", ["incomplete", "failed", "queued", "cancelled", "in_progress"])
def test_canary_noncompletion_never_retries_or_passes(tmp_path, monkeypatch, status):
    config = setup(tmp_path, monkeypatch)
    calls = []
    def transport(*args):
        calls.append(1)
        return provider_response('{"ping":"ok"}') | {"status": status}
    output = tmp_path / "canary"
    assert canary.canary(config, output, transport)["status"] == "NOT_PASSED"
    assert calls == [1]
    with pytest.raises(ValueError, match="passing"):
        canary.verify_receipt(config, output / "canary-report.json")


def test_canary_rejects_scientific_and_repository_output_paths():
    for path in (pilot.ROOT, pilot.ARTIFACT_DIRECTORY, pilot.ROOT / "canary", pilot.V12_DIRECTORY):
        with pytest.raises(ValueError, match="outside"):
            canary._external(Path(path))
