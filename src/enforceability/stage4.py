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
from typing import Any, Mapping

from enforceability.generation import canonical_json

STAGE4_VERSION = "stage4.formal-freeze.v1"


@dataclass(frozen=True, slots=True)
class MechanismCoverageSpec:
    """Versioned, outcome-independent list of required formal mechanisms."""

    version: str
    dimensions: Mapping[str, tuple[str, ...]]

    @classmethod
    def load(cls, path: str | Path) -> "MechanismCoverageSpec":
        raw = json.loads(Path(path).read_text())
        if set(raw) != {"version", "dimensions"} or raw["version"] != STAGE4_VERSION:
            raise ValueError("unsupported mechanism coverage specification")
        dimensions = {str(k): tuple(v) for k, v in raw["dimensions"].items()}
        identifiers = [item for values in dimensions.values() for item in values]
        if not dimensions or len(identifiers) != len(set(identifiers)):
            raise ValueError("mechanism identifiers must be globally unique")
        if any(not x or x.lower() != x or " " in x for x in identifiers):
            raise ValueError("mechanism identifiers must be stable lower-case tokens")
        return cls(raw["version"], dimensions)

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
    dev, eva = retained(dev), retained(eva)
    dev_ids = {x["game_id"] for x in dev}
    dev_classes = {x["isomorphism"]["class_id"] for x in dev if (x.get("isomorphism") or {}).get("status") == "RESOLVED"}
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
    }
    report["passes"] = not report["exact_id_overlap"] and not report["resolved_isomorphism_overlap"]
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


def build_benchmark_freeze(development: str | Path, evaluation: str | Path,
                           mechanisms: MechanismCoverageSpec) -> dict[str, Any]:
    """Create date-independent formal split metadata, failing on contamination."""

    _, dev_manifest = _load_artifact(development)
    eva_ledger, eva_manifest = _load_artifact(evaluation)
    overlap = audit_corpus_overlap(development, evaluation)
    if not overlap["passes"]:
        raise ValueError("forbidden development/evaluation overlap")
    retained = [x for x in eva_ledger if (x.get("retention") or {}).get("retained")]
    payload = {
        "split_construction_version": STAGE4_VERSION,
        "development_corpus_fingerprint": dev_manifest["corpus_fingerprint"],
        "evaluation_corpus_fingerprint": eva_manifest["corpus_fingerprint"],
        "retained_evaluation_game_ids": [x["game_id"] for x in retained],
        "retained_resolved_evaluation_isomorphism_class_ids": [x["isomorphism"]["class_id"] for x in retained if x["isomorphism"]["status"] == "RESOLVED"],
        "mechanism_spec_fingerprint": mechanisms.fingerprint,
        "formal_mechanism_coverage": {k: list(v) for k, v in mechanisms.dimensions.items()},
        "evaluation_oracle_status_counts": {s: sum(x["oracle"]["status"] == s for x in retained) for s in ("WINNING", "LOSING")},
        "deterministic_build_inputs": {"development_spec_fingerprint": dev_manifest["corpus_spec_fingerprint"], "evaluation_spec_fingerprint": eva_manifest["corpus_spec_fingerprint"]},
    }
    return {**payload, "benchmark_freeze_fingerprint": hashlib.sha256(canonical_json(payload).encode()).hexdigest()}
