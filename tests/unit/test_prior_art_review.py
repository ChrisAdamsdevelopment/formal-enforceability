from pathlib import Path

from enforceability.prior_art_review import REQUIRED_CLAIMS, REQUIRED_SOURCES, validate


def test_collision_matrix_is_complete_and_canonical() -> None:
    path = Path("artifacts/prior-art-review-v1/collision-matrix.json")
    data, fingerprint = validate(path)
    assert REQUIRED_SOURCES <= {source["id"] for source in data["sources"]}
    assert set(data["claim_verdicts"]) == REQUIRED_CLAIMS
    assert len(fingerprint) == 64
