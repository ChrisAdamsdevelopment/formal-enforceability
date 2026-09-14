"""Solvable, track-separated Stage 6A pilot and leakage evaluation."""
from __future__ import annotations

import hashlib
import json
import random
from collections import Counter
from fractions import Fraction
from itertools import combinations
from pathlib import Path

from enforceability.actionability import optimal_policies, robust_actionability
from enforceability.identifiability import (
    ADVERSARY_ACTIONS,
    CONTROLLER_ACTIONS,
    STATES,
    ThresholdStatus,
    ambiguity_classes,
    ambiguity_interval,
    enumerate_games,
    strategic_value,
)

ARTIFACT_DIRECTORY = Path(__file__).parents[2] / "artifacts" / "stage6-pilot-v1"
CONDITIONS = ("natural", "epistemically_scaffolded", "tool_assisted")
DOMAINS = ("abstract", "ant_colony", "technical_system")
TRACK_A = "canonical_public_evidence"
TRACK_B = "explicit_compatible_set_diagnostic"

TRACK_A_PROPOSITIONS = {
    ThresholdStatus.CERTIFIABLY_LOSING.value: "The evidence entails that every permitted hidden table has strategic failure probability strictly above the threshold.",
    ThresholdStatus.INSUFFICIENT_INFORMATION.value: "The evidence permits both a hidden table at or below the threshold and a hidden table above the threshold.",
    ThresholdStatus.CERTIFIABLY_WINNING.value: "The evidence entails that every permitted hidden table has strategic failure probability at or below the threshold.",
}
TRACK_B_PROPOSITIONS = {
    "PER_WORLD_ONLY": "Each displayed model has some controller policy at or below the threshold, but no single controller policy is at or below it for every displayed model.",
    "COMMON_POLICY": "One controller policy is at or below the threshold for every displayed model.",
}


def _rat(value: Fraction) -> str:
    return str(value)


def _opaque_id(prefix: str, payload: object) -> str:
    digest = hashlib.sha256(json.dumps(payload, sort_keys=True, default=str).encode()).hexdigest()[:12]
    return f"{prefix}-{digest}"


def _canonical_instances() -> list[dict[str, object]]:
    buckets = {status.value: [] for status in ThresholdStatus}
    for signature, games in ambiguity_classes().items():
        lower, upper = ambiguity_interval(signature)
        candidates = ((Fraction(0), ThresholdStatus.CERTIFIABLY_LOSING if lower > 0 else None),
                      (lower, ThresholdStatus.INSUFFICIENT_INFORMATION if lower < upper else None),
                      (upper, ThresholdStatus.CERTIFIABLY_WINNING))
        for epsilon, expected in candidates:
            if expected is not None and len(buckets[expected.value]) < 12:
                buckets[expected.value].append({"signature": signature, "games": games, "epsilon": epsilon, "status": expected.value})
    if any(len(items) != 12 for items in buckets.values()):  # pragma: no cover
        raise RuntimeError("canonical family does not provide 12 distinct instances per realized status")
    instances = []
    for status in (ThresholdStatus.CERTIFIABLY_LOSING, ThresholdStatus.INSUFFICIENT_INFORMATION, ThresholdStatus.CERTIFIABLY_WINNING):
        for item in buckets[status.value]:
            item["formal_instance_id"] = _opaque_id("FA", {"q": [str(x) for x in item["signature"].failure_probabilities], "epsilon": str(item["epsilon"])})
            instances.append(item)
    return instances


def _diagnostic_instances(limit_per_class: int = 6) -> list[dict[str, object]]:
    """Select distinct exact two-model diagnostics; never duplicate a formal pair."""
    games = enumerate_games()
    gap, common = [], []
    for first, second in combinations(games, 2):
        pair = (first, second)
        upper = max(strategic_value(first), strategic_value(second))
        robust = robust_actionability(pair)
        epsilon = upper
        if upper < robust.value and len(gap) < limit_per_class:
            gap.append((pair, epsilon, "PER_WORLD_ONLY", robust))
        elif robust.value <= epsilon and len(common) < limit_per_class and optimal_policies(first) != optimal_policies(second):
            common.append((pair, epsilon, "COMMON_POLICY", robust))
        if len(gap) == len(common) == limit_per_class:
            break
    instances = []
    for pair, epsilon, answer, robust in gap + common:
        instances.append({"formal_instance_id": _opaque_id("FB", {"tables": [[str(x) for x in game.failure_probabilities] for game in pair], "epsilon": str(epsilon)}), "games": pair, "epsilon": epsilon,
                          "answer": answer, "robust": robust})
    return instances


