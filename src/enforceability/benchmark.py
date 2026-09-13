"""Build and verify the complete Stage-4 formal dependency graph."""
import argparse
import json
from pathlib import Path

from enforceability.corpus import CorpusSpec, verify_corpus
from enforceability.generation import GeneratorConfig, canonical_json, generate, game_id
from enforceability.generation.core import GeneratedGame
from enforceability.corpus import canonicalize_isomorphism
from enforceability.stage4 import (MechanismCoverageSpec, audit_corpus_overlap, build_benchmark_freeze,
                                   build_mechanism_evidence, validate_mechanism_evidence, validate_pair_registry)
from enforceability.stage4_fixtures import (build_corpus_mechanics, build_pair_registry, build_probability_fixtures,
                                            build_probe_fixtures, build_restoration_fixtures, build_timing_fixtures)


def _read(path): return json.loads(Path(path).read_text())
def _write(path, value): Path(path).write_text(json.dumps(value, sort_keys=True, indent=2) + "\n")


def build_diversity_audit():
    families = ("observation-conflict", "authority-limitation", "probe", "timing", "capability-restriction", "mixed-restoration")
    rows = []
    for family in families:
        generated = []
        for seed in range(4):
            value = generate(GeneratorConfig(family, seed))
            if isinstance(value, GeneratedGame): generated.append(value.game)
        ids = {game_id(x) for x in generated}; classes = {canonicalize_isomorphism(x).class_id for x in generated}
        rows.append({"family": family, "attempted": 4, "generated": len(generated), "exact_unique": len(ids),
                     "resolved_isomorphism_classes": len(classes), "exact_collapse_ratio": str(len(ids)) + "/" + str(len(generated)),
                     "isomorphism_collapse_ratio": str(len(classes)) + "/" + str(len(generated)),
                     "seed_effective": len(ids) > 1})
    return {"version": "stage4.diversity-audit.v1", "families": rows}


def deterministic_fixture_mismatches(root):
    """Return checked-in Stage-4 fixtures that differ from reconstruction."""
    root = Path(root)
    constructors = {"matched-pair-registry.json": build_pair_registry, "probability-fixtures.json": build_probability_fixtures,
                    "restoration-fixtures.json": build_restoration_fixtures, "probe-fixtures.json": build_probe_fixtures,
                    "timing-fixtures.json": build_timing_fixtures, "diversity-audit.json": build_diversity_audit}
    return [name for name, constructor in constructors.items()
            if canonical_json(_read(root / name)) != canonical_json(constructor())]


def _corpus_refs(development, complexity, unresolved, mechanics):
    dev_manifest = _read(Path(development) / "corpus-manifest.json")
    complexity_manifest = _read(Path(complexity) / "corpus-manifest.json")
    unresolved_manifest = _read(Path(unresolved) / "corpus-manifest.json")
    return {"development": {"corpus_fingerprint": dev_manifest["corpus_fingerprint"], "game_id": dev_manifest["retained_game_ids"][0]},
            "complexity": {"corpus_fingerprint": complexity_manifest["corpus_fingerprint"], "candidate_state": "COMPLEXITY_REJECTED"},
            "unresolved": {"corpus_fingerprint": unresolved_manifest["corpus_fingerprint"], "candidate_state": "ISOMORPHISM_UNRESOLVED"},
            **mechanics}


def build(args):
    output = Path(args.artifacts); output.mkdir(parents=True, exist_ok=True)
    spec = MechanismCoverageSpec.load(args.mechanisms)
    pairs = build_pair_registry(); probability = build_probability_fixtures(); restorations = build_restoration_fixtures(); probes = build_probe_fixtures(); timing = build_timing_fixtures()
    mechanics = build_corpus_mechanics(pairs); refs = _corpus_refs(args.development, args.complexity, args.unresolved, mechanics)
    evidence = build_mechanism_evidence(spec, pairs, probability, restorations, probes, timing, refs)
    overlap = audit_corpus_overlap(args.development, args.evaluation)
    freeze = build_benchmark_freeze(args.development, args.evaluation, spec, complexity=args.complexity, unresolved=args.unresolved,
                                    pair_registry=pairs, evidence_report=evidence, overlap_report=overlap)
    for name, value in (("matched-pair-registry.json", pairs), ("probability-fixtures.json", probability),
                        ("restoration-fixtures.json", restorations), ("probe-fixtures.json", probes),
                        ("timing-fixtures.json", timing),
                        ("mechanism-evidence-report.json", evidence), ("overlap-report.json", overlap),
                        ("diversity-audit.json", build_diversity_audit()), ("formal-evaluation-freeze-v1.json", freeze)):
        _write(output / name, value)
    return freeze


def verify(args):
    for spec_path, corpus in ((args.development_spec, args.development), (args.evaluation_spec, args.evaluation),
                              (args.complexity_spec, args.complexity), (args.unresolved_spec, args.unresolved)):
        verify_corpus(CorpusSpec.load(spec_path), corpus)
    root = Path(args.artifacts); spec = MechanismCoverageSpec.load(args.mechanisms)
    pairs, probability = _read(root / "matched-pair-registry.json"), _read(root / "probability-fixtures.json")
    restorations, probes = _read(root / "restoration-fixtures.json"), _read(root / "probe-fixtures.json")
    timing = _read(root / "timing-fixtures.json")
    evidence, overlap = _read(root / "mechanism-evidence-report.json"), _read(root / "overlap-report.json")
    mechanics = build_corpus_mechanics(pairs); refs = _corpus_refs(args.development, args.complexity, args.unresolved, mechanics)
    mismatches = deterministic_fixture_mismatches(root)
    if mismatches: raise ValueError("deterministic Stage-4 fixture mismatch: " + str(mismatches))
    evidence_result = validate_mechanism_evidence(spec, evidence, pairs, probability, restorations, probes, timing, refs)
    if not evidence_result["passed"] or not evidence["coverage_complete"]: raise ValueError("mechanism evidence incomplete or invalid: " + str(evidence_result))
    actual = build_benchmark_freeze(args.development, args.evaluation, spec, complexity=args.complexity, unresolved=args.unresolved,
                                    pair_registry=pairs, evidence_report=evidence, overlap_report=overlap)
    if actual != _read(root / "formal-evaluation-freeze-v1.json"): raise ValueError("formal freeze mismatch")
    return {"verified": True, "coverage_complete": True, "pair_registry": validate_pair_registry(pairs),
            "benchmark_freeze_fingerprint": actual["benchmark_freeze_fingerprint"]}


def main():
    parser = argparse.ArgumentParser(prog="python -m enforceability.benchmark"); sub = parser.add_subparsers(dest="command", required=True)
    audit = sub.add_parser("audit-overlap"); audit.add_argument("--development", required=True); audit.add_argument("--evaluation", required=True)
    for command in (sub.add_parser("build-formal-freeze"), sub.add_parser("verify-formal-freeze")):
        for name in ("development", "evaluation", "complexity", "unresolved", "mechanisms", "artifacts"): command.add_argument("--" + name.replace("_", "-"), required=True)
        if command.prog.endswith("verify-formal-freeze"):
            for name in ("development_spec", "evaluation_spec", "complexity_spec", "unresolved_spec"): command.add_argument("--" + name.replace("_", "-"), required=True)
    args = parser.parse_args()
    result = audit_corpus_overlap(args.development, args.evaluation) if args.command == "audit-overlap" else build(args) if args.command == "build-formal-freeze" else verify(args)
    print(json.dumps(result, sort_keys=True, indent=2))
    if args.command == "audit-overlap" and not result["passes"]: raise SystemExit(1)


if __name__ == "__main__": main()
