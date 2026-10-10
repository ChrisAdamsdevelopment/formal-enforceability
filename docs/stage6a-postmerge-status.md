# Stage 6A v1.3 — post-merge status and offline handoff

Dated recovery: 2026-10-10 UTC. This document supplements the unchanged
[pre-merge audit](stage6a-premerge-audit.md); its older main/open-PR observations
remain historical. The scientific specification is the frozen artifact set.

## Repository evidence and local recovery

**SUPPORTED:** GitHub records [PR #14](https://github.com/ChrisAdamsdevelopment/formal-enforceability/pull/14)
merged at **2026-10-10 02:52:12 UTC**. Current main at inspection is
`3f4e71d585f981671419e2e14c450634ed3540de`; its parents are
`9e5c8d4855b0cdea9e396cee0ea809fd3dbd6cf7` and source head
`8a999b245e5613f3c2dd69f32a7963a8c49bf13b`. The merge tree equals the source
head tree. No expected SHA or merge-history discrepancy was found.

Post-merge [hosted workflow 38018537697](https://github.com/ChrisAdamsdevelopment/formal-enforceability/actions/runs/38018537697):
**PASS**, completed successfully; all 16 reported job steps succeeded.
Observation timestamp: **2026-10-10 03:10:33 UTC** (run updated 03:07:18 UTC).
Local follow-up branch: `codex/postmerge-state-offline-preflight`, based on
that fresh main. Changes are documentation only; no PR, push or merge performed.
Do not confuse main's hosted checks with hosted checks of this local follow-up.

**Path discrepancy, explicitly unresolved historically:** the owner identified
the historical root as `D:\formal-enforceabilty`. Literal-path checks at
2026-10-10 03:02:07 UTC found that path absent and independently located the
ordinary directory `D:\formal-enforceability` and Git top level
`D:\formal-enforceability\repo`. Origin matches this repository. This task did
not rename or move anything; a prior rename is UNKNOWN. The commands below use
the actually verified checkout, not an inferred historical spelling. Local
notes, downloaded archive and independent files were preserved. Two pre-existing
inaccessible pytest-cache directories were left alone; tracked files were clean
before the branch was created.

## Freeze verification

**IMPLEMENTATION-VALIDATED:** read-only comparison of the approved source head,
merge commit and checkout found no mismatches across all **126 artifact files**.
The broader comparison also covered runtime, tests, configuration, packaging and
the historical pre-merge audit (185 protected files total). Nothing was rebuilt,
normalized or repaired. Historical v1.1/v1.2 and Stage 6 remain unchanged.

All **70** v1.3 subject objects equal v1.2 after removing only condition, domain,
track, formal_instance_id, render_id, template_id and schema_version. Recursive
inspection finds none of these fields in subject objects; all prompt hashes
match the adapter's exact compact UTF-8 input string (not the enclosing HTTP
body). Outer evaluator attribution is retained. Scientific plan, H1–H6, mappings,
conditions, thresholds, metrics, sample selection and model/treatment remain
byte-identical to the merged source. All **140** keys match both source and merge.
Offline invalid-count probes reject zero, one and three configurations without
credential lookup. The accepted configuration has exactly medium and high roles.

SHA-256 fingerprints (paths relative to `artifacts/`):

| File | SHA-256 |
| --- | --- |
| stage6-pilot-v1/pilot-freeze.json | `917364477c330cfeee6e368dfe9692f35238c7bfb11ce37c744f5cfa5a6336c1` |
| stage6a-model-pilot-v1/pilot-plan.json | `ab393f32b9da8f8b27f1d45cdd1795a88b35073ce9eef948811e5205a4dee2f5` |
| stage6a-model-pilot-v1/request-manifest.json | `1181bcdebd3e09e3b0793d219578e1164fd3d653448afcdfd4303e85ee752c77` |
| stage6a-model-pilot-v1/pilot-freeze.json | `6896a50e173fd6175172a9ab08313e88bc61151342a4c97963aeea89166d79ac` |
| stage6a-model-pilot-v1.2/pilot-plan.json | `15109fb0f023dbfa56bafff2dcd2b3c14fd761bcadf1d669220fa8d3f8cf2f82` |
| stage6a-model-pilot-v1.2/request-manifest.json | `010a41d2b60df1b43866228eab4c1cab59c54b501646ef79e093ead829349ef4` |
| stage6a-model-pilot-v1.2/pilot-freeze.json | `4f7835badc8ed1e1d7b1ce9665bd48c3811436d8643c3a92f7bf7913a7de9958` |
| stage6a-model-pilot-v1.3/pilot-plan.json | `1d9a98f126cf7f556e36b2173428c04d86b1f0befb00d9334b2f54bfdf00ee02` |
| stage6a-model-pilot-v1.3/request-manifest.json | `8b1d1b0279030b23fb197e19ab4f3e08344e5ee7a980a62d995838314dcf062e` |
| stage6a-model-pilot-v1.3/pilot-freeze.json | `5b49bbcd85edde420448fcceed2b8531546b65827a916c8733b68399ff2f5571` |

The sorted execution-key list, each key followed by LF, hashes to
`6b27dffa3312ae2bb1e70807b327544a22efb526f99531197e377e063a78688d`.
The unchanged example configuration file hashes to
`993f3e5fddf73ea6d0fbb59eaf2592c7dbdc8490da1eb9ee78f84cdc995f21c7`.
These are verification fingerprints, not new scientific artifacts.

**SUPPORTED:** all v1.1/v1.2/v1.3 evidence JSONL streams are zero bytes, with no
scientific execution manifest/freeze. Recorded real provider responses = **0**.
No completed real canary or scientific execution is evidenced. This task made
zero provider calls or model-list probes. Public documentation/GitHub/package
retrieval is distinct from provider API testing. Fake-transport tests operate
on temporary copies, not scientific evidence. No scoring of actual evidence
was performed.

## Offline verification record

Commands ran in the checkout's `.venv` (Python 3.12); hosted CI uses Python 3.11.
The suite blocks socket connections in tests. No command below initiates a
provider request. Full stdout/stderr, exit codes and timings are retained in
local `research-memory/evidence/postmerge-2026-10-10/` outside the checkout.

| Exact command, environment executable prefix omitted | Result |
| --- | --- |
| `python -m pip install -e '.[test]'` | PASS, exit 0 |
| `ruff check src tests` | PASS, exit 0 |
| `python -m pytest` | PASS, exit 0; 662 passed in 565.21 seconds |
| `validate-independent-oracle` | PASS, exit 0 |
| `verify-identifiability` | PASS, exit 0 |
| `verify-prior-art-review` | PASS, exit 0 |
| `verify-stage6a-pilot` | PASS, exit 0 |
| `stage6a-model-pilot verify` | PASS, exit 0 |
| `verify-stage6a-model-pilot` | PASS, exit 0 |
| `git diff --check` | PASS, exit 0 |

All ten commands completed between 02:58:37 and 03:08:33 UTC on 2026-10-10.
Tests ran with HEAD at the verified merge; the follow-up changes only documents.
Local logs establish the 662-test count; hosted step results are separately
reported above. No skipped or failed check is represented as passing.

Six independent numerical threshold cases remain unresolved; passing comparison
checks does not convert them into exact certificates. See
[PROJECT_STATE](../PROJECT_STATE.md) for formal scope, the negative actionability
search, unresolved adaptive upper value and source-archival/recovery gaps.
The old environment-specific NOT_READY statement in `stage6-pilot-design.md`
is a historical foundation status; its construct limitations remain, while
current execution gates are recorded here. No foundation artifact was changed.

## Operational handoff and authorization gates

### A. Verified offline

The merged [adapter](../src/enforceability/model_pilot.py) constructs independent
Responses requests, sends `store=false`, omits conversation reuse and reads only
completed output-text messages with ID/usage provenance. Noncompleted envelopes
are preserved and remain missing outcomes. Only malformed completed output may
receive one format-only repair; semantic errors get no retry. The same adapter
serves the segregated [canary](../src/enforceability/provider_canary.py).
No in-scope defect requiring an implementation change was identified.

The scientific execution manifest binds configuration, selected plan/request
bytes, current Git SHA and source hash. Journal intents are fsynced before
transport and envelopes before parsing; an exclusive writer marker prevents
concurrent run/score. Evidence and repair attribution are checked. Score requires
all 140 terminal outcomes and full freeze integrity; run/score reject post-freeze
mutation. These are implementation guarantees with explicit crash boundaries,
not an exactly-once network or provider-signature guarantee.

### B–C. Unknown live facts and exact prerequisites

Account access, available credits/quotas, live parameter acceptance, latency,
returned usage and actual model behavior are UNKNOWN. Current documentation
supports the required API/model; see [provider options](provider-options.md).

Use the unchanged `configs/stage6a-models.example.json`: OpenAI Responses over
HTTPS, `gpt-5.6-terra`, medium/high, 25,000 max output tokens. `temperature=0` and
`seed=null` are recorded values but both are omitted from the actual payload.
Exactly two configurations are required. The key must be loaded externally as
`OPENAI_API_KEY` in the operator process; the JSON contains its environment
variable name only. No key was requested, inspected, tested or stored in this
task. Do not paste it into chats, docs, logs, command history or configuration.

Select and pin the execution checkout before authorization. Real transport
requires committed runtime/configuration sources. A receipt also binds the full
Git SHA: even a docs-only commit invalidates an older receipt. Configuration,
source or checkout drift requires a new separately authorized canary. The plan's
historical `repository_sha` is a design-base reference, not the live harness SHA.

### D. First separately authorizable live action — canary only

Owner approval must cover **at most two billable, non-benchmark requests**, one
medium and one high, with no repair/retry. A failed first request stops the
canary before the second. The [cost note](provider-options.md) estimates up to
$0.60 output allowance plus input/other applicable charges for this attempt.
This paragraph and the command below are a proposal, not authorization.

From the verified `D:\formal-enforceability\repo` checkout, after external
credential setup and explicit approval, the proposed exact command is:

```powershell
.\.venv\Scripts\stage6a-model-pilot.exe canary --config .\configs\stage6a-models.example.json --output 'D:\formal-enforceability\provider-preflight\canary-20261010-001' --acknowledge-provider-calls
```

The output path was absent at the offline check and is outside the checkout.
It must still be absent when authorized; never overwrite an earlier attempt.
No canary output directory was created by this task.

### E. Required canary evidence and success check

Preserve `canary-report.json` and `canary-evidence.jsonl` together outside the
checkout. The report must say PASSED, `transport_mode=real`, scientific_requests=0,
and bind configuration, harness Git/source, canary source and evidence hashes.
The two evidence rows must retain exact fixed payloads, completed provider
envelopes, IDs and usage, and the accepted `{"ping":"ok"}` answer.
Archive the invocation, environment/version and operator timestamps separately
without credentials. The current report records its creation timestamp; do not
invent unrecorded per-request timing.

A normally returning CLI can still emit NOT_PASSED. Validate the actual receipt
with this **offline** command after the authorized canary; merely seeing exit 0
or running the scientific `verify` command does not validate a canary receipt:

```powershell
.\.venv\Scripts\python.exe -c "from pathlib import Path; from enforceability.provider_canary import verify_receipt; print(verify_receipt(Path('configs/stage6a-models.example.json'), Path('D:/formal-enforceability/provider-preflight/canary-20261010-001/canary-report.json'))['status'])"
```

### F. Stop conditions

Missing credentials/access, request rejection, timeout/transport failure,
noncompletion, wrong fixed answer, missing provenance, invalid receipt, drift,
freeze/hash mismatch or a stale writer marker blocks progression. A canary
failure needs investigation; no automatic retry or budget/prompt tuning is
authorized. During scientific execution, noncompletion is retained and skipped,
not silently retried; it prevents scoring even if other keys are attempted.

An unfinished intent or received envelope without terminal evidence blocks
automatic resume as AMBIGUOUS_PROVIDER_ATTEMPT. Preserve all bytes/markers and
obtain an audited recovery plan; never delete evidence to make resume pass.
Even an explicit transport error does not prove no billable work happened.
The merged harness permits a separately initiated resume of some transport
errors, but this task authorizes no such retry or recovery.

### G–H. Separate scientific authorization, then analysis/publication

After a passing canary, review/preserve its receipt and select the same pinned
configuration/revision. Obtain separate explicit authorization for **140 frozen
scientific keys**, including the possibility of up to 140 format-repair requests
and associated input/output charges. No authorization follows automatically from
tests, merge or canary success. Gemini substitution is outside v1.3.

Only after complete evidence and separate applicable approval may frozen scoring,
verification, repair sensitivity and analysis proceed. Preserve tracks/conditions,
formal-unit dependence, missing outcomes and negative results. Publication needs
bounded EXPLORATORY interpretation and completion of outstanding reviewed-source
archival work; no new novelty or hidden-cognition conclusion is licensed.
