"""Deterministic formal fixtures used by the Stage-4 evidence freeze."""
from __future__ import annotations

from dataclasses import asdict
from fractions import Fraction
import hashlib
from typing import Any

from enforceability import Restoration, optimal_restoration, solve
from enforceability.generation import (GeneratedGame, GeneratorConfig, add_controller_action,
                                       canonical_json, game_id, generate, transform)
from enforceability.generation.core import rational_json
from enforceability.schema import Game, SCHEMA_VERSION
from enforceability.stage4 import intervention_value


def _game(*, states, initial, actions, adversaries, observations, transitions,
          horizon=1, epsilon="0", availability=None, extra_observations=(), rewards=None):
    rows = []
    for state in states:
        for action in actions:
            for adversary in adversaries:
                outcome = transitions.get((state, action, adversary), state)
                distribution = {outcome: Fraction(1)} if isinstance(outcome, str) else outcome
                rows.append({"state": state, "controller_action": action, "adversary_action": adversary,
                             "outcomes": [{"state": target, "probability": rational_json(probability)} for target, probability in distribution.items()]})
    mass = Fraction(1, len(initial))
    raw = {"schema_version": SCHEMA_VERSION, "states": list(states),
           "initial_distribution": [{"state": x, "probability": rational_json(mass)} for x in initial],
           "controller_actions": list(actions), "adversary_actions": list(adversaries),
           "observations": sorted(set(observations.values()) | set(extra_observations)), "observation_map": observations,
           "transitions": rows, "failure_states": ["x"], "recovery_states": ["r"], "horizon": horizon,
           "epsilon": epsilon, "action_availability": availability or {x: list(range(horizon)) for x in actions},
           "legitimate_rewards": [{"state": s, "controller_action": a, "reward": rational_json(v)} for (s, a), v in (rewards or {}).items()],
           "display_labels": {}}
    return Game.from_dict(raw)


def _conflict(common=False):
    states = ("q0", "q1", "r", "x"); actions = ("c0", "c1") + (("common",) if common else ())
    transitions = {}
    for i in range(2):
        for action in actions:
            transitions[f"q{i}", action, "a0"] = "r" if action in (f"c{i}", "common") else "x"
    return _game(states=states, initial=states[:2], actions=actions, adversaries=("a0",),
                 observations={"q0": "o", "q1": "o", "r": "r", "x": "x"}, transitions=transitions,
                 extra_observations=("u0", "u1"))


def _restriction(relevant=True):
    transitions = {("q", "c", "a0"): "r", ("q", "c", "a1"): "x" if relevant else "r"}
    return _game(states=("q", "r", "x"), initial=("q",), actions=("c",), adversaries=("a0", "a1"),
                 observations={x: x for x in ("q", "r", "x")}, transitions=transitions)


def _pair(category, parent, child, record, chain=()):
    parent_oracle, child_oracle = solve(parent).to_dict(), solve(child).to_dict()
    value = intervention_value(parent_oracle, child_oracle)
    identity = {"category": category, "parent_game_id": game_id(parent), "child_game_id": game_id(child),
                "transformation_type": record.transformation_type, "changed_formal_fields": list(record.changed_formal_fields),
                "transformation_chain": list(chain)}
    return {"pair_id": hashlib.sha256(canonical_json(identity).encode()).hexdigest(), **identity,
            "transformation_record": asdict(record), "parent_game": parent.to_dict(), "child_game": child.to_dict(),
            "parent_oracle": parent_oracle, "child_oracle": child_oracle,
            "exact_improvement": value["improvement"], "threshold_crossing": value["threshold_crossing"]}


