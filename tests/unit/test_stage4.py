from fractions import Fraction
import json

import pytest

from enforceability.corpus import CorpusBuildError, CorpusSpec, verify_corpus
from enforceability.stage4 import (MechanismCoverageSpec, audit_corpus_overlap, build_mechanism_evidence,
                                   intervention_value, validate_pair_registry)
from enforceability.stage4_fixtures import (build_pair_registry, build_probability_fixtures,
                                            build_probe_fixtures, build_restoration_fixtures)


def test_mechanism_matrix_is_deeply_immutable():
    source = {"dimension": ["neutral-id-v1"]}; spec = MechanismCoverageSpec("stage4.formal-freeze.v1", source)
    fingerprint = spec.fingerprint; source["dimension"].append("mutation-v1")
    assert spec.required_mechanisms == ("neutral-id-v1",) and spec.fingerprint == fingerprint
    with pytest.raises(TypeError): spec.dimensions["dimension"] = ()


def test_pair_registry_reproduces_positive_zero_and_compound_relations():
    registry = build_pair_registry(); assert validate_pair_registry(registry)["passed"]
    pairs = {x["category"]: x for x in registry["pairs"]}
    assert Fraction(pairs["positive-value-observation"]["exact_improvement"]) > 0
    assert Fraction(pairs["zero-value-observation"]["exact_improvement"]) == 0
    assert Fraction(pairs["positive-value-restriction"]["exact_improvement"]) > 0
    assert Fraction(pairs["zero-value-restriction"]["exact_improvement"]) == 0
    assert [x["oracle"]["threshold_satisfied"] for x in pairs["compound-repair"]["component_children"]] == [False, False]
    assert pairs["compound-repair"]["child_oracle"]["threshold_satisfied"]
    assert pairs["horizon-only"]["parent_oracle"]["failure_probability"] != pairs["horizon-only"]["child_oracle"]["failure_probability"]


def test_probability_threshold_fixtures_are_exact():
    fixtures = {x["fixture_id"]: x for x in build_probability_fixtures()}
    assert {fixtures[x]["oracle"]["failure_probability"] for x in ("zero", "third-boundary", "half-boundary", "quarter", "one")} == {"0", "1/3", "1/2", "1/4", "1"}
    assert [fixtures[x]["oracle"]["threshold_satisfied"] for x in ("quarter", "third-boundary", "half-above-third")] == [True, True, False]
    assert {fixtures[x]["game"]["epsilon"] for x in ("quarter", "third-boundary", "half-above-third")} == {"1/3"}
    assert fixtures["minimax-half"]["construction"] == "adversarial-minimax"


def test_restoration_categories_are_evidenced():
    rows = build_restoration_fixtures(); categories = {x for row in rows for x in row["categories"]}
    assert {"unique-optimum", "tied-optima", "dominated-safe", "no-feasible", "compound-repair"} <= categories
    compound = next(x for x in rows if x["case_id"] == "compound")
    assert [x["oracle"]["threshold_satisfied"] for x in compound["evaluations"]] == [False, False, True]


def test_probe_delays_have_explicit_distinct_trajectories():
    rows = build_probe_fixtures(); assert {x["probe_delay"] for x in rows} == {1, 2, 3}
    assert {len(x["delay_states"]) for x in rows} == {0, 2, 4}
    assert max(x["game"]["horizon"] for x in rows) == 4


def test_missing_evidence_keeps_coverage_incomplete():
    spec = MechanismCoverageSpec("stage4.formal-freeze.v1", {"x": ("missing-v1",)})
    report = build_mechanism_evidence(spec, build_pair_registry(), build_probability_fixtures(), build_restoration_fixtures(), build_probe_fixtures(), {})
    assert report["missing_mechanisms"] == ["missing-v1"] and not report["coverage_complete"]


def _copy_corpus(source, target):
    import shutil
    shutil.copytree(source, target)


def test_overlap_detects_exact_and_resolved_class_contamination(tmp_path):
    dev, eva = tmp_path / "dev", tmp_path / "eval"; _copy_corpus("artifacts/development-v1", dev); _copy_corpus("artifacts/evaluation-v1", eva)
    dev_row = next(x for x in json.loads((dev / "candidate-ledger.json").read_text()) if (x.get("retention") or {}).get("retained"))
    rows = json.loads((eva / "candidate-ledger.json").read_text()); row = next(x for x in rows if (x.get("retention") or {}).get("retained"))
    row["game_id"] = dev_row["game_id"]; row["isomorphism"] = dev_row["isomorphism"]; (eva / "candidate-ledger.json").write_text(json.dumps(rows))
    report = audit_corpus_overlap(dev, eva)
    assert report["exact_id_overlap"] and report["resolved_isomorphism_overlap"] and not report["passes"]


def test_stage3_corruption_is_rejected_before_stage4(tmp_path):
    corpus = tmp_path / "corpus"; _copy_corpus("artifacts/development-v1", corpus)
    retained = next((corpus / "retained").glob("*.json")); raw = json.loads(retained.read_text()); raw["formal_game"]["display_labels"] = {"tampered": "yes"}; retained.write_text(json.dumps(raw))
    with pytest.raises(CorpusBuildError): verify_corpus(CorpusSpec.load("corpus_specs/development-v1.json"), corpus)


def test_intervention_value_accepts_frozen_oracle_shape():
    result = intervention_value({"failure_probability": "1/2", "threshold_satisfied": False}, {"failure_probability": "1/3", "threshold_satisfied": True})
    assert Fraction(result["improvement"]) == Fraction(1, 6) and result["threshold_crossing"]
