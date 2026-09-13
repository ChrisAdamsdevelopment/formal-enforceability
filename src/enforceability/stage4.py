"""Stage-4 formal benchmark metadata and cross-corpus audits.

This module deliberately operates on solved Stage-3 corpus artifacts.  It does
not render games and it never participates in generation or oracle decisions.
"""
from __future__ import annotations

from dataclasses import dataclass
from fractions import Fraction
import hashlib
import json
from pathlib import Path
from types import MappingProxyType
from typing import Any, Mapping

from enforceability.generation import canonical_json
from enforceability.generation import add_controller_action, game_id
from enforceability.restoration import apply_restoration
from enforceability.schema import Game
from enforceability import Restoration, solve

STAGE4_VERSION = "stage4.formal-freeze.v1"


@dataclass(frozen=True, slots=True)
class MechanismCoverageSpec:
    """Versioned, outcome-independent list of required formal mechanisms."""

    version: str
    dimensions: Mapping[str, tuple[str, ...]]

    def __post_init__(self) -> None:
        snapshot = {str(k): tuple(v) for k, v in self.dimensions.items()}
        identifiers = [item for values in snapshot.values() for item in values]
        if self.version != STAGE4_VERSION or not snapshot or len(identifiers) != len(set(identifiers)):
            raise ValueError("invalid mechanism coverage specification")
        if any(not x or x.lower() != x or " " in x for x in identifiers):
            raise ValueError("mechanism identifiers must be stable lower-case tokens")
        object.__setattr__(self, "dimensions", MappingProxyType(snapshot))

    @classmethod
    def load(cls, path: str | Path) -> "MechanismCoverageSpec":
        raw = json.loads(Path(path).read_text())
        if set(raw) != {"version", "dimensions"} or raw["version"] != STAGE4_VERSION:
            raise ValueError("unsupported mechanism coverage specification")
        dimensions = {str(k): tuple(v) for k, v in raw["dimensions"].items()}
        return cls(raw["version"], dimensions)

    @property
    def required_mechanisms(self) -> tuple[str, ...]:
        return tuple(sorted(x for values in self.dimensions.values() for x in values))

    @property
    def fingerprint(self) -> str:
        value = {"version": self.version, "dimensions": {k: list(v) for k, v in self.dimensions.items()}}
        return hashlib.sha256(canonical_json(value).encode()).hexdigest()


def _load_artifact(corpus: str | Path) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    root = Path(corpus)
    return (json.loads((root / "candidate-ledger.json").read_text()), json.loads((root / "corpus-manifest.json").read_text()))