def build_pair_registry() -> dict[str, Any]:
    pairs = []
    parent = _conflict(); child, record = transform(parent, Restoration("refine", observation_overrides=(("q0", "u0"), ("q1", "u1"))), 400)
    pairs.append(_pair("positive-value-observation", parent, child, record))
    parent = _conflict(True); child, record = transform(parent, Restoration("refine", observation_overrides=(("q0", "u0"), ("q1", "u1"))), 401)
    pairs.append(_pair("zero-value-observation", parent, child, record))
    for relevant, category, seed in ((True, "positive-value-restriction", 402), (False, "zero-value-restriction", 403)):
        parent = _restriction(relevant); child, record = transform(parent, Restoration("remove", remove_adversary_actions=frozenset({"a1"})), seed)
        pairs.append(_pair(category, parent, child, record))
    states = ("q", "r", "x"); transitions = {("q", "wait", "a0"): "x", ("q", "act", "a0"): "r"}
    parent = _game(states=states, initial=("q",), actions=("wait", "act"), adversaries=("a0",), observations={x: x for x in states},
                   transitions=transitions, horizon=2, availability={"wait": [0, 1], "act": [1]})
    child, record = transform(parent, Restoration("earlier", availability_overrides=(("act", (0, 1)),)), 404)
    pairs.append(_pair("timing-rescue", parent, child, record))
    parent = _conflict()
    outcomes = {(s, "a0"): (("r" if s.startswith("q") else s, Fraction(1)),) for s in parent.states}
    child, record = add_controller_action(parent, "common", outcomes, (0,), 405)
    pairs.append(_pair("common-safe-action-addition", parent, child, record))
    transitions = {("q", "wait", "a0"): "d", ("d", "wait", "a0"): "x"}
    parent = _game(states=("q", "d", "r", "x"), initial=("q",), actions=("wait",), adversaries=("a0",),
                   observations={x: x for x in ("q", "d", "r", "x")}, transitions=transitions, horizon=1)
    raw = parent.to_dict(); raw["horizon"] = 2; raw["action_availability"]["wait"] = [0, 1]; child = Game.from_dict(raw)
    from enforceability.generation import TransformationRecord
    record = TransformationRecord(game_id(parent), game_id(child), "horizon-change", ("horizon", "action_availability"), "stage2.v2", 406)
    pairs.append(_pair("horizon-only", parent, child, record))
    # Two independent defects: aliased hidden state and an adversarial veto.
    parent = _game(states=("q0", "q1", "r", "x"), initial=("q0", "q1"), actions=("c0", "c1"), adversaries=("a0", "a1"),
        observations={"q0": "o", "q1": "o", "r": "r", "x": "x"}, extra_observations=("u0", "u1"),
        transitions={(f"q{i}", f"c{j}", a): ("r" if a == "a0" and i == j else "x") for i in range(2) for j in range(2) for a in ("a0", "a1")})
    info_rest = Restoration("information", observation_overrides=(("q0", "u0"), ("q1", "u1")))
    restriction_rest = Restoration("restriction", remove_adversary_actions=frozenset({"a1"}))
    info, _ = transform(parent, info_rest, 407); restriction, _ = transform(parent, restriction_rest, 408)
    combined_rest = Restoration("combined", observation_overrides=info_rest.observation_overrides, remove_adversary_actions=restriction_rest.remove_adversary_actions)
    combined, record = transform(parent, combined_rest, 409)
    pair = _pair("compound-repair", parent, combined, record, ("observation-refinement", "adversary-capability-removal"))
    pair["component_children"] = [{"component": "observation-refinement", "game": info.to_dict(), "game_id": game_id(info), "oracle": solve(info).to_dict()},
                                  {"component": "adversary-capability-removal", "game": restriction.to_dict(), "game_id": game_id(restriction), "oracle": solve(restriction).to_dict()}]
    pairs.append(pair)
    payload = {"version": "stage4.pair-registry.v1", "pairs": pairs}
    return {**payload, "fingerprint": hashlib.sha256(canonical_json(payload).encode()).hexdigest()}


def build_probability_fixtures():
    fixtures = []
    for name, probability, epsilon in (("zero", Fraction(0), "1/3"), ("third-below", Fraction(1, 3), "1/2"),
                                       ("third-boundary", Fraction(1, 3), "1/3"), ("third-above", Fraction(1, 3), "1/4"),
                                       ("half-boundary", Fraction(1, 2), "1/2"), ("half-above-third", Fraction(1, 2), "1/3"),
                                       ("quarter", Fraction(1, 4), "1/3"), ("one", Fraction(1), "1/2")):
        game = _game(states=("q", "r", "x"), initial=("q",), actions=("c",), adversaries=("a",),
                     observations={x: x for x in ("q", "r", "x")}, transitions={("q", "c", "a"): {"x": probability, "r": 1 - probability}}, epsilon=epsilon)
        fixtures.append({"fixture_id": name, "game_id": game_id(game), "game": game.to_dict(), "oracle": solve(game).to_dict(), "construction": "transition-distribution"})
    # Deterministic matching-pennies matrix; the 1/2 is produced by minimax mixing.
    transitions = {("q", c, a): ("x" if c[-1] == a[-1] else "r") for c in ("c0", "c1") for a in ("a0", "a1")}
    game = _game(states=("q", "r", "x"), initial=("q",), actions=("c0", "c1"), adversaries=("a0", "a1"),
                 observations={x: x for x in ("q", "r", "x")}, transitions=transitions, epsilon="1/2")
    fixtures.append({"fixture_id": "minimax-half", "game_id": game_id(game), "game": game.to_dict(), "oracle": solve(game).to_dict(), "construction": "adversarial-minimax"})
    return fixtures


