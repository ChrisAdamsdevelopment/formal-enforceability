"""Bounded, auditable extensive-form translation of a repository ``Game``.

This module is a structural representation and profile evaluator, not a second
equilibrium solver.  In particular, the controller-first ordering is only a
tree encoding of a simultaneous move: the adversary information key omits the
controller's current action.
"""
from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from fractions import Fraction
from typing import Mapping

from enforceability.schema import Game


class ExpansionLimitError(RuntimeError):
    """The explicit tree would exceed its caller-supplied audit bound."""


class NodeType(str, Enum):
    INITIAL_CHANCE = "initial_chance"
    CONTROLLER = "controller"
    ADVERSARY = "adversary"
    TRANSITION_CHANCE = "transition_chance"
    TERMINAL = "terminal"


@dataclass(frozen=True, slots=True)
class ControllerInformationSet:
    """Exactly the observations and the controller's own previous actions."""

    observations: tuple[str, ...]
    previous_actions: tuple[str, ...]


@dataclass(frozen=True, slots=True)
class AdversaryInformationSet:
    """State/action recall, deliberately excluding the current controller action."""

    states: tuple[str, ...]
    previous_controller_actions: tuple[str, ...]
    previous_adversary_actions: tuple[str, ...]


@dataclass(frozen=True, slots=True)
class Edge:
    target: int
    action: str | None = None
    probability: Fraction | None = None


@dataclass(frozen=True, slots=True)
class Node:
    id: int
    type: NodeType
    round_index: int
    state: str | None
    state_history: tuple[str, ...] = ()
    previous_controller_actions: tuple[str, ...] = ()
    previous_adversary_actions: tuple[str, ...] = ()
    current_controller_action: str | None = None
    current_adversary_action: str | None = None
    available_actions: tuple[str, ...] = ()
    controller_information_set: ControllerInformationSet | None = None
    adversary_information_set: AdversaryInformationSet | None = None
    terminal_payoff: Fraction | None = None
    terminal_reason: str | None = None
    edges: tuple[Edge, ...] = ()


@dataclass(frozen=True, slots=True)
class ExtensiveFormGame:
    """Finite two-player zero-sum IIEFG with controller loss as payoff."""

    nodes: tuple[Node, ...]
    root: int = 0

    def node(self, node_id: int) -> Node:
        return self.nodes[node_id]

    @property
    def controller_information_sets(self) -> tuple[ControllerInformationSet, ...]:
        return tuple(dict.fromkeys(n.controller_information_set for n in self.nodes if n.controller_information_set is not None))

    @property
    def adversary_information_sets(self) -> tuple[AdversaryInformationSet, ...]:
        return tuple(dict.fromkeys(n.adversary_information_set for n in self.nodes if n.adversary_information_set is not None))


@dataclass(frozen=True, slots=True)
class ExpansionLimits:
    max_nodes: int = 100_000