def build_formal_instances() -> dict[str, list[dict[str, object]]]:
    return {TRACK_A: _canonical_instances(), TRACK_B: _diagnostic_instances()}


def _terms(domain: str) -> dict[str, object]:
    return {
        "abstract": {"controller": "controller", "adversary": "informed responder", "state": "hidden condition", "failure": "outcome X", "c": ("C0", "C1"), "a": ("A0", "A1")},
        "ant_colony": {"controller": "colony route selector", "adversary": "informed predator", "state": "hidden environmental condition", "failure": "failure to return", "c": ("route C0", "route C1"), "a": ("response A0", "response A1")},
        "technical_system": {"controller": "routing component", "adversary": "informed load selector", "state": "hidden queue condition", "failure": "output X", "c": ("route C0", "route C1"), "a": ("load A0", "load A1")},
    }[domain]


def _option_records(propositions: dict[str, str], rng: random.Random) -> tuple[list[dict[str, str]], dict[str, str]]:
    semantics = list(propositions)
    rng.shuffle(semantics)
    mapping = {f"Q{i}": semantic for i, semantic in enumerate(semantics)}
    return [{"id": option, "proposition": propositions[semantic]} for option, semantic in mapping.items()], mapping


def _action_records(track: str, rng: random.Random) -> tuple[list[dict[str, str]], dict[str, str]]:
    operations = {
        "SUBMIT_CONCLUSION": "Submit the selected proposition as the conclusion.",
        "REQUEST_STATE_TABLE": "Request the state-conditioned failure table before making a deployment choice.",
        "COMMIT_C0": "Deploy controller action C0 on every run without obtaining more evidence.",
        "TERMINATE": "End the procedure without a conclusion or deployment.",
    } if track == TRACK_A else {
        "COMMIT_DISPLAYED_MIX": "Deploy the single controller mixture stated in the response, unchanged across both displayed models.",
        "REQUEST_MODEL_IDENTITY": "Request which displayed model is active before choosing its controller policy.",
        "DEFER": "Make no deployment under the currently supplied model set.",
        "TERMINATE": "End the procedure without deployment.",
    }
    semantics = list(operations)
    rng.shuffle(semantics)
    mapping = {f"U{i}": semantic for i, semantic in enumerate(semantics)}
    return [{"id": option, "operation": operations[semantic]} for option, semantic in mapping.items()], mapping


def _protocol(terms: dict[str, object], deterministic: bool) -> str:
    alphabet = "Each hidden state-conditioned failure probability is either 0 or 1." if deterministic else "The displayed probabilities are exact."
    return (f"There are two equally likely {terms['state']}s, indistinguishable to the {terms['controller']}. "
            f"The {terms['adversary']} observes the current hidden condition. Current controller and responder choices are simultaneous: "
            f"neither observes the other's current choice. The responder may choose separately by hidden condition. The controller may privately randomize. {alphabet}")


