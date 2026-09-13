from fractions import Fraction

from enforceability.stage4 import MechanismCoverageSpec, intervention_value


def test_mechanism_matrix_is_versioned_and_stable():
    spec = MechanismCoverageSpec.load("corpus_specs/stage4-mechanisms-v1.json")
    assert len(spec.fingerprint) == 64
    assert "epsilon-boundary-v1" in spec.dimensions["probability"]


def test_intervention_value_is_exact_and_boundary_inclusive():
    result = intervention_value(
        {"value": "1/2", "epsilon": "1/3"},
        {"value": "1/3", "epsilon": "1/3"},
    )
    assert Fraction(result["improvement"]) == Fraction(1, 6)
    assert result["threshold_crossing"] is True