def build_restoration_fixtures():
    records = []
    def restoration_dict(restoration):
        return {"name": restoration.name, "remove_adversary_actions": sorted(restoration.remove_adversary_actions),
                "remove_controller_actions": sorted(restoration.remove_controller_actions),
                "observation_overrides": [list(x) for x in restoration.observation_overrides],
                "availability_overrides": [[a, list(rounds)] for a, rounds in restoration.availability_overrides]}
    for mode in ("base", "tie", "none"):
        generated = generate(GeneratorConfig("mixed-restoration" if mode != "none" else "capability-restriction", 500,
                                             mode=mode, adversary_action_count=2))
        assert isinstance(generated, GeneratedGame)
        result = optimal_restoration(generated.game, generated.restorations)
        evaluations = [{"candidate_id": e.restoration.name, "oracle": e.game_result.to_dict(),
                        "cost": rational_json(e.cost)} for e in result.evaluations]
        safe = [e for e in evaluations if e["oracle"]["threshold_satisfied"]]
        costs = [Fraction(e["cost"]) for e in safe]
        categories = []
        if not safe: categories.append("no-feasible")
        if costs and costs.count(min(costs)) == 1: categories.append("unique-optimum")
        if costs and costs.count(min(costs)) > 1: categories.append("tied-optima")
        if costs and any(x > min(costs) for x in costs): categories.append("dominated-safe")
        records.append({"case_id": mode, "game_id": game_id(generated.game), "game": generated.game.to_dict(),
                        "categories": categories, "restorations": [restoration_dict(x) for x in generated.restorations], "evaluations": evaluations})
    # Two safe availability restorations with unequal endogenous utility cost.
    game = _game(states=("q0", "q1", "r", "x"), initial=("q0", "q1"), actions=("c0", "c1", "c2", "c3"), adversaries=("a0",),
        observations={"q0": "o", "q1": "o", "r": "r", "x": "x"},
        transitions={(f"q{i}", action, "a0"): ("r" if action in (f"c{i}", "c2", "c3") else "x") for i in range(2) for action in ("c0", "c1", "c2", "c3")},
        availability={"c0": [0], "c1": [0], "c2": [], "c3": []},
        rewards={(f"q{i}", f"c{i}"): Fraction(10) for i in range(2)} | {(f"q{i}", "c2"): Fraction(7) for i in range(2)} | {(f"q{i}", "c3"): Fraction(5) for i in range(2)})
    candidates = (Restoration("enable-c2", availability_overrides=(("c2", (0,)),)), Restoration("enable-c3", availability_overrides=(("c3", (0,)),)))
    result = optimal_restoration(game, candidates)
    evaluations = [{"candidate_id": e.restoration.name, "oracle": e.game_result.to_dict(), "cost": rational_json(e.cost)} for e in result.evaluations]
    records.append({"case_id": "dominated", "game_id": game_id(game), "game": game.to_dict(), "categories": ["unique-optimum", "dominated-safe"],
                    "restorations": [restoration_dict(x) for x in candidates], "evaluations": evaluations})
    # Reuse the compound pair's exact parent and derive restoration evaluations.
    compound = next(x for x in build_pair_registry()["pairs"] if x["category"] == "compound-repair")
    game = Game.from_dict(compound["parent_game"])
    candidates = (Restoration("information", observation_overrides=(("q0", "u0"), ("q1", "u1"))),
                  Restoration("restriction", remove_adversary_actions=frozenset({"a1"})),
                  Restoration("combined", observation_overrides=(("q0", "u0"), ("q1", "u1")), remove_adversary_actions=frozenset({"a1"})))
    result = optimal_restoration(game, candidates)
    evaluations = [{"candidate_id": e.restoration.name, "oracle": e.game_result.to_dict(), "cost": rational_json(e.cost)} for e in result.evaluations]
    records.append({"case_id": "compound", "game_id": game_id(game), "game": game.to_dict(), "categories": ["compound-repair", "unique-optimum"],
                    "restorations": [restoration_dict(x) for x in candidates], "evaluations": evaluations})
    return records


