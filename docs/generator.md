# Stage-2 procedural formal-game generator

## Architecture and versions

Stage 2 is a formal experimental instrument. `GeneratorConfig` is passed to
`generate`, which constructs and schema-round-trips a `Game`. Only the separate
`build_manifest` step calls the exact Stage-1 oracle and restoration evaluator.
Structural output therefore has no status or answer field. Each `GeneratedGame`
carries its immutable `GeneratorConfig` and a canonical config fingerprint;
`build_manifest(generated)` derives all provenance from that artifact. The old
two-argument form verifies exact config equality and rejects mismatches. Generator version
`stage2.v2`, schema version, and oracle version are independently recorded.

The public pipeline is:

```python
generated = generate(config)
manifest = build_manifest(generated)  # oracle invocation occurs here
```

`GeneratorConfig` records family, integer seed, exact horizon, action counts,
ambiguity/aliasing controls, common-action availability, response coverage,
probe availability/informativeness/delay, intervention round, exact epsilon,
stochasticity switch, neutral structural mode, and complexity limits. Invalid
Booleans must be actual `bool` objects; epsilon follows the Stage-1 exact-number
contract (floats and booleans are rejected); and modes are validated per family.
Probe and timing horizons must be at least two, probe delay must be positive,
and the probe horizon must include the probe, its delay, and the decision. Invalid
fields raise `GenerationError`; over-limit candidates return
`GenerationRejected`, including configuration, seed, estimates, and the reason
`estimated_oracle_complexity`. A rejection has no game-theoretic status.

## Seed semantics and canonical representation

Each call creates a fresh `random.Random(config.seed)` (Python's documented
MT19937 implementation). There is no module-global random state. Random draws
are made in a fixed order by generator version; changing implementation order
requires a generator-version change. Reproducibility consequently also assumes
a compatible Python `random` implementation. Probabilities are built as
`Fraction` values and serialized as integer or rational strings.

The reproducibility identifier is lowercase hexadecimal SHA-256 of UTF-8
canonical Game JSON: all `Game.to_dict()` fields, sorted keys, compact JSON
separators, with `display_labels` replaced by an empty object. Thus states,
initial distribution (including explicit zero entries), actions, observations,
observation map, all transitions, terminal sets, horizon, epsilon, availability,
legitimate rewards, and schema version contribute. Display labels do not. This
is an identifier, not cryptographic attestation or a security guarantee.

## Structural families

* **observation-conflict** creates aliased initial states whose response action
  is selected by a seeded permutation; a common action and adversary response
  count are configurable.
* **authority-limitation** varies controller actions, adversary capabilities,
  response coverage, and the existence of a robust response.
* **probe** includes a first-round probe, explicit hidden delay stages,
  informative or aliased decision observations, configurable availability and
  a common option. Every non-progress action at a delay or decision deadline
  reaches failure, so waiting cannot evade the decision. `probe_delay = k`
  means exactly `k` action rounds elapse from selecting the probe until the
  informed decision action is available: `k=1` reveals on the probe transition;
  larger values add `k-1` distinct hidden delay stages. In `too-late` mode the
  deadline expires at the first delay stage before revelation can be used.
* **timing** places an intervention on a declared round while a waiting action
  exercises action-availability and terminal timing semantics.
* **capability-restriction** creates relevant and irrelevant adversary
  capabilities and a declared restriction library, including multi-capability
  and unavailable-repair modes.
* **mixed-restoration** declares observation refinement, adversary restriction,
  and timing/availability candidates. Legitimate rewards are declarations on
  the game; candidate cost is always computed by the existing endogenous
  legitimate-utility evaluator rather than assigned by the generator.

These parameters describe construction, not an oracle answer. Modes are
structural switches and family frequencies have no prevalence interpretation.

## Transformations, manifests, and filtering

`transform` applies a Stage-1 `Restoration`; `add_controller_action` adds an
explicit total transition slice. Both return a `TransformationRecord` with
parent/child IDs, transformation type, exact changed formal field names,
generator version, and transformation seed. Other formal fields are copied.
The category is derived from the actual operation (or `compound`), and changed
fields are obtained by comparing validated before/after formal dictionaries.
A mismatched legacy caller label is rejected. Records make no outcome claim.

A manifest separates `config` and `formal_game` from `oracle`, restoration
evaluations, structural `descriptors`, and optional ancestry/transformation.
Descriptors include state/reachable-state and action counts, horizon,
observation-class sizes, ambiguous classes, stochastic branching, restoration
count, and oracle explored profiles. They are not a universal difficulty score.
The explicit recursive banned-key check rejects `winning_case`, `losing_case`,
`correct_action`, `safe_restoration`, and `fatal_branch`. This small guard is not
proof that metadata contains no leakage.

`filter_after_solution` supports transparent retention decisions only after a
manifest and oracle output exist, returning the complete oracle result, game ID,
decision, and declared reason. It does not prescribe benchmark balance.

## Complexity and batch interface

Limits cover effective generated states, effective horizon, controller histories,
policy profiles, and candidates per batch. Cheap family-exact dimensions are
checked before allocating the game. After construction, bounded traversal of
the actual nonterminal game estimates information histories and profiles before
any oracle call. Saturating multiplication/power stops at the declared limit,
so pathological integer inputs cannot trigger enormous exponentiation.
Estimates are deliberately conservative upper bounds and can reject tractable
games; they do not silently drop cases.
Generate a batch with:

```bash
python -m enforceability.generation --family observation-conflict \
  --seed-start 0 --count 100 --output artifacts/dev/
```

One canonical JSON manifest is written per seed plus `summary.json`. Existing
paths cause an error rather than overwrite. Summary status counts come only from
oracle results; rejected candidates are counted separately.

## Biases, assumptions, and scientific limitations

The families are small, stylized, often deterministic, uniformly initialize
their live states, and use systematic identifiers and simple transition
templates. Seed diversity may permute only a response relation. The profile
estimate is not the oracle's exact workload. Reachability descriptors ignore
policy feasibility when taking their conservative transition closure. Synthetic
legitimate rewards are formal utility declarations and not economic costs.

Scientific assumptions introduced in this implementation are: uniform initial
mass across ambiguous states; simultaneous controller/adversary action in each
oracle round; terminal absorption as already defined by Stage 1; MT19937 as the
versioned RNG mechanism; and conservative product-form complexity estimates.
The repaired probe additionally assumes that any action other than prescribed
delay progress consumes the deadline and fails, and that `too-late` means the
deadline expires at the first post-probe delay stage. These choices must be controlled or revised before benchmark conclusions are
drawn. Correlated templates, repeated isomorphic games, parameter imbalance,
identifier leakage, or changes in Python RNG behavior could invalidate naive
later benchmark use. Canonical IDs detect identity, not graph isomorphism.

Procedural generation does not create independent evidence about real AI systems. It creates formal test cases whose mathematical ground truth is supplied by the formal oracle.

Generated games do not represent deployments; family frequency does not
estimate real-world frequency; structural descriptors do not predict LLM
difficulty; status balance has no natural prevalence; restoration utility is
not real cost; and generation does not discover or externally validate safety
theory. A next stage should freeze audited regression corpora and distributions,
check isomorphism and leakage more deeply, then add rendering only as a separate
layer without modifying formal artifacts or oracle outputs.
