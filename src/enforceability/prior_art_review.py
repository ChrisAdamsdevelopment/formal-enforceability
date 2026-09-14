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


def repository_root() -> Path:
    return Path(__file__).resolve().parents[2]


def validate(path: Path) -> tuple[dict, str]:
    raw = path.read_bytes()
    data = json.loads(raw)
    assert data["review_version"] == "prior-art-review-v1"
    assert data["project_commit"] == "ff706903ca742d516d4ad58e0d665c36de51be97"
    assert "generated_at" not in data and "generated-at" not in data
    sources = data["sources"]
    ids = [source["id"] for source in sources]
    assert len(ids) == len(set(ids)), "source IDs must be unique"
    assert REQUIRED_SOURCES <= set(ids), "a required primary source is absent"
    assert ids == sorted(ids), "sources must be deterministically sorted by stable ID"
    for source in sources:
        assert source["primary_source_locator"].startswith("https://")
        assert source["theorem_assumption_references"], source["id"]
        assert source["version_specific_logical_wording"].strip()
        assert source["move_timing"].strip()
        assert source["learner_observes"].strip()
        assert set(source["interface_mapping"]) == {"I_public", "I_node", "I_full"}
        for item in source["interface_mapping"].values():
            assert item["status"] in MAPPINGS
            assert item["argument"].strip()
        for item in source["proposition_mapping"].values():
            assert item["collision_status"] in COLLISIONS
            assert item["reason"].strip()
            assert item["primary_source_locator"] == source["primary_source_locator"]

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
        assert all(reference in joined for reference in required), source_id
        assert "main theorem" not in joined.lower(), source_id
    assert by_id["li-thesis-2025"]["primary_source_locator"] == (
        "https://personal.ntu.edu.sg/boan/thesis/Li_Shuxin_PhD_Thesis.pdf"
    )
    chen_version = by_id["chen-et-al-2605.13025"]["version_reviewed"]
    assert "arXiv v1" in chen_version and "13 May 2026" in chen_version
    verdicts = data["claim_verdicts"]
    assert set(verdicts) == REQUIRED_CLAIMS
    for verdict in verdicts.values():
        assert verdict["score"] in range(6)
        assert verdict["collision_status"] in COLLISIONS
        assert verdict["evidence_that_moves_score_up"].strip()
        assert verdict["evidence_that_moves_score_down"].strip()
    canonical = json.dumps(data, indent=2, sort_keys=True, ensure_ascii=False) + "\n"
    assert raw.decode() == canonical, "matrix must use canonical sorted/indented JSON"
    return data, hashlib.sha256(raw).hexdigest()


def main() -> None:
    path = repository_root() / "artifacts/prior-art-review-v1/collision-matrix.json"
    data, fingerprint = validate(path)
    print(f"verified {len(data['sources'])} sources and {len(data['claim_verdicts'])} claim verdicts")
    print(f"sha256:{fingerprint}")


if __name__ == "__main__":
    main()