def build_iiefg(game: Game, limits: ExpansionLimits = ExpansionLimits()) -> ExtensiveFormGame:
    """Expand ``game`` deterministically into a bounded explicit IIEFG tree."""
    nodes: list[Node | None] = []

    def reserve() -> int:
        if len(nodes) >= limits.max_nodes:
            raise ExpansionLimitError(f"IIEFG nodes exceed limit {limits.max_nodes}")
        nodes.append(None)
        return len(nodes) - 1

    def put(node_id: int, **kwargs) -> int:
        nodes[node_id] = Node(node_id, **kwargs)
        return node_id

    def terminal(round_index: int, states: tuple[str, ...], cs: tuple[str, ...], adversaries: tuple[str, ...], reason: str) -> int:
        node_id = reserve()
        payoff = Fraction(1) if reason == "failure" else Fraction(0)
        return put(node_id, type=NodeType.TERMINAL, round_index=round_index, state=states[-1], state_history=states,
                   previous_controller_actions=cs, previous_adversary_actions=adversaries,
                   terminal_payoff=payoff, terminal_reason=reason)

    def controller(round_index: int, states: tuple[str, ...], observations: tuple[str, ...],
                   cs: tuple[str, ...], adversaries: tuple[str, ...]) -> int:
        state = states[-1]
        if state in game.failure_states:
            return terminal(round_index, states, cs, adversaries, "failure")
        if state in game.recovery_states:
            return terminal(round_index, states, cs, adversaries, "recovery")
        if round_index >= game.horizon:
            return terminal(round_index, states, cs, adversaries, "horizon")
        node_id = reserve()
        key = ControllerInformationSet(observations, cs)
        actions = game.available_actions(round_index)
        edges = tuple(Edge(adversary_node(round_index, states, observations, cs, adversaries, action), action=action) for action in actions)
        return put(node_id, type=NodeType.CONTROLLER, round_index=round_index, state=state, state_history=states,
                   previous_controller_actions=cs, previous_adversary_actions=adversaries,
                   available_actions=actions, controller_information_set=key, edges=edges)

    def adversary_node(round_index: int, states: tuple[str, ...], observations: tuple[str, ...],
                       cs: tuple[str, ...], adversaries: tuple[str, ...], current_c: str) -> int:
        node_id = reserve()
        key = AdversaryInformationSet(states, cs, adversaries)
        edges = tuple(Edge(chance(round_index, states, observations, cs, adversaries, current_c, action), action=action)
                      for action in game.adversary_actions)
        return put(node_id, type=NodeType.ADVERSARY, round_index=round_index, state=states[-1], state_history=states,
                   previous_controller_actions=cs, previous_adversary_actions=adversaries,
                   current_controller_action=current_c, available_actions=game.adversary_actions,
                   adversary_information_set=key, edges=edges)

    def chance(round_index: int, states: tuple[str, ...], observations: tuple[str, ...], cs: tuple[str, ...],
               adversaries: tuple[str, ...], current_c: str, current_a: str) -> int:
        node_id = reserve()
        edges = []
        for next_state, probability in game.transitions[(states[-1], current_c, current_a)]:
            next_states = states + (next_state,)
            target = controller(round_index + 1, next_states, observations + (game.observation_map[next_state],),
                                cs + (current_c,), adversaries + (current_a,))
            edges.append(Edge(target, probability=probability))
        return put(node_id, type=NodeType.TRANSITION_CHANCE, round_index=round_index, state=states[-1], state_history=states,
                   previous_controller_actions=cs, previous_adversary_actions=adversaries,
                   current_controller_action=current_c, current_adversary_action=current_a, edges=tuple(edges))

    root = reserve()
    initial_edges = []
    for state in game.states:
        probability = game.initial_distribution.get(state, Fraction(0))
        if probability > 0:
            target = controller(0, (state,), (game.observation_map[state],), (), ())
            initial_edges.append(Edge(target, probability=probability))
    put(root, type=NodeType.INITIAL_CHANCE, round_index=0, state=None, edges=tuple(initial_edges))
    assert all(node is not None for node in nodes)
    return ExtensiveFormGame(tuple(node for node in nodes if node is not None), root)


def evaluate_pure_profile(
    tree: ExtensiveFormGame,
    controller_policy: Mapping[ControllerInformationSet, str],
    adversary_policy: Mapping[AdversaryInformationSet, str],
) -> Fraction:
    """Return exact terminal failure mass for one total pure strategy profile."""
    def visit(node_id: int) -> Fraction:
        node = tree.node(node_id)
        if node.type is NodeType.TERMINAL:
            assert node.terminal_payoff is not None
            return node.terminal_payoff
        if node.type is NodeType.CONTROLLER:
            action = controller_policy[node.controller_information_set]
            return visit(next(edge.target for edge in node.edges if edge.action == action))
        if node.type is NodeType.ADVERSARY:
            action = adversary_policy[node.adversary_information_set]
            return visit(next(edge.target for edge in node.edges if edge.action == action))
        return sum((edge.probability * visit(edge.target) for edge in node.edges), Fraction(0))

    return visit(tree.root)
