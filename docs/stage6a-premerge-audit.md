# Stage 6A pre-merge audit and execution boundary

Audit date: 2026-10-09 America/Phoenix (2026-10-10 UTC).
Initial hosted main: `9e5c8d4855b0cdea9e396cee0ea809fd3dbd6cf7`.
Initial PR #14 head: `70fb5acc0b0c685a054356cad636fe5b4d7a343c`.
GitHub reported clean mergeability and successful Sourcery/two test checks.
These are dated observations; inspect the actual final PR head and hosted CI
before a merge decision. This document neither merges nor authorizes execution.

## Findings and focused corrections

- The hosted repair-noncompletion review concern was already fixed at the
  initial head. Its evidence-preservation/resume tests are retained.
- Execution accepted extra configurations; it now requires exactly two before
  any manifest or transport operation.
- Manifest self-hashes did not bind the selected artifact directory/current
  harness. Version-2 runtime manifests now bind both plus exact source bytes;
  run, score and verify reject drift and invented SHA overrides.
- Score omitted pre-execution verification; result-freeze validation accepted
  an incomplete file map. Score now checks the freeze before analysis, refuses
  overwrite, and verification requires full coverage and manifest links. Run
  also refuses to append sessions/evidence after an execution freeze exists.
- All 70 v1.2 prompts exposed evaluator metadata, and all 70 recorded hashes
  differed from the adapter's input serialization. The user explicitly
  authorized **v1.3**, preserving v1.1/v1.2 rather than rewriting them. V1.3
  strips only seven evaluator/version fields and uses exact compact UTF-8
  inputs. Regression checks compare all remaining fields and scientific plan
  components against v1.2. Upstream Stage 6 remains unchanged.
- Returned envelopes could be lost before a terminal append; concurrent writers
  could duplicate keys. A fsynced attempt journal and exclusive writer marker
  preserve evidence/block ambiguous resume. Completed evidence is checked
  against the journal's original envelope, including received repair attempts.
  This is not an exactly-once network
  guarantee; ambiguous attempts require audited recovery.
- The mandatory canary lacked a reproducible adapter path. The new segregated
  fixed-prompt command exercises the same payload/parser, writes only outside
  the checkout, and supplies a configuration/runtime-bound receipt. Scientific
  execution checks that receipt and rejects receipts marked as mock transport.
  Canary tests use fake transport only.
- Verify no longer calls an intact pre-execution freeze provider-ready. README
  and operator instructions now distinguish main, historical freezes, proposed
  v1.3, hosted checks and actual execution gates.

V1.3 fingerprints (SHA-256):

| File | Hash |
| --- | --- |
| pilot-plan.json | 1d9a98f126cf7f556e36b2173428c04d86b1f0befb00d9334b2f54bfdf00ee02 |
| request-manifest.json | 8b1d1b0279030b23fb197e19ab4f3e08344e5ee7a980a62d995838314dcf062e |
| pilot-freeze.json | 5b49bbcd85edde420448fcceed2b8531546b65827a916c8733b68399ff2f5571 |

All 112 artifact files already present at the initial PR head were compared
byte-for-byte and remained unchanged. All 70 new prompt objects equal their
v1.2 counterparts after removing only the seven listed metadata fields; all
70 hashes match the adapter input bytes. Empty v1.3 response/journal placeholders
are new pre-execution files, not collected provider evidence.

## Epistemic status

| Status | Scope |
| --- | --- |
| Proved | Existing exact finite-family propositions under repository assumptions; untouched here. |
| Implementation-validated | Local/hosted deterministic checks and fake-transport regressions; not model evidence. |
| Supported | Byte comparisons, observable hosted state and bounded source-based audit findings. |
| Hypothesis | Frozen H1–H6; no outcomes collected. |
| Exploratory | Stage 6A construct-validity design and historical manual tests; not confirmatory population claims. |
| Rejected | Overbroad novelty/model-ranking interpretations already rejected in prior-art/history remain rejected. |
| Unknown | Account access, actual provider behavior/results, unresolved continuous adaptive value questions and generalization. |

