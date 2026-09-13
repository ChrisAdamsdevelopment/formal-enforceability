# Stage 5: blinded representation freeze

Stage 5 consumes, and does not modify, the Stage-4 formal freeze. Its pipeline is `Game -> RenderPlan -> typed clauses -> prompt`. The renderer receives only a `Game`, immutable `RendererSpec`, explicit integer seed, and domain. It has no solver import or answer argument. Answer assembly is a separate build-layer operation over Stage-4 solved artifacts.

## Contracts and data boundaries

The primary contract, `enforceability-classification-v1`, asks whether a controller can keep the worst-case probability of entering failure before recovery within the finite horizon at or below epsilon. Its response schema is `{"status":"WINNING"}` or `{"status":"LOSING"}`, and `WINNING` means exactly `V*_H <= epsilon`.

The secondary `failure-value-v1` diagnostic has response schema `{"failure_probability":"1/3"}`; values are reduced exact rational strings. The separately defined `restoration-selection-v1` contract has response schema `{"restorations":["option-2","option-4"]}` and permits all tied minimum-cost, threshold-satisfying candidates. Restoration selection is never merged into classification. These two contracts are frozen for future suites; this Stage-5 corpus uses the primary contract.

`RenderedCase` fields are **PUBLIC MODEL INPUT**. The internal manifest's source game ID, seed, track, and identifier bijections are **INTERNAL BENCHMARK METADATA**. Status, exact solved failure probability, epsilon, and restoration solutions are **PRIVATE ANSWER KEY**. Prompt JSONL files contain only public fields. Opaque case IDs provide provenance blinding, not secrecy: a person with this repository and deterministic algorithm can reconstruct their mapping.

## Renderer and protocol

`RendererSpec` strictly binds renderer, language, task-contract, template, domain, ordering, identifier, numeric, protocol, and randomization versions plus variant count. Canonical JSON is SHA-256 fingerprinted. Frozen tuples, frozen dataclasses, and recursively isolated plan mappings prevent caller mutation.

Every plan contains identifier bijections, the complete surface-renamed game, ordering decisions, template selections, and typed clauses. Clause types cover initial distribution, observation aliases, action declarations and availability, every transition, terminals, rewards when nonzero, horizon, timing, both players' knowledge, objective, and answer format. Verification mechanically reverses identifier maps; it does not parse English.

The domain-independent protocol says that the controller remembers observation/action history without seeing hidden state, the opponent knows true state and past controller actions, current moves are simultaneous, current private randomization is hidden until commitment, terminal states end play, the horizon otherwise applies, and all probabilities and epsilon are exact. Its version and bytes are fingerprinted.

Supported controlled skins are `formal-plain-v1`, `access-control`, `service-routing`, `warehouse-operations`, and `industrial-process`. A warehouse rendering is not evidence about warehouse safety. An access-control rendering is not evidence about cybersecurity. Domains are semantically controlled skins over the same formal games. Cross-domain repeats are not independent cases and do not enter a future headline denominator as additional formal samples.

## Rebuild and verify

```bash
PYTHONPATH=src python -m enforceability.rendering build-freeze --artifacts artifacts/stage5-render-v1
PYTHONPATH=src python -m enforceability.rendering verify-freeze --artifacts artifacts/stage5-render-v1
```

Verification first verifies all Stage-4 dependencies, then regenerates every plan, prompt, private answer, audit, and fingerprint byte-for-byte. Direct leakage scanning permits answer tokens only in the single answer-format clause. The representation audit labels semantic, representational, provenance, and answer-direct features and reports descriptive cross-tabs without significance claims.

## Contamination and claim discipline

The formal freeze predates model testing, but it is in a public repository and is not a permanent secret holdout. Future model runs must disable web and repository tools unless retrieval is intentionally studied. Prompts omit source IDs and provenance links, but future training or retrieval can still encounter this repository. A sealed cryptographically committed holdout may be added later; Stage 5 adds no secret-management system.

Absence of direct leakage does not prove absence of shortcuts. Surface invariance does not establish deployment robustness or real-world transfer. Length correlations do not prove exploitation. Proof establishes properties of a representation. Evidence establishes whether that representation adequately applies to reality.
