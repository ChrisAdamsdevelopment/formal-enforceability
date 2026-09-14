"""Deterministic bounded case generators for independent cross-validation."""
from __future__ import annotations

from fractions import Fraction
from itertools import product

from enforceability.schema import SCHEMA_VERSION, Game


def _game(
    *, states, initial, controller_actions, adversary_actions=("WAIT",), observations,
    transitions, failure=("FAIL",), recovery=(), horizon=1, epsilon="1/4", availability=None,
) -> Game:
    rows = []
    for state, controller, adversary in product(states, controller_actions, adversary_actions):
        outcome = transitions.get((state, controller, adversary), state)
        distribution = {outcome: Fraction(1)} if isinstance(outcome, str) else outcome
        rows.append({
            "state": state, "controller_action": controller, "adversary_action": adversary,
            "outcomes": [{"state": target, "probability": str(probability)} for target, probability in distribution.items()],
        })
    initial_mass = Fraction(1, len(initial))
    return Game.from_dict({
        "schema_version": SCHEMA_VERSION,
        "states": list(states),
        "initial_distribution": [{"state": state, "probability": str(initial_mass)} for state in initial],
        "controller_actions": list(controller_actions),
        "adversary_actions": list(adversary_actions),
        "observations": sorted(set(observations.values())),
        "observation_map": observations,
        "transitions": rows,
        "failure_states": list(failure),
        "recovery_states": list(recovery),
        "horizon": horizon,
        "epsilon": epsilon,
        "action_availability": availability or {action: list(range(horizon)) for action in controller_actions},
    })


def matching_pennies() -> Game:
    states = ("start", "SAFE", "FAIL")
    transitions = {
        ("start", "LEFT", "LEFT"): "FAIL", ("start", "LEFT", "RIGHT"): "SAFE",
        ("start", "RIGHT", "LEFT"): "SAFE", ("start", "RIGHT", "RIGHT"): "FAIL",
    }
    return _game(
        states=states, initial=("start",), controller_actions=("LEFT", "RIGHT"),
        adversary_actions=("LEFT", "RIGHT"), observations={state: state for state in states},
        transitions=transitions, epsilon="1/2",
    )


def one_third() -> Game:
    states = ("start", "SAFE", "FAIL")
    return _game(
        states=states, initial=("start",), controller_actions=("ACT",),
        observations={state: state for state in states},
        transitions={("start", "ACT", "WAIT"): {"SAFE": Fraction(2, 3), "FAIL": Fraction(1, 3)}},
        epsilon="1/3",
    )


def hand_fixtures() -> tuple[tuple[str, Game], ...]:
    terminal_states = ("start", "SAFE", "FAIL")
    observations = {state: state for state in terminal_states}
    winning = _game(
        states=terminal_states, initial=("start",), controller_actions=("ACT",), observations=observations,
        transitions={("start", "ACT", "WAIT"): "SAFE"}, epsilon="0",
    )
    losing = _game(
        states=terminal_states, initial=("start",), controller_actions=("ACT",), observations=observations,
        transitions={("start", "ACT", "WAIT"): "FAIL"}, epsilon="0",
    )
    zero_horizon = _game(
        states=terminal_states, initial=("start",), controller_actions=("ACT",), observations=observations,
        transitions={}, horizon=0, epsilon="0",
    )
    recovery_states = ("start", "RECOVERED", "FAIL")
    recovery = _game(
        states=recovery_states, initial=("start",), controller_actions=("ACT",),
        observations={state: state for state in recovery_states},
        transitions={("start", "ACT", "WAIT"): "RECOVERED"}, recovery=("RECOVERED",), horizon=2, epsilon="0",
    )
    hidden_states = ("s0", "s1", "SAFE", "FAIL")
    conflict = {
        ("s0", "LEFT", "WAIT"): "SAFE", ("s0", "RIGHT", "WAIT"): "FAIL",
        ("s1", "LEFT", "WAIT"): "FAIL", ("s1", "RIGHT", "WAIT"): "SAFE",
    }
    partial = _game(
        states=hidden_states, initial=("s0", "s1"), controller_actions=("LEFT", "RIGHT"),
        observations={"s0": "hidden", "s1": "hidden", "SAFE": "safe", "FAIL": "fail"},
        transitions=conflict, epsilon="2/3",
    )
    refined = _game(
        states=hidden_states, initial=("s0", "s1"), controller_actions=("LEFT", "RIGHT"),
        observations={"s0": "zero", "s1": "one", "SAFE": "safe", "FAIL": "fail"},
        transitions=conflict, epsilon="0",
    )
    horizon_states = ("start", "danger", "FAIL")
    horizon_two = _game(
        states=horizon_states, initial=("start",), controller_actions=("WAIT",),
        observations={state: state for state in horizon_states},
        transitions={("start", "WAIT", "WAIT"): "danger", ("danger", "WAIT", "WAIT"): "FAIL"},
        horizon=2, epsilon="1/2",
    )
    informed_states = ("s0", "s1", "SAFE", "FAIL")
    informed_transitions = {
        (state, "ACT", action): ("FAIL" if (state[-1] == action[-1]) else "SAFE")
        for state in ("s0", "s1") for action in ("a0", "a1")
    }
    informed = _game(
        states=informed_states, initial=("s0", "s1"), controller_actions=("ACT",),
        adversary_actions=("a0", "a1"),
        observations={"s0": "hidden", "s1": "hidden", "SAFE": "safe", "FAIL": "fail"},
        transitions=informed_transitions, epsilon="3/4",
    )
    return (
        ("winning-zero", winning), ("losing-one", losing), ("horizon-zero", zero_horizon),
        ("recovery", recovery), ("partial-observation", partial), ("refined-observation", refined),
        ("horizon-two", horizon_two), ("informed-adversary", informed),
        ("one-third", one_third()), ("simultaneous-matching-pennies", matching_pennies()),
    )


