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
