"""Bounded, independent numerical validation of small reach--avoid games.

This module deliberately does not import :mod:`enforceability.oracle`.  It
builds its own reachable tree, enumerates policies locally, propagates exact
trajectory mass forward, and delegates only the final matrix game to HiGHS.
"""
from __future__ import annotations

from dataclasses import dataclass
from fractions import Fraction
from itertools import product
import math

from enforceability.schema import Game

VALIDATOR_VERSION = "explicit-tree-highs.v1"
EXTERNAL_BACKEND = "scipy.optimize.linprog(method='highs')"
DEFAULT_TOLERANCE = 1e-9


class ValidationLimitError(RuntimeError):
    """The requested game exceeds a configured scientific-validation limit."""


class LinearProgramError(RuntimeError):
    """HiGHS failed, or its independently solved bounds disagree."""


@dataclass(frozen=True, slots=True)
class ValidationLimits:
    max_information_sets: int = 32
    max_controller_policies: int = 4096
    max_adversary_policies: int = 4096
    max_matrix_cells: int = 65_536


@dataclass(frozen=True, slots=True)
class ControllerView:
    observations: tuple[str, ...]
    previous_actions: tuple[str, ...]


@dataclass(frozen=True, slots=True)
class AdversaryView:
    states: tuple[str, ...]
    previous_controller_actions: tuple[str, ...]
    previous_adversary_actions: tuple[str, ...]


@dataclass(frozen=True, slots=True)
class TreePosition:
    round_index: int
    state: str
    controller_view: ControllerView
    adversary_view: AdversaryView


@dataclass(frozen=True, slots=True)
class TreeEdge:
    controller_action: str
    adversary_action: str
    next_state: str
    probability: Fraction
    child: TreePosition | None


@dataclass(frozen=True, slots=True)
class ReachableTree:
    initial: tuple[tuple[TreePosition, Fraction], ...]
    layers: tuple[tuple[TreePosition, ...], ...]
    edges: dict[TreePosition, tuple[TreeEdge, ...]]
    controller_information_sets: tuple[ControllerView, ...]
    adversary_information_sets: tuple[AdversaryView, ...]


@dataclass(frozen=True, slots=True)
class IndependentResult:
    primal_value: float
    dual_value: float
    primal_dual_gap: float
    controller_mixture: tuple[float, ...]
    adversary_mixture: tuple[float, ...]
    controller_policy_count: int
    adversary_policy_count: int
    payoff_matrix: tuple[tuple[Fraction, ...], ...]
    tolerance: float

    @property
    def value(self) -> float:
        return (self.primal_value + self.dual_value) / 2.0

    def classification(self, epsilon: Fraction) -> str:
        """Return WINNING/LOSING, or UNRESOLVED near the numeric boundary."""
        threshold = float(epsilon)
        lower = self.dual_value - self.tolerance
        upper = self.primal_value + self.tolerance
        if upper <= threshold:
            return "WINNING"
        if lower > threshold:
            return "LOSING"
        return "UNRESOLVED"


def _terminal(game: Game, state: str) -> bool:
    return state in game.failure_states or state in game.recovery_states


def build_reachable_tree(game: Game, limits: ValidationLimits = ValidationLimits()) -> ReachableTree:
    """Traverse every positive-probability path under every available action."""
    initial = []
    for state in game.initial_states:
        cv = ControllerView((game.observation_map[state],), ())
        av = AdversaryView((state,), (), ())
        initial.append((TreePosition(0, state, cv, av), game.initial_distribution[state]))

    current = {position for position, _ in initial if not _terminal(game, position.state) and game.horizon}
    layers: list[tuple[TreePosition, ...]] = []
    edges: dict[TreePosition, tuple[TreeEdge, ...]] = {}
    controller_sets: set[ControllerView] = set()
    adversary_sets: set[AdversaryView] = set()

    for round_index in range(game.horizon):
        layer = tuple(sorted(current, key=repr))
        layers.append(layer)
        following: set[TreePosition] = set()
        for position in layer:
            controller_sets.add(position.controller_view)
            adversary_sets.add(position.adversary_view)
            information_set_count = len(controller_sets) + len(adversary_sets)
            if information_set_count > limits.max_information_sets:
                raise ValidationLimitError(
                    f"reachable information sets {information_set_count} exceed limit {limits.max_information_sets}"
                )
            node_edges = []
            for controller_action in game.available_actions(round_index):
                for adversary_action in game.adversary_actions:
                    for next_state, probability in game.transitions[(position.state, controller_action, adversary_action)]:
                        if probability <= 0:
                            continue
                        next_cv = ControllerView(
                            position.controller_view.observations + (game.observation_map[next_state],),
                            position.controller_view.previous_actions + (controller_action,),
                        )
                        next_av = AdversaryView(
                            position.adversary_view.states + (next_state,),
                            position.adversary_view.previous_controller_actions + (controller_action,),
                            position.adversary_view.previous_adversary_actions + (adversary_action,),
                        )
                        child = None
                        if round_index + 1 < game.horizon and not _terminal(game, next_state):
                            child = TreePosition(round_index + 1, next_state, next_cv, next_av)
                            following.add(child)
                        node_edges.append(TreeEdge(controller_action, adversary_action, next_state, probability, child))
            edges[position] = tuple(node_edges)
        current = following

    return ReachableTree(
        tuple(initial), tuple(layers), edges,
        tuple(sorted(controller_sets, key=repr)), tuple(sorted(adversary_sets, key=repr)),
    )


