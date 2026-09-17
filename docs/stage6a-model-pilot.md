# Small Stage 6A model pilot v1.2

## Status and immutable boundary

**Pre-execution successor: `stage6a-model-pilot-v1.2`. Real provider calls: 0.**
V1.1 remains byte-for-byte in `artifacts/stage6a-model-pilot-v1/` and is
superseded pre-execution. V1.2 is separately frozen in
`artifacts/stage6a-model-pilot-v1.2/`; its freeze records the v1.1 plan,
request-manifest, and freeze fingerprints. Thus evidence from the two versions
cannot be confused.

No real provider responses existed under v1.1.

Pre-execution review found that Responses API `max_output_tokens` includes
reasoning tokens as well as visible output. The frozen value of 500 can
therefore truncate stronger-reasoning responses before a visible answer is
produced, creating differential failure risk between medium and high reasoning.

The pilot was revised before provider call #1.

The v1.2 cap is 25,000 for both configurations. This is the smallest defensible
initial cap because OpenAI's reasoning guidance recommends allowing at least
25,000 tokens for reasoning and output when first experimenting, before actual
reasoning-token requirements are known. This correction changes no formal
instance, render, prompt, answer/action ID, hypothesis, threshold, scoring rule,
or sample size. Primary references reviewed were OpenAI's
[reasoning guide](https://platform.openai.com/docs/guides/reasoning) and
[Responses reference](https://platform.openai.com/docs/api-reference/responses).

Provenance summary:

```text
v1.1:
0 provider responses
superseded pre-execution

v1.2:
successor execution specification
0 provider responses at time of freeze
```

## Frozen scientific design

Selection uses deterministic generator order and frozen class-local indices.
Track A has four cases each of `CERTIFIABLY_LOSING`,
`INSUFFICIENT_INFORMATION`, and `CERTIFIABLY_WINNING`. Track B separately has
three `PER_WORLD_ONLY` and three `COMMON_POLICY`: 18 unique formal units.

Each case receives independent `abstract` calls in `natural`,
`epistemically_scaffolded`, and `tool_assisted`: 54 primary calls per model.
The cross-domain subset has two Track A cases per class and one Track B case per
class. Natural `ant_colony` and `technical_system` renders add 16 calls, for 70
calls per configuration. Alternate renders are repeated measurements, not
independent observations. Natural has no added hint; scaffolding only identifies
the compatible-model abstraction; tool assistance adds exact repository-derived
values and candidate-policy losses, never the semantic gold label.

Hypotheses H1–H6, the `confidence >= 0.80` threshold, metrics, instance IDs,
conditions, prompts, and scoring semantics are unchanged. The exact public
payload and prompt SHA-256 for every call are in `request-manifest.json`.

## Narrow provider adapter and configuration freeze

The intended first execution uses OpenAI `gpt-5.6-terra` for both roles:
`medium` reasoning for `standard/default reasoning`, and `high` reasoning for
`stronger reasoning`. Using one model isolates reasoning effort. Credentials
remain external in `OPENAI_API_KEY`. Primary public documentation reviewed for
this freeze explicitly lists `gpt-5.6-terra`, Responses API availability, and
the `medium` and `high` reasoning levels. It does not establish exact-model
acceptance of `temperature` or `seed`; no claim is inferred from a third-party
schema. The example therefore records `temperature: 0` but lists
`temperature` as unsupported so it is omitted, and likewise records `seed:
null` with `seed` unsupported because the Responses request reference does not
document a seed field. Exact model, medium/high effort, and parameter acceptance
must pass the non-benchmark canary below before scientific call #1.

Every request unconditionally emits `store: false`. This is a runtime/privacy
control, not a scientific parameter: each request is independent and requires
no provider-side conversational state.

A top-level `status: completed` is required before `output_text` extraction or
answer parsing. Missing status is a protocol failure. `incomplete` and every
other explicit noncompleted status (`failed`, `in_progress`, `cancelled`, or
`queued`) fail closed even if an output field exists. For `incomplete`, the
documented reason is retained without assigning any invented meaning.

For either the initial or repair phase, the harness preserves the entire safe
noncompleted JSON envelope, response ID, usage, timestamp, latency,
configuration/request identity, status, reason, execution key, and phase in
`incomplete-responses.jsonl`. It performs no further repair and no automatic
retry. If a completed initial answer was malformed and its single permitted
repair is noncompleted, the noncompletion record also embeds all initial raw
answer metadata before the initial record is appended to `raw-responses.jsonl`.
This append order makes both pieces crash-safe in one first append; the two
streams may intentionally share that execution key only for repair-phase
noncompletion. Resume skips the evidenced key, and verification subtracts it
from completed scientific answers and reports `EXECUTION_INCOMPLETE`. OpenAI
currently documents `max_output_tokens` and `content_filter` as incomplete
reasons; handling is generic for any provider-supplied reason.


V1 supports only `openai_responses_compatible`: bearer-authenticated HTTP with
an OpenAI Responses-style request and raw `output[].content[]` extraction for
`output_text`. It is not advertised as an arbitrary-provider adapter. Provider
error envelopes and malformed/missing output are transport/protocol events, not
model answers.

Before call 1, the runner validates the complete configuration schema, safe
endpoint, supported adapter, allowed unsupported-parameter names, positive
output limit, unique IDs, unique substantive configurations, and exactly one
configuration for each required role. It enforces the exact role mapping
`standard/default reasoning = medium` and `stronger reasoning = high`. Adapter,
normalized endpoint, model ID, 25,000-token cap, temperature and seed values,
and unsupported-parameter policy must match, so reasoning effort is the only
generation-treatment difference. Neither required role may list `reasoning` or
`reasoning_effort` as unsupported: validated scientific payloads must contain
exactly `{"reasoning": {"effort": "medium"}}` and
`{"reasoning": {"effort": "high"}}`, respectively, rather than silently using
a provider default. It confirms each credential environment variable
exists without serializing its value. Parameters declared unsupported are
actually omitted; in the required pair this applies to `temperature` and
`seed`, never to the mandatory reasoning treatment. Optional future
non-scientific configurations may still omit reasoning when explicitly marked
unsupported.

It then writes `execution-manifest.json` before calling the provider. That
sanitized file records configuration ID and role, adapter, safe endpoint
origin/path, credential environment-variable **name**, model/version, reasoning
effort, temperature, seed, maximum output tokens, unsupported parameters,
harness Git SHA, pilot-plan SHA, request-manifest SHA, and its own SHA. Any
later drift is rejected.

## Strict format-only repair and sensitivity

Responses contain only `answer_id`, `action_id`, confidence in `[0,1]`, and an
optional short `brief_basis`; chain of thought is neither requested nor scored.
On initial syntax/schema failure, exactly one repair call receives only:

```json
{
  "format_only_message": "Reformat the previous response only. Do not solve the problem again. Do not reconsider, recompute, or change its answer choice, action choice, confidence, or substantive content. Return only a JSON object matching response_schema.",
  "response_schema": {"answer_id": "...", "action_id": "...", "confidence": "...", "brief_basis": "..."},
  "malformed_response": "the exact initial raw response"
}
```

The benchmark problem is not resubmitted. The raw record separately retains
initial and repair raw text, provider request ID, usage, latency, and timestamp.
Scored rows record `repair_attempted`, `repair_succeeded`, and whether `initial`
or `repair` supplied the scored structure. Semantic errors are never retried.

Preregistered scoring uses a successful permitted repair. The conservative
sensitivity view treats every repaired item as a parse failure. The separate
report includes `parse_failure_initial`, `parse_failure_after_repair`,
`accuracy_with_allowed_format_repair`, and
`accuracy_treating_all_repairs_as_failures`.

## Crash safety, sessions, and transport events

The execution key is `SHA256(configuration_id + ":" + request_id)`. Raw records
are append-only and fsynced. At every invocation the runner validates all
existing records, rejects duplicate/unexpected keys and request/configuration
drift, skips completed keys, and calls only missing keys. A partial run is thus
resumable without ever silently reissuing a completed answer.

Provider/network/protocol failures append to `transport-events.jsonl` with the
execution key, configuration ID, request ID, timestamp, exception class, safe
provider status, and session ID—never credentials. There is no automatic
transport retry in a session. A later manual invocation creates a new session
and may attempt a key having only a transport event and no completed answer.

Every provider-capable invocation appends a safe `execution-sessions.jsonl`
record: session ID, start/end timestamp, harness Git SHA, plan/request/execution
manifest hashes, completed count before/during the session, transport failures,
and end status.

## Analysis, freezes, and verification

Track metrics and paired transitions remain preregistered. Cross-domain analysis
now measures `REPRESENTATION_INCONSISTENCY` at its correct unit—the
model/formal-instance three-render set—and reports both case count and IDs.
Per-response errors retain directly observable
`FAILED_TO_RECOGNIZE_NONIDENTIFICATION`, `FALSE_ABSTENTION`,
`QUANTIFIER_ORDER_ERROR`,
`UNSAFE_DEPLOYMENT_AFTER_CORRECT_EPISTEMIC_ANSWER`, `PARSE_FAILURE`, and
`OTHER`. A generic Track A mistake is `OTHER`, not an inferred cognitive
mechanism. The exact oracle baseline remains explicitly non-model evidence.

The oracle and deliberately ignorant pre-execution baselines use one canonical
`natural`/`abstract` render per unique formal instance: oracle N is 18, Track A
ignorant-baseline N is 12, and Track B ignorant-baseline N is 6. Alternate
conditions and domains are repeated experimental measurements and are not
treated as independent baseline observations.

`pilot-freeze.json` is the immutable pre-provider freeze and is never rewritten
by `run`, `score`, or `verify`. Explicit `score` writes analysis files and a
separate `execution-freeze.json` hashing the execution manifest, raw answers,
transport events, sessions, scored responses, aggregate, sensitivity,
cross-domain, and transition reports. `verify` is read-only: it checks the
Stage 6A source freeze and every frozen design hash, configuration self-hash and
roles, JSONL structure, execution keys, prompt hashes, configuration snapshots,
and result-freeze hashes. A partial execution returns `EXECUTION_INCOMPLETE`;
a normal two-configuration experiment requires all 140 responses.

`score` independently enforces the complete-execution gate before writing any
analysis byte. It self-validates the execution manifest and frozen
configurations, validates both completed and noncompleted streams, reconstructs
the exact 140-key set, and rejects missing keys, any initial- or repair-phase
noncompletion, and any unfinished repair. Thus scientific scoring implies all
140 frozen execution keys are complete, and `EXECUTION_INCOMPLETE` prohibits
scoring and execution-freeze creation. A rejected scoring attempt leaves every
existing analysis and freeze file byte-for-byte unchanged; partial records are
never converted into a smaller denominator or `PARSE_FAILURE` result set.

`build` is pre-execution-only and non-destructive. It creates artifacts only in
an absent or empty directory. For an exact existing pre-execution artifact set,
it compares the regenerated bytes and leaves every file untouched. It fails
closed without deleting or truncating anything if a response, transport event,
session, execution manifest, execution freeze, scored response, unexpected
file, or mismatched frozen artifact indicates that execution or analysis has
begun.

## Mandatory non-benchmark canary

After provider configuration but before scientific call #1, an operator must
run a segregated canary using a trivial prompt that is not a Stage 6A prompt and
contains no formal benchmark instance. Run it once with `reasoning.effort =
medium` and once with `high`, with the exact endpoint, `gpt-5.6-terra`, 25,000
cap, and `store: false`. It must verify:

1. endpoint and authentication;
2. exact model and both reasoning-effort values are accepted;
3. the payload's parameter set is accepted (temperature remains omitted unless
   primary exact-model documentation establishes support; seed remains omitted);
4. the outgoing JSON contains `store: false`;
5. envelope parsing, top-level completed/incomplete status behavior, nested
   `output[*].content[*].output_text`, response ID, and usage fields required by
   the harness.

Canary input/output must be stored outside the artifact directory. It must not
enter `raw-responses.jsonl`, `incomplete-responses.jsonl`, or the scientific
execution manifest, and does not count toward 140 scientific responses. It may
only diagnose operational compatibility; it must never tune prompts or
benchmark difficulty. Any failure blocks scientific call #1 until the
operational configuration is corrected and the canary passes. This repository
revision does not run that canary or make any provider request.

Copy `configs/stage6a-models.example.json` to a secure path, configure the two frozen same-model reasoning roles, then use the explicit flow:

```bash
stage6a-model-pilot verify
stage6a-model-pilot run --config /secure/path/stage6a-models.json
stage6a-model-pilot score
verify-stage6a-model-pilot
```
