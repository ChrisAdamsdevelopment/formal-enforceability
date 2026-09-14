"""Deterministic validation for the source-to-project collision matrix."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

MAPPINGS = {
    "EQUIVALENT",
    "SOURCE STRICTLY RICHER",
    "PROJECT INTERFACE STRICTLY RICHER",
    "INCOMPARABLE",
    "NOT YET ESTABLISHED",
}
COLLISIONS = {
    "DIRECTLY PROVED BY PRIOR WORK",
    "DIRECT COROLLARY AFTER EXPLICIT REDUCTION",
    "KNOWN GENERAL PHENOMENON, PROJECT-SPECIFIC EXACT WITNESS",
    "RELATED BUT FORMALLY DISTINCT",
    "NO MATERIAL COLLISION FOUND",
    "NOT ENOUGH INFORMATION TO DETERMINE",
}
REQUIRED_SOURCES = {
    "li-et-al-oef-2207.05285",
    "li-et-al-bomb-openreview-Re5iu0hBTs",
    "li-et-al-oef-bomb-openreview-h8u0KWgg9C",
    "li-thesis-2025",
    "cui-du-2201.03522",
    "yan-et-al-opre-2022.0342",
    "chen-et-al-2605.13025",
    "cui-et-al-congestion-2210.13396",
    "horak-et-al-os-posg-2010.11243",
    "dynamic-games-ijio-102915",
    "galichon-henry-2102.12249",
}
REQUIRED_CLAIMS = {"A", "B", "C", "D", "broader_threshold_question"}
REQUIRED_PROPOSITIONS = {"A", "B", "C", "D"}


def repository_root() -> Path:
    return Path(__file__).resolve().parents[2]


def _require(condition: bool, message: str) -> None:
    if not condition:
        raise ValueError(message)


def validate(path: Path) -> tuple[dict, str]:
    raw = path.read_bytes()
    data = json.loads(raw)
    _require(data["review_version"] == "prior-art-review-v1", "unexpected review_version")
    _require(
        data["project_commit"] == "ff706903ca742d516d4ad58e0d665c36de51be97",
        "unexpected project_commit",
    )
    _require("generated_at" not in data and "generated-at" not in data, "generated timestamp is forbidden")
    sources = data["sources"]
    ids = [source["id"] for source in sources]
    _require(len(ids) == len(set(ids)), "source IDs must be unique")
    _require(REQUIRED_SOURCES <= set(ids), "a required primary source is absent")
    _require(ids == sorted(ids), "sources must be deterministically sorted by stable ID")
    for source in sources:
        source_id = source["id"]
        _require(source["primary_source_locator"].startswith("https://"), f"{source_id}: invalid primary source locator")
        _require(bool(source["theorem_assumption_references"]), f"{source_id}: theorem/assumption references required")
        _require(bool(source["version_specific_logical_wording"].strip()), f"{source_id}: version wording required")
        _require(bool(source["move_timing"].strip()), f"{source_id}: move timing required")
        _require(bool(source["learner_observes"].strip()), f"{source_id}: learner-observes description required")
        _require(
            set(source["interface_mapping"]) == {"I_public", "I_node", "I_full"},
            f"{source_id}: interface mappings must cover I_public, I_node, and I_full exactly",
        )
        for item in source["interface_mapping"].values():
            _require(item["status"] in MAPPINGS, f"{source_id}: invalid interface mapping status")
            _require(bool(item["argument"].strip()), f"{source_id}: interface mapping argument required")
        _require(
            set(source["proposition_mapping"]) == REQUIRED_PROPOSITIONS,
            f"{source_id}: proposition mappings must cover A-D exactly",
        )
        for item in source["proposition_mapping"].values():
            _require(item["collision_status"] in COLLISIONS, f"{source_id}: invalid collision status")
            _require(bool(item["reason"].strip()), f"{source_id}: proposition-mapping reason required")
            _require(
                item["primary_source_locator"] == source["primary_source_locator"],
                f"{source_id}: proposition locator must match source locator",
            )

    by_id = {source["id"]: source for source in sources}
    exact_references = {
        "li-et-al-bomb-openreview-Re5iu0hBTs": {
            "Definition 4.1",
            "Definition 4.2",
            "Assumption 4.3",
            "Theorem 4.4",
            "Theorem 4.5",
            "Theorem 4.6",
        },
        "li-et-al-oef-bomb-openreview-h8u0KWgg9C": {
            "Definition 4.1",
            "Definition 4.2",
            "Assumption 4.3",
            "Theorem 4.4",
            "Theorem 4.5",
            "Theorem 4.6",
        },
        "li-thesis-2025": {
            "Chapter 6",
            "Section 6.5",
            "Assumption 6.3",
            "Assumption 6.4",
            "Table 6.2",
            "Theorem 6.6",
        },
    }
    for source_id, required in exact_references.items():
        joined = "\n".join(by_id[source_id]["theorem_assumption_references"])
        _require(all(reference in joined for reference in required), f"{source_id}: exact references incomplete")
        _require("main theorem" not in joined.lower(), f"{source_id}: generic main-theorem placeholder forbidden")
    _require(
        by_id["li-thesis-2025"]["primary_source_locator"]
        == "https://personal.ntu.edu.sg/boan/thesis/Li_Shuxin_PhD_Thesis.pdf",
        "thesis must use the official NTU primary locator",
    )
    chen_version = by_id["chen-et-al-2605.13025"]["version_reviewed"]
    _require(
        "arXiv v1" in chen_version and "13 May 2026" in chen_version,
        "Chen et al. must remain pinned to arXiv v1 and its submission date",
    )
    verdicts = data["claim_verdicts"]
    _require(set(verdicts) == REQUIRED_CLAIMS, "claim verdicts must match the required claim set exactly")
    for verdict in verdicts.values():
        _require(verdict["score"] in range(6), "claim score must be in 0..5")
        _require(verdict["collision_status"] in COLLISIONS, "invalid claim collision status")
        _require(bool(verdict["evidence_that_moves_score_up"].strip()), "missing score-up evidence")
        _require(bool(verdict["evidence_that_moves_score_down"].strip()), "missing score-down evidence")
    canonical = json.dumps(data, indent=2, sort_keys=True, ensure_ascii=False) + "\n"
    _require(raw.decode() == canonical, "matrix must use canonical sorted/indented JSON")
    return data, hashlib.sha256(raw).hexdigest()


def main() -> None:
    path = repository_root() / "artifacts/prior-art-review-v1/collision-matrix.json"
    data, fingerprint = validate(path)
    print(f"verified {len(data['sources'])} sources and {len(data['claim_verdicts'])} claim verdicts")
    print(f"sha256:{fingerprint}")


if __name__ == "__main__":
    main()