def audit_corpus_overlap(development: str | Path, evaluation: str | Path) -> dict[str, Any]:
    """Report exact and resolved-isomorphism contamination between two freezes."""

    dev, _ = _load_artifact(development)
    eva, _ = _load_artifact(evaluation)
    retained = lambda rows: [x for x in rows if (x.get("retention") or {}).get("retained")]
    raw_dev, raw_eva = dev, eva
    raw_dev_ids = {x.get("game_id") for x in raw_dev if x.get("game_id")}
    raw_dev_classes = {x["isomorphism"]["class_id"] for x in raw_dev if (x.get("isomorphism") or {}).get("status") == "RESOLVED"}
    raw_exact = sorted({x["game_id"] for x in raw_eva if x.get("game_id") in raw_dev_ids})
    raw_iso = sorted({x["isomorphism"]["class_id"] for x in raw_eva if (x.get("isomorphism") or {}).get("status") == "RESOLVED" and x["isomorphism"]["class_id"] in raw_dev_classes})
    raw_dev_unresolved = sorted(x["candidate_key"] for x in raw_dev if (x.get("isomorphism") or {}).get("status") == "ISOMORPHISM_UNRESOLVED")
    raw_eval_unresolved = sorted(x["candidate_key"] for x in raw_eva if (x.get("isomorphism") or {}).get("status") == "ISOMORPHISM_UNRESOLVED")
    dev, eva = retained(dev), retained(eva)
    dev_ids = {x["game_id"] for x in dev}
    dev_classes = {x["isomorphism"]["class_id"] for x in dev if (x.get("isomorphism") or {}).get("status") == "RESOLVED"}
    retained_dev_unresolved = sorted(x["candidate_key"] for x in dev if (x.get("isomorphism") or {}).get("status") != "RESOLVED")
    details = []
    for item in eva:
        iso = item.get("isomorphism") or {}
        details.append({
            "candidate_key": item["candidate_key"],
            "game_id": item["game_id"],
            "exact_id_in_development": item["game_id"] in dev_ids,
            "isomorphism_class_id": iso.get("class_id"),
            "resolved_class_in_development": iso.get("status") == "RESOLVED" and iso.get("class_id") in dev_classes,
            "isomorphism_unresolved": iso.get("status") != "RESOLVED",
            "same_family_template": any(x["family"] == item["family"] for x in dev),
        })
    report = {
        "version": STAGE4_VERSION,
        "evaluation_cases": details,
        "exact_id_overlap": sorted(x["game_id"] for x in details if x["exact_id_in_development"]),
        "resolved_isomorphism_overlap": sorted(x["isomorphism_class_id"] for x in details if x["resolved_class_in_development"]),
        "unresolved_evaluation_cases": sorted(x["candidate_key"] for x in details if x["isomorphism_unresolved"]),
        "same_family_template_count": sum(x["same_family_template"] for x in details),
        "raw_exact_id_overlap": raw_exact,
        "raw_resolved_isomorphism_overlap": raw_iso,
        "raw_development_unresolved_cases": raw_dev_unresolved,
        "raw_evaluation_unresolved_cases": raw_eval_unresolved,
        "retained_development_unresolved_cases": retained_dev_unresolved,
    }
    report["passes"] = not any((report["exact_id_overlap"], report["resolved_isomorphism_overlap"],
                                report["unresolved_evaluation_cases"], report["retained_development_unresolved_cases"]))
    return report


def intervention_value(parent_oracle: Mapping[str, Any], child_oracle: Mapping[str, Any]) -> dict[str, Any]:
    """Compute pair-specific improvement = parent failure value - child value."""

    # Frozen oracle artifacts call the value ``failure_probability``.  The
    # shorter alias is accepted for small audit-only records.
    parent = Fraction(parent_oracle.get("failure_probability", parent_oracle.get("value")))
    child = Fraction(child_oracle.get("failure_probability", child_oracle.get("value")))
    if "threshold_satisfied" in parent_oracle and "threshold_satisfied" in child_oracle:
        crossing = parent_oracle["threshold_satisfied"] != child_oracle["threshold_satisfied"]
    else:
        crossing = (parent <= Fraction(parent_oracle["epsilon"])) != (child <= Fraction(child_oracle["epsilon"]))
    return {
        "parent_value": str(parent), "child_value": str(child),
        "improvement": str(parent - child),
        "threshold_crossing": crossing,
        "sign_convention": "positive means lower child failure probability",
    }


def _fingerprint(value: Any) -> str:
    return hashlib.sha256(canonical_json(value).encode()).hexdigest()


