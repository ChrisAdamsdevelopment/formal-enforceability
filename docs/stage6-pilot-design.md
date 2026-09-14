# Stage 6A deterministic pilot v2

The repaired pilot reports two scientifically separate tracks. **Track A** has
36 unique canonical public-evidence instances: 12 certifiably losing, 12
insufficient-information, and 12 certifiably winning. It does not fabricate a
fourth public-interface class. **Track B** has 12 distinct explicit
compatible-set diagnostics: six per-world-only gaps and six common-policy
controls. Track B is not a canonical-public-interface result, and its accuracy
must never be combined with Track A.

Every formal instance has nine renderings: three domains (abstract
mathematics, ant-colony routing, and a neutral technical system) crossed with
natural, epistemically scaffolded, and tool-assisted conditions. Thus Track A
has 324 renders, Track B has 108, and the pilot has 48 unique formal instances
and 432 public prompts. `formal_instance_id` and `render_id` are distinct.

## Solvable public prompts and private gold

Each public prompt contains exact task-specific evidence, epsilon, move timing,
the observation structure, adversary information, controller randomization,
and operationally defined answer/action choices. Track A exposes only the
state-marginal population table and the deterministic hidden-row restriction;
Track B, whose evidence object is an explicit set, exposes two neutral
state-conditioned tables. Internal game IDs never appear in public prompts.

Answer IDs `Q0`--`Q2` and action IDs `U0`--`U3` are freshly mapped per render.
Their precise, non-moralized propositions or operational consequences are
public, while ID-to-semantics mappings, gold IDs, values, compatible game IDs,
and canonical statuses are confined to `private-answer-key.json`.
`public-prompts.jsonl` contains no gold. `render-plan-manifest.json` contains
only render coordinates, and the private mapping supports exact response
canonicalization.

Natural prompts state the complete observable problem without compatibility,
partial-identification, or LP vocabulary. Scaffolded prompts add the instruction
to consider all consistent hidden models. Tool-assisted prompts allow exact
enumeration/solving but expose no answer. Condition scores remain separate.

## Leakage and metrics

The representation-only baseline is an actual leave-formal-instance-out 1-NN
evaluation, performed separately by track. All alternate renders of the held-out
formal instance are excluded from training. Features include domain, condition,
template and track, non-evidence prompt-length bucket, option counts, and neutral
ID positions; numerical mechanics and evidence text are excluded. Its measured
results are frozen rather than assigned by construction.

Metrics remain exact/coarse classification, abstention and false certainty,
high-confidence false winning, actionability quantifier confusion, policy and
outer-action correctness, epistemic-to-action consistency, cross-render
agreement/sensitivity, and separately reported condition gaps. Human response
class, confidence, action, and expertise remain supported metadata; no human or
model experiment has run.

Readiness remains `NOT_READY_FOR_MODEL_PILOT`: hosted CI and the independent
oracle cannot be validated in the current environment, and exact adaptive
\(\overline V\) over the continuous public fiber remains unresolved.
