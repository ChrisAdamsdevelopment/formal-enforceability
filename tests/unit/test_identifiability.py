from fractions import Fraction
import json

import pytest

from enforceability.identifiability import (
    ADVERSARY_ACTIONS, ARTIFACT_DIRECTORY, CANONICAL_COLLECTION_REGIME, COLLECTION_REGIME_VERSION,
    CONTROLLER_ACTIONS, PublicSignature, ThresholdStatus, ambiguity_classes, ambiguity_interval,
    ambiguity_values, as_schema_game, build_artifacts, enumerate_games, public_signature,
    probabilistic_phenomenon_witnesses, select_witnesses, strategic_value, threshold_phase_structure,
    threshold_status, threshold_sweep, verify_artifacts,
)
from enforceability.independent_validation import build_reachable_tree, validate_game


def game_by_id(game_id):
    return next(game for game in enumerate_games() if game.game_id == game_id)


def test_complete_deterministic_family_and_collection_regime():
    games = enumerate_games()
    assert len(games) == 256
    assert len({g.failure_probabilities for g in games}) == 256
    regime = CANONICAL_COLLECTION_REGIME
    assert regime.state_blind and regime.version == COLLECTION_REGIME_VERSION
    assert regime.joint_action_probabilities == (Fraction(1, 4),) * 4
    assert all(probability > 0 for probability in regime.joint_action_probabilities)


def test_signature_is_exact_public_information_only():
    signature = public_signature(game_by_id("d006"))
    assert signature.failure_probabilities == (Fraction(0), Fraction(1, 2), Fraction(1, 2), Fraction(0))
    assert all(isinstance(value, Fraction) for value in signature.failure_probabilities)
    serialized = json.dumps({"failure_conditionals": [str(x) for x in signature.failure_probabilities]})
    assert "s0" not in serialized and "s1" not in serialized


def test_grouping_values_intervals_and_weak_threshold_boundary():
    classes = ambiguity_classes()
    assert len(classes) == 81 and sum(map(len, classes.values())) == 256
    signature = public_signature(game_by_id("d006"))
    assert game_by_id("d036") in classes[signature]
    values = tuple(sorted({strategic_value(game) for game in classes[signature]}))
    assert ambiguity_values(signature) == values
    assert ambiguity_interval(signature) == (min(values), max(values)) == (Fraction(1, 4), Fraction(1, 2))
    assert threshold_status(PublicSignature((Fraction(0),) * 4), Fraction(0)) == ThresholdStatus.CERTIFIABLY_WINNING
    assert threshold_status(signature, Fraction(1, 4)) == ThresholdStatus.INSUFFICIENT_INFORMATION
    assert threshold_status(signature, Fraction(0)) == ThresholdStatus.CERTIFIABLY_LOSING


def test_frozen_witnesses_and_deterministic_selection():
    witnesses = select_witnesses()
    assert witnesses == select_witnesses()
    for name in ("witness_A", "witness_B"):
        witness = witnesses[name]
        games = [game_by_id(game_id) for game_id in witness["game_ids"]]
        epsilon = Fraction(witness["epsilon"])
        assert public_signature(games[0]) == public_signature(games[1])
        assert strategic_value(games[0]) != strategic_value(games[1])
        assert [strategic_value(game) <= epsilon for game in games] == [True, False]
    assert witnesses["witness_B"]["all_public_joint_actions_positive_probability"]
    assert len(set(public_signature(game_by_id("d015")).failure_probabilities)) == 1
    witness_c = witnesses["witness_C"]
    assert witness_c["game_ids"] == ["d006", "d036"]
    assert witness_c["epsilon"] == "1/2"
    assert witness_c["epsilon_nonidentified"] == "1/4"
    assert witness_c["game_labels"] == ["WINNING", "WINNING"]
    c_games = ambiguity_classes()[public_signature(game_by_id(witness_c["game_ids"][0]))]
    assert len({strategic_value(game) for game in c_games}) > 1
    epsilon = Fraction(witness_c["epsilon"])
    assert len({strategic_value(game) <= epsilon for game in c_games}) == 1