def validate_pair_registry(registry: Mapping[str, Any]) -> dict[str, Any]:
    """Reproduce every child and recompute every exact pair value."""
    failures = []
    for pair in registry.get("pairs", ()):
        try:
            parent, declared_child = Game.from_dict(pair["parent_game"]), Game.from_dict(pair["child_game"])
            before, after = parent.to_dict(), declared_child.to_dict()
            changed = tuple(k for k in before if k != "display_labels" and before[k] != after[k])
            if tuple(pair["changed_formal_fields"]) != changed:
                failures.append(f'{pair["pair_id"]}: changed fields')
            record = pair["transformation_record"]
            if (record["parent_game_id"], record["child_game_id"], record["transformation_type"], tuple(record["changed_formal_fields"])) != (
                    pair["parent_game_id"], pair["child_game_id"], pair["transformation_type"], changed):
                failures.append(f'{pair["pair_id"]}: transformation record')
            transformation = pair["transformation_type"]
            if transformation == "controller-capability-addition":
                added = next(iter(set(declared_child.controller_actions) - set(parent.controller_actions)))
                outcomes = {(s, a): declared_child.transitions[s, added, a] for s in parent.states for a in parent.adversary_actions}
                reproduced, _ = add_controller_action(parent, added, outcomes, tuple(declared_child.action_availability[added]), pair["transformation_record"]["seed"])
            elif transformation == "horizon-change":
                raw = before; raw["horizon"] = declared_child.horizon
                raw["action_availability"] = {k: sorted(v) for k, v in declared_child.action_availability.items()}
                reproduced = Game.from_dict(raw)
            else:
                obs = tuple((s, declared_child.observation_map[s]) for s in parent.states if parent.observation_map[s] != declared_child.observation_map[s])
                removed = frozenset(set(parent.adversary_actions) - set(declared_child.adversary_actions))
                availability = tuple((a, tuple(declared_child.action_availability[a])) for a in parent.controller_actions
                                     if parent.action_availability[a] != declared_child.action_availability[a])
                reproduced = apply_restoration(parent, Restoration("reproduce", remove_adversary_actions=removed,
                                                                    observation_overrides=obs, availability_overrides=availability))
            if reproduced != declared_child or game_id(parent) != pair["parent_game_id"] or game_id(reproduced) != pair["child_game_id"]:
                failures.append(f'{pair["pair_id"]}: reproduction or ID')
            po, co = solve(parent).to_dict(), solve(reproduced).to_dict()
            value = intervention_value(po, co)
            if po != pair["parent_oracle"] or co != pair["child_oracle"] or value["improvement"] != pair["exact_improvement"] or value["threshold_crossing"] != pair["threshold_crossing"]:
                failures.append(f'{pair["pair_id"]}: oracle value')
            improvement = Fraction(value["improvement"])
            if pair["category"].startswith("positive-value-") and improvement <= 0:
                failures.append(f'{pair["pair_id"]}: expected positive value')
            if pair["category"].startswith("zero-value-") and improvement != 0:
                failures.append(f'{pair["pair_id"]}: expected zero value')
            if pair["category"] in {"timing-rescue", "common-safe-action-addition", "compound-repair"} and improvement <= 0:
                failures.append(f'{pair["pair_id"]}: expected rescue')
            if pair["category"] == "horizon-only" and improvement == 0:
                failures.append(f'{pair["pair_id"]}: expected horizon contrast')
            if pair["category"] == "compound-repair":
                if [x["component"] for x in pair["component_children"]] != ["observation-refinement", "adversary-capability-removal"]:
                    failures.append(f'{pair["pair_id"]}: compound order')
                if any(x["oracle"]["threshold_satisfied"] for x in pair["component_children"]) or not co["threshold_satisfied"]:
                    failures.append(f'{pair["pair_id"]}: compound relationship')
        except Exception as exc:  # artifact validation must return all failures
            failures.append(f'{pair.get("pair_id", "unknown")}: {type(exc).__name__}: {exc}')
    payload = {"version": registry.get("version"), "pairs": registry.get("pairs", [])}
    if registry.get("fingerprint") != _fingerprint(payload):
        failures.append("registry fingerprint")
    return {"passed": not failures, "failures": failures, "pair_count": len(registry.get("pairs", ())) }


