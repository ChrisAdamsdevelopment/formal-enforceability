from fractions import Fraction

from enforceability.actionability import (
    ActionabilityStatus,
    classify,
    fixed_policy_loss,
    optimal_policies,
    robust_actionability,
    verify_canonical_families,
    wait_and_see,
)
from enforceability.identifiability import ambiguity_classes, ambiguity_interval, enumerate_games, strategic_value


GAMES = {game.game_id: game for game in enumerate_games()}


def test_wait_and_see_is_upper_and_never_exceeds_here_and_now_all_families():
    assert verify_canonical_families() == {"deterministic_classes": 81, "probabilistic_classes": 625}


def test_fixed_policy_vertex_evaluation_matches_exhaustive_models():
    games = (GAMES["d006"], GAMES["d036"])
    for x in map(Fraction, ("0", "1/3", "1")):
        assert max(fixed_policy_loss(game, x) for game in games) == max(
            b + m * x
            for game in games
            for b, m, _ in __import__("enforceability.actionability", fromlist=["adversary_lines"]).adversary_lines(game)
        )


def test_exact_lp_matches_rational_brute_grid_on_small_cases():
    games = (GAMES["d051"], GAMES["d204"])
    solution = robust_actionability(games)
    brute = min(max(fixed_policy_loss(g, Fraction(k, 100)) for g in games) for k in range(101))
    assert solution.value == brute == Fraction(1, 2)
    assert solution.controller_c0_probabilities == (Fraction(1, 2),)


def test_generic_exact_actionability_gap_and_world_policies():
    games = (GAMES["d051"], GAMES["d204"])
    assert [strategic_value(g) for g in games] == [0, 0]
    assert [optimal_policies(g) for g in games] == [(Fraction(1),), (Fraction(0),)]
    assert wait_and_see(games) == 0 < robust_actionability(games).value
    assert classify(games, Fraction(0)) == ActionabilityStatus.CERTIFIABLY_WINNING_BUT_NOT_UNIFORMLY_ACTIONABLE


def test_hierarchical_examples_cover_uniform_ambiguous_and_losing():
    statuses = set()
    for signature, games in ambiguity_classes().items():
        lower, upper = ambiguity_interval(signature)
        statuses.add(classify(games, upper))
        if lower < upper:
            statuses.add(classify(games, lower))
        if lower > 0:
            statuses.add(classify(games, Fraction(0)))
    assert ActionabilityStatus.UNIFORMLY_ACTIONABLE_WINNING in statuses
    assert ActionabilityStatus.INSUFFICIENT_INFORMATION in statuses
    assert ActionabilityStatus.CERTIFIABLY_LOSING in statuses


def test_controller_label_permutation_preserves_values():
    for game in (GAMES["d051"], GAMES["d204"]):
        values = game.failure_probabilities
        swapped = type(game)(game.game_id + "s", values[2:4] + values[0:2] + values[6:8] + values[4:6])
        assert strategic_value(swapped) == strategic_value(game)
