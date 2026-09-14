"""Reproducible primary-versus-independent bounded validation report."""
from __future__ import annotations

from dataclasses import asdict, dataclass
import json

from enforceability.independent_validation import (
    DEFAULT_TOLERANCE, EXTERNAL_BACKEND, VALIDATOR_VERSION, validate_game,
)
from enforceability.oracle import solve as primary_solve
from enforceability.validation_cases import (
    deterministic_family, hand_fixtures, multi_round_stochastic, probabilistic_family,
)


@dataclass(frozen=True, slots=True)
class ValidationReport:
    validator_version: str
    external_backend: str
    numerical_tolerance: float
    total_cases: int
    hand_fixture_cases: int
    deterministic_exhaustive_cases: int
    probabilistic_exhaustive_cases: int
    multi_round_cases: int
    maximum_value_error: float
    maximum_primal_dual_gap: float
    value_mismatches: int
    status_disagreements: int
    numerically_unresolved_threshold_cases: int
    result: str

    def to_dict(self):
        return asdict(self)


def run_cross_validation(tolerance: float = DEFAULT_TOLERANCE) -> ValidationReport:
    groups = (hand_fixtures(), deterministic_family(), probabilistic_family(), (("multi-round-stochastic", multi_round_stochastic()),))
    maximum_error = 0.0
    maximum_gap = 0.0
    mismatches = 0
    disagreements = 0
    unresolved = 0
    for cases in groups:
        for _name, game in cases:
            independent = validate_game(game, tolerance=tolerance)
            # Deliberately run the primary only after the independent answer exists.
            primary = primary_solve(game)
            error = abs(independent.value - float(primary.failure_probability))
            maximum_error = max(maximum_error, error)
            maximum_gap = max(maximum_gap, independent.primal_dual_gap)
            mismatches += error > tolerance
            classification = independent.classification(game.epsilon)
            if classification == "UNRESOLVED":
                unresolved += 1
            else:
                disagreements += classification != primary.status.value
    counts = tuple(len(group) for group in groups)
    passed = mismatches == 0 and disagreements == 0 and maximum_gap <= tolerance
    return ValidationReport(
        VALIDATOR_VERSION, EXTERNAL_BACKEND, tolerance, sum(counts), counts[0], counts[1], counts[2], counts[3],
        maximum_error, maximum_gap, mismatches, disagreements, unresolved, "PASS" if passed else "FAIL",
    )


def main() -> None:
    report = run_cross_validation()
    print(json.dumps(report.to_dict(), sort_keys=True, indent=2))
    if report.result != "PASS":
        raise SystemExit(1)


if __name__ == "__main__":
    main()