def build_mechanism_evidence(spec: MechanismCoverageSpec, registry: Mapping[str, Any], probability_fixtures,
                             restoration_fixtures, probe_fixtures, timing_fixtures, corpus_refs: Mapping[str, Any]) -> dict[str, Any]:
    """Build an evidence-linked report; declarations alone never imply coverage."""
    pair_by_category = {x["category"]: x for x in registry["pairs"]}
    probability_by_id = {x["fixture_id"]: x for x in probability_fixtures}
    restoration_by_category = {category: row for row in restoration_fixtures for category in row["categories"]}
    probe_by_id = {x["fixture_id"]: x for x in probe_fixtures}
    timing_by_id = {x["fixture_id"]: x for x in timing_fixtures}
    refs: dict[str, list[dict[str, Any]]] = {}
    def pair(mid, category):
        x = pair_by_category[category]; refs[mid] = [{"artifact_type": "matched_pair", "pair_id": x["pair_id"], "parent_game_id": x["parent_game_id"], "child_game_id": x["child_game_id"]}]
    for mid, category in (("obs-refinement-positive-v1", "positive-value-observation"), ("obs-refinement-zero-v1", "zero-value-observation"),
                          ("restriction-positive-v1", "positive-value-restriction"), ("restriction-zero-v1", "zero-value-restriction"),
                          ("timing-multiple-positions-v1", "timing-rescue"), ("timing-multiple-horizons-v1", "horizon-only"),
                          ("obs-ambiguous-common-policy-v1", "zero-value-observation"), ("obs-ambiguous-incompatible-v1", "positive-value-observation"),
                          ("authority-robust-response-v1", "common-safe-action-addition"), ("authority-perfect-insufficient-v1", "positive-value-restriction"),
                          ("restriction-joint-v1", "compound-repair"), ("repair-information-only-v1", "positive-value-observation"),
                          ("repair-restriction-only-v1", "positive-value-restriction"), ("repair-timing-only-v1", "timing-rescue"),
                          ("repair-compound-v1", "compound-repair"), ("matched-transformation-v1", "common-safe-action-addition")):
        pair(mid, category)
    for mid, fixture in (("transition-deterministic-v1", "minimax-half"), ("transition-stochastic-rational-v1", "third-boundary"),
                         ("probability-half-v1", "half-boundary"), ("probability-third-v1", "third-boundary"),
                         ("probability-other-rational-v1", "quarter"), ("epsilon-nonzero-v1", "third-boundary"),
                         ("epsilon-boundary-v1", "third-boundary"), ("epsilon-neighboring-v1", "third-above")):
        x = probability_by_id[fixture]; refs[mid] = [{"artifact_type": "oracle_value", "fixture_id": fixture, "game_id": x["game_id"]}]
    for mid, category in (("restoration-unique-optimum-v1", "unique-optimum"), ("restoration-tied-optima-v1", "tied-optima"),
                          ("restoration-dominated-v1", "dominated-safe"), ("restoration-none-feasible-v1", "no-feasible")):
        x = restoration_by_category[category]; refs[mid] = [{"artifact_type": "restoration", "case_id": x["case_id"], "game_id": x["game_id"], "category": category}]
    x = restoration_by_category["compound-repair"]
    refs["repair-compound-v1"] = refs["repair-compound-v1"] + [{"artifact_type": "restoration", "case_id": x["case_id"], "game_id": x["game_id"], "category": "compound-repair"}]
    for mid, fixture in (("timing-before-deadline-v1", "before-deadline"), ("timing-last-usable-v1", "last-usable"),
                         ("timing-after-failure-v1", "too-late"), ("intervention-round-0-v1", "before-deadline"),
                         ("intervention-round-1-v1", "last-usable"), ("intervention-too-late-v1", "too-late")):
        x = timing_by_id[fixture]; refs[mid] = [{"artifact_type": "timing", "fixture_id": fixture, "game_id": x["game_id"]}]
    for mid, fixture in (("probe-useful-v1", "useful-short"), ("probe-delay-multiple-v1", "useful-delay3"),
                         ("probe-useless-v1", "useless"), ("probe-too-late-v1", "too-late")):
        x = probe_by_id[fixture]; refs[mid] = [{"artifact_type": "probe", "fixture_id": fixture, "game_id": x["game_id"]}]
    refs["probe-delay-multiple-v1"] = [{"artifact_type": "probe", "fixture_id": fixture, "game_id": probe_by_id[fixture]["game_id"]}
                                        for fixture in ("useful-short", "useful-long", "useful-delay3")]
    refs["epsilon-neighboring-v1"] = [{"artifact_type": "oracle_value", "fixture_id": fixture, "game_id": probability_by_id[fixture]["game_id"]}
                                       for fixture in ("quarter", "third-boundary", "half-above-third")]
    for mid, fixture in (("probability-zero-v1", "zero"), ("probability-one-v1", "one"), ("minimax-nontrivial-v1", "minimax-half")):
        x = probability_by_id[fixture]; refs[mid] = [{"artifact_type": "oracle_value", "fixture_id": fixture, "game_id": x["game_id"]}]
    for mid, category, endpoint in (("horizon-1-v1", "horizon-only", "parent"), ("horizon-2-v1", "horizon-only", "child"),
                                    ):
        x = pair_by_category[category]; refs[mid] = [{"artifact_type": "matched_pair", "pair_id": x["pair_id"], "game_id": x[f"{endpoint}_game_id"]}]
    for mid, fixture in (("horizon-3-v1", "useful-long"), ("horizon-4-v1", "useful-delay3"),
                         ("probe-delay-1-v1", "useful-short"), ("probe-delay-2-v1", "useful-long"), ("probe-delay-3-v1", "useful-delay3")):
        x = probe_by_id[fixture]; refs[mid] = [{"artifact_type": "probe", "fixture_id": fixture, "game_id": x["game_id"]}]
    # Corpus mechanics are evidenced by independently verified Stage-3 ledgers.
    for mid, key in (("complexity-rejected-fixture-v1", "complexity"), ("isomorphism-unresolved-fixture-v1", "unresolved"),
                     ("unique-resolved-v1", "development"), ("duplicate-exact-v1", "exact_duplicate"),
                     ("duplicate-isomorphic-v1", "isomorphic_duplicate")):
        if key in corpus_refs:
            refs[mid] = [{"artifact_type": "corpus", "fixture": key, **corpus_refs[key]}]
    rows = [{"mechanism_id": mid, "observed": bool(refs.get(mid)), "evidence_refs": refs.get(mid, []),
             "notes": "mechanically validated Stage-4 evidence" if refs.get(mid) else "no evidence"} for mid in spec.required_mechanisms]
    observed = [x["mechanism_id"] for x in rows if x["observed"]]; missing = [x["mechanism_id"] for x in rows if not x["observed"]]
    payload = {"version": STAGE4_VERSION, "mechanisms": rows, "observed_count": len(observed), "missing_count": len(missing),
               "observed_mechanisms": observed, "missing_mechanisms": missing, "coverage_complete": not missing}
    return {**payload, "fingerprint": _fingerprint(payload)}