def build_probe_fixtures():
    """Small probe trajectories whose delay stages affect reachable structure."""
    fixtures = []
    for delay, informative, too_late, name in ((1, True, False, "useful-short"), (2, True, False, "useful-long"),
                                                (3, True, False, "useful-delay3"), (1, False, False, "useless"),
                                                (3, True, True, "too-late")):
        states = ["q0", "q1"] + [f"d{stage}_{i}" for stage in range(1, delay) for i in range(2)] + ["p0", "p1", "r", "x"]
        observations = {"q0": "o", "q1": "o", "r": "r", "x": "x", "p0": "p0" if informative else "p", "p1": "p1" if informative else "p"}
        observations.update({f"d{stage}_{i}": f"d{stage}" for stage in range(1, delay) for i in range(2)})
        transitions = {}
        for i in range(2):
            transitions[f"q{i}", "probe", "a0"] = f"p{i}" if delay == 1 else f"d1_{i}"
            for stage in range(1, delay):
                transitions[f"d{stage}_{i}", "wait", "a0"] = "x" if too_late else (f"p{i}" if stage == delay - 1 else f"d{stage + 1}_{i}")
            transitions[f"p{i}", f"resolve{i}", "a0"] = "r"
            transitions[f"p{i}", f"resolve{1-i}", "a0"] = "x"
        horizon = delay + 1
        availability = {"probe": [0], "wait": list(range(1, delay)), "resolve0": [delay], "resolve1": [delay]}
        game = _game(states=tuple(states), initial=("q0", "q1"), actions=("probe", "wait", "resolve0", "resolve1"), adversaries=("a0",),
                     observations=observations, transitions=transitions, horizon=horizon, availability=availability)
        fixtures.append({"fixture_id": name, "game_id": game_id(game), "game": game.to_dict(), "oracle": solve(game).to_dict(),
                         "probe_delay": delay, "informative": informative, "too_late": too_late,
                         "delay_states": [x for x in states if x.startswith("d")]})
    return fixtures


def build_timing_fixtures():
    """One staged deadline with early, last-usable, and too-late authority."""
    states = ("q0", "q1", "r", "x")
    transitions = {("q0", "wait", "a0"): "q1", ("q1", "wait", "a0"): "x",
                   ("q0", "act", "a0"): "r", ("q1", "act", "a0"): "r"}
    fixtures = []
    for fixture_id, round_ in (("before-deadline", 0), ("last-usable", 1), ("too-late", 2)):
        game = _game(states=states, initial=("q0",), actions=("wait", "act"), adversaries=("a0",),
                     observations={x: x for x in states}, transitions=transitions, horizon=3,
                     availability={"wait": [0, 1, 2], "act": [round_]})
        fixtures.append({"fixture_id": fixture_id, "intervention_round": round_, "game_id": game_id(game),
                         "game": game.to_dict(), "oracle": solve(game).to_dict()})
    return fixtures


def build_corpus_mechanics(registry):
    """Derive exact-duplicate and different-ID isomorphic audit witnesses."""
    from enforceability.corpus.core import IsomorphismLimits, _renamed_dict, canonicalize_isomorphism
    first = Game.from_dict(registry["pairs"][0]["parent_game"])
    renamed = Game.from_dict(_renamed_dict(first, tuple(f"z{i}" for i in range(len(first.states))),
                                           tuple(f"k{i}" for i in range(len(first.controller_actions))),
                                           tuple(f"b{i}" for i in range(len(first.adversary_actions))),
                                           tuple(f"v{i}" for i in range(len(first.observations)))))
    left, right = canonicalize_isomorphism(first, IsomorphismLimits()), canonicalize_isomorphism(renamed, IsomorphismLimits())
    assert game_id(first) != game_id(renamed) and left.class_id == right.class_id
    return {
        "exact_duplicate": {"game_id": game_id(first), "occurrences": 2},
        "isomorphic_duplicate": {"game_ids": [game_id(first), game_id(renamed)], "isomorphism_class_id": left.class_id},
    }
