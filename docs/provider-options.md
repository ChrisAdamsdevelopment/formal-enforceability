# Provider options — v1.3 and a separate Gemini proposal

Primary documentation checked 2026-10-10 UTC. This note changes no provider
configuration and authorizes no calls. Account-specific access remains UNKNOWN.

## Frozen v1.3: OpenAI only

**SUPPORTED by current documentation:** the exact `gpt-5.6-terra` model page
lists Responses API support, medium/high reasoning and a 128,000-token output
maximum. The frozen [configuration](../configs/stage6a-models.example.json)
uses `https://api.openai.com/v1/responses`, medium versus high, and
`max_output_tokens=25000`. There is no model substitution.
[Source: model documentation](https://developers.openai.com/api/docs/models/gpt-5.6-terra).

The [reasoning guide](https://developers.openai.com/api/docs/guides/reasoning)
states that the output cap includes reasoning and visible output; exhaustion
can precede a visible answer and still incur charges. Temperature and seed stay
omitted under the merged policy. Exact-treatment temperature acceptance was
not established; omission is not a claim that all API endpoints reject it.
Account access, billing, quotas, returned status/usage and actual latency remain
UNKNOWN until a separately authorized canary. A passing canary cannot show that
25,000 tokens suffices for every benchmark case.

`store=false` is always sent. It is not a universal zero-retention promise:
abuse-monitoring and prompt-cache handling have distinct controls.
[Source: OpenAI data controls](https://developers.openai.com/api/docs/guides/your-data).

## Cost exposure, not a spending guarantee

**SUPPORTED inputs / calculated scenarios:** the model page lists standard
short-context USD prices of **$2 per million input tokens** and **$12 per million
output tokens**. It also lists cached-input/cache-write rates and higher prices
above 272,000 input tokens. The following calculation assumes standard service,
short context, no caching benefit or cache-write surcharge, no tax or other fee:

\[
C=(2I+12O)/10^6\quad\text{USD}.
\]

Here \(I\) is total charged input tokens and \(O\) includes charged reasoning
and visible output. This is scenario arithmetic, not a token-count measurement.

| Planned requests, without additional authorized retries | Maximum requested output allowance | Output-only scenario cost |
| --- | --- | --- |
| Canary: one medium + one high | 50,000 tokens | $0.60 |
| Scientific initial calls: 140 | 3,500,000 tokens | $42.00 |
| Initial calls + at most one format repair per key: 280 | 7,000,000 tokens | $84.00 |
| Canary + all initial calls + all possible repairs: 282 | 7,050,000 tokens | $84.60 |

Add actual input charges: for illustration, 2,000 input tokens per scientific
initial call adds $0.56 across 140 calls; this input length is an assumption.
Repair input includes the malformed response and schema and can be larger.
Actual outputs may be much shorter. Repeated canaries/manual resumes, ambiguous
transport outcomes, caching charges, changed prices or service settings can add
cost. The harness has no dollar-denominated stop limit. Owner cost approval must
cover inputs and potential repairs, not merely the 140-key count.
[Sources: model pricing](https://developers.openai.com/api/docs/models/gpt-5.6-terra),
[pricing reference](https://developers.openai.com/api/docs/pricing).

## Gemini: separate EXPLORATORY work only

A Gemini key cannot satisfy v1.3's OpenAI model/treatment. No Gemini adapter or
configuration is introduced here. A later separately authorized protocol could
select an exact Gemini model/version, freeze fresh isolated inputs and scoring,
and retain separate manifests, canaries and append-only evidence. It must state
how provider-specific thinking controls differ; matching a label such as high
does not establish matched computation or an equivalent treatment. Never pool
that run into v1.3 or use its outcomes to tune v1.3.
[Sources: Gemini models](https://ai.google.dev/gemini-api/docs/models),
[thinking controls](https://ai.google.dev/gemini-api/docs/thinking).

**SUPPORTED:** free-tier availability is model-specific. Quotas constrain
requests and tokens and vary with project/tier/model; possession of a key does
not establish remaining quota. Avoid an invented fixed RPM/RPD budget. Record
model ID, date, returned version if available, parameters, exact prompt hashes,
usage, refusals/noncompletions and quota errors; freeze a retry policy before
execution. Hosted model changes limit bitwise reproducibility even with identical
inputs. [Pricing](https://ai.google.dev/gemini-api/docs/pricing),
[rate limits](https://ai.google.dev/gemini-api/docs/rate-limits).

**SUPPORTED privacy constraint / UNKNOWN account applicability:** Google's
unpaid-service terms permit use of submitted content/responses for improvement
and human review, and exclude sensitive/confidential/personal submissions.
The terms have regional exceptions for EEA/Switzerland/UK data use and distinguish
projects with active billing; a description such as free key does not establish
which terms apply. Determine applicable project/tier/region before authorizing
any such experiment. Use only suitable non-sensitive stimuli, never project
chats, credentials or private research memory.
[Source: Gemini API terms](https://ai.google.dev/gemini-api/terms).
