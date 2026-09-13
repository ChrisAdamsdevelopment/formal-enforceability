# Stage-5 semantic representation freeze

The answer-blind renderer follows `Game → RenderPlan → TypedClause semantic payload → deterministic text`. It never invokes the oracle. The answer-key assembler is a separate artifact layer that joins already-verified Stage-4 answers only after rendering. Frozen mappings are explicitly thawed before JSON serialization or `Game.from_dict`; callers receive defensive ordinary JSON values from `to_dict()`.

## Visibility boundaries

* **MODEL INPUT:** `{ "prompt": "..." }` only.
* **PUBLIC BENCHMARK RECORD:** prompt, opaque render-case ID, domain, variant, contract, and representation fingerprints.
* **INTERNAL BENCHMARK METADATA:** source game ID, render seed, surface bijections, and track.
* **PRIVATE ANSWER KEY:** status, exact failure probability, epsilon, and (for future restoration tasks) restoration answers.

Source display labels are declared non-semantic metadata: they are excluded from semantic signatures and never copied into prompts. Opaque case IDs provide provenance blinding, not secrecy.

## Information protocol

At the start of every round `t`, the current hidden state is `s_t`. The controller receives the current observation `o_t = obs(s_t)` before selecting its round-`t` action, remembers its entire prior observation/action history, and may privately randomize. The strategic adversary knows the current true state, prior state history available under the formal model, its own previous actions, previous controller actions, and the game/protocol, all with perfect recall. Current actions are simultaneous commitments: neither player conditions on the other's current unrevealed action, and the adversary cannot observe the controller's current private random draw before committing.

## Scientific limitations and contamination

Synthetic domains do not represent real deployments. Cross-domain agreement does not establish real-world robustness, and repeated skins are repeated measurements rather than independent cases. Absence of direct leakage does not prove absence of shortcuts. The source repository is public; opaque IDs are provenance blinding, not secrecy. Stage-5 validates representation consistency, not external validity.

> A proof establishes a property of a representation. Evidence establishes whether that representation adequately applies to reality.

Future model evaluations must disable web access, repository retrieval, code search, and connected GitHub tools unless retrieval is deliberately the treatment under study. This public benchmark must not be described as permanently secret or uncontaminated.
