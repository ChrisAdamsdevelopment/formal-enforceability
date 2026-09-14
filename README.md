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
refinement only inside the certifiably-WINNING branch. A deterministic
[Stage 6A pilot](docs/stage6-pilot-design.md) is the next experimental gate;
no frontier-model evaluation has started, and the canonical-interface witness
gap documented there remains a blocker.
