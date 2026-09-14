import json
import hashlib
from collections import Counter

import pytest

from enforceability.stage6_pilot import (
    CONDITIONS, DOMAINS, TRACK_A, TRACK_B, TRACK_A_PROPOSITIONS, TRACK_B_PROPOSITIONS,
    ARTIFACT_DIRECTORY, build_artifacts, build_formal_instances, build_renders,
    canonicalize_response, render_instance, representation_leakage_report, verify_artifacts,
)


def test_tracks_are_separate_and_formal_instances_are_unique():
    tracks = build_formal_instances()
    assert set(tracks) == {TRACK_A, TRACK_B}
    assert len(tracks[TRACK_A]) == 36
    assert Counter(item["status"] for item in tracks[TRACK_A]) == {
        "CERTIFIABLY_LOSING": 12, "INSUFFICIENT_INFORMATION": 12, "CERTIFIABLY_WINNING": 12}
    assert len(tracks[TRACK_B]) == 12
    assert Counter(item["answer"] for item in tracks[TRACK_B]) == {"PER_WORLD_ONLY": 6, "COMMON_POLICY": 6}
    for track, items in tracks.items():
        assert len({item["formal_instance_id"] for item in items}) == len(items), track
    assert len({tuple(g.game_id for g in item["games"]) for item in tracks[TRACK_B]}) == 12


def test_public_prompts_are_solvable_and_private_gold_is_separate():
    public, private = build_renders()
    assert len(public) == len(private) == (36 + 12) * 3 * 3
    forbidden = {"canonical_answer", "gold_answer_id", "answer_id_to_semantic", "action_id_to_semantic",
                 "compatible_game_ids", "V_lower", "V_upper", "R", "R_frozen_class", "V_values"}
    semantic_enum_names = {"CERTIFIABLY_LOSING", "INSUFFICIENT_INFORMATION", "CERTIFIABLY_WINNING",
                           "CERTIFIABLY_WINNING_BUT_NOT_UNIFORMLY_ACTIONABLE", "UNIFORMLY_ACTIONABLE_WINNING"}
    for prompt in public:
        serialized = json.dumps(prompt)
        assert not forbidden.intersection(prompt)
        assert not semantic_enum_names.intersection(option["id"] for option in prompt["answer_options"])
        assert all(option["id"].startswith("Q") for option in prompt["answer_options"])
        assert all(option["id"].startswith("U") and option["operation"] for option in prompt["action_options"])
        assert prompt["epsilon"] in serialized and len(prompt["evidence"]) >= 2
        assert "simultaneous" in prompt["protocol"] and "observes" in prompt["protocol"] and "privately randomize" in prompt["protocol"]
        assert "d051" not in serialized and "d204" not in serialized
    assert all(forbidden.intersection(key) for key in private)


def test_domains_preserve_mechanical_evidence_and_conditions_change_only_instruction():
    instance = build_formal_instances()[TRACK_A][5]
    renders = [render_instance(instance, TRACK_A, domain, condition) for domain in DOMAINS for condition in CONDITIONS]
    normalized = []
    for public, _ in renders:
        normalized.append(tuple(row["observed_failure_probability"] for row in public["evidence"]))
    assert len(set(normalized)) == 1
    for domain in DOMAINS:
        domain_prompts = [render_instance(instance, TRACK_A, domain, condition)[0] for condition in CONDITIONS]
        assert len({json.dumps(prompt["evidence"], sort_keys=True) for prompt in domain_prompts}) == 1
        assert len({prompt["question"] for prompt in domain_prompts}) == 3


def test_neutral_mappings_round_trip_and_are_not_fixed():
    public, private = build_renders()
    for prompt, key in zip(public, private, strict=True):
        assert canonicalize_response(key["gold_answer_id"], key["gold_action_ids"][0], key) == (
            key["canonical_answer"], key["correct_action_semantic"])
    assert len({key["gold_answer_id"] for key in private}) > 1
    assert len({key["gold_action_ids"][0] for key in private}) > 1
    with pytest.raises(ValueError):
        canonicalize_response("Q9", "U9", private[0])


def test_deliberately_corrupted_public_record_is_detected_by_integrity_contract():
    public, private = build_renders()
    corrupt = dict(public[0]); corrupt["canonical_answer"] = private[0]["canonical_answer"]
    forbidden = {"canonical_answer", "gold_answer_id", "answer_id_to_semantic", "action_id_to_semantic"}
    assert forbidden.intersection(corrupt)
    missing = dict(public[0]); missing.pop("evidence")
    assert "evidence" not in missing


def test_actual_leave_instance_out_leakage_baseline():
    public, private = build_renders()
    report = representation_leakage_report(public, private)
    assert report["mechanics_excluded"] and report["tracks_reported_separately"]
    for track in (TRACK_A, TRACK_B):
        result = report["tracks"][track]
        assert result["unique_formal_instances"] in (36, 12)
        assert "leave_formal_instance_out_surface_1nn_accuracy" in result
        assert result["feature_schema"]


def test_artifacts_public_private_split_and_deterministic_freeze():
    expected = build_artifacts()
    assert set(expected) == {"public-prompts.jsonl", "private-answer-key.json", "render-plan-manifest.json",
                             "representation-leakage-report.json", "pilot-freeze.json"}
    assert all((ARTIFACT_DIRECTORY / name).read_bytes() == data for name, data in expected.items())
    assert verify_artifacts()
    first_public = json.loads(expected["public-prompts.jsonl"].splitlines()[0])
    assert "canonical_answer" not in first_public and "gold_answer_id" not in first_public
    assert TRACK_A_PROPOSITIONS and TRACK_B_PROPOSITIONS


def test_previous_identifiability_freeze_is_untouched():
    expected = {
        "deterministic-family-report.json": "1a2ce0d51bd7b713bee9b6363c0c0b59975892f70f04213748372aac236fca97",
        "identifiability-freeze.json": "79befa8db92a4df526c3e5f8158b6ef3f98eaab1a54f487d7c61f580e91a5f2d",
        "probabilistic-family-report.json": "bbbe523748e6113d7aae08aa920771620aa462a2cb1670a6a1bacf2e4b9ed585",
        "witnesses.json": "9c49995e6686ed2d3cbc3646f7c701e392a99f7767b5a30789ca611740e72730",
    }
    root = ARTIFACT_DIRECTORY.parent / "identifiability-v1"
    assert {path.name: hashlib.sha256(path.read_bytes()).hexdigest() for path in root.glob("*.json")} == expected
