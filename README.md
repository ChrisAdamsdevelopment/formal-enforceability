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
and the current [threshold-identifiability theorem sprint](docs/threshold-identifiability.md).

The repository does not yet establish a general theorem that passive public
evidence identifies strategic enforceability. No publication or novelty claim
is made here.
