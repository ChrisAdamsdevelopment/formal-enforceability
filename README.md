# Formal Enforceability

A small exact-rational reference implementation for finite-horizon,
one-sided partially observed reach-avoid games and finite structural
restorations. See the [formal model](docs/formal_model.md).

```bash
python -m pip install -e '.[test]'
ruff check src tests
python -m pytest
validate-independent-oracle
verify-identifiability
```

## Project status

The repository now has exact formal semantics; an
[audited corpus/freeze](docs/corpus.md); the [Stage-4 formal benchmark](docs/stage4.md);
a [semantic representation freeze](docs/stage5-rendering.md); an
[independently cross-validated probabilistic oracle](docs/independent-probabilistic-validation.md);
a [value-preserving perfect-recall IIEFG reduction](docs/formal-iiefg-reduction.md);
the [threshold-identifiability theorem sprint](docs/threshold-identifiability.md);
and a [source-by-source prior-art collision review](docs/prior-art-collision.md).
The review selects **Paper Shape B (theory + benchmark)**: the finite examples
remain exact benchmark constructions, but their generic partial-identification
and feedback-dependent-coverage principles are not claimed as new.

The repository does not establish a new general identifiability theorem. The
[actionability formalization](docs/actionability.md) instead records the exact
identity `W = upper V`, the standard inequality `W <= R`, and a finite one-step
vertex reduction for a fixed policy. Uniform actionability is a hierarchical
refinement only inside the certifiably-WINNING branch. The
[small Stage 6A model-pilot plan](docs/stage6a-model-pilot.md) and execution
harness have a **merged v1.3 pre-execution freeze**. PR #14 merged on
2026-10-10 UTC as `3f4e71d585f981671419e2e14c450634ed3540de`, preserving
both historical v1.1 and v1.2 byte-for-byte.
V1.3 removes evaluator metadata from subject inputs and binds prompt hashes to
the exact transmitted input string. Real provider responses collected: **0**.
Provider execution requires review of the selected revision/hosted CI, exactly two
same-model medium/high configurations, a passing segregated non-benchmark canary
receipt, and explicit execution authorization. Local or hosted green tests alone
do not establish provider readiness. Start with [PROJECT_STATE](PROJECT_STATE.md),
[DECISION_LOG](DECISION_LOG.md), the [post-merge operator handoff](docs/stage6a-postmerge-status.md)
and [provider options/cost assumptions](docs/provider-options.md).
The [pre-merge audit](docs/stage6a-premerge-audit.md) remains a dated historical record.
