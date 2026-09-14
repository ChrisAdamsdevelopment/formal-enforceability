"""Exact uniform-actionability calculations for finite one-step games.

This module is additive: it does not alter the frozen identifiability oracle.
The implemented LP is specialized to the canonical two-controller-action
family, and is solved exactly by enumerating the breakpoints of its epigraph.
"""
from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from fractions import Fraction
from itertools import product

from enforceability.identifiability import (
    ADVERSARY_ACTIONS,
    STATES,
    OneStepGame,
    PublicSignature,
    ambiguity_interval,
    compatible_games,
    strategic_value,
)


class ActionabilityStatus(str, Enum):
    CERTIFIABLY_LOSING = "CERTIFIABLY_LOSING"
    INSUFFICIENT_INFORMATION = "INSUFFICIENT_INFORMATION"
    CERTIFIABLY_WINNING_BUT_NOT_UNIFORMLY_ACTIONABLE = "CERTIFIABLY_WINNING_BUT_NOT_UNIFORMLY_ACTIONABLE"
    UNIFORMLY_ACTIONABLE_WINNING = "UNIFORMLY_ACTIONABLE_WINNING"


@dataclass(frozen=True, slots=True)
class RobustSolution:
    value: Fraction
    controller_c0_probabilities: tuple[Fraction, ...]


@dataclass(frozen=True, slots=True)
class FiberPoint:
    """One exact state-conditioned table in a continuous public fiber."""

    failure_probabilities: tuple[Fraction, ...]

    def probability(self, state: str, controller: str, adversary: str) -> Fraction:
        from enforceability.identifiability import CELLS

        return self.failure_probabilities[CELLS.index((state, controller, adversary))]


def public_fiber_vertices(signature: PublicSignature) -> tuple[FiberPoint, ...]:
    """Vertices of ``q[c,a]=(p[0,c,a]+p[1,c,a])/2`` over ``[0,1]^8``."""
    from enforceability.identifiability import CELLS, PUBLIC_CELLS

    endpoints = []
    for q in signature.failure_probabilities:
        low, high = max(Fraction(0), 2 * q - 1), min(Fraction(1), 2 * q)
        endpoints.append(tuple(dict.fromkeys((low, high))))
    vertices = []
    for state0_values in product(*endpoints):
        by_cell = dict(zip(PUBLIC_CELLS, state0_values, strict=True))
        values = tuple(
            by_cell[(c, a)] if state == STATES[0] else 2 * signature.failure_probabilities[PUBLIC_CELLS.index((c, a))] - by_cell[(c, a)]
            for state, c, a in CELLS
        )
        vertices.append(FiberPoint(values))
    return tuple(dict.fromkeys(vertices))


def adversary_lines(game: OneStepGame | FiberPoint) -> tuple[tuple[Fraction, Fraction, tuple[str, ...]], ...]:
    """Return ``(intercept, slope, alpha)`` for loss at ``x=P(c0)``."""
    result = []
    for alpha in product(ADVERSARY_ACTIONS, repeat=len(STATES)):
        intercept = sum(game.probability(s, "c1", a) for s, a in zip(STATES, alpha, strict=True)) / len(STATES)
        slope = sum(
            game.probability(s, "c0", a) - game.probability(s, "c1", a)
            for s, a in zip(STATES, alpha, strict=True)
        ) / len(STATES)
        result.append((intercept, slope, alpha))
    return tuple(result)


def fixed_policy_loss(game: OneStepGame | FiberPoint, controller_c0_probability: Fraction) -> Fraction:
    if not 0 <= controller_c0_probability <= 1:
        raise ValueError("controller probability must be in [0,1]")
    return max(b + m * controller_c0_probability for b, m, _ in adversary_lines(game))


def optimal_policies(game: OneStepGame) -> tuple[Fraction, ...]:
    solution = robust_actionability((game,))
    if solution.value != strategic_value(game):
        raise RuntimeError("single-model robust value disagrees with strategic value")
    return solution.controller_c0_probabilities


def robust_actionability(games: tuple[OneStepGame | FiberPoint, ...]) -> RobustSolution:
    """Solve ``min_x z`` s.t. ``z >= b_i + m_i x, 0 <= x <= 1`` exactly."""
    if not games:
        raise ValueError("compatibility set must be nonempty")
    lines = tuple((b, m) for game in games for b, m, _ in adversary_lines(game))
    candidates = {Fraction(0), Fraction(1)}
    for b, m in lines:
        for other_b, other_m in lines:
            if m != other_m:
                x = (other_b - b) / (m - other_m)
                if 0 <= x <= 1:
                    candidates.add(x)
    objective = lambda x: max(b + m * x for b, m in lines)
    value = min(objective(x) for x in candidates)
    return RobustSolution(value, tuple(sorted(x for x in candidates if objective(x) == value)))


def wait_and_see(games: tuple[OneStepGame, ...]) -> Fraction:
    if not games:
        raise ValueError("compatibility set must be nonempty")
    return max(strategic_value(game) for game in games)


def classify(games: tuple[OneStepGame, ...], epsilon: Fraction) -> ActionabilityStatus:
    values = tuple(strategic_value(game) for game in games)
    lower, upper = min(values), max(values)
    if lower > epsilon:
        return ActionabilityStatus.CERTIFIABLY_LOSING
    if upper > epsilon:
        return ActionabilityStatus.INSUFFICIENT_INFORMATION
    if robust_actionability(games).value > epsilon:
        return ActionabilityStatus.CERTIFIABLY_WINNING_BUT_NOT_UNIFORMLY_ACTIONABLE
    return ActionabilityStatus.UNIFORMLY_ACTIONABLE_WINNING


def canonical_class_solution(signature: PublicSignature, probabilistic: bool = False) -> RobustSolution:
    games = compatible_games(signature, probabilistic)
    if not games:
        raise ValueError("signature has no compatible canonical models")
    return robust_actionability(games)


def verify_canonical_families() -> dict[str, int]:
    """Exhaustively check W=upper V<=R for every frozen-family class."""
    from enforceability.identifiability import ambiguity_classes

    counts = {}
    for probabilistic, name in ((False, "deterministic_classes"), (True, "probabilistic_classes")):
        classes = ambiguity_classes(probabilistic)
        for signature, games in classes.items():
            _, upper = ambiguity_interval(signature, probabilistic)
            if wait_and_see(games) != upper:
                raise RuntimeError(f"wait-and-see identity failed for {name}")
            if upper > robust_actionability(games).value:
                raise RuntimeError(f"minimax order inequality failed for {name}")
        counts[name] = len(classes)
    return counts
