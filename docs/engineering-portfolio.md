# Engineering portfolio guide

**Focus:** Python evaluation infrastructure, exact reference answers, benchmark integrity, reproducible LLM experiments, and scientific software engineering.

Formal Enforceability is a finite-game reference implementation and evaluation research program. It combines exact-rational reach-avoid game semantics, reference oracles, benchmark construction, frozen prompts and evidence-aware model execution. It is **not** a general-purpose AI safety certification.

## What the implementation demonstrates

| Engineering challenge | Project approach | Inspectable starting point |
| --- | --- | --- |
| Defensible reference answers | Exact-rational model and independent probabilistic validation | [Formal model](formal_model.md), [independent oracle validation](independent-probabilistic-validation.md) |
| Repeatable evaluation inputs | Audited corpus, deterministic generation, duplicate/isomorphism handling and benchmark freezing | [Corpus](corpus.md), [Stage 4 benchmark](stage4.md) |
| Semantic and presentation controls | Frozen representations and carefully scoped stimulus revisions | [Stage 5 rendering](stage5-rendering.md), [Stage 6A pilot](stage6a-model-pilot.md) |
| Controlled provider execution | Versioned prompt bytes and hashes, configuration provenance, bounded/resumable execution, evidence journals and scoring | [Stage 6A documentation](stage6a-postmerge-status.md), `src/enforceability/` |
| Scientific credibility | Verification, explicit assumptions, corrections and negative/nonconfirmatory outcomes | [Actionability](actionability.md), [prior-art review](prior-art-collision.md) |

## Historical public code versus subsequent local experiments

The public repository's Stage 6A v1.3 documentation describes an **October 10 pre-execution freeze**, when it correctly recorded zero real-provider responses. That number should not be mistaken for the status of later **local** experimentation.

As of October 12, 2026, the separate local research record reports:

- Stage 6A: **140/140 expected execution positions verified**, using real provider responses.
- Stage 6B: **401/401 scheduled observations in each of two provider configurations** (802 total); local closure reports verified evidence chains and byte-identical offline scoring reproduction.
- Stage 6C: **1,980 scheduled experimental positions**, of which **1,972 were technically complete** and **eight censored or technically noncomplete** across three provider configurations.

These subsequent provider journals and audits are **local records, not evidence artifacts included in this public repository**. They should not be represented as independently reproducible from this GitHub checkout alone.

**Scientific qualification:** Stage 6C did **not** establish the preregistered primary orientation effect at its frozen robust/class-tier threshold. Narrower item-level patterns were conditional; other patterns were exploratory. The local audit also documents a post-start technical stopping-rule deviation. Finite, implementation-validated findings do not establish a new general theorem or model-wide behavioral property.

## A reproducible code review

With a compatible Python environment, start with the root README's documented commands:

```bash
python -m pip install -e '.[test]'
ruff check src tests
python -m pytest
validate-independent-oracle
verify-identifiability
```

Run these against the specific checkout and report the results actually obtained. The tests verify implementation properties; they do not substitute for provider-execution audits or mathematical proofs of generality.

## Where the engineering generalizes

The reusable engineering techniques are reference-oracle design, benchmark provenance, immutable test inputs, input/response validation, deterministic scoring, resumable execution, audit-friendly evidence, and explicit accounting for missing/failed observations.

The finite-game results themselves remain scoped to the studied formal tasks, policies, models and assumptions. No claim of hidden cognition, intentional misreporting or broad real-world deployment reliability follows from these experiments.
