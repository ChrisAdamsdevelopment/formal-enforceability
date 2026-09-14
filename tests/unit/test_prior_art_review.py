import json
from pathlib import Path

import pytest

from enforceability.prior_art_review import REQUIRED_CLAIMS, REQUIRED_SOURCES, validate


def test_collision_matrix_is_complete_and_canonical() -> None:
    path = Path("artifacts/prior-art-review-v1/collision-matrix.json")
    data, fingerprint = validate(path)
    assert REQUIRED_SOURCES <= {source["id"] for source in data["sources"]}
    assert set(data["claim_verdicts"]) == REQUIRED_CLAIMS
    assert len(fingerprint) == 64


def test_validation_rejects_missing_source_proposition_mapping(tmp_path: Path) -> None:
    source_path = Path("artifacts/prior-art-review-v1/collision-matrix.json")
    data = json.loads(source_path.read_text())
    del data["sources"][0]["proposition_mapping"]["D"]
    invalid = tmp_path / "collision-matrix.json"
    invalid.write_text(json.dumps(data, indent=2, sort_keys=True, ensure_ascii=False) + "\n")
    with pytest.raises(ValueError, match="proposition mappings must cover A-D exactly"):
        validate(invalid)


def test_validation_uses_explicit_errors_not_assertions(tmp_path: Path) -> None:
    source_path = Path("artifacts/prior-art-review-v1/collision-matrix.json")
    data = json.loads(source_path.read_text())
    data["project_commit"] = "not-the-reviewed-commit"
    invalid = tmp_path / "collision-matrix.json"
    invalid.write_text(json.dumps(data, indent=2, sort_keys=True, ensure_ascii=False) + "\n")
    with pytest.raises(ValueError, match="unexpected project_commit"):
        validate(invalid)


def test_versioned_bomb_thesis_and_chen_records_are_pinned() -> None:
    data, _ = validate(Path("artifacts/prior-art-review-v1/collision-matrix.json"))
    sources = {source["id"]: source for source in data["sources"]}
    assert "if and only if" in sources["li-et-al-bomb-openreview-Re5iu0hBTs"]["version_specific_logical_wording"]
    assert "not recorded as an iff" in sources["li-et-al-oef-bomb-openreview-h8u0KWgg9C"]["version_specific_logical_wording"]
    assert sources["li-thesis-2025"]["primary_source_locator"].endswith("Li_Shuxin_PhD_Thesis.pdf")
    assert "only v1" in sources["chen-et-al-2605.13025"]["version_reviewed"]


def test_os_posg_evidence_interfaces_are_incomparable() -> None:
    data, _ = validate(Path("artifacts/prior-art-review-v1/collision-matrix.json"))
    source = next(source for source in data["sources"] if source["id"] == "horak-et-al-os-posg-2010.11243")
    assert source["interface_mapping"]["I_public"]["status"] == "INCOMPARABLE"
    assert source["interface_mapping"]["I_node"]["status"] == "INCOMPARABLE"
    assert source["interface_mapping"]["I_full"]["status"] == "EQUIVALENT"


def test_congestion_source_only_directly_supports_feedback_coverage_collision() -> None:
    data, _ = validate(Path("artifacts/prior-art-review-v1/collision-matrix.json"))
    source = next(source for source in data["sources"] if source["id"] == "cui-et-al-congestion-2210.13396")
    assert source["proposition_mapping"]["A"]["collision_status"] == "RELATED BUT FORMALLY DISTINCT"
    assert source["proposition_mapping"]["B"]["collision_status"] == "RELATED BUT FORMALLY DISTINCT"
    assert source["proposition_mapping"]["C"]["collision_status"] == "RELATED BUT FORMALLY DISTINCT"
    assert source["proposition_mapping"]["D"]["collision_status"] == (
        "KNOWN GENERAL PHENOMENON, PROJECT-SPECIFIC EXACT WITNESS"
    )