def test_witness_class_has_all_three_exact_threshold_phases():
    signature = public_signature(game_by_id("d006"))
    expected = {
        Fraction(0): ThresholdStatus.CERTIFIABLY_LOSING,
        Fraction(1, 4): ThresholdStatus.INSUFFICIENT_INFORMATION,
        Fraction(1, 3): ThresholdStatus.INSUFFICIENT_INFORMATION,
        Fraction(1, 2): ThresholdStatus.CERTIFIABLY_WINNING,
        Fraction(3, 4): ThresholdStatus.CERTIFIABLY_WINNING,
    }
    assert {epsilon: threshold_status(signature, epsilon) for epsilon in expected} == expected
    assert threshold_phase_structure(signature) == {
        "ambiguity_interval": ["1/4", "1/2"],
        "standard_partial_identification_logic": True,
        "phases": [
            {"epsilon_region": "epsilon < 1/4", "status": "CERTIFIABLY_LOSING"},
            {"epsilon_region": "1/4 <= epsilon < 1/2", "status": "INSUFFICIENT_INFORMATION"},
            {"epsilon_region": "epsilon >= 1/2", "status": "CERTIFIABLY_WINNING"},
        ],
    }


def test_schema_conversion_preserves_information_semantics_for_all_256_games():
    for family_game in enumerate_games():
        schema_game = as_schema_game(family_game)
        tree = build_reachable_tree(schema_game)
        assert tuple(position.state for position, _ in tree.initial) == ("s0", "s1")
        assert {position.controller_view.observations for position, _ in tree.initial} == {("hidden",)}
        assert {position.adversary_view.states for position, _ in tree.initial} == {("s0",), ("s1",)}


def test_independent_validator_agrees_on_all_256_games_including_witnesses():
    pytest.importorskip("scipy")
    witness_ids = {game_id for witness in select_witnesses().values() if isinstance(witness, dict) and "game_ids" in witness for game_id in witness["game_ids"]}
    checked = set()
    for family_game in enumerate_games():
        schema_game = as_schema_game(family_game)
        independent = validate_game(schema_game)
        assert abs(independent.value - float(strategic_value(family_game))) < independent.tolerance
        checked.add(family_game.game_id)
    assert witness_ids <= checked


def test_probabilistic_extension_and_sweeps_are_bounded_and_deterministic():
    assert len(enumerate_games(True)) == 6561
    classes = ambiguity_classes(True)
    assert len(classes) == 625 and sum(map(len, classes.values())) == 6561
    assert sum(len(ambiguity_values(signature, True)) > 1 for signature in classes) == 297
    phenomena = probabilistic_phenomenon_witnesses()
    p1 = phenomena["P1_value_nonidentification"]
    p2 = phenomena["P2_threshold_nonidentification"]
    p3 = phenomena["P3_threshold_identification_without_value_identification"]
    assert len(p1["exact_values"]) > 1
    assert len(p2["exact_values"]) > 1 and p2["threshold_status"] == "INSUFFICIENT_INFORMATION"
    assert len(p3["exact_values"]) > 1
    assert p3["threshold_status"] in {"CERTIFIABLY_WINNING", "CERTIFIABLY_LOSING"}
    assert phenomena == probabilistic_phenomenon_witnesses()
    assert threshold_sweep() == threshold_sweep()


def test_artifacts_are_byte_identical_and_malformed_freezes_are_rejected(tmp_path):
    expected = build_artifacts()
    assert set(expected) == {path.name for path in ARTIFACT_DIRECTORY.glob("*.json")}
    assert all((ARTIFACT_DIRECTORY / name).read_bytes() == content for name, content in expected.items())
    assert verify_artifacts()
    for name, content in expected.items():
        (tmp_path / name).write_bytes(content)
    (tmp_path / "identifiability-freeze.json").write_text("{}\n")
    with pytest.raises(ValueError, match="artifact mismatch"):
        verify_artifacts(tmp_path)
    (tmp_path / "unexpected.json").write_text("{}\n")
    with pytest.raises(ValueError, match="file set mismatch"):
        verify_artifacts(tmp_path)


def test_action_sets_are_the_declared_two_by_two_family():
    game = as_schema_game(game_by_id("d000"))
    assert game.controller_actions == CONTROLLER_ACTIONS
    assert game.adversary_actions == ADVERSARY_ACTIONS
