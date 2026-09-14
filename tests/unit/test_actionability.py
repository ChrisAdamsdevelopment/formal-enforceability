from fractions import Fraction

from enforceability.actionability import (
    ActionabilityStatus,
    classify,
    FiberPoint, fixed_policy_loss, public_fiber_vertices,
    optimal_policies,
    robust_actionability,
    verify_canonical_families,
    wait_and_see,
)
from enforceability.identifiability import ambiguity_classes, ambiguity_interval, enumerate_games, strategic_value


GAMES = {game.game_id: game for game in enumerate_games()}


def test_wait_and_see_is_upper_and_never_exceeds_here_and_now_all_families():
    assert verify_canonical_families() == {"deterministic_classes": 81, "probabilistic_classes": 625}


def test_continuous_public_fiber_vertices_and_fixed_policy_bound():
    from enforceability.identifiability import PublicSignature, public_signature

    signature = PublicSignature((Fraction(1, 4), Fraction(1, 2), Fraction(3, 4), Fraction(0)))
    vertices = public_fiber_vertices(signature)
    assert len(vertices) == 8  # three nondegenerate cell segments
    for point in vertices:
        assert all(0 <= value <= 1 for value in point.failure_probabilities)
        assert public_signature(type(GAMES["d000"])("vertex", point.failure_probabilities)) == signature
    interior = FiberPoint(tuple((sum(v.failure_probabilities[i] for v in vertices) / len(vertices)) for i in range(8)))
    for x in (Fraction(0), Fraction(1, 3), Fraction(1)):
        assert fixed_policy_loss(interior, x) <= max(fixed_policy_loss(vertex, x) for vertex in vertices)
    solution = robust_actionability(vertices)
    brute_grid = min(max(fixed_policy_loss(vertex, Fraction(k, 100)) for vertex in vertices) for k in range(101))
    assert solution.value <= brute_grid
    assert solution.value == max(fixed_policy_loss(vertex, Fraction(1, 3)) for vertex in vertices)


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