def validate_mechanism_evidence(spec: MechanismCoverageSpec, report: Mapping[str, Any], registry: Mapping[str, Any],
                                probability_fixtures, restoration_fixtures, probe_fixtures, timing_fixtures, corpus_refs) -> dict[str, Any]:
    """Reject stale, missing, or semantically incorrect evidence references."""
    expected = build_mechanism_evidence(spec, registry, probability_fixtures, restoration_fixtures, probe_fixtures, timing_fixtures, corpus_refs)
    failures = []
    if canonical_json(report) != canonical_json(expected): failures.append("evidence report does not reproduce")
    if not validate_pair_registry(registry)["passed"]: failures.append("pair registry invalid")
    for fixture in probability_fixtures:
        game = Game.from_dict(fixture["game"])
        if game_id(game) != fixture["game_id"] or solve(game).to_dict() != fixture["oracle"]: failures.append(f'probability:{fixture["fixture_id"]}')
    # Every restoration evaluation, cost, and category is derived again.
    for row in restoration_fixtures:
        game = Game.from_dict(row["game"])
        restorations = tuple(Restoration(x["name"], frozenset(x["remove_adversary_actions"]), frozenset(x["remove_controller_actions"]),
                                         tuple(tuple(y) for y in x["observation_overrides"]),
                                         tuple((a, tuple(rounds)) for a, rounds in x["availability_overrides"])) for x in row["restorations"])
        from enforceability import optimal_restoration
        result = optimal_restoration(game, restorations)
        evaluations = [{"candidate_id": e.restoration.name, "oracle": e.game_result.to_dict(), "cost": str(e.cost)} for e in result.evaluations]
        if evaluations != row["evaluations"]: failures.append(f'restoration:{row["case_id"]}:evaluations')
        safe = [x for x in evaluations if x["oracle"]["threshold_satisfied"]]; costs = [Fraction(x["cost"]) for x in safe]
        derived = set()
        if not safe: derived.add("no-feasible")
        if costs and costs.count(min(costs)) == 1: derived.add("unique-optimum")
        if costs and costs.count(min(costs)) > 1: derived.add("tied-optima")
        if costs and any(x > min(costs) for x in costs): derived.add("dominated-safe")
        if row["case_id"] == "compound" and [x["oracle"]["threshold_satisfied"] for x in evaluations] == [False, False, True]: derived.add("compound-repair")
        if set(row["categories"]) != derived: failures.append(f'restoration:{row["case_id"]}:categories')
    for fixture in probe_fixtures:
        game = Game.from_dict(fixture["game"])
        valid = game_id(game) == fixture["game_id"] and solve(game).to_dict() == fixture["oracle"]
        initial = tuple(game.initial_states)
        valid &= len(initial) == 2 and game.observation_map[initial[0]] == game.observation_map[initial[1]]
        endpoints = []
        for hidden in range(2):
            state = f"q{hidden}"
            for step in range(fixture["probe_delay"]):
                action = "probe" if step == 0 else "wait"
                outcome = game.transitions[state, action, "a0"]
                if len(outcome) != 1 or outcome[0][1] != 1: valid = False; break
                state = outcome[0][0]
            endpoints.append(state)
        expected_delay_states = {f"d{stage}_{hidden}" for stage in range(1, fixture["probe_delay"]) for hidden in range(2)}
        valid &= set(fixture["delay_states"]) == expected_delay_states
        if fixture["fixture_id"].startswith("useful"):
            valid &= endpoints == ["p0", "p1"] and game.observation_map["p0"] != game.observation_map["p1"] and fixture["oracle"]["threshold_satisfied"]
            raw = game.to_dict(); raw["observation_map"]["p1"] = raw["observation_map"]["p0"]
            neutral = Game.from_dict(raw)
            valid &= not solve(neutral).threshold_satisfied
        elif fixture["fixture_id"] == "useless":
            valid &= endpoints == ["p0", "p1"] and game.observation_map["p0"] == game.observation_map["p1"] and not fixture["oracle"]["threshold_satisfied"]
        elif fixture["fixture_id"] == "too-late":
            valid &= endpoints == ["x", "x"] and game.observation_map["p0"] != game.observation_map["p1"] and not fixture["oracle"]["threshold_satisfied"]
        else:
            valid = False
        if not valid:
            failures.append(f'probe:{fixture["fixture_id"]}')
    timing_by_id = {x["fixture_id"]: x for x in timing_fixtures}
    if set(timing_by_id) != {"before-deadline", "last-usable", "too-late"}:
        failures.append("timing:fixture set")
    else:
        games = {key: Game.from_dict(value["game"]) for key, value in timing_by_id.items()}
        structural = []
        for key, game in games.items():
            raw = game.to_dict(); raw["action_availability"] = {}
            structural.append(canonical_json(raw))
            if game_id(game) != timing_by_id[key]["game_id"] or solve(game).to_dict() != timing_by_id[key]["oracle"]:
                failures.append(f"timing:{key}:artifact")
        if len(set(structural)) != 1 or [timing_by_id[x]["intervention_round"] for x in ("before-deadline", "last-usable", "too-late")] != [0, 1, 2]:
            failures.append("timing:unrelated structure")
        if [timing_by_id[x]["oracle"]["failure_probability"] for x in ("before-deadline", "last-usable", "too-late")] != ["0", "0", "1"]:
            failures.append("timing:deadline relationship")
        last = games["last-usable"]
        after_wait = last.transitions["q0", "wait", "a0"]
        after_act = last.transitions["q1", "act", "a0"]
        late = games["too-late"].transitions["q1", "wait", "a0"]
        if after_wait != (("q1", Fraction(1)),) or after_act != (("r", Fraction(1)),) or late != (("x", Fraction(1)),):
            failures.append("timing:formal trajectory")
    return {"passed": not failures, "failures": failures}


