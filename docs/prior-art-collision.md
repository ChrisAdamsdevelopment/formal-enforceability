# Prior-art collision review: public evidence and strategic enforceability

## Decision, scope, and evidentiary rule

This review compares the exact frozen Propositions A–D in
[`threshold-identifiability.md`](threshold-identifiability.md) with theorem statements—not
keyword overlap. The reviewed project commit is
`ff706903ca742d516d4ad58e0d665c36de51be97`. **Decision: PAPER SHAPE B —
THEORY + BENCHMARK.** The examples are valuable exact tests of false certainty,
but generic partial-identification logic and feedback-dependent coverage make a
headline claim of a new general insufficiency principle untenable. A plausible
research gap remains: operational information conditions for identifying a
minimax threshold bit with strictly less information than value, equilibrium,
or model recovery.

The machine-readable record is
[`collision-matrix.json`](../artifacts/prior-art-review-v1/collision-matrix.json).
It distinguishes a theorem's target and quantifiers from surrounding motivation.
No PDF is committed. Primary locators are the arXiv, OpenReview, DOI, or
proceedings links in the tables. Version-specific theorem numbers should always
be paired with the listed version because BOMB/OEF numbering evolved.

### Frozen comparison target

* **A:** equal `I_public`, unequal exact value.
* **B:** equal `I_public`, values on opposite sides of `V_H <= epsilon`.
* **C:** unequal compatible values but a constant threshold bit.
* **D:** full support on every public joint action is insufficient when a
  deployment adversary sees latent state erased by the collection interface.

Nothing here changes the canonical families, witnesses, oracle, independent
validator, IIEFG reduction, or frozen artifacts.

## Interface crosswalk and reduction discipline

`I_public` is the population law of stopped public records under the specified
state-blind full-support collector; it logs observations, completed joint
actions, and terminal outcome, but not `s_t`. `I_node` additionally exposes the
underlying reachable node/state-history identifier, information-set identifier,
and state-conditioned chance law. `I_full` exposes the complete semantic game,
including unreachable transition rows. These are population interfaces, not
claims about finite-sample estimation.

A state-indexed offline tuple `(s_h,a_h,b_h,r_h,s_{h+1})` cannot be mapped to
`I_public`: the concrete extra variable is `s_h` (and hence a conditional law
by state). Conversely, samples do not generally expose the unreachable rows in
`I_full`. Thus “more action coverage” never repairs the loss of the conditioning
variable. No reviewed collision is labelled a direct corollary: no source
reduction simultaneously preserves our games, `I_public`, state-blind coverage,
and threshold estimand.

## Source-by-source comparison

### Li et al., *Offline Equilibrium Finding* (OEF)

