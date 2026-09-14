"""Exact threshold-identifiability analysis for the canonical one-step family.

The collection policy below generates offline public evidence.  It is not the
state-informed strategic adversary used in :func:`strategic_value`.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from dataclasses import dataclass
from enum import Enum
from fractions import Fraction
from functools import lru_cache
from itertools import product
from pathlib import Path

from enforceability.schema import Game, rational_json

FAMILY_VERSION = "one-step-2state-2x2.v1"
COLLECTION_REGIME_VERSION = "state-blind-uniform-joint-actions.v1"
SIGNATURE_VERSION = "public-failure-conditionals.v1"
STATES = ("s0", "s1")
CONTROLLER_ACTIONS = ("c0", "c1")
ADVERSARY_ACTIONS = ("a0", "a1")
CELLS = tuple(product(STATES, CONTROLLER_ACTIONS, ADVERSARY_ACTIONS))
PUBLIC_CELLS = tuple(product(CONTROLLER_ACTIONS, ADVERSARY_ACTIONS))
ARTIFACT_DIRECTORY = Path(__file__).parents[2] / "artifacts" / "identifiability-v1"


@dataclass(frozen=True, slots=True)
class CollectionRegime:
    version: str = COLLECTION_REGIME_VERSION
    state_blind: bool = True
    joint_action_probabilities: tuple[Fraction, ...] = (Fraction(1, 4),) * 4

    def __post_init__(self) -> None:
        if not self.state_blind or len(self.joint_action_probabilities) != 4:
            raise ValueError("canonical regime must be state-blind over four joint actions")
        if any(p <= 0 for p in self.joint_action_probabilities) or sum(self.joint_action_probabilities) != 1:
            raise ValueError("collection probabilities must have full support and sum to one")


CANONICAL_COLLECTION_REGIME = CollectionRegime()


@dataclass(frozen=True, slots=True)
class OneStepGame:
    game_id: str
    failure_probabilities: tuple[Fraction, ...]

    def __post_init__(self) -> None:
        if len(self.failure_probabilities) != 8 or any(p not in (0, Fraction(1, 2), 1) for p in self.failure_probabilities):
            raise ValueError("a family game needs eight probabilities in {0,1/2,1}")

    def probability(self, state: str, controller: str, adversary: str) -> Fraction:
        return self.failure_probabilities[CELLS.index((state, controller, adversary))]


@dataclass(frozen=True, slots=True)
class PublicSignature:
    failure_probabilities: tuple[Fraction, ...]
    collection_regime_version: str = COLLECTION_REGIME_VERSION
    signature_version: str = SIGNATURE_VERSION

    def __post_init__(self) -> None:
        if len(self.failure_probabilities) != 4:
            raise ValueError("public signature needs four joint-action conditionals")


class ThresholdStatus(str, Enum):
    CERTIFIABLY_WINNING = "CERTIFIABLY_WINNING"
    CERTIFIABLY_LOSING = "CERTIFIABLY_LOSING"
    INSUFFICIENT_INFORMATION = "INSUFFICIENT_INFORMATION"


@lru_cache(maxsize=2)
def enumerate_games(probabilistic: bool = False) -> tuple[OneStepGame, ...]:
    alphabet = (Fraction(0), Fraction(1, 2), Fraction(1)) if probabilistic else (Fraction(0), Fraction(1))
    prefix = "p" if probabilistic else "d"
    width = 4 if probabilistic else 3
    return tuple(OneStepGame(f"{prefix}{index:0{width}d}", values) for index, values in enumerate(product(alphabet, repeat=8)))


def public_signature(game: OneStepGame, collection_regime: CollectionRegime = CANONICAL_COLLECTION_REGIME) -> PublicSignature:
    if collection_regime != CANONICAL_COLLECTION_REGIME:
        raise ValueError("only the canonical collection regime is defined")
    # State is deliberately averaged out and never serialized into the signature.
    return PublicSignature(tuple(sum((game.probability(s, c, a) for s in STATES), Fraction()) / 2 for c, a in PUBLIC_CELLS))


def strategic_value(game: OneStepGame) -> Fraction:
    """Exact min over controller mixtures of the informed adversary's response."""
    # x is P(c0). Each state's maximum of its two affine adversary payoffs can
    # change slope only where those lines intersect, so endpoints plus their
    # intersections are a complete exact candidate set.
    candidates = {Fraction(0), Fraction(1)}
    for state in STATES:
        b0 = game.probability(state, "c1", "a0")
        b1 = game.probability(state, "c1", "a1")
        m0 = game.probability(state, "c0", "a0") - b0
        m1 = game.probability(state, "c0", "a1") - b1
        if m0 != m1:
            x = (b1 - b0) / (m0 - m1)
            if 0 <= x <= 1:
                candidates.add(x)
    def objective(x: Fraction) -> Fraction:
        return sum(max(x * game.probability(s, "c0", a) + (1 - x) * game.probability(s, "c1", a) for a in ADVERSARY_ACTIONS) for s in STATES) / 2
    return min(map(objective, candidates))