def build_benchmark_freeze(development: str | Path, evaluation: str | Path, mechanisms: MechanismCoverageSpec,
                           *, complexity: str | Path, unresolved: str | Path, pair_registry: Mapping[str, Any],
                           evidence_report: Mapping[str, Any], overlap_report: Mapping[str, Any]) -> dict[str, Any]:
    """Create date-independent formal split metadata, failing on contamination."""

    _, dev_manifest = _load_artifact(development)
    eva_ledger, eva_manifest = _load_artifact(evaluation)
    _, complexity_manifest = _load_artifact(complexity); _, unresolved_manifest = _load_artifact(unresolved)
    overlap = audit_corpus_overlap(development, evaluation)
    if not overlap["passes"] or canonical_json(overlap) != canonical_json(overlap_report):
        raise ValueError("forbidden development/evaluation overlap")
    retained = [x for x in eva_ledger if (x.get("retention") or {}).get("retained")]
    payload = {
        "split_construction_version": STAGE4_VERSION,
        "development_corpus_fingerprint": dev_manifest["corpus_fingerprint"],
        "evaluation_corpus_fingerprint": eva_manifest["corpus_fingerprint"],
        "complexity_fixture_corpus_fingerprint": complexity_manifest["corpus_fingerprint"],
        "complexity_fixture_spec_fingerprint": complexity_manifest["corpus_spec_fingerprint"],
        "unresolved_fixture_corpus_fingerprint": unresolved_manifest["corpus_fingerprint"],
        "unresolved_fixture_spec_fingerprint": unresolved_manifest["corpus_spec_fingerprint"],
        "retained_evaluation_game_ids": [x["game_id"] for x in retained],
        "retained_resolved_evaluation_isomorphism_class_ids": [x["isomorphism"]["class_id"] for x in retained if x["isomorphism"]["status"] == "RESOLVED"],
        "mechanism_spec_fingerprint": mechanisms.fingerprint,
        "mechanism_evidence_report_fingerprint": evidence_report["fingerprint"],
        "matched_pair_registry_fingerprint": pair_registry["fingerprint"],
        "overlap_report_fingerprint": _fingerprint(overlap_report),
        "required_mechanism_ids": list(mechanisms.required_mechanisms),
        "observed_mechanism_ids": list(evidence_report["observed_mechanisms"]),
        "missing_mechanism_ids": list(evidence_report["missing_mechanisms"]),
        "coverage_complete": evidence_report["coverage_complete"],
        "evaluation_oracle_status_counts": {s: sum(x["oracle"]["status"] == s for x in retained) for s in ("WINNING", "LOSING")},
        "deterministic_build_inputs": {"development_spec_fingerprint": dev_manifest["corpus_spec_fingerprint"], "evaluation_spec_fingerprint": eva_manifest["corpus_spec_fingerprint"],
                                       "complexity_spec_fingerprint": complexity_manifest["corpus_spec_fingerprint"], "unresolved_spec_fingerprint": unresolved_manifest["corpus_spec_fingerprint"]},
    }
    return {**payload, "benchmark_freeze_fingerprint": hashlib.sha256(canonical_json(payload).encode()).hexdigest()}