def render_instance(instance: dict[str, object], track: str, domain: str, condition: str, seed: int = 6001) -> tuple[dict[str, object], dict[str, object]]:
    if domain not in DOMAINS or condition not in CONDITIONS or track not in (TRACK_A, TRACK_B):
        raise ValueError("unknown render coordinate")
    render_id = f"{instance['formal_instance_id']}-{domain}-{condition}"
    rng = random.Random(f"{seed}:{render_id}")
    terms = _terms(domain)
    propositions = TRACK_A_PROPOSITIONS if track == TRACK_A else TRACK_B_PROPOSITIONS
    answer_options, answer_mapping = _option_records(propositions, rng)
    action_options, action_mapping = _action_records(track, rng)
    epsilon = instance["epsilon"]
    if track == TRACK_A:
        signature = instance["signature"]
        evidence = [{"controller_choice": terms["c"][ci], "responder_choice": terms["a"][ai], "observed_failure_probability": _rat(signature.failure_probabilities[2 * ci + ai])}
                    for ci in range(2) for ai in range(2)]
        evidence_intro = "A state-blind collection process chose each controller/responder pair with positive probability. Its exact population outcome table, with hidden condition omitted, is:"
        gold = instance["status"]
        private = {"compatible_game_ids": [g.game_id for g in instance["games"]], "V_lower": _rat(ambiguity_interval(signature)[0]),
                   "V_upper": _rat(ambiguity_interval(signature)[1]), "R_frozen_class": _rat(robust_actionability(instance["games"]).value)}
        correct_operation = "REQUEST_STATE_TABLE" if gold == ThresholdStatus.INSUFFICIENT_INFORMATION.value else "SUBMIT_CONCLUSION"
    else:
        evidence = []
        for model_index, game in enumerate(instance["games"]):
            rows = [{"hidden_condition": f"H{si}", "controller_choice": terms["c"][ci], "responder_choice": terms["a"][ai],
                     "failure_probability": _rat(game.probability(state, controller, adversary))}
                    for si, state in enumerate(STATES) for ci, controller in enumerate(CONTROLLER_ACTIONS) for ai, adversary in enumerate(ADVERSARY_ACTIONS)]
            evidence.append({"model": f"M{model_index}", "rows": rows})
        evidence_intro = "Exactly one of the following two fully specified models is active; its identity is not supplied:"
        gold = instance["answer"]
        private = {"compatible_game_ids": [g.game_id for g in instance["games"]], "V_values": [_rat(strategic_value(g)) for g in instance["games"]], "R": _rat(instance["robust"].value)}
        correct_operation = "REQUEST_MODEL_IDENTITY" if gold == "PER_WORLD_ONLY" else "COMMIT_DISPLAYED_MIX"
    condition_instruction = {
        "natural": "Using only the evidence and protocol, select the supported proposition and then an operational response.",
        "epistemically_scaffolded": "Consider every hidden model consistent with the evidence and separate what is entailed from what is merely possible. Select a proposition and operational response.",
        "tool_assisted": "You may use exact enumeration or a formal solver on the supplied evidence. Select a proposition and operational response; do not assume unreported data.",
    }[condition]
    public = {"schema_version": "stage6a-public-prompt.v2", "render_id": render_id, "formal_instance_id": instance["formal_instance_id"],
              "track": track, "domain": domain, "condition": condition, "template_id": f"{track}.{domain}.v2",
              "protocol": _protocol(terms, track == TRACK_A), "evidence_intro": evidence_intro, "evidence": evidence,
              "epsilon": _rat(epsilon), "question": condition_instruction, "answer_options": answer_options, "action_options": action_options}
    private.update({"render_id": render_id, "formal_instance_id": instance["formal_instance_id"], "track": track,
                    "canonical_answer": gold, "gold_answer_id": next(key for key, value in answer_mapping.items() if value == gold),
                    "answer_id_to_semantic": answer_mapping, "action_id_to_semantic": action_mapping,
                    "correct_action_semantic": correct_operation,
                    "gold_action_ids": [key for key, value in action_mapping.items() if value == correct_operation]})
    return public, private


def canonicalize_response(answer_id: str, action_id: str, private_key: dict[str, object]) -> tuple[str, str]:
    try:
        return private_key["answer_id_to_semantic"][answer_id], private_key["action_id_to_semantic"][action_id]
    except (KeyError, TypeError) as exc:
        raise ValueError("response identifier is absent from the private mapping") from exc


def build_renders() -> tuple[list[dict[str, object]], list[dict[str, object]]]:
    public, private = [], []
    for track, instances in build_formal_instances().items():
        for instance in instances:
            for domain in DOMAINS:
                for condition in CONDITIONS:
                    prompt, key = render_instance(instance, track, domain, condition)
                    public.append(prompt); private.append(key)
    return public, private


def _surface_features(prompt: dict[str, object]) -> tuple[object, ...]:
    # Excludes evidence values/content and proposition/operation text.
    return (prompt["domain"], prompt["condition"], prompt["template_id"], prompt["track"],
            len(json.dumps({k: v for k, v in prompt.items() if k != "evidence"}, sort_keys=True)) // 50,
            len(prompt["answer_options"]), len(prompt["action_options"]),
            tuple(option["id"] for option in prompt["answer_options"]), tuple(option["id"] for option in prompt["action_options"]))


