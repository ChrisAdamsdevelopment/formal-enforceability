# Small Stage 6A model pilot

## Status and immutable boundary

**Local integrity status: verified. Decision gate:
`NOT_READY_FOR_PROVIDER_EXECUTION` pending fresh green hosted CI and automated
review. Real provider responses collected: 0.** The execution-integrity revision is
`stage6a-model-pilot-v1.1`. It supersedes the pre-review plan fingerprint
`b69f9e7017512b91b42ab03dfe9f5e8eea8ebddd697d11b163b245d1f37f81fd`
before any provider response existed. The scientific design did not change;
the revision specifies strict format-repair context, configuration freezing,
crash-safe resume, transport/session auditing, and repair sensitivity.

The source benchmark remains `artifacts/stage6-pilot-v1/pilot-freeze.json`
(SHA-256 `917364477c330cfeee6e368dfe9692f35238c7bfb11ce37c744f5cfa5a6336c1`),
and the pilot base remains repository SHA
`7abe966c79a461073153fa178eb394ad9406263b`. The normative machine plan is
`artifacts/stage6a-model-pilot-v1/pilot-plan.json`; its current fingerprint is
recorded in immutable `pilot-freeze.json`.

Once a completed raw response exists, plan, requests, execution manifest,
prompts, mappings, and scoring rules cannot change. A genuine validity defect
invalidates this version and requires a documented successor; model difficulty
must never cause tuning.

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

V1 supports only `openai_responses_compatible`: bearer-authenticated HTTP with
an OpenAI Responses-style request and raw `output[].content[]` extraction for
`output_text`. It is not advertised as an arbitrary-provider adapter. Provider
error envelopes and malformed/missing output are transport/protocol events, not
model answers.

Before call 1, the runner validates the complete configuration schema, safe
endpoint, supported adapter, allowed unsupported-parameter names, positive
output limit, unique IDs, unique substantive configurations, exactly one role
per record, and presence of both `standard/default reasoning` and `stronger
reasoning`. It confirms each explicitly named credential environment variable
exists without serializing its value. Parameters declared unsupported are
actually omitted (`temperature`, `seed`, and `reasoning`/`reasoning_effort`).

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

`build` is pre-execution-only and non-destructive. It creates artifacts only in
an absent or empty directory. For an exact existing pre-execution artifact set,
it compares the regenerated bytes and leaves every file untouched. It fails
closed without deleting or truncating anything if a response, transport event,
session, execution manifest, execution freeze, scored response, unexpected
file, or mismatched frozen artifact indicates that execution or analysis has
begun.

Copy `configs/stage6a-models.example.json` to a secure path, configure two real
and substantively distinct models, then use the explicit flow:

```bash
stage6a-model-pilot verify
stage6a-model-pilot run --config /secure/path/stage6a-models.json
stage6a-model-pilot score
verify-stage6a-model-pilot
```

## Execution configuration handoff

Provider execution must not start from guessed credentials, endpoints, models,
or provider capabilities. When those details have not been supplied, the
checked-in `configs/stage6a-models.example.json` is the execution-ready handoff
template. Keep the fixed roles, adapter, temperature, seed, and output limit in
that template unchanged. The operator must supply only these provider-specific
values for each configuration before `run`:

- `id`: a unique, stable configuration identifier;
- `endpoint`: the exact OpenAI Responses-compatible endpoint;
- `credential_env`: the name of an environment variable containing the secret
  (never the secret itself);
- `model`: the exact pinned model/version identifier, not a moving `latest`
  alias when a stable identifier is available;
- `reasoning_effort`: the exact provider-supported setting that fulfills the
  configuration's frozen role; and
- `unsupported_parameters`: every optional request parameter unsupported by
  that endpoint, selected only from `temperature`, `seed`, `reasoning`, and
  `reasoning_effort`.

The standard/default and stronger-reasoning configurations must remain
substantively distinct. If the selected provider does not support a reasoning
parameter, record that fact in `unsupported_parameters`; do not invent a
setting. Credentials remain exclusively in the named environment variables.
Validate the completed file and obtain any required cost/configuration approval
before provider call 1.