def _policy_count(choice_counts: list[int]) -> int:
    count = 1
    for choices in choice_counts:
        count *= choices
    return count


def _enumerate_policies(information_sets, choices):
    for selected in product(*choices):
        yield dict(zip(information_sets, selected, strict=True))


def _pure_policies(game: Game, tree: ReachableTree, limits: ValidationLimits):
    controller_choices = [game.available_actions(len(view.previous_actions)) for view in tree.controller_information_sets]
    controller_count = _policy_count([len(items) for items in controller_choices])
    adversary_count = len(game.adversary_actions) ** len(tree.adversary_information_sets)
    if controller_count > limits.max_controller_policies:
        raise ValidationLimitError(f"controller policies {controller_count} exceed limit {limits.max_controller_policies}")
    if adversary_count > limits.max_adversary_policies:
        raise ValidationLimitError(f"adversary policies {adversary_count} exceed limit {limits.max_adversary_policies}")
    if controller_count * adversary_count > limits.max_matrix_cells:
        raise ValidationLimitError(
            f"payoff cells {controller_count * adversary_count} exceed limit {limits.max_matrix_cells}"
        )
    controllers = tuple(_enumerate_policies(tree.controller_information_sets, controller_choices))
    adversaries = tuple(
        _enumerate_policies(tree.adversary_information_sets, [game.adversary_actions] * len(tree.adversary_information_sets))
    )
    return controllers, adversaries


def evaluate_profile(game: Game, tree: ReachableTree, controller_policy, adversary_policy) -> Fraction:
    """Evaluate one profile by iterative exact forward mass propagation."""
    failure_mass = Fraction(0)
    frontier: dict[TreePosition, Fraction] = {}
    for position, mass in tree.initial:
        if position.state in game.failure_states:
            failure_mass += mass
        elif position.state not in game.recovery_states and game.horizon:
            frontier[position] = frontier.get(position, Fraction(0)) + mass

    for _round_index in range(game.horizon):
        following: dict[TreePosition, Fraction] = {}
        for position, mass in frontier.items():
            chosen_controller = controller_policy[position.controller_view]
            chosen_adversary = adversary_policy[position.adversary_view]
            for edge in tree.edges[position]:
                if edge.controller_action != chosen_controller or edge.adversary_action != chosen_adversary:
                    continue
                branch_mass = mass * edge.probability
                if edge.next_state in game.failure_states:
                    failure_mass += branch_mass
                elif edge.next_state not in game.recovery_states and edge.child is not None:
                    following[edge.child] = following.get(edge.child, Fraction(0)) + branch_mass
        frontier = following
    return failure_mass


def _solve_both_sides(matrix: tuple[tuple[Fraction, ...], ...], tolerance: float):
    import numpy as np
    from scipy.optimize import linprog

    values = np.asarray([[float(value) for value in row] for row in matrix], dtype=float)
    row_count, column_count = values.shape

    primal_objective = np.r_[np.zeros(row_count), 1.0]
    primal_ub = np.c_[values.T, -np.ones(column_count)]
    primal = linprog(
        primal_objective, A_ub=primal_ub, b_ub=np.zeros(column_count),
        A_eq=np.array([np.r_[np.ones(row_count), 0.0]]), b_eq=np.array([1.0]),
        bounds=[(0.0, None)] * row_count + [(None, None)], method="highs",
    )

    dual_objective = np.r_[np.zeros(column_count), -1.0]
    dual_ub = np.c_[-values, np.ones(row_count)]
    dual = linprog(
        dual_objective, A_ub=dual_ub, b_ub=np.zeros(row_count),
        A_eq=np.array([np.r_[np.ones(column_count), 0.0]]), b_eq=np.array([1.0]),
        bounds=[(0.0, None)] * column_count + [(None, None)], method="highs",
    )
    if not primal.success or not dual.success:
        raise LinearProgramError(f"HiGHS failure: primal={primal.message!r}; dual={dual.message!r}")
    primal_value = float(primal.x[-1])
    dual_value = float(dual.x[-1])
    gap = abs(primal_value - dual_value)
    if gap > tolerance:
        raise LinearProgramError(f"primal-dual gap {gap:.17g} exceeds tolerance {tolerance:.17g}")
    return primal_value, dual_value, gap, tuple(map(float, primal.x[:-1])), tuple(map(float, dual.x[:-1]))


def validate_game(
    game: Game,
    *,
    limits: ValidationLimits = ValidationLimits(),
    tolerance: float = DEFAULT_TOLERANCE,
) -> IndependentResult:
    """Compute a bounded independent validation estimate for ``game``."""
    if not math.isfinite(tolerance) or tolerance <= 0:
        raise ValueError("tolerance must be positive and finite")
    tree = build_reachable_tree(game, limits)
    controllers, adversaries = _pure_policies(game, tree, limits)
    matrix = tuple(
        tuple(evaluate_profile(game, tree, controller, adversary) for adversary in adversaries)
        for controller in controllers
    )
    primal, dual, gap, controller_mix, adversary_mix = _solve_both_sides(matrix, tolerance)
    return IndependentResult(
        primal, dual, gap, controller_mix, adversary_mix, len(controllers), len(adversaries), matrix, tolerance
    )