@lru_cache(maxsize=2)
def ambiguity_classes(probabilistic: bool = False) -> dict[PublicSignature, tuple[OneStepGame, ...]]:
    grouped: dict[PublicSignature, list[OneStepGame]] = {}
    for game in enumerate_games(probabilistic):
        grouped.setdefault(public_signature(game), []).append(game)
    return {signature: tuple(games) for signature, games in sorted(grouped.items(), key=lambda item: item[0].failure_probabilities)}


def compatible_games(signature: PublicSignature, probabilistic: bool = False) -> tuple[OneStepGame, ...]:
    return ambiguity_classes(probabilistic).get(signature, ())


def ambiguity_values(signature: PublicSignature, probabilistic: bool = False) -> tuple[Fraction, ...]:
    return tuple(sorted({strategic_value(game) for game in compatible_games(signature, probabilistic)}))


def ambiguity_interval(signature: PublicSignature, probabilistic: bool = False) -> tuple[Fraction, Fraction]:
    values = ambiguity_values(signature, probabilistic)
    if not values:
        raise ValueError("signature is not compatible with this family")
    return min(values), max(values)


def threshold_status(signature: PublicSignature, epsilon: Fraction, probabilistic: bool = False) -> ThresholdStatus:
    lower, upper = ambiguity_interval(signature, probabilistic)
    if upper <= epsilon:
        return ThresholdStatus.CERTIFIABLY_WINNING
    if lower > epsilon:
        return ThresholdStatus.CERTIFIABLY_LOSING
    return ThresholdStatus.INSUFFICIENT_INFORMATION


def threshold_phase_structure(signature: PublicSignature, probabilistic: bool = False) -> dict[str, object]:
    """Describe the three threshold regions induced by an exact ambiguity interval.

    This is only standard partial-identification threshold logic applied to the
    computed lower and upper values; it is not a new theorem.
    """
    lower, upper = ambiguity_interval(signature, probabilistic)
    return {
        "ambiguity_interval": [_rat(lower), _rat(upper)],
        "standard_partial_identification_logic": True,
        "phases": [
            {"epsilon_region": f"epsilon < {_rat(lower)}", "status": ThresholdStatus.CERTIFIABLY_LOSING.value},
            {"epsilon_region": f"{_rat(lower)} <= epsilon < {_rat(upper)}", "status": ThresholdStatus.INSUFFICIENT_INFORMATION.value},
            {"epsilon_region": f"epsilon >= {_rat(upper)}", "status": ThresholdStatus.CERTIFIABLY_WINNING.value},
        ],
    }


