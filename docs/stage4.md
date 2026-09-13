# Stage 4: mechanically evidenced formal freeze

Stage 4 keeps the outcome-independent mechanism requirements separate from observed evidence. `stage4-mechanisms-v1.json` is only the required matrix; `mechanism-evidence-report.json` links every observed identifier to a formal game, matched pair, restoration audit, oracle-value fixture, or independently verified Stage-3 corpus fixture. `coverage_complete` is derived from missing references and is never inferred from the size of the requirement list.

The frozen registry contains positive- and zero-value observation refinements, positive- and zero-value adversary restrictions, timing rescue, common-action addition, a horizon-only contrast, and an ordered compound repair. A separate staged-deadline fixture distinguishes intervention before the deadline, at round 1 (the last usable round), and at round 2 (after forced failure), with exact values `0`, `0`, and `1`. Improvement is the pair-specific exact rational `V(parent) - V(child)`; positive means lower child failure probability, not a universal control margin. Every child, oracle, changed-field list, compound component, and value is reproduced during verify.

Probability fixtures cover exact values 0, 1/4, 1/3, 1/2, and 1. The 1/2 matching-pennies fixture comes from adversarial minimax mixing. The common 1/3 epsilon set contains below, exact-boundary, and above cases, with equality satisfying the unchanged `failure_probability <= epsilon` rule. Probe fixtures contain explicit delay-stage trajectories for delays 1, 2, and 3 and meaningful horizons through 4. Restoration records recompute endogenous costs and classify unique, tied, dominated, infeasible, and compound cases.

Development uses seeds beginning at 0 and evaluation uses seeds beginning at 101, but seed disjointness is not independence. The overlap audit separately reports raw and retained exact-ID and exact-isomorphism-class overlap. Shared families are descriptive and allowed. Selection uses formal structure, exact oracle results, and deterministic rules only—never model behavior.

The complexity and unresolved fixtures retain local bounds and are bound into the freeze by both corpus and spec fingerprints. Full verification first runs Stage-3 verification on all four corpora, so corruption of a retained artifact fails before Stage-4 reconstruction. It then regenerates and canonically compares every deterministic Stage-4 fixture before independently checking the claimed semantics.

## Rebuild and verify

```bash
PYTHONPATH=src python -m enforceability.benchmark build-formal-freeze --development artifacts/development-v1 --evaluation artifacts/evaluation-v1 --complexity artifacts/complexity-fixture-v1 --unresolved artifacts/unresolved-fixture-v1 --mechanisms corpus_specs/stage4-mechanisms-v1.json --artifacts artifacts/stage4-formal-v1
PYTHONPATH=src python -m enforceability.benchmark verify-formal-freeze --development artifacts/development-v1 --evaluation artifacts/evaluation-v1 --complexity artifacts/complexity-fixture-v1 --unresolved artifacts/unresolved-fixture-v1 --mechanisms corpus_specs/stage4-mechanisms-v1.json --artifacts artifacts/stage4-formal-v1 --development-spec corpus_specs/development-v1.json --evaluation-spec corpus_specs/evaluation-v1.json --complexity-spec corpus_specs/complexity-fixture-v1.json --unresolved-spec corpus_specs/unresolved-fixture-v1.json
PYTHONPATH=src python -m enforceability.benchmark audit-overlap --development artifacts/development-v1 --evaluation artifacts/evaluation-v1
```

Formal mechanism coverage is not real-world diversity; synthetic stochasticity is not model uncertainty; disjoint isomorphism classes are not statistical independence; and the freeze does not measure deployment risk or validate its underlying model of reality.

> The formal evaluation freeze prevents later model-facing choices from silently changing which mathematical cases are evaluated. It does not establish that the formal cases represent real AI deployments.
