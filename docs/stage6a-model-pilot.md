# Small Stage 6A model pilot v1.3

## Status and immutable boundaries

PR #14 proposes v1.3; merged main at audit start is
`9e5c8d4855b0cdea9e396cee0ea809fd3dbd6cf7` and contains historical v1.1.
**Real provider responses collected: 0.** V1.1 and v1.2 remain byte-for-byte
unchanged. V1.1 was superseded because its 500-token cap could cause differential
reasoning truncation. V1.2 raised the cap to 25,000 and hardened noncompletion.
OpenAI's [reasoning guide](https://developers.openai.com/api/docs/guides/reasoning)
recommends initially reserving at least 25,000 tokens for reasoning and output;
this does not prove that this budget suffices for this benchmark.

The user explicitly authorized v1.3 during the pre-merge audit after finding
evaluator metadata inside all 70 v1.2 prompt objects. V1.3 removes condition,
domain, track, formal_instance_id, render_id, template_id, and schema_version
from model-visible input. Attribution remains in the outer manifest only.
Every other stimulus field, response option, selected formal instance, mapping,
hypothesis, threshold, metric and sample size remains unchanged. This is a
versioned stimulus correction, not a claim of behavioral effects. No project
context or descriptive experimental title is supplied to subjects.

The adapter sends sorted compact JSON encoded as UTF-8 and checks its hash
against the frozen request manifest before each initial request. V1.2's compact
hash differed from its adapter's whitespace-bearing input; v1.3 corrects this
byte-provenance discrepancy. Frozen Stage 6 source artifacts are untouched.
V1.3 lives in `artifacts/stage6a-model-pilot-v1.3/` and fingerprints both
predecessors. Historical zero-response streams and all their frozen files are
verified, not rewritten.

## Scientific scope

This remains an **exploratory construct-validity pilot**, not confirmatory
real-model evidence. Track A contains four cases of each three-way epistemic
class. Track B separately contains three PER_WORLD_ONLY and three COMMON_POLICY
cases: 18 unique formal units. Each receives abstract natural, scaffolded and
tool-assisted conditions (54 requests/configuration). Eight units additionally
receive natural ant-colony and technical-system renders (16 more), totaling
70/configuration and 140 scientific keys for exactly two configurations.

Repeated renders are not independent units; tracks and conditions must not be
pooled. Tool assistance supplies exact values/policy losses, not semantic gold
labels. H1–H6, confidence >= 0.80, mapping rules, actionability semantics and
scoring are in the frozen plan. Preserve null/negative results. Exact-oracle and
deliberately ignorant baselines validate the pipeline only: their denominators
are 18 total, 12 Track A, and 6 Track B. They are not model observations.
Observable error labels do not establish hidden cognitive mechanisms.
The prior-art collision review limits novelty claims.

## Provider configuration and parsing

Exactly two same-model configurations are permitted: OpenAI gpt-5.6-terra with
medium and high reasoning. Endpoint, model, output cap, temperature/seed values
and omission policy must match. Required reasoning cannot be marked unsupported.
Both configurations use 25,000 max_output_tokens and store=false. Temperature
and seed remain omitted: generic schema support does not establish acceptance
for this exact model/treatment. See [the dated API audit](stage6a-premerge-audit.md).
Credentials remain external; only their environment-variable names enter the
execution manifest. Real transport requires HTTPS, committed runtime/configuration
sources, and a passing canary receipt.

Each request is independent: no previous_response_id, conversation, project
memory, system experiment labels or repair history is reused. store=false
disables response storage for later API retrieval; it is not a blanket
zero-retention promise.

Only top-level completed status permits answer extraction. The adapter gathers
text from output[].content[] entries of type output_text; reasoning items are
not scored. Incomplete, failed (including error-bearing failed envelopes),
in_progress, queued and cancelled states fail closed. Their envelope, reason,
response ID, usage, timestamp, latency, key and attribution are preserved.
Missing status and malformed envelopes are protocol failures. No semantic retry
or automatic transport retry occurs.

## Format-only repair and raw evidence