def as_schema_game(game: OneStepGame, epsilon: Fraction = Fraction(0)) -> Game:
    rows = []
    for state, controller, adversary in CELLS:
        p = game.probability(state, controller, adversary)
        outcomes = [{"state": state, "probability": rational_json(probability)} for state, probability in (("SAFE", 1 - p), ("FAIL", p)) if probability]
        rows.append({"state": state, "controller_action": controller, "adversary_action": adversary, "outcomes": outcomes})
    # Terminal rows are unreachable but required by the total-transition schema.
    for state, controller, adversary in product(("SAFE", "FAIL"), CONTROLLER_ACTIONS, ADVERSARY_ACTIONS):
        rows.append({"state": state, "controller_action": controller, "adversary_action": adversary, "outcomes": [{"state": state, "probability": "1"}]})
    return Game.from_dict({"schema_version": "stage1.v2", "states": [*STATES, "SAFE", "FAIL"],
        "initial_distribution": [{"state": "s0", "probability": "1/2"}, {"state": "s1", "probability": "1/2"}], "controller_actions": list(CONTROLLER_ACTIONS),
        "adversary_actions": list(ADVERSARY_ACTIONS), "observations": ["hidden", "safe", "fail"],
        "observation_map": {"s0": "hidden", "s1": "hidden", "SAFE": "safe", "FAIL": "fail"},
        "transitions": rows, "failure_states": ["FAIL"], "recovery_states": ["SAFE"], "horizon": 1,
        "epsilon": rational_json(epsilon)})


def _rat(value: Fraction) -> str:
    return rational_json(value)


def _signature_json(signature: PublicSignature) -> dict[str, object]:
    return {"collection_regime_version": signature.collection_regime_version, "failure_conditionals": [_rat(x) for x in signature.failure_probabilities], "signature_version": signature.signature_version}


def _family_report(probabilistic: bool) -> dict[str, object]:
    classes = ambiguity_classes(probabilistic)
    records = []
    all_values = set()
    for signature, games in classes.items():
        values = tuple(sorted({strategic_value(g) for g in games})); all_values.update(values)
        records.append({"signature": _signature_json(signature), "game_ids": [g.game_id for g in games], "exact_values": [_rat(v) for v in values], "V_lower": _rat(min(values)), "V_upper": _rat(max(values))})
    ambiguous = sum(len(r["exact_values"]) > 1 for r in records)
    report = {"family_version": FAMILY_VERSION, "probability_alphabet": ["0", "1/2", "1"] if probabilistic else ["0", "1"],
        "total_games": len(enumerate_games(probabilistic)), "distinct_public_signatures": len(classes),
        "public_equivalence_class_sizes": sorted(len(g) for g in classes.values()), "exact_value_set": [_rat(v) for v in sorted(all_values)],
        "singleton_value_public_classes": len(classes) - ambiguous, "value_ambiguous_public_classes": ambiguous, "public_classes": records}
    if probabilistic:
        report["phenomenon_witnesses"] = probabilistic_phenomenon_witnesses()
    return report


SWEEP_THRESHOLDS = tuple(map(Fraction, ("0", "1/4", "1/3", "1/2", "2/3", "3/4", "1")))


def threshold_sweep(probabilistic: bool = False) -> list[dict[str, object]]:
    signatures = tuple(ambiguity_classes(probabilistic))
    result = []
    for epsilon in SWEEP_THRESHOLDS:
        counts = {status.value: 0 for status in ThresholdStatus}
        for signature in signatures:
            counts[threshold_status(signature, epsilon, probabilistic).value] += 1
        result.append({"epsilon": _rat(epsilon), **counts})
    return result