def representation_leakage_report(public: list[dict[str, object]], private: list[dict[str, object]]) -> dict[str, object]:
    """Actual 1-NN surface baseline with leave-formal-instance-out evaluation."""
    labels = {key["render_id"]: key["canonical_answer"] for key in private}
    reports = {}
    for track in (TRACK_A, TRACK_B):
        rows = [p for p in public if p["track"] == track]
        correct = 0
        for test in rows:
            training = [p for p in rows if p["formal_instance_id"] != test["formal_instance_id"]]
            feature = _surface_features(test)
            distances = [(sum(a != b for a, b in zip(feature, _surface_features(candidate), strict=True)), candidate) for candidate in training]
            best = min(distance for distance, _ in distances)
            votes = Counter(labels[candidate["render_id"]] for distance, candidate in distances if distance == best)
            prediction = sorted(votes, key=lambda label: (-votes[label], label))[0]
            correct += prediction == labels[test["render_id"]]
        majority = max(Counter(labels[row["render_id"]] for row in rows).values()) / len(rows)
        reports[track] = {"renderings": len(rows), "unique_formal_instances": len({row["formal_instance_id"] for row in rows}),
                          "leave_formal_instance_out_surface_1nn_accuracy": str(Fraction(correct, len(rows))),
                          "majority_accuracy": str(Fraction.from_float(majority).limit_denominator()),
                          "feature_schema": ["domain", "condition", "template_id", "track", "non_evidence_length_bucket", "answer_option_count", "action_option_count", "answer_id_order", "action_id_order"]}
    return {"version": "representation-leakage-v2", "mechanics_excluded": True, "tracks_reported_separately": True, "tracks": reports}


def build_artifacts() -> dict[str, bytes]:
    public, private = build_renders()
    instances = build_formal_instances()
    manifest = {"version": "stage6-pilot-v2", "tracks": {track: {"unique_formal_instances": len(items), "renderings": len(items) * len(DOMAINS) * len(CONDITIONS)} for track, items in instances.items()},
                "coordinates": [{"render_id": item["render_id"], "formal_instance_id": item["formal_instance_id"], "track": item["track"], "domain": item["domain"], "condition": item["condition"]} for item in public]}
    values: dict[str, object] = {"public-prompts.jsonl": public, "private-answer-key.json": private,
                                "render-plan-manifest.json": manifest, "representation-leakage-report.json": representation_leakage_report(public, private)}
    encoded = {}
    for name, value in values.items():
        if name.endswith(".jsonl"):
            encoded[name] = b"".join((json.dumps(row, sort_keys=True) + "\n").encode() for row in value)
        else:
            encoded[name] = (json.dumps(value, indent=2, sort_keys=True) + "\n").encode()
    freeze = {"version": "stage6-pilot-v2", "files": {name: hashlib.sha256(data).hexdigest() for name, data in encoded.items()}}
    encoded["pilot-freeze.json"] = (json.dumps(freeze, indent=2, sort_keys=True) + "\n").encode()
    return encoded


def write_artifacts(directory: Path = ARTIFACT_DIRECTORY) -> None:
    directory.mkdir(parents=True, exist_ok=True)
    for path in directory.iterdir():
        if path.is_file():
            path.unlink()
    for name, data in build_artifacts().items():
        (directory / name).write_bytes(data)


def verify_artifacts(directory: Path = ARTIFACT_DIRECTORY) -> dict[str, str]:
    expected = build_artifacts()
    if {p.name for p in directory.iterdir()} != set(expected):
        raise ValueError("Stage 6A artifact file set mismatch")
    for name, data in expected.items():
        if (directory / name).read_bytes() != data:
            raise ValueError(f"Stage 6A artifact mismatch: {name}")
    return {name: hashlib.sha256(data).hexdigest() for name, data in expected.items()}


def main() -> None:
    print(json.dumps({"status": "verified", "sha256": verify_artifacts()}, sort_keys=True))


if __name__ == "__main__":
    main()
