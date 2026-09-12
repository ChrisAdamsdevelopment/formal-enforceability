# Stage-3 formal corpus audit and freeze

Stage 3 is formal only: specification → procedural candidates → exact oracle → audits and exact renaming analysis → deterministic retention → immutable manifest.

> The corpus is a controlled sample of formal games produced by declared synthetic generators. Its distributions do not estimate the frequency of safety mechanisms in real AI systems.

## CorpusSpec and complete ledger

`CorpusSpec` is frozen and strictly parsed. Required fields declare all component versions, ordered families and half-open seed ranges, complete generator parameter sets, complexity/isomorphism limits, retention, stratification, tie-break, and quotas. Unsupported versions and unknown or missing fields fail. Sorted compact JSON is canonical; its SHA-256 is the spec fingerprint. Candidate order is family order then seed order. There is no global or hidden sampling RNG.

Every attempted combination has one final state: `COMPLEXITY_REJECTED`, `GENERATION_ERROR`, `FILTERED_AFTER_SOLUTION`, `DUPLICATE_EXCLUDED`, `ISOMORPHIC_EXCLUDED`, `ISOMORPHISM_UNRESOLVED`, or `RETAINED`. Generation and solution are represented by populated fields rather than competing final states. Each record preserves the candidate key, full config and versions, config fingerprint, game ID, exact oracle/restoration results, descriptors, complexity calibration, isomorphism result, decision, stratum, tie-break, and exact reason.

## Formal isomorphism and duplicate taxonomy

Games are isomorphic exactly when bijections on state, controller-action, adversary-action, and observation IDs make their complete mathematical representations equal. Bijections preserve exact initial and transition probabilities, observation mapping, failure/recovery membership, horizon, epsilon, availability by round, legitimate rewards, action roles, timing, and schema version. Only `display_labels` are ignored.

`stage3.exact-permutation.v1` partitions states by failure/recovery/other role, enumerates every within-role state permutation and every action and observation permutation, serializes each renamed game, and selects the lexicographic minimum. Its class ID hashes the version and minimum. The declared `max_permutations` is checked before work; overflow produces typed `ISOMORPHISM_UNRESOLVED`, never a false “different”.

An **exact duplicate** shares the Stage-2 `game_id`. A **formal isomorphic duplicate** has a different ID but shares the exact class ID. **Template-relative similarity** merely means a common generator family and is descriptive, not duplication. Neither deduplication nor class separation establishes independence or fundamentally different safety problems.

## Retention and fingerprints

Policies explicitly select `retain_first` or `retain_all`; quotas are optional declared strata. The tie-break is the lowest canonical candidate key. There is no implicit 50/50 balance. The corpus fingerprint is SHA-256 of canonical JSON containing the complete canonical spec, ordered retained game IDs, and generator, schema, oracle, isomorphism, and retention versions. The ledger has a separate canonical SHA-256. These are reproducibility identifiers, not security attestations.

## Audits

Raw and retained distributions and per-family counts are separate. Coverage reports families/statuses, horizons, counts, aliasing and stochasticity; gaps are descriptors, not evidence of completeness. Configs and restoration results retain probe delay, intervention position, capability/restoration counts, tied/unique/no-feasible repairs, and information needed for mechanically matched intervention comparisons.

Transformation integrity requires a recomputed child ID, a ledger parent (or declared external artifact), equal generator version, canonical category, and equality of reported versus actual changed formal fields. Unexpected changes fail audit. The regression spec has no transformations and reports that explicitly.

Leakage risks are categorized as `SEMANTIC`, `REPRESENTATIONAL`, `PROVENANCE-ONLY`, and `ANSWER-DIRECT`. The report calls out names, ordering, terminal conventions, counts, restoration count, family/mode labels, and generator artifacts. A blacklist cannot prove absence of shortcuts. The audit-only neutral view deterministically maps input-order identifiers to `s0`, `c0`, `a0`, and `o0` without oracle results. It neither mutates the game nor changes its ID, and is weaker than exact isomorphism canonicalization.

Complexity calibration records estimated controller histories/profiles, actual oracle `explored_profiles`, thresholds, saturation, and overestimate ratios. Actual histories remain `null` because the oracle does not expose that measurement. Wall-clock samples are stored separately in `complexity-timing-diagnostics.json`; they are diagnostics only and excluded from reproducibility verification. Complexity estimates are operational protection, not conceptual difficulty.

## Freeze and verification

The checked-in freeze contains the spec, complete raw ledger, retained formal manifests, corpus manifest, audit, duplicate/isomorphism report, retention report, and timing diagnostics.

```bash
PYTHONPATH=src python -m enforceability.corpus build \
  --spec corpus_specs/regression-v1.json --output /tmp/regression-v1
PYTHONPATH=src python -m enforceability.corpus verify \
  --spec corpus_specs/regression-v1.json --corpus artifacts/regression-corpus-v1
```

Verification regenerates and loudly compares ledger fingerprint, retained IDs, corpus fingerprint, aggregate counts, and deterministic audit, duplicate, and retention outputs. It never overwrites the freeze.

Known biases include tiny stylized families, systematic names and terminal labels, fixed ordering, uniform initial distributions, repeated games across seeds, sparse stochastic coverage, and family-specific counts/modes. Balance does not estimate prevalence; coverage does not prove completeness; low leakage risk cannot prove no shortcuts; retained games do not represent deployments, real autonomous agents, or model behavior. Stage 3 assumes terminal-role partitioning is a sound invariant and unresolved cases must remain visible. Reproduce the freeze and expand declared mechanism coverage before introducing a separately versioned rendering stage.
