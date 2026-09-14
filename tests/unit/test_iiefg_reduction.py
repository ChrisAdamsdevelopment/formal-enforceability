"""Machine-checkable structural and profile checks for the IIEFG reduction."""
from fractions import Fraction
from itertools import product

import pytest

from enforceability.iiefg import (
    AdversaryInformationSet,
    ControllerInformationSet,
    ExpansionLimitError,
    ExpansionLimits,
    NodeType,
    build_iiefg,
    evaluate_pure_profile,
)
from enforceability.independent_validation import build_reachable_tree, evaluate_profile
from enforceability.validation_cases import hand_fixtures, matching_pennies, multi_round_stochastic


def fixture(name):
    return dict(hand_fixtures())[name]


def nodes(tree, kind):
    return tuple(node for node in tree.nodes if node.type is kind)


def all_policies(keys, choices):
    return tuple(dict(zip(keys, selected, strict=True)) for selected in product(*choices))


def test_controller_key_is_only_observation_and_own_action_history():
    tree = build_iiefg(fixture("partial-observation"))
    keys = tree.controller_information_sets
    assert ControllerInformationSet.__slots__ == ("observations", "previous_actions")
    assert len(keys) == 1
    controller_nodes = nodes(tree, NodeType.CONTROLLER)
    assert {node.state for node in controller_nodes} == {"s0", "s1"}
    assert len({node.controller_information_set for node in controller_nodes}) == 1


def test_adversary_knows_state_history_but_not_current_controller_action():
    tree = build_iiefg(fixture("informed-adversary"))
    adversary_nodes = nodes(tree, NodeType.ADVERSARY)
    assert AdversaryInformationSet.__slots__ == (
        "states", "previous_controller_actions", "previous_adversary_actions"
    )
    assert len({node.adversary_information_set for node in adversary_nodes}) == 2
    assert {node.adversary_information_set.states for node in adversary_nodes} == {("s0",), ("s1",)}
    assert "current_controller_action" not in AdversaryInformationSet.__slots__


def test_current_controller_choices_are_merged_for_adversary_matching_pennies():
    tree = build_iiefg(matching_pennies())
    adversary_nodes = nodes(tree, NodeType.ADVERSARY)
    assert {node.current_controller_action for node in adversary_nodes} == {"LEFT", "RIGHT"}
    assert len({node.adversary_information_set for node in adversary_nodes}) == 1


def test_later_adversary_key_preserves_both_players_previous_actions():
    tree = build_iiefg(multi_round_stochastic())
    later = [node.adversary_information_set for node in nodes(tree, NodeType.ADVERSARY) if node.round_index == 1]
    assert later
    assert {key.previous_controller_actions for key in later} == {("c0",), ("c1",)}
    assert {key.previous_adversary_actions for key in later} == {("WAIT",)}


def test_round_specific_availability_is_copied():
    game = multi_round_stochastic()
    raw = game.to_dict()
    raw["action_availability"] = {"c0": [0], "c1": [1]}
    tree = build_iiefg(type(game).from_dict(raw))
    assert {node.available_actions for node in nodes(tree, NodeType.CONTROLLER) if node.round_index == 0} == {("c0",)}
    assert {node.available_actions for node in nodes(tree, NodeType.CONTROLLER) if node.round_index == 1} == {("c1",)}


def test_transition_probabilities_are_exactly_copied():
    tree = build_iiefg(multi_round_stochastic())
    first_transition = next(node for node in nodes(tree, NodeType.TRANSITION_CHANCE) if node.round_index == 0)
    assert tuple(edge.probability for edge in first_transition.edges) == (Fraction(1, 3), Fraction(2, 3))
    assert all(isinstance(edge.probability, Fraction) for edge in first_transition.edges)


@pytest.mark.parametrize(("case", "reason", "payoff"), [
    ("losing-one", "failure", Fraction(1)),
    ("recovery", "recovery", Fraction(0)),
    ("horizon-two", "failure", Fraction(1)),
])
def test_failure_recovery_and_horizon_stopping(case, reason, payoff):
    tree = build_iiefg(fixture(case))
    terminals = nodes(tree, NodeType.TERMINAL)
    assert any(node.terminal_reason == reason and node.terminal_payoff == payoff for node in terminals)
    assert all(not node.edges for node in terminals)


def test_horizon_without_failure_has_zero_payoff():
    tree = build_iiefg(fixture("winning-zero"))
    terminal = nodes(tree, NodeType.TERMINAL)[0]
    assert terminal.terminal_reason == "horizon"
    assert terminal.terminal_payoff == 0


def test_initial_terminal_and_zero_horizon_create_no_decisions():
    for case in ("horizon-zero",):
        tree = build_iiefg(fixture(case))
        assert not nodes(tree, NodeType.CONTROLLER)
        assert not nodes(tree, NodeType.ADVERSARY)
        assert nodes(tree, NodeType.TERMINAL)[0].terminal_reason == "horizon"


def test_translation_is_deterministic_and_explicitly_bounded():
    game = multi_round_stochastic()
    assert build_iiefg(game) == build_iiefg(game)
    with pytest.raises(ExpansionLimitError):
        build_iiefg(game, ExpansionLimits(max_nodes=2))


@pytest.mark.parametrize("game", [
    fixture("partial-observation"),
    fixture("informed-adversary"),
    fixture("recovery"),
    fixture("horizon-two"),
    matching_pennies(),
    multi_round_stochastic(),
])
def test_all_bounded_pure_profiles_have_exactly_equal_failure_probability(game):
    """Regression check only; the mathematical proof is in the formal document."""
    translated = build_iiefg(game)
    repository = build_reachable_tree(game)
    controller_keys = translated.controller_information_sets
    adversary_keys = translated.adversary_information_sets
    controllers = all_policies(controller_keys, [game.available_actions(len(key.previous_actions)) for key in controller_keys])
    adversaries = all_policies(adversary_keys, [game.adversary_actions] * len(adversary_keys))

    for controller, adversary in product(controllers, adversaries):
        repository_controller = {
            view: controller[ControllerInformationSet(view.observations, view.previous_actions)]
            for view in repository.controller_information_sets
        }
        repository_adversary = {
            view: adversary[AdversaryInformationSet(
                view.states, view.previous_controller_actions, view.previous_adversary_actions
            )]
            for view in repository.adversary_information_sets
        }
        actual = evaluate_pure_profile(translated, controller, adversary)
        expected = evaluate_profile(game, repository, repository_controller, repository_adversary)
        assert isinstance(actual, Fraction)
        assert actual == expected
