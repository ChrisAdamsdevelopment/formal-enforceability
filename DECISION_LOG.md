# Formal Enforceability — recovered decision record

Recovery date: 2026-10-10 UTC. These entries summarize inspectable evidence;
they are not invented contemporaneous minutes. Dates below identify source
commits/observations. Frozen plans control over these summaries. Append later
decisions with authority, scope, evidence and explicit supersession.

## R01 — Preserve finite scope and distinguish proof from novelty

**PROVED / REJECTED / UNKNOWN:** repository Propositions A–D retain their
finite-family proofs. The collision review selects theory + benchmark and
rejects broad novelty claims for known identification/coverage principles.
Broader threshold-only characterization remains a question. Source:
[threshold-identifiability](docs/threshold-identifiability.md),
[prior-art collision verdicts](docs/prior-art-collision.md). This recovery
does not conduct a new novelty search or turn bounded negative search into
proof of absence.

## R02 — v1.1 execution-integrity repair, 2026-09-14

**SUPPORTED:** commit
[`3d89b1e`](https://github.com/ChrisAdamsdevelopment/formal-enforceability/commit/3d89b1e4217d3f262205d01e95a0f683caf11eb2)
and the historical [v1.1 plan](artifacts/stage6a-model-pilot-v1/pilot-plan.json)
record format-only repair context, resumability, configuration freeze,
transport/session audit and repair sensitivity before any provider response.
The directory is named `stage6a-model-pilot-v1`, while its plan version is v1.1.
Its preceding plan hash is retained in that file. Its 500-token budget is a
historical design fact; the inspected rationale does not establish that the
budget was empirically adequate. Do not retrospectively claim otherwise.

## R03 — v1.2 truncation-validity successor, 2026-09-17

**SUPPORTED:** commit
[`4d238a7f`](https://github.com/ChrisAdamsdevelopment/formal-enforceability/commit/4d238a7f92daf2a5233ffc819d4446f3e0a37d6c)
introduced v1.2. Its [plan revision reason](artifacts/stage6a-model-pilot-v1.2/pilot-plan.json)
states that output limits include reasoning as well as visible output; 500
could cause differential truncation between medium/high treatments. V1.2 uses
25,000, preserves v1.1 and records zero prior real responses. This is a
pre-execution validity concern, not an observed model effect.

Subsequent commits `53ee231b`, `74cdfc85`, `6eb955f2` and `70fb5acc` record
noncompletion preservation, required reasoning treatments, complete-outcome
scoring gates and canonical attribution. The frozen v1.2 plan and Git history
are the sources; 25,000 is not proved sufficient for the benchmark.

## R04 — Authorized v1.3 metadata/input-byte correction, 2026-10-09 local

**SUPPORTED / IMPLEMENTATION-VALIDATED:** the dated
[pre-merge audit](docs/stage6a-premerge-audit.md), local pre-merge audit/decision
record and [commit `8a999b24`](https://github.com/ChrisAdamsdevelopment/formal-enforceability/commit/8a999b245e5613f3c2dd69f32a7963a8c49bf13b)
record explicit owner approval for a v1.3 successor after evaluator metadata
was found in all 70 v1.2 subject prompts. V1.3 removes only seven evaluator or
version fields and hashes the exact compact UTF-8 input. All other stimulus
fields and scientific choices remain unchanged; outer attribution is retained.
The [v1.3 revision reason and predecessor hash](artifacts/stage6a-model-pilot-v1.3/pilot-plan.json)
bind this transition. V1.1/v1.2 remain historical, never rewritten.

That commit also binds selected artifact bytes and current runtime provenance,
requires exactly two configurations, preserves attempts/evidence and result
freeze integrity, and adds a segregated fixed-input canary with receipt checks.
The former canary requirement lacked a reproducible adapter path. Mocked
testing validates mechanisms only; no successful real canary is established.

## R05 — Merge verified; execution authorization remains separate

**SUPPORTED:** GitHub records PR #14 merged at 2026-10-10 02:52:12 UTC as
[`3f4e71d5`](https://github.com/ChrisAdamsdevelopment/formal-enforceability/commit/3f4e71d585f981671419e2e14c450634ed3540de),
with `8a999b24` as its second parent. The merged tree matches that source head.
The [post-merge status](docs/stage6a-postmerge-status.md) records hosted CI and
offline evidence. Merge does not imply a canary, scientific run or publication.

The current owner's task authorizes fresh-main recovery and offline preflight,
not live calls, scientific scoring, PR creation or another merge. This follow-up
leaves implementation, configuration and scientific artifacts unchanged.
The optional Gemini comparison is **EXPLORATORY**, requires a separate protocol,
adapter and authorization, and cannot be substituted into v1.3.

## Recovery limits and source hierarchy

Local `research-memory/PREMERGE_AUDIT_2026-10-09.md`, `DECISION_LOG.md`,
`PROJECT_STATE.md` and `MIGRATION_AUDIT.md` informed recovery as secondary
provenance. They do not override this repository's frozen files. Their older
open-PR/no-clone statements are dated historical observations, not current facts.
The pre-merge audit itself is preserved unchanged.

The local migration audit reports missing D038–D042, 37 truncated chat items,
unexposed historical attachments/citations, incomplete exploratory indexing
and three empty DOCX placeholders. Exact missing contents and any undocumented
historical rationale remain **UNKNOWN**. No missing decisions or experiments
are reconstructed here. Existing negative results and rejected hypotheses
remain visible in PROJECT_STATE and the canonical formal/review documents.
