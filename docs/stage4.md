# Stage 4: formal evaluation freeze

Stage 4 adds an outcome-independent, machine-readable mechanism matrix, two
seed-disjoint corpus specifications, and separate deliberately bounded audit
fixtures. The matrix declares intended coverage; mechanically derived audit
reports remain the authority for observed coverage.

Development uses seeds beginning at 0 and evaluation uses seeds beginning at
101. More importantly, `audit_corpus_overlap` compares exact game IDs and
resolved exact-isomorphism class IDs. Seed disjointness is not statistical
independence. Same-family/template-relative overlap is reported and allowed.

The complexity fixture uses Stage 2's pre-solution rejection path with
`max_policy_profiles = 1`; its ledger has no oracle result. The unresolved
fixture uses `max_permutations = 1` locally and retains its solved game under
the declared unresolved policy without inventing a class ID. Normal corpus
limits are unchanged.

All probabilities and epsilon values are rational strings. Pair-specific
intervention improvement is `V(parent) - V(child)`: positive means the child
has lower exact failure probability. It is not a universal control margin.
Exact equality succeeds because the unchanged oracle rule is
`failure_probability <= epsilon`.

## Commands

```bash
PYTHONPATH=src python -m enforceability.corpus verify --spec corpus_specs/development-v1.json --corpus artifacts/development-v1
PYTHONPATH=src python -m enforceability.corpus verify --spec corpus_specs/evaluation-v1.json --corpus artifacts/evaluation-v1
PYTHONPATH=src python -m enforceability.benchmark audit-overlap --development artifacts/development-v1 --evaluation artifacts/evaluation-v1
PYTHONPATH=src python -m enforceability.benchmark verify-formal-freeze --development artifacts/development-v1 --evaluation artifacts/evaluation-v1 --mechanisms corpus_specs/stage4-mechanisms-v1.json --freeze artifacts/formal-evaluation-freeze-v1.json
```

The small freeze reports gaps rather than hiding generation rejection or
isomorphism collapse. Listed mechanism coverage does not prove completeness,
synthetic stochasticity is not real model uncertainty, and this corpus does
not measure deployment risk. Natural-language rendering should remain delayed
until every intended matched transformation and restoration contrast is frozen.

> The formal evaluation freeze prevents later model-facing choices from silently changing which mathematical cases are evaluated. It does not establish that the formal cases represent real AI deployments.
