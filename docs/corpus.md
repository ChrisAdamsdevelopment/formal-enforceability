# Stage-3 formal corpus audit and freeze

Stage 3 is formal only: specification → candidates → exact oracle → structural and duplicate audit → declared retention → frozen corpus.

> The corpus is a controlled sample of formal games produced by declared synthetic generators. Its distributions do not estimate the frequency of safety mechanisms in real AI systems.

## Immutable specification and complete provenance

`CorpusSpec` strictly declares all component versions, ordered families and half-open seed ranges, complete generator parameters, complexity and exact-isomorphism limits, retention rules, supported stratification fields, canonical `|`-separated quota keys, and the `candidate_key` tie-break. Unsupported versions, fields, policies, or strata fail. Nested mappings/lists are recursively copied into read-only mappings/tuples; serialization explicitly thaws a copy. Sorted compact JSON and SHA-256 define the fingerprint. This is semantic immutability, not a security boundary.

Before validation, every attempt records family, seed, generator version, limits, exact supplied parameters, and its attempted-config fingerprint. Valid and complexity-rejected attempts additionally record normalized configuration and its fingerprint. Thus configuration errors and complexity rejections remain reproducible from the ledger.

`max_generated_candidates` is a hard corpus-build bound over the total attempted seed/configuration combinations. The builder sums every half-open seed range and rejects an over-limit specification before creating the output directory, invoking generation, or calling the oracle; it never processes a partial prefix.

## Raw classification before retention

The pipeline first generates, solves, checks emitted component versions, and performs exact isomorphism. It then sorts solved candidates by canonical candidate key and classifies the entire raw set, before any sampling:

1. same game ID → `EXACT_DUPLICATE`;
2. otherwise same resolved class → `FORMAL_ISOMORPHIC_DUPLICATE`;
3. otherwise unresolved canonicalization → `ISOMORPHISM_UNRESOLVED`;
4. otherwise → `UNIQUE`.

Each relation names its lowest-key representative when known. Exact and formal-isomorphic categories are disjoint. Only after classification are category policies and quotas applied, again in candidate-key order. Exact and isomorphic policies accept `retain_first` or `retain_all`; unresolved accepts `retain_all` or `exclude`. Retained unresolved artifacts remain marked unresolved. Raw statistics derive from classification/isomorphism results, while retained statistics derive from dispositions, so quotas cannot rewrite raw duplication facts. Retention semantics are version `stage3.deterministic-retention.v2`.

## Exact formal isomorphism

Two games are isomorphic exactly when independent bijections on state, controller-action, adversary-action, and observation IDs preserve exact initial/transition probabilities, observations, failure/recovery roles, horizon, epsilon, per-round availability, rewards, timing, action roles, and schema version. Only display labels are ignored. Algorithm `stage3.exact-permutation.v1` is unchanged: partition states by failure/recovery/other role, enumerate every role-compatible state and every action/observation permutation, and choose lexicographically minimal canonical JSON. The versioned hash identifies the class. If the declared permutation bound would be exceeded, it returns typed `ISOMORPHISM_UNRESOLVED`, never false non-equivalence.

Exact duplicates share `game_id`; formal-isomorphic duplicates have different IDs but the same resolved class; template-relative similarity is descriptive family membership only. None implies statistical independence or fundamentally distinct safety problems.

## Data-derived audits

The audit contains deterministic status contingency tables for family and mode; state/controller/adversary counts, horizon, ambiguous classes, restoration count, and stochastic branching; identifier-prefix signatures, terminal naming, and ordering-role patterns. Each row gives `WINNING`, `LOSING`, support, and descriptive `status_pure_in_this_corpus`. Purity is not proof of leakage or predictive validity. Oracle/restoration fields are explicitly answer-direct and separated from merely correlated provenance, semantic, and representational fields. Relevant naming diagnostics are repeated on the oracle-independent neutralized `s0/c0/a0/o0` view, which never mutates the original or its ID.

Coverage mechanically reports all-six-family and both-status flags, horizons, state/action counts, aliasing, deterministic/stochastic modes, probe delays, timing positions, adversary capabilities, restoration counts, inferable tied-optimal/no-feasible cases, matched-pair count, complexity rejections, unresolved canonicalizations, and explicit gaps. Complexity records estimates, actual `explored_profiles`, thresholds, saturation, and ratios. Actual history counts remain null because the oracle does not expose them. Nondeterministic wall-clock diagnostics are separate and never fingerprinted.

Matched-pair validation recomputes child IDs, versions, categories, parent availability, and exact changed fields. Unexpected differences fail.

## Fingerprints and frozen verification

The corpus fingerprint hashes canonical JSON containing the complete spec, ordered retained IDs, and verified generator/schema/oracle/isomorphism/retention versions. The ledger fingerprint hashes its canonical records. These are reproducibility identifiers, not attestations.

Verification regenerates into a temporary directory, but independently validates the actual frozen files: complete canonical equality of the frozen and regenerated corpus manifests; canonical frozen spec and manifest fingerprint; frozen ledger recomputation and three-way fingerprint equality; exact retained filename set; ledger-to-manifest IDs; recomputed formal game IDs; canonical equality of every frozen and regenerated retained manifest; deterministic reports; and timing-diagnostic schema/key coverage. Complete manifest equality covers version declarations, the non-attestation flag, and future deterministic fields in addition to targeted diagnostic checks. Missing, extra, unparsable, or corrupt artifacts fail loudly. Timing values alone are intentionally not compared.

```bash
PYTHONPATH=src python -m enforceability.corpus build \
  --spec corpus_specs/regression-v1.json --output /tmp/regression-v1
PYTHONPATH=src python -m enforceability.corpus verify \
  --spec corpus_specs/regression-v1.json --corpus artifacts/regression-corpus-v1
```

## Limitations and next step

The freeze remains tiny and stylized, with systematic names, fixed ordering, uniform initialization, seed-insensitive templates, a single horizon, and no stochastic, transformed, rejected, or unresolved retained examples. Balance does not estimate prevalence; coverage does not prove completeness; low observed leakage risk does not prove absence of shortcuts; complexity is not conceptual difficulty; retained games do not represent deployments, agents, or model behavior. Reproduce this fingerprint and expand the declared formal mechanism coverage before adding any separately versioned rendering layer.