def deterministic_family() -> tuple[tuple[str, Game], ...]:
    games = []
    states = ("s0", "s1", "SAFE", "FAIL")
    cells = tuple(product(("s0", "s1"), ("c0", "c1"), ("a0", "a1")))
    for mask in range(256):
        transitions = {cell: ("FAIL" if mask & (1 << index) else "SAFE") for index, cell in enumerate(cells)}
        games.append((f"deterministic-{mask:03d}", _game(
            states=states, initial=("s0", "s1"), controller_actions=("c0", "c1"),
            adversary_actions=("a0", "a1"),
            observations={"s0": "hidden", "s1": "hidden", "SAFE": "safe", "FAIL": "fail"},
            transitions=transitions, epsilon="1/3",
        )))
    return tuple(games)


def probabilistic_family() -> tuple[tuple[str, Game], ...]:
    games = []
    states = ("s0", "s1", "SAFE", "FAIL")
    cells = tuple(product(("s0", "s1"), ("a0", "a1")))
    for index, probabilities in enumerate(product((Fraction(0), Fraction(1, 2), Fraction(1)), repeat=4)):
        transitions = {
            (state, "ACT", adversary): {"SAFE": 1 - probability, "FAIL": probability}
            for (state, adversary), probability in zip(cells, probabilities, strict=True)
        }
        games.append((f"probabilistic-{index:02d}", _game(
            states=states, initial=("s0", "s1"), controller_actions=("ACT",),
            adversary_actions=("a0", "a1"),
            observations={"s0": "hidden", "s1": "hidden", "SAFE": "safe", "FAIL": "fail"},
            transitions=transitions, epsilon="1/3",
        )))
    return tuple(games)


def multi_round_stochastic() -> Game:
    states = ("start", "x", "y", "SAFE", "FAIL")
    controller_actions = ("c0", "c1")
    adversary_actions = ("WAIT",)
    transitions = {}
    for controller, adversary in product(controller_actions, adversary_actions):
        transitions[("start", controller, adversary)] = {"x": Fraction(1, 3), "y": Fraction(2, 3)}
    for state, controller, adversary in product(("x", "y"), controller_actions, adversary_actions):
        transitions[(state, controller, adversary)] = "FAIL" if (state == "x") == (controller == "c0") else "SAFE"
    return _game(
        states=states, initial=("start",), controller_actions=controller_actions, adversary_actions=adversary_actions,
        observations={"start": "repeat", "x": "repeat", "y": "repeat", "SAFE": "safe", "FAIL": "fail"},
        transitions=transitions, horizon=2, epsilon="3/4",
    )
