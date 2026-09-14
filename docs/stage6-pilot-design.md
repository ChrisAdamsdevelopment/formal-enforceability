# Stage 6A deterministic pilot

The frozen pilot contains 48 canonical tasks, 12 per hierarchical status, and
432 render records (three domains times three experimental conditions per
task). Domains are abstract mathematics, ant-colony routing, and a neutral
technical system. Options/actions use neutral identifiers and deterministic
seeded permutations. Render answers canonicalize to the same formal status.

Conditions remain separate: `natural` supplies no compatibility/LP hint;
`epistemically_scaffolded` asks the respondent to reason over all compatible
models; `tool_assisted` permits exact enumeration or an LP. Scores must never
pool these conditions.

The outer wrapper includes continuation, deferral, and robust-controller cases;
information requests are outer actions, not part of the one-step theorem.
The schema reserves response class, confidence, action choice, and expertise
for later nonexpert, technical, and expert human comparisons. No human or
frontier-model evaluation has been run.

Metrics are exact-status and coarse WINNING/LOSING/INSUFFICIENT accuracy;
actionability-refinement accuracy; correct/false abstention, false certainty,
and high-confidence false-WINNING probability conditional on
\(\underline V\le\epsilon<\overline V\); quantifier-confusion frequency,
recommended-policy correctness and robust-policy violations; and, conditional
on a correct epistemic statement, epistemic-to-action consistency. Rendering
metrics are canonical agreement, worst-render accuracy, option/domain
sensitivity, and confidence variance. Condition gaps are reported separately.

The representation-only harness records chance, majority, and template/domain
baselines. The balanced freeze makes all three 1/4, so it is not flagged as
contaminated. This is only a design-time surface check, not evidence about
future free-form prompts.

Important qualification: the 12 non-uniform tasks use the explicitly declared
compatible set `{d051,d204}`. They validate the generic experimental construct,
but no such gap exists in the exhaustively searched frozen public-signature
classes. Consequently the corpus has all four formal categories without
semantic labels, but it is **not ready** for a model pilot intended to make
claims specifically about the canonical public-signature interface.