def probabilistic_phenomenon_witnesses() -> dict[str, object]:
    """Select canonical exact witnesses for P1/P2/P3 in ``{0,1/2,1}^8``."""
    candidates = []
    for signature, games in ambiguity_classes(True).items():
        values = tuple(sorted({strategic_value(game) for game in games}))
        if len(values) > 1:
            candidates.append((min(game.game_id for game in games), signature, games, values))
    candidates.sort(key=lambda item: item[0])

    def payload(candidate, epsilon=None):
        _, signature, games, values = candidate
        result = {"signature": _signature_json(signature), "ambiguity_interval": [_rat(values[0]), _rat(values[-1])],
            "exact_values": [_rat(value) for value in values], "canonical_game_ids": [game.game_id for game in games]}
        if epsilon is not None:
            result.update({"epsilon": _rat(epsilon), "threshold_status": threshold_status(signature, epsilon, True).value})
        return result

    p1 = candidates[0]
    p2_options = [(candidate[0], epsilon, candidate) for candidate in candidates for epsilon in SWEEP_THRESHOLDS
        if threshold_status(candidate[1], epsilon, True) == ThresholdStatus.INSUFFICIENT_INFORMATION]
    _, p2_epsilon, p2 = min(p2_options)
    p3_options = [(candidate[0], 0 if status == ThresholdStatus.CERTIFIABLY_WINNING else 1, epsilon, candidate)
        for candidate in candidates for epsilon in SWEEP_THRESHOLDS
        if (status := threshold_status(candidate[1], epsilon, True)) != ThresholdStatus.INSUFFICIENT_INFORMATION]
    _, _, p3_epsilon, p3 = min(p3_options)
    return {"P1_value_nonidentification": payload(p1), "P2_threshold_nonidentification": payload(p2, p2_epsilon),
        "P3_threshold_identification_without_value_identification": payload(p3, p3_epsilon),
        "selection_rule": "lexicographically smallest compatible game ID, then declared epsilon; P3 prefers certifiably winning"}


def select_witnesses() -> dict[str, object]:
    classes = ambiguity_classes()
    candidates = []
    for signature, games in classes.items():
        by_value: dict[Fraction, OneStepGame] = {}
        for game in games:
            by_value.setdefault(strategic_value(game), game)
        values = sorted(by_value)
        if len(values) > 1:
            candidates.append((by_value[values[0]].game_id, by_value[values[-1]].game_id, signature, values, games))
    _, _, sig_a, vals_a, _ = min(candidates)
    ga = min(compatible_games(sig_a), key=lambda g: (strategic_value(g), g.game_id)); gb = min(compatible_games(sig_a), key=lambda g: (-strategic_value(g), g.game_id))
    epsilon_a = vals_a[0]
    # Cleanest means all four visible conditionals equal; ties are canonical IDs.
    clean = [x for x in candidates if len(set(x[2].failure_probabilities)) == 1]
    _, _, sig_b, vals_b, _ = min(clean, key=lambda x: (-x[3][-1] + x[3][0], x[0], x[1]))
    b0 = min(compatible_games(sig_b), key=lambda g: (strategic_value(g), g.game_id)); b1 = min(compatible_games(sig_b), key=lambda g: (-strategic_value(g), g.game_id))
    epsilon_b = vals_b[0]
    # Prefer Witness A's class when it has both a nonidentified declared
    # threshold and an identified threshold.  At the latter, prefer the exact
    # upper boundary, which is certifiably winning under weak <= semantics.
    ordered_c_classes = [(sig_a, vals_a, compatible_games(sig_a))] + [
        (signature, values, games) for _, _, signature, values, games in candidates if signature != sig_a]
    for sig_c, vals_c, c_games in ordered_c_classes:
        nonidentified = [epsilon for epsilon in SWEEP_THRESHOLDS if threshold_status(sig_c, epsilon) == ThresholdStatus.INSUFFICIENT_INFORMATION]
        winning = [epsilon for epsilon in SWEEP_THRESHOLDS if threshold_status(sig_c, epsilon) == ThresholdStatus.CERTIFIABLY_WINNING]
        if nonidentified and winning:
            epsilon_nonidentified = min(nonidentified)
            epsilon_c = vals_c[-1] if vals_c[-1] in winning else min(winning)
            status_c = threshold_status(sig_c, epsilon_c)
            break
    else:  # pragma: no cover - finite family invariant guarded by tests
        raise RuntimeError("no threshold-dependent value-ambiguous class")
    def pair_payload(signature, low, high, epsilon):
        return {"signature": _signature_json(signature), "game_ids": [low.game_id, high.game_id], "values": [_rat(strategic_value(low)), _rat(strategic_value(high))], "epsilon": _rat(epsilon),
            "game_labels": ["WINNING" if strategic_value(g) <= epsilon else "LOSING" for g in (low, high)]}
    c_low = min(c_games, key=lambda g: (strategic_value(g), g.game_id)); c_high = min(c_games, key=lambda g: (-strategic_value(g), g.game_id))
    return {"selection_rule": "lexicographic canonical IDs after stated scientific filters", "witness_A": pair_payload(sig_a, ga, gb, epsilon_a),
        "witness_B": {**pair_payload(sig_b, b0, b1, epsilon_b), "all_public_joint_actions_positive_probability": True, "equal_visible_conditionals": True},
        "witness_C": {**pair_payload(sig_c, c_low, c_high, epsilon_c), "class_value_set": [_rat(v) for v in vals_c],
            "epsilon_nonidentified": _rat(epsilon_nonidentified), "threshold_status": status_c.value,
            "threshold_phase_structure": threshold_phase_structure(sig_c),
            "selection_rule": "prefer Witness A class with both identified and nonidentified declared thresholds; choose its upper boundary when certifiably winning"}}