Exact-oracle baselines remain explicitly non-model evidence. Synthetic checks
are never promoted to real-model results. No hidden cognition is inferred.
No new theory, CROSSFLOW, appraisal/emotion work or novelty claim is introduced.
The prior-art review's known-principle qualifications and negative actionability
search result remain in the existing formal documentation.

## Current primary OpenAI documentation

Reviewed on the audit date; public documentation is not account access evidence.

| Assumption | Finding and source |
| --- | --- |
| Exact gpt-5.6-terra ID; Responses; medium/high | Listed by the [Terra model page](https://developers.openai.com/api/docs/models/gpt-5.6-terra). No model substitution. |
| 25,000 output cap | Within the model's documented output maximum. The [reasoning guide](https://developers.openai.com/api/docs/guides/reasoning) explains the cap includes reasoning and visible output; truncation may precede visible text. |
| store=false | The [Responses creation reference](https://developers.openai.com/api/reference/resources/responses/methods/create) documents the response-storage control. It is always emitted, without conversation reuse. This is not a claim of universal zero retention. |
| Top-level status | That reference lists completed, failed, in_progress, cancelled, queued and incomplete. Only completed is parsed. Failed envelopes with an error object remain noncompleted evidence. |
| Incomplete reasons | Current reference includes max_output_tokens, max_messages, content_filter and steered. The parser preserves arbitrary supplied reasons and fails closed; no assumption of only two reasons remains. |
| Output shape | [Text generation](https://developers.openai.com/api/docs/guides/text) shows output messages containing content entries of type output_text with a text field. The harness reads those entries, not a presumed first-item string or reasoning content. |
| Temperature | Generic Responses schema exposes it; inspected exact-model documentation does not establish acceptance for Terra medium/high. Keep omitted. |
| Seed | No request seed parameter located in the inspected Responses creation schema. Keep omitted; do not infer support from other endpoints. |

No verified API fact required changing model, reasoning treatments or token
budget. Exact-model temperature acceptance remains unknown, not asserted false.
The canary must use the frozen omission policy; it must not tune the benchmark.
The complete Responses reference was retrieved separately after the browser
tool's large-page retrieval failed; its source HTML SHA-256 is
`cc2781489f4f7835ec9f4049c40f3bd48e827930b752f7c0a498502fc3f9d35c`.

## Verification and remaining work

Run the complete non-provider suite on the final checkout:

```bash
python -m pip install -e '.[test]'
ruff check src tests
python -m pytest
validate-independent-oracle
verify-identifiability
verify-prior-art-review
verify-stage6a-pilot
stage6a-model-pilot verify
verify-stage6a-model-pilot
git diff --check
```

Tests prohibit socket connections and use fake transports/temp artifact copies.
Neither build, score nor verify calls a provider. Verify does not write artifacts.
The independent numerical validator reports its unresolved threshold cases;
passing validation does not turn those into exact certificates.

Before merge: review the actual final diff, v1.3 stimulus correction/fingerprints,
zero-response state, non-provider results and hosted CI at the exact pushed head.
No merge is performed by this task.

After merge, before scientific execution: preserve the final refs/environment,
configure credentials externally, obtain explicit canary authorization, run the
segregated canary, inspect its receipt, then obtain explicit scientific-run
authorization. A failed/noncompleted canary blocks scientific call #1.

Execution itself: attempt 140 frozen scientific keys, retain initial/repair and
noncompleted evidence append-only, stop on validity defects, and never silently
retry ambiguous attempts or tune prompts. Scoring requires complete outcomes.

After execution: frozen scoring/verification, separate track/condition and
repair-sensitivity reporting, preserve nulls/negative results, and bounded
analysis/publication under the existing novelty review. Complete outstanding
primary-source archival work before archival-complete manuscript claims.

Repository PROJECT_STATE/DECISION_LOG files were absent. They are deferred to a
focused fresh-main follow-up; the local research-memory files remain provenance
and coordinator memory, not competing frozen specifications. No historical
decisions were invented for this PR.
