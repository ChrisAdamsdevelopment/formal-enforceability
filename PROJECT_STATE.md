# Formal Enforceability — project state

Recovered on 2026-10-10 UTC from the repository, hosted GitHub and explicitly
identified local provenance. This is a navigational state record, not an
alternative scientific specification. Frozen files and their verifiers control.

## Mission and authority

Develop conditional, mechanically checkable statements about strategic
enforceability, information limits and evidence-to-action consistency in finite
reference games. These results do not establish a general guarantee about AI
systems or reveal hidden cognition from observed responses.

When sources conflict, use current repository/frozen artifacts, current
state/decision records, later project chats, historical Drive sources, then
model memory. Report discrepancies; preserve counterevidence and superseded
sources. Experimental subjects must receive only the frozen stimulus in fresh
contexts, never this document, project chats or evaluator metadata.

## Current repository and execution state

**SUPPORTED:** [PR #14](https://github.com/ChrisAdamsdevelopment/formal-enforceability/pull/14)
merged at **2026-10-10 02:52:12 UTC** as
`3f4e71d585f981671419e2e14c450634ed3540de`, with source head
`8a999b245e5613f3c2dd69f32a7963a8c49bf13b`. Its parents are the former main
`9e5c8d4855b0cdea9e396cee0ea809fd3dbd6cf7` and that source head.
See the [post-merge status and handoff](docs/stage6a-postmerge-status.md) for
dated hosted CI evidence, offline checks, fingerprints and authorization gates.

**SUPPORTED:** Stage 6A v1.3 is merged and frozen before execution. Historical
v1.1 and v1.2 are preserved. All recorded provider evidence streams are empty;
recorded real provider responses = **0**. There is no recorded successful real
canary and no scientific execution. Off-repository provider activity has not
been queried and cannot be ruled out by empty files alone. This recovery task
made no provider calls, performed no scientific scoring, created no PR and
performed no merge.

## Established formal results

**PROVED, within the repository's stated finite assumptions:** for finite
states/actions, rational transitions, a finite horizon, perfect recall and an
informed adversary unable to observe the controller's current private draw,

\[
V_H=\min_{\pi_C}\max_{\pi_A}\Pr(F\text{ before }R\text{ within }H).
\]

WINNING means \(V_H\le\epsilon\); LOSING means \(V_H>\epsilon\).
Invalid data, unsupported games and unresolved computations are not LOSING.
The [formal model](docs/formal_model.md) controls these definitions.

For compatible games \(\mathcal M(I)\), define
\(\underline V=\inf_G V(G)\), \(\overline V=\sup_G V(G)\).
The three epistemic labels are winning if \(\overline V\le\epsilon\), losing
if \(\underline V>\epsilon\), and insufficient if
\(\underline V\le\epsilon<\overline V\).
[Propositions A–D](docs/threshold-identifiability.md) prove exact finite-family
witnesses; they are not general necessary-and-sufficient characterizations.

The [actionability note](docs/actionability.md) establishes
\(W=\sup_G\min_\pi L(\pi,G)=\overline V\le R=\min_\pi\sup_G L(\pi,G)\)
and fixed-policy vertex sufficiency in its one-step affine scope. Having a safe
policy in every compatible world need not identify a common safe policy.
Actionability refines the winning branch, not the three-way label hierarchy.
The [IIEFG reduction](docs/formal-iiefg-reduction.md) is value-preserving under
its assumptions, not a new model of general intelligence.

## Implementation, frozen specifications and evidence

| Category | Current state and canonical source |
| --- | --- |
| IMPLEMENTATION-VALIDATED | Exact oracle and bounded independent numerical checks, plus fake-transport execution/provenance tests. The [independent validation](docs/independent-probabilistic-validation.md) is not a second exact certificate or real-model evidence. Six numerical threshold cases remain unresolved. |
| HYPOTHESIS | H1–H6 and their operational metrics remain the frozen hypotheses in [v1.3 pilot-plan.json](artifacts/stage6a-model-pilot-v1.3/pilot-plan.json). No outcomes collected. |
| EXPLORATORY | Stage 6A is a construct-validity pilot: 18 formal units, 70 requests per configuration, 140 keys; same-model medium/high reasoning. Tracks, conditions and repeated renders must not be pooled as independent observations. |
| IMPLEMENTATION-VALIDATED, synthetic only | Frozen exact-oracle and deliberately ignorant baselines in [aggregate-report.json](artifacts/stage6a-model-pilot-v1.3/aggregate-report.json) validate the pipeline, not model behavior. Historical synthetic projects and manual chat trials remain separate provenance. |
| SUPPORTED, actual provider evidence | Empty v1.1/v1.2/v1.3 streams and absent execution manifest/freeze support zero recorded Stage 6A results. They are not missing-data substitutes or negative model findings. |
| REJECTED | The [prior-art collision review](docs/prior-art-collision.md) rejects broad novelty for feedback-dependent coverage, coarsened-functional identification and the general model. It selects theory + benchmark; finite proofs do not establish novelty. |
| UNKNOWN | Account access, live model/parameter acceptance, quotas, actual model performance and generalization; no live checks were authorized. |

Canonical stimulus bytes and evaluator attribution live in
[request-manifest.json](artifacts/stage6a-model-pilot-v1.3/request-manifest.json);
[pilot-freeze.json](artifacts/stage6a-model-pilot-v1.3/pilot-freeze.json) records
their integrity. The [example configuration](configs/stage6a-models.example.json)
and [runtime](src/enforceability/model_pilot.py) control operational treatment.
Do not copy a mutable prompt specification into this state file.

## Open questions, negative results and deferred work

- **UNKNOWN:** exact continuous-public-fiber adaptive \(\overline V\). The
  fixed-policy/robust-\(R\) vertex result does not settle it.
- **SUPPORTED negative result:** no gap in the 81 deterministic and 625 bounded
  probabilistic canonical public classes searched. The explicit-set diagnostic
  `{d051,d204}` has different public signatures and is not a canonical witness.
- **UNKNOWN:** a broader operational threshold-only identification
  characterization. No new theory or novelty review was attempted here.
- **Outstanding archival work:** preserve the exact reviewed OpenReview
  revisions before treating the prior-art review as archival-complete.
- **Historical recovery gaps:** local migration records report 37 truncated
  chat items, incomplete attachment/citation recovery and incomplete exploratory
  trial indexing. Historical D038–D042 were not located; three DOCX placeholders
  are empty. These are missing evidence, not invitations to reconstruct content.
- **Deferred EXPLORATORY directions:** boundary forecasting, local Forge/Ollama
  plans, historical manual-chat follow-ups and a separately versioned Gemini
  comparison. No CROSSFLOW, emotion/appraisal or new research is authorized.

## Next milestones

This follow-up is offline recovery/documentation only. The next possible live
action is a separately authorized, segregated two-request canary. Scientific
execution needs a passing receipt bound to the chosen checkout/configuration
and a second explicit authorization for the 140-key run. Scoring, sensitivity
analysis and publication follow only after the relevant evidence and approvals.
See the [operator handoff](docs/stage6a-postmerge-status.md) and
[provider options](docs/provider-options.md). A PR or another merge also needs
owner approval. Passing tests never substitutes for these gates.