def build_artifacts(directory: Path = ARTIFACT_DIRECTORY) -> dict[str, bytes]:
    deterministic = _family_report(False); probabilistic = _family_report(True); witnesses = select_witnesses()
    sweep = threshold_sweep()
    freeze = {"family_version": FAMILY_VERSION, "collection_regime_version": COLLECTION_REGIME_VERSION, "interface_signature_version": SIGNATURE_VERSION,
        "ordered_canonical_game_ids": [g.game_id for g in enumerate_games()],
        "assignments": [{"game_id": g.game_id, "public_signature": [_rat(x) for x in public_signature(g).failure_probabilities], "exact_value": _rat(strategic_value(g))} for g in enumerate_games()],
        "ambiguity_intervals": [{"public_signature": [_rat(x) for x in s.failure_probabilities], "interval": [_rat(x) for x in ambiguity_interval(s)]} for s in ambiguity_classes()],
        "selected_witness_ids": {key: value["game_ids"] for key, value in witnesses.items() if key.startswith("witness_")},
        "selected_witnesses": {key: value for key, value in witnesses.items() if key.startswith("witness_")}, "threshold_sweep": sweep}
    values = {"deterministic-family-report.json": deterministic, "probabilistic-family-report.json": probabilistic,
        "witnesses.json": witnesses, "identifiability-freeze.json": freeze}
    return {name: (json.dumps(value, indent=2, sort_keys=True) + "\n").encode() for name, value in values.items()}


def write_artifacts(directory: Path = ARTIFACT_DIRECTORY) -> None:
    directory.mkdir(parents=True, exist_ok=True)
    for name, content in build_artifacts(directory).items():
        (directory / name).write_bytes(content)


def verify_artifacts(directory: Path = ARTIFACT_DIRECTORY) -> dict[str, str]:
    expected = build_artifacts(directory)
    actual_names = {path.name for path in directory.glob("*.json")}
    if actual_names != set(expected):
        raise ValueError("artifact file set mismatch")
    fingerprints = {}
    for name, content in expected.items():
        if (directory / name).read_bytes() != content:
            raise ValueError(f"artifact mismatch: {name}")
        fingerprints[name] = hashlib.sha256(content).hexdigest()
    return fingerprints


def main() -> None:
    parser = argparse.ArgumentParser(); parser.add_argument("--rebuild", action="store_true"); args = parser.parse_args()
    if args.rebuild:
        write_artifacts()
    fingerprints = verify_artifacts()
    print(json.dumps({"status": "verified", "sha256": fingerprints}, sort_keys=True))


if __name__ == "__main__":
    main()