Only a completed response failing syntax/schema validation gets at most one
repair. It contains only the frozen format-only instruction, response schema
and initial malformed text, never the benchmark problem or gold answer.
Initial/repair text, IDs, token usage, latency and timestamps remain separate.
Instructions cannot prove semantic preservation; report the primary permitted-
repair score alongside the conservative view treating all repairs as failures.
Semantic mistakes are never retried.

An incomplete repair first appends an incomplete record embedding the initial
evidence, then appends the initial raw record. Both streams may share a key only
for this repair case. It never becomes a completed scientific outcome.
Repair transport failure also preserves the initial raw record and remains
unscorable. Resume skips keys with initial or repair noncompletion.

The execution key is SHA256(configuration_id + ":" + request_id). All evidence
appends use UTF-8, flush and fsync. An exclusive writer marker prevents
concurrent run/score. A process crash may leave that marker; investigate before
removing it. The append-only attempt-journal.jsonl records intent before
transport and received envelopes before parsing/repair. An unfinished intent or
received envelope without terminal evidence blocks resume/scoring as
AMBIGUOUS_PROVIDER_ATTEMPT. Preserve the journal and use a separately audited
recovery procedure; never delete evidence to force a retry. No software can
guarantee saving a response immediately before process termination. Such
ambiguity blocks automatic reissue. Explicit transport errors may be manually
resumed under a new recorded session, but do not prove the provider did no work.

## Provenance, analysis and verification

The version-2 execution manifest binds the selected artifact directory's
plan/request bytes, configuration, current harness Git SHA and exact source hash.
An invented SHA override is rejected. Run, score and verify check the binding;
all completed/noncompleted records must match canonical request attribution,
execution key, configuration and prompt hash. Noncompletion metadata must agree
with its preserved envelope.

Score validates the pre-execution freeze before mutation and requires every
one of 140 keys to have a completed terminal outcome. Missing/noncompleted
responses, unfinished repairs and ambiguous attempts block analysis. No
denominator reduction or conversion of missing work to parse failures occurs.
Score refuses to overwrite an existing execution freeze; run refuses further
session/evidence appends after that freeze. The separate execution
freeze must cover the full required file set and bind the pre-execution freeze
and execution manifest. Verify is read-only; it never contacts a provider or
rebuilds artifacts. Its pre-execution result is
PRE_EXECUTION_VERIFIED_CANARY_REQUIRED, not provider readiness.

Build is non-destructive: create only an absent/empty directory, or compare an
exact existing pre-execution set without writes. Any mismatch or evidence of
execution/analysis fails closed. No historical artifact is rebuilt.

## Segregated mandatory canary

The canary command uses the same adapter with a fixed trivial ping task, never
a benchmark prompt. It makes one medium and one high request, without repair
or retry. Both must complete with the fixed answer, response ID and usage.
Noncompletion branches are tested with fake transports; the operator does not
tune the frozen budget to induce them. Public docs do not establish account
access or live acceptance; these remain unknown until the authorized canary.

Canary writes only canary-report.json and canary-evidence.jsonl in a fresh
directory outside the entire checkout. It never touches a scientific manifest,
response stream or freeze and counts as zero scientific requests. Failure
leaves NOT_PASSED; reruns require a fresh directory. Passing receipts bind
configuration, runtime and evidence hashes. They are provenance records, not
provider signatures. Receipts explicitly distinguish mock transport; mock
evidence cannot authorize real scientific calls. Any runtime/configuration
change requires a new canary.

The following are **future commands requiring explicit authorization**.
This pre-merge task executes neither canary nor scientific run:

```bash
stage6a-model-pilot verify
stage6a-model-pilot canary --config /secure/stage6a-models.json --output /outside-checkout/canary-001 --acknowledge-provider-calls
stage6a-model-pilot run --config /secure/stage6a-models.json --canary-receipt /outside-checkout/canary-001/canary-report.json
stage6a-model-pilot score
verify-stage6a-model-pilot
```

Review the actual final GitHub head, hosted CI, configurations and v1.3 hashes
before authorization. Green tests alone do not establish provider readiness.
