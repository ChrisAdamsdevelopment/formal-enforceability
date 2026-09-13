# Formal Enforceability

A deliberately small Python 3.11+ exact-rational reference implementation for
finite-horizon probabilistic, one-sided partially observed reach-avoid games and
finite structural restorations. Deterministic sure safety remains a special case. See
[`docs/formal_model.md`](docs/formal_model.md) for the precise semantics.

```bash
python -m pip install -e '.[test]'
ruff check src tests
python -m pytest
```

Stage 3 adds the entirely formal, deterministic audited-corpus pipeline described
in [`docs/corpus.md`](docs/corpus.md): complete candidate ledgers, exact
identifier-renaming isomorphism, declared retention, and a rebuildable freeze.

Stage 4's formal split and benchmark-freeze workflow is documented in
[`docs/stage4.md`](docs/stage4.md).