Primary source: [arXiv:2207.05285](https://arxiv.org/abs/2207.05285), 2022
submission/later arXiv revision reviewed. Relevant locations: §3 formal OEF and
offline trajectory data; §4 model-based result.

| Field | Exact comparison |
|---|---|
| Game class / information / timing | Finite imperfect-information extensive-form games; histories, players, legal actions, and information partitions belong to the represented game. Sequential tree timing follows the EFG. |
| Offline evidence / learner observation | Fixed trajectories assigned to represented histories/nodes and actions to estimate a game model. That node/history index is absent from `I_public` whenever latent histories share a public record. |
| Coverage | Strategically relevant history/node-action coverage for the model-based method; later BOMB makes the uniform quantitative form clearer. This is not merely positive support for public joint actions. |
| Estimand | Equilibrium strategy/profile and true-game exploitability of the learned-model solution—not a threshold bit and not a sharp compatibility set for exact value. |
| Guarantee / necessity | Model-estimation-to-equilibrium convergence under assumptions. The theorem is sufficient for the analyzed pipeline; it is not an all-algorithms threshold impossibility. |
| Interface status | `I_public`: **SOURCE STRICTLY RICHER** (underlying history/node index); `I_node`: **INCOMPARABLE** (closely node indexed, but finite trajectory sample versus a population chance-law interface); `I_full`: **PROJECT INTERFACE STRICTLY RICHER** (complete semantic rows). |
| Closest proposition / formal relation | D; **RELATED BUT FORMALLY DISTINCT**. It warns that public action support is not node-action coverage, but does not prove A–D. |

### Li et al., ICLR-2025 OEF/BOMB revision (`Re5iu0hBTs`)

Primary source: [OpenReview primary PDF](https://openreview.net/forum?id=Re5iu0hBTs),
*Offline Equilibrium Finding in Extensive-Form Games: Datasets, Methods, and
Analysis*, ICLR 2025 submission/revision. The exact sequence is Definition 4.1
(uniform coverage), Definition 4.2 (epsilon-equilibrium coverage), Assumption
4.3 (sufficiently small neural-network training error), Theorem 4.4 (MB
coverage/convergence), Theorem 4.5 (BC coverage/convergence), and Theorem 4.6
(BOMB performance relation).

| Field | Exact comparison |
|---|---|
| Game / data | Finite IIEFG model plus offline episodes used to estimate node/action-conditioned dynamics. Information sets are part of the representation, and samples used by the estimator are assigned to underlying nodes/actions. |
| Coverage | Definitions 4.1–4.2 define uniform and epsilon-equilibrium coverage. These are not four-way public joint-action support. |
| Exact logic | Under Assumption 4.3, Theorem 4.4 uses **if and only if** for the stated model-based algorithm convergence guarantee. It is therefore algorithm/framework-specific necessity and sufficiency—not merely sufficiency. |
| Limits of the iff | It is **not** an all-algorithms information-theoretic lower bound, a theorem about arbitrary functionals, exact equilibrium-value identification, or `1[V<=epsilon]`. Theorems 4.5–4.6 concern BC/BOMB performance, not those identification objects. |
| Interface status | `I_public`: **SOURCE STRICTLY RICHER** because node/state identity is erased by `I_public`; `I_node`: **INCOMPARABLE** because finite samples and a population node-conditioned interface differ; `I_full`: **PROJECT INTERFACE STRICTLY RICHER**. |
| Witness-B test | Retaining the node/state-action evidence object separates Witness B's state-conditioned outcomes. The games remain equivalent only after discarding the labels required by the source evidence object. |
| Collision | A–D: **RELATED BUT FORMALLY DISTINCT**. The iff does not create an interface- and estimand-preserving reduction. |

### Li et al., ICLR-2026 OEF/BOMB revision (`h8u0KWgg9C`)

Primary source: [OpenReview primary PDF](https://openreview.net/forum?id=h8u0KWgg9C),
same title, ICLR 2026 submission/revision. It retains Definition 4.1 (uniform
coverage), Definition 4.2 (epsilon-equilibrium coverage), Assumption 4.3
(training-error condition), and Theorems 4.4–4.6 for MB, BC, and BOMB
performance respectively.

The logical wording is materially different: Theorem 4.4 states that the MB
guarantee holds **if** its conditions hold and that, if either condition fails,
the guarantee **may no longer hold**. This review does not turn that warning
into an iff. It also does not quantify over all algorithms, identify exact
value, or prove threshold-bit nonidentification. Its interface mapping,
Witness-B incompatibility, and A–D verdict remain the same as the 2025 version.

### Li, 2025 doctoral thesis

Primary source: Shuxin Li, *Scalable, Generalizable, and Offline Methods for
Imperfect-Information Extensive-Form Games*, Nanyang Technological University
(2025), [official NTU faculty-hosted thesis PDF](https://personal.ntu.edu.sg/boan/thesis/Li_Shuxin_PhD_Thesis.pdf).
The BOMB treatment is Chapter 6, §6.5. The exact references used here are
Assumption 6.3 (random dataset as uniform cover), Assumption 6.4 (expert dataset
as equilibrium cover), Table 6.2 (theoretical-results summary), and Theorem 6.6
(BOMB convergence under random/expert datasets). Intermediate results 6.4/6.5
are deliberately not assigned a Lemma/Theorem label because they are unnecessary
to this comparison and the searchable text is inconsistent. No separate NTU
institutional-repository record was located; the official NTU-hosted PDF is the
stable primary locator used here.

### OEF/BOMB version delta

| Version | Coverage definition | Result numbering | Target estimand | Necessity/sufficiency wording | Algorithm-specific? | Threshold-identifiability result? |
|---|---|---|---|---|---|---|
| 2022 OEF, arXiv:2207.05285 | node/history-action coverage in the original OEF formulation | §3 data/problem; §4 model-based analysis; numbering is not imported into later versions | equilibrium/profile and exploitability through a learned model | sufficient conditions for analyzed procedure | Yes | No |
| ICLR 2025, `Re5iu0hBTs` | Def. 4.1 uniform; Def. 4.2 epsilon-equilibrium coverage | Assumption 4.3; Theorems 4.4 MB, 4.5 BC, 4.6 BOMB | algorithm convergence/performance | Thm. 4.4 is **iff** under Assumption 4.3 | Yes | No |
| 2025 NTU thesis | Assumption 6.3 random/uniform cover; Assumption 6.4 expert/equilibrium cover | §6.5; Table 6.2; Theorem 6.6 | BOMB convergence under random/expert datasets | convergence under the stated dataset conditions | Yes | No |
| ICLR 2026, `h8u0KWgg9C` | Def. 4.1 uniform; Def. 4.2 epsilon-equilibrium coverage | Assumption 4.3; Theorems 4.4 MB, 4.5 BC, 4.6 BOMB | algorithm performance guarantees | **if** conditions hold; if either fails, guarantee **may no longer hold**—not recorded as iff | Yes | No |

**Fresh collision audit.** The 2025 iff remains scoped to one algorithm and
Assumption 4.3, so it proves none of A–D directly. The 2026 revision does not
strengthen this into all-algorithms necessity. Neither version identifies exact
equilibrium value or studies a threshold bit. Neither permits Witness-B games
to remain observationally equivalent while retaining its node/state-action
evidence. Consequently the stronger corrected record changes neither the
A–D scores nor Paper Shape B; that conclusion follows from the mismatched
quantifiers, evidence object, and estimand rather than from weakening BOMB.

### Cui and Du, *When is Offline Two-Player Zero-Sum Markov Game Solvable?*

Primary source: [arXiv:2201.03522](https://arxiv.org/abs/2201.03522), arXiv v3 /
NeurIPS 2022. Exact references: Definition 3.1 single-policy concentration;
Definition 3.2 unilateral concentration; Theorem 4.3 sufficiency; Theorem 4.4
necessity/lower bound; §§2–4.

| Field | Exact comparison |
|---|---|
| Game / observations | Finite-horizon tabular simultaneous-move zero-sum Markov game. Both players' policies and the learner use the same Markov state. There is no controller-coarsened observation paired with an opponent-private true state. |
| Dataset | Offline trajectories/transition records contain the state, joint action, reward, and next state. The behavior distribution supplies state-action occupancies; knowing the behavior policy is not what creates the result. |
| Single-strategy concentration | Controls density/occupancy ratios only for the equilibrium policy/profile relative to the dataset. |
| Unilateral concentration | Controls occupancies obtained by fixing either equilibrium player while allowing every unilateral policy of the other player; it is quantitative, not positive support alone. |
| Sufficiency | Theorem 4.3 gives a high-probability policy/duality-gap guarantee under unilateral concentration. |
| Necessity | Theorem 4.4's hard-instance quantifiers show that single-policy concentration alone is insufficient for uniformly learning a Nash solution at the claimed accuracy/sample scale. It is not a lower bound for every nonconstant functional or for arbitrary threshold bits. |
| Estimand | Nash policies/profile and duality gap; equilibrium-value accuracy follows from policy guarantees where stated, but sharp exact-value identification and threshold classification are not studied. |
| Interface status | `I_public`: **SOURCE STRICTLY RICHER** (`s_h` and state-conditioned transition); `I_node`: **INCOMPARABLE** (common-state Markov tuples versus one-sided EFG nodes/population laws); `I_full`: **PROJECT INTERFACE STRICTLY RICHER** (all semantic rows). |
| Collision | D and A–C: **RELATED BUT FORMALLY DISTINCT**. |

**Attempted one-step translation.** Treat `(s_0,s_1)` as the Markov state,
controller/adversary actions as simultaneous actions, failure as reward, and
append an absorbing terminal. This maps the payoff table into a one-step Markov
game, but it fails to map the experiment: Cui–Du record `s`, both policies may
condition on it, and our controller and `I_public` may not. Mapping only the
data to `I_node` still fails to preserve the controller's restricted
information unless their policy class is separately constrained. Consequently
Proposition D is neither a special case nor a direct corollary of Theorem 4.4.

### Yan, Li, Chen, and Fan, model-based offline zero-sum Markov games

Primary source: [Operations Research DOI 10.1287/opre.2022.0342](https://doi.org/10.1287/opre.2022.0342),
version of record reviewed. Relevant locations: §2 model/data; Assumption 1
unilateral concentrability; main pessimistic model-based upper-bound theorem
and minimax lower-bound theorem.

| Field | Exact comparison |
|---|---|
| Model/data/coverage | Tabular finite-horizon common-state Markov game; offline state/joint-action transition tuples; quantitative unilateral concentrability. |
| Recovery | Nash policies, duality gap, and value consequences, with sharp or near-sharp finite-sample rates. |
| Interpretation | Strengthens the statistical/rate case for unilateral coverage in the fully observed model; it does not change coverage into public support or supply a latent-coupling threshold lower bound. |
| Mapping | `I_public`: **SOURCE STRICTLY RICHER** (`s_h`); `I_node`: **INCOMPARABLE**; `I_full`: **PROJECT INTERFACE STRICTLY RICHER**. |
| Collision | A–D: **RELATED BUT FORMALLY DISTINCT**. |

### Chen et al., KL-regularized offline zero-sum Markov games

Primary source: [arXiv:2605.13025](https://arxiv.org/abs/2605.13025), **arXiv v1, submitted 13 May 2026**. The official submission history was rechecked and contains only v1. Relevant items are its KL-regularized objective, unilateral
coverage definition, and main finite-sample upper/lower bounds; theorem numbering from that v1 record.

The common Markov state remains in the data and both players' information;
regularization modifies the equilibrium target and coverage/rate tradeoff. It
does not make public joint-action support sufficient and does not study a
threshold bit. Mapping: `I_public` **SOURCE STRICTLY RICHER**, `I_node`
**INCOMPARABLE**, `I_full` **PROJECT INTERFACE STRICTLY RICHER**. Collision:
**RELATED BUT FORMALLY DISTINCT**. Later regularized theory therefore changes
the estimand and statistical difficulty, not the key interface mismatch.

### Offline congestion games: feedback changes coverage

Primary source: [arXiv:2210.13396](https://arxiv.org/abs/2210.13396), conference
version associated with ICLR 2023. Relevant locations: §3 feedback models and
Theorems 1–3 for trajectory/facility/agent feedback guarantees and lower
bounds (numbering in the reviewed conference version).

| Field | Exact comparison |
|---|---|
| Model / feedback | Finite congestion games, with offline joint actions and different levels of payoff feedback (trajectory, facility, or more decomposed feedback). |
| Coverage / target | Feedback-specific structural coverage for approximate Nash recovery; upper and lower bounds change when the feedback interface changes. |
| Mapping | `I_public`: **INCOMPARABLE** (payoff aggregation and congestion structure differ); `I_node`: **INCOMPARABLE** (facility is not a latent tree node); `I_full`: **PROJECT INTERFACE STRICTLY RICHER** for the project game. |
| Collision | D: **KNOWN GENERAL PHENOMENON, PROJECT-SPECIFIC EXACT WITNESS**. The general proposition that richer feedback can reduce data-coverage requirements is established. The paper does not prove the one-sided latent-state minimax or threshold witness. |

Accordingly the project must abandon any broad claim that it discovered the
principle “coverage sufficiency depends on feedback.” Its contribution can only
be a strategic-enforceability instantiation under the exact frozen interface.

### Horák et al., zero-sum one-sided POSGs

Primary source: [arXiv:2010.11243](https://arxiv.org/abs/2010.11243) and
[Artificial Intelligence 316, 103838](https://doi.org/10.1016/j.artint.2022.103838),
journal/arXiv version reviewed. Relevant locations: Definition 1 zs-OS-POSG;
§3 belief/value representation and Theorem 1 Bellman/value properties; §§4–5
approximations.

| Axis | Source versus project |
|---|---|
| Actions/timing | Simultaneous actions in both. |
| Information | One player receives partial observations/belief information; the other observes true state. This subsumes the project's one-sided asymmetry after selecting the observation kernel/history convention. |
| Histories | Source's action/observation history convention is broader; the repository fixes exactly which previous actions each player observes. |
| Horizon/payoff | Source emphasizes discounted stochastic reward; add time to state and absorbing failure/recovery terminals to represent the project's finite-horizon reach-avoid loss. |
| Strategies/value | Behavioral/history-dependent strategies and zero-sum value; the finite perfect-recall project normal form is realization-equivalent for its finite specialization. |
| Offline evidence | None: the complete game is solver input. |
| Interface mapping | `I_full`: **EQUIVALENT** for the augmented finite specialization; `I_node`: **INCOMPARABLE**; `I_public`: **INCOMPARABLE**. Horák et al. take a known game as solver input, while the latter two are evidence interfaces for identification; neither category is strictly richer merely because the paper has no offline sample. |
| Collision | Game-model novelty is preempted. A–D remain **RELATED BUT FORMALLY DISTINCT** because OS-POSG solution theory assumes the model rather than identifying it from public evidence. |

Thus the repository game is a **finite-horizon reach-avoid special case after
time/absorbing-state augmentation**, not a new game class. The only potentially
new direction is information-relative offline identification.

### Generic partial identification in games

Primary sources:

* *A partial identification framework for dynamic games*,
  [IJIO 87 (2023), 102915](https://doi.org/10.1016/j.ijindorg.2022.102915),
  especially §2 and the identified-set/moment-inequality results in §§3–4.
* Galichon and Henry, *Set Identification in Models with Multiple Equilibria*,
  [arXiv:2102.12249](https://arxiv.org/abs/2102.12249), Definition 1 and
  Theorem 1 in §§2–3 (capacity/optimal-transport characterization).

These econometric interfaces observe distributions and impose equilibrium or
model restrictions; they are **INCOMPARABLE** with all three project
interfaces rather than silently “richer.” They establish that compatibility
sets and set-identified functionals are standard. If an identified set for
`V` lies wholly in a threshold level set, the coarsened decision is identified
although `V` is not. This follows directly from the definition of functional
identification; it is not game-model novelty.

Consequently Proposition C's **principle** is at score 1: a routine
coarsening of an identified set. Its exact finite strategic witness is useful,
but applying the principle to a minimax value once its compatibility set is
computed is routine. Neither paper supplies the project's hidden-state
minimax tables or a coverage theorem for them.

## Critical information and estimand audit

| Source family | True state in records? | Information sets / private type exposed? | State-conditioned transitions? | Behavior known? | Coverage index and strength | Can Witness-B couplings remain observationally equal? | Primary estimand |
|---|---|---|---|---|---|---|---|
| OEF/BOMB/thesis | Underlying EFG node/history used by model | Information partition is in represented game; private history is node-resolved for estimation | Yes, through node/action model fitting | Collection process specified as required by method | node-action; quantitative/uniform | **No** under the theorem's node-indexed evidence; yes only after coarsening outside its assumption | model, equilibrium/profile, exploitability |
| Cui–Du | Yes, common `s_h` | No private type; both use common state | Yes | Not the decisive distinction | occupancy/state-joint-action; quantitative unilateral concentration | **No**: state-conditioned payoff rows differ | NE policies/profile, duality gap/value consequences |
| Yan et al. | Yes | No private state | Yes | Method-dependent | quantitative unilateral concentrability | **No** | NE policies/duality gap/value consequences |
| Chen et al. KL | Yes | No private state | Yes | Method-dependent | quantitative regularized/unilateral coverage | **No** | KL-regularized equilibrium/value |
| Congestion feedback | No analogous latent state | Feedback exposes trajectory/facility/agent payoff components | Facility-conditioned where feedback permits | Model-specific | joint actions plus feedback-specific structure; quantitative | Not a representation of Witness B | approximate NE |
| OS-POSG | Full model is input, not a record | Observation kernel and player information are specified | Yes in known model | N/A | N/A | **No** in `I_full`; there is no offline evidence equivalence | value/strategy of known game |
| Partial-ID games | Latents generally not point observed | Types/selection enter maintained restrictions | Through structural restrictions, not project tuples | N/A | moment/compatibility restrictions | Possibly generically, but not the specific witness theorem | parameter/counterfactual identified sets |

No reviewed source targets `1[V<=epsilon]`; this negative statement is about
the exact theorems inspected, not all literature. A policy-learning lower bound
cannot be promoted to threshold impossibility unless its hard instances are
observationally identical under the same interface and their values straddle
the proposed cutoff. None of the reviewed bounds supplies that reduction.

## Citation-chain and targeted-search disposition

Backward/forward searches around Cui–Du and targeted searches for offline
IIEFGs, private-information offline games, offline POSGs/one-sided POSGs,
information-set and counterfactual coverage, trajectory feedback, latent-state
identification, robust minimax games, hidden-confounding policy values, and
decision identification repeatedly reached three buckets:

1. fully observed state-indexed offline Markov-game coverage and policy learning;
2. known-model POSG/OS-POSG planning; or
3. generic compatible-model/robust/partial-identification logic.

Expansion stopped when new candidates did not combine all four collision
coordinates: one-sided private state, a state-marginal public population
interface, passive public joint-action support, and exact minimax threshold
identification. This is evidence of **no material collision found**, not proof
of absence. The reviewed primary versions now resolve the earlier thesis-locator and Chen-version questions.

## Collision verdicts and publication consequences

| Claim | Collision status | Score | Adversarial verdict | What moves it up / down |
|---|---|---:|---|---|
| A | **KNOWN GENERAL PHENOMENON, PROJECT-SPECIFIC EXACT WITNESS** | 2 | Observational equivalence with unequal functionals is standard; exact finite one-sided minimax pair remains useful. | Up: exhaustive search excluding prior minimax public-marginal examples. Down: an earlier equivalent-value counterexample under the same interface. |
| B | **KNOWN GENERAL PHENOMENON, PROJECT-SPECIFIC EXACT WITNESS** | 2 | A cutoff straddled by an identified set is standard nonidentification. | Up: a nontrivial structural separation theorem. Down: a prior hidden-state lower bound with threshold-straddling values. |
| C | **KNOWN GENERAL PHENOMENON, PROJECT-SPECIFIC EXACT WITNESS** | 1 | Coarsened-functional identification without parameter point identification is routine; only the exact strategic witness is project-specific. | Up: useful game-specific necessary-and-sufficient information conditions. Down: an earlier identical minimax threshold example. |
| D | **KNOWN GENERAL PHENOMENON, PROJECT-SPECIFIC EXACT WITNESS** | 2 | Feedback-dependent coverage is known; this public-versus-privileged-state construction is a benchmark instantiation. | Up: proof existing offline-POSG lower bounds cannot encode the interface. Down: a prior state-blind public-support theorem with threshold-straddling latent couplings. |
| Broader threshold-only characterization | **NO MATERIAL COLLISION FOUND** | 4 | A plausible structural gap: characterize information sufficient for a minimax level-set decision but insufficient for value/equilibrium/model. This is a question, not a result. | Up: matching necessary/sufficient operational theorem. Down: a robust-game or partial-ID theorem already giving that characterization. |

**No proposition is a direct corollary of a reviewed source.** There is
therefore no purported reduction to report. The strongest surviving gap is the
broader threshold-only characterization. The strongest abandoned claim is any
general statement that the project newly discovered either feedback-dependent
coverage or “decision identified while parameter is not.” Model novelty is
also abandoned because the game is an OS-POSG specialization.

## Blocking caveat

The verdict is strong enough to choose Shape B and to prohibit stronger novelty
language. Before a manuscript treats the review as archival-complete, however,
preserve the reviewed OpenReview revisions because their theorem wording differs. No source-specific uncertainty currently changes a collision verdict. This review deliberately retains
**PROVED HERE FOR THE DECLARED FINITE FAMILY; NOVELTY NOT YET ESTABLISHED** for
A–D.

## Drafting matrix (all required comparison fields)

The detailed source cards above control if this compact matrix is ambiguous.
“Interface” lists `I_public / I_node / I_full` in that order.

| Source; citation/year | Exact theorem / assumption | Game class; player information; move timing | Offline evidence; learner observation; coverage | Recovery object; guarantee; necessity/sufficiency | Project interface mapping | Closest proposition; formal relationship; collision verdict; reason |
|---|---|---|---|---|---|---|
| Li et al., OEF; arXiv:2207.05285 (2022) | §3 OEF/data; §4 model-based result | finite IIEFG; represented information sets; EFG timing | node/history-assigned trajectories; learner sees model node/action; node-action coverage | equilibrium/profile, exploitability; convergence; procedure-level sufficiency | **SOURCE STRICTLY RICHER / INCOMPARABLE / PROJECT INTERFACE STRICTLY RICHER** | D; no interface-preserving reduction; **RELATED BUT FORMALLY DISTINCT** because state/node labels exceed public records and no threshold is targeted |
| Li et al., ICLR-2025 OEF/BOMB; OpenReview Re5iu0hBTs | Defs. 4.1–4.2; Assumption 4.3; Theorems 4.4–4.6 | finite IIEFG; represented nodes/information sets; EFG timing | episodes for node/action model estimation; uniform quantitative node-action coverage | model, equilibrium/profile, exploitability; convergence; Thm. 4.4 iff for MB guarantee under Assumption 4.3; not universal necessity | **SOURCE STRICTLY RICHER / INCOMPARABLE / PROJECT INTERFACE STRICTLY RICHER** | D; no reduction; **RELATED BUT FORMALLY DISTINCT** because “minimal” is not an all-algorithms threshold theorem |
| Li et al., ICLR-2026 OEF/BOMB; OpenReview h8u0KWgg9C | Defs. 4.1–4.2; Assumption 4.3; Theorems 4.4–4.6 | finite IIEFG; represented nodes/information sets; EFG timing | node/action episodes; uniform/equilibrium coverage | MB/BC/BOMB performance; conditional and may-no-longer-hold wording, not iff | **SOURCE STRICTLY RICHER / INCOMPARABLE / PROJECT INTERFACE STRICTLY RICHER** | A–D; **RELATED BUT FORMALLY DISTINCT**; no all-algorithms or threshold theorem |
| Li thesis (2025) | Chapter 6 §6.5; Assumptions 6.3–6.4; Table 6.2; Theorem 6.6 | finite IIEFG; same one-sided possibilities; EFG timing | node/action trajectories and fitted model; uniform coverage | model/equilibrium/exploitability; convergence; framework sufficiency | **SOURCE STRICTLY RICHER / INCOMPARABLE / PROJECT INTERFACE STRICTLY RICHER** | D; **RELATED BUT FORMALLY DISTINCT**; later exposition does not strengthen quantifiers |
| Cui–Du; arXiv:2201.03522 / NeurIPS 2022 | Defs. 3.1–3.2; Thms. 4.3–4.4 | tabular zero-sum Markov game; common observed state; simultaneous stage actions | state/action/reward/next-state trajectories; learner sees `s`; quantitative occupancy ratios | NE policies/profile, duality gap/value consequences; finite-sample upper/lower bounds; unilateral sufficiency and NE-learning necessity | **SOURCE STRICTLY RICHER / INCOMPARABLE / PROJECT INTERFACE STRICTLY RICHER** | D; attempted reduction fails at state observability/policy class; **RELATED BUT FORMALLY DISTINCT** |
| Yan–Li–Chen–Fan; DOI 10.1287/opre.2022.0342 (version of record) | §2; Assumption 1; main upper/lower-bound theorems | tabular zero-sum Markov game; common state; simultaneous | state-indexed transition data; quantitative unilateral concentrability | NE policies, duality gap/value consequences; rate bounds; sufficient/sharp for learning objective | **SOURCE STRICTLY RICHER / INCOMPARABLE / PROJECT INTERFACE STRICTLY RICHER** | D; **RELATED BUT FORMALLY DISTINCT** because latent state is not marginalized |
| Chen et al.; arXiv:2605.13025 (May 2026) | regularized objective/coverage definitions; main upper/lower bounds | KL-regularized common-state Markov game; simultaneous | state-indexed offline transitions; regularized/unilateral coverage | regularized policy/profile/value; statistical bounds; objective-specific upper/lower results | **SOURCE STRICTLY RICHER / INCOMPARABLE / PROJECT INTERFACE STRICTLY RICHER** | D; **RELATED BUT FORMALLY DISTINCT**; different information and estimand |
| Offline congestion games; arXiv:2210.13396 (ICLR 2023 version) | §3; Thms. 1–3 | congestion game; feedback-dependent payoff knowledge; simultaneous joint actions | joint actions plus trajectory/facility/agent feedback; feedback-specific structural coverage | approximate NE; upper/lower bounds; interface-specific necessity/sufficiency | **INCOMPARABLE / INCOMPARABLE / PROJECT INTERFACE STRICTLY RICHER** | D; no exact game reduction; **KNOWN GENERAL PHENOMENON, PROJECT-SPECIFIC EXACT WITNESS** because feedback changes coverage but no latent minimax threshold appears |
| Horák et al.; AI 316 (2023), Def. 1 / Thm. 1 | Def. 1; §3 Thm. 1; §§4–5 | zs-OS-POSG; one partial/one state-informed player; simultaneous | no offline evidence—known model input; no coverage | value/strategies; DP/approximation; not identification | **INCOMPARABLE / INCOMPARABLE / EQUIVALENT** (for augmented specialization) | A–D; model reduction succeeds but evidence reduction does not; **RELATED BUT FORMALLY DISTINCT** |
| Dynamic-games partial-ID; IJIO 87 (2023), 102915 | §2 and identified-set propositions in §§3–4 | econometric dynamic game; private shocks/types; dynamic actions | population market states/actions plus restrictions; no offline support condition | structural/counterfactual identified sets; sharp/set bounds; not OEF coverage | **INCOMPARABLE / INCOMPARABLE / INCOMPARABLE** | A–C; **KNOWN GENERAL PHENOMENON, PROJECT-SPECIFIC EXACT WITNESS** because functional set identification is generic |
| Galichon–Henry; arXiv:2102.12249 (2021) | Def. 1; Thm. 1; §§2–3 | multiple-equilibrium econometric model; latent selection; model-specific timing | observable distribution plus equilibrium correspondence; capacity/compatibility inequalities | structural identified set; sharp characterization; neither coverage nor equilibrium recovery | **INCOMPARABLE / INCOMPARABLE / INCOMPARABLE** | A–C; **KNOWN GENERAL PHENOMENON, PROJECT-SPECIFIC EXACT WITNESS** because coarsenings of non-singleton sets are standard |
