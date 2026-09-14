from fractions import Fraction
import ast
from pathlib import Path

import pytest

from enforceability.independent_validation import (
    DEFAULT_TOLERANCE,
    ValidationLimitError,
    ValidationLimits,
    build_reachable_tree,
    validate_game,
)
from enforceability.oracle import solve
from enforceability.validation_cases import (
    deterministic_family,
    hand_fixtures,
    matching_pennies,
    multi_round_stochastic,
    one_third,
    probabilistic_family,
)
from enforceability.validation_report import run_cross_validation


def _agrees(game):
    independent = validate_game(game)
    primary = solve(game)
    assert independent.primal_dual_gap <= DEFAULT_TOLERANCE
    assert independent.value == pytest.approx(float(primary.failure_probability), abs=DEFAULT_TOLERANCE)
    return independent, primary


@pytest.mark.parametrize(("name", "game"), hand_fixtures(), ids=lambda value: value if isinstance(value, str) else None)
def test_semantic_hand_fixtures(name, game):
    del name
    _agrees(game)


def test_exact_one_third_and_numerical_estimate():
    independent, primary = _agrees(one_third())
    assert primary.failure_probability == Fraction(1, 3)
    assert independent.value == pytest.approx(1 / 3, abs=DEFAULT_TOLERANCE)


def test_matching_pennies_requires_private_controller_mixture():
    independent, primary = _agrees(matching_pennies())
    assert primary.failure_probability == Fraction(1, 2)
    assert independent.value == pytest.approx(0.5, abs=DEFAULT_TOLERANCE)
    assert sorted(independent.controller_mixture) == pytest.approx([0.5, 0.5])


@pytest.mark.parametrize(("name", "game"), deterministic_family(), ids=lambda value: value if isinstance(value, str) else None)
def test_exhaustive_256_game_deterministic_family(name, game):
    del name
    _agrees(game)


@pytest.mark.parametrize(("name", "game"), probabilistic_family(), ids=lambda value: value if isinstance(value, str) else None)
def test_exhaustive_81_game_probabilistic_family(name, game):
    del name
    _agrees(game)


def test_multi_round_stochastic_tree_and_value():
    game = multi_round_stochastic()
    tree = build_reachable_tree(game)
    _agrees(game)
    assert len(tree.layers) == 2
    assert any(len(view.previous_actions) == 1 for view in tree.controller_information_sets)
    assert any(len(view.previous_controller_actions) == 1 for view in tree.adversary_information_sets)
    assert any(len(view.previous_adversary_actions) == 1 for view in tree.adversary_information_sets)
    # Both hidden second-round states share each controller information set.
    second_round = tree.layers[1]
    assert len({position.controller_view for position in second_round}) < len(second_round)


def test_validator_remains_operational_when_primary_internals_raise(monkeypatch):
    import enforceability.oracle as oracle

    def forbidden(*_args, **_kwargs):
        raise AssertionError("primary oracle must not be called")

    for name in (
        "profile_failure", "solve_matrix", "enumerate_controller_policies",
        "enumerate_adversary_policies", "solve",
    ):
        monkeypatch.setattr(oracle, name, forbidden)
    assert validate_game(matching_pennies()).value == pytest.approx(0.5, abs=DEFAULT_TOLERANCE)


def test_production_validator_has_no_oracle_import():
    path = Path(__file__).parents[2] / "src/enforceability/independent_validation.py"
    tree = ast.parse(path.read_text())
    imported = {
        alias.name
        for node in ast.walk(tree)
        if isinstance(node, ast.Import)
        for alias in node.names
    }
    imported.update(
        node.module or "" for node in ast.walk(tree) if isinstance(node, ast.ImportFrom)
    )
    assert all(not name.startswith("enforceability.oracle") for name in imported)


def test_explicit_complexity_limits_fail_clearly():
    with pytest.raises(ValidationLimitError, match="information sets"):
        validate_game(matching_pennies(), limits=ValidationLimits(max_information_sets=1))
    with pytest.raises(ValidationLimitError, match="controller policies"):
        validate_game(matching_pennies(), limits=ValidationLimits(max_controller_policies=1))
    with pytest.raises(ValidationLimitError, match="adversary policies"):
        validate_game(matching_pennies(), limits=ValidationLimits(max_adversary_policies=1))
    with pytest.raises(ValidationLimitError, match="payoff cells"):
        validate_game(matching_pennies(), limits=ValidationLimits(max_matrix_cells=3))


@pytest.mark.parametrize("tolerance", (0.0, -1e-9, float("nan"), float("inf"), float("-inf")))
def test_invalid_tolerances_are_rejected(tolerance):
    with pytest.raises(ValueError, match="tolerance must be positive and finite"):
        validate_game(matching_pennies(), tolerance=tolerance)


def test_finite_positive_tolerance_is_accepted():
    result = validate_game(matching_pennies(), tolerance=1e-8)
    assert result.tolerance == 1e-8


def test_reproducible_full_report():
    report = run_cross_validation()
    assert report.result == "PASS"
    assert report.total_cases == 348
    assert report.hand_fixture_cases == 10
    assert report.deterministic_exhaustive_cases == 256
    assert report.probabilistic_exhaustive_cases == 81
    assert report.multi_round_cases == 1
    assert report.value_mismatches == 0
    assert report.status_disagreements == 0
