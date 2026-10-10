"""Explicit, segregated operational check. Importing this module makes no calls."""
import json
import os
from pathlib import Path

from enforceability import model_pilot as pilot

CANARY_PROMPT = {"instruction": "Return exactly the JSON object {\"ping\":\"ok\"}."}


def _external(path: Path) -> Path:
    path = path.resolve()
    # Exclude the entire checkout, not merely the current version's directory.
    if path == pilot.ROOT.resolve() or pilot.ROOT.resolve() in path.parents:
        raise ValueError("canary evidence must be outside the repository")
    return path


def _configuration_binding(configs):
    return pilot._sha(pilot._json(configs))


def _clean_revision():
    import subprocess
    paths = ["src", "configs", "pyproject.toml"]
    if subprocess.check_output(["git", "status", "--porcelain", "--", *paths], cwd=pilot.ROOT):
        raise ValueError("provider execution requires committed runtime/configuration sources")
    return pilot._git_sha()


def canary(config_path: Path, output: Path, transport=pilot._perform_http):
    """Exactly two independent trivial requests; never retry or repair."""
    configs = pilot.validate_configurations(json.loads(config_path.read_text(encoding="utf-8"))["configurations"])
    if any(c["model"] != "gpt-5.6-terra" or c["endpoint"] != "https://api.openai.com/v1/responses" or
           set(c["unsupported_parameters"]) != {"temperature", "seed"} for c in configs):
        raise ValueError("canary requires documented Terra/Responses configuration, omitting temperature and seed")
    output = _external(output)
    if transport is pilot._perform_http:
        _clean_revision()
    output.mkdir(parents=True, exist_ok=False)
    result = {"version": "nonbenchmark-canary-v1", "status": "NOT_PASSED", "created_at": pilot._now(),
              "transport_mode": "real" if transport is pilot._perform_http else "mock",
              "harness_git_sha": pilot._git_sha(), "harness_source_sha256": pilot._sha(Path(pilot.__file__).read_bytes()),
              "canary_source_sha256": pilot._sha(Path(__file__).read_bytes()),
              "configuration_sha256": _configuration_binding(configs), "scientific_requests": 0, "checks": []}
    report = output / "canary-report.json"
    # Record intent first; a crash leaves NOT_PASSED. A rerun needs a fresh path.
    report.write_bytes(pilot._json(result))
    for config in configs:
        payload = pilot.build_initial_payload(config, CANARY_PROMPT)
        evidence = {"configuration_id": config["id"], "payload": payload}
        credential = os.environ[config["credential_env"]]
        try:
            response = transport(config, payload, credential)
            if credential and len(credential) >= 8 and credential in json.dumps(response):
                raise ValueError("credential echoed by provider; response not serialized")
            evidence["provider_response"] = response
            raw, usage, response_id = pilot.extract_openai_responses(response)
            if json.loads(raw) != {"ping": "ok"} or not isinstance(response_id, str) or not isinstance(usage, dict):
                raise ValueError("canary completed response did not meet the fixed acceptance criteria")
            evidence["passed"] = True
        except Exception as exc:
            evidence.update({"passed": False, "error_class": type(exc).__name__})
            pilot._append_jsonl(output / "canary-evidence.jsonl", evidence)
            return result
        pilot._append_jsonl(output / "canary-evidence.jsonl", evidence)
        result["checks"].append({"configuration_id": config["id"], "reasoning_effort": config["reasoning_effort"], "passed": True})
    result["status"] = "PASSED"
    result["evidence_sha256"] = pilot._sha((output / "canary-evidence.jsonl").read_bytes())
    report.write_bytes(pilot._json(result))
    return result


def verify_receipt(config_path: Path, receipt: Path, *, expected_transport: str = "real"):
    receipt = _external(receipt)
    configs = pilot.validate_configurations(json.loads(config_path.read_text(encoding="utf-8"))["configurations"], require_credentials=False)
    result = json.loads(receipt.read_text(encoding="utf-8"))
    if result.get("status") != "PASSED" or result.get("version") != "nonbenchmark-canary-v1":
        raise ValueError("passing nonbenchmark canary receipt required")
    if result.get("transport_mode") != expected_transport:
        raise ValueError("canary transport provenance mismatch; mocked evidence cannot authorize real calls")
    bindings = {"harness_git_sha": pilot._git_sha(), "harness_source_sha256": pilot._sha(Path(pilot.__file__).read_bytes()),
                "canary_source_sha256": pilot._sha(Path(__file__).read_bytes()), "configuration_sha256": _configuration_binding(configs),
                "scientific_requests": 0}
    if any(result.get(k) != v for k, v in bindings.items()):
        raise ValueError("canary receipt configuration or runtime drift")
    evidence_path = receipt.parent / "canary-evidence.jsonl"
    if result.get("evidence_sha256") != pilot._sha(evidence_path.read_bytes()):
        raise ValueError("canary evidence hash mismatch")
    rows = pilot._read_jsonl(evidence_path)
    if len(rows) != 2:
        raise ValueError("canary requires exactly two completed checks")
    for config, row in zip(configs, rows, strict=True):
        if row.get("configuration_id") != config["id"] or row.get("payload") != pilot.build_initial_payload(config, CANARY_PROMPT):
            raise ValueError("canary payload/configuration mismatch")
        raw, usage, response_id = pilot.extract_openai_responses(row.get("provider_response"))
        if row.get("passed") is not True or json.loads(raw) != {"ping": "ok"} or not isinstance(usage, dict) or not isinstance(response_id, str):
            raise ValueError("canary evidence did not pass")
    return result
