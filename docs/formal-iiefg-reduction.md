# A perfect-recall imperfect-information extensive-form representation

## Status and scope

This note fixes a conventional extensive-form representation of the repository's
finite strategic-safety game before any identifiability claim is attempted. The
reduction is an application of established finite imperfect-information game
theory; **no novelty is claimed for the reduction**. Its implementation is an
auditable bounded tree, not an equilibrium algorithm.

### Assumptions

The theorem below applies exactly to a validated `stage1.v2` `Game`:

* (S,C,A,O) are finite nonempty sets and (H\in\mathbb N);
* (b_0\in\Delta(S)) and every (T(\cdot\mid s,c,a)\in\Delta(S)) have exact
  rational probabilities;
* (obs:S\to O) is deterministic; (F,R\subseteq S) are disjoint;
* the controller availability set (C_t\ne\varnothing) is determined by the
  round, and the adversary action set is the fixed finite set (A);
* both players know the complete formal game and protocol; and
* payoff is failure probability. Optional legitimate rewards and display labels
  are outside this reduction because they do not define that payoff.

These are the implementation's assumptions, not claims about continuous,
infinite-horizon, stochastic-observation, or partially informed-adversary games.

## 1. Source protocol

**Definition 1 (repository play).** Chance draws (s_0\sim b_0). Initial states
in (F) or (R) stop immediately. Otherwise, at each (t<H):

1. the controller receives (o_t=obs(s_t)), and its information is
   \[
   h^C_t=(o_0,c_0,o_1,c_1,\ldots,c_{t-1},o_t);
   \]
2. the informed adversary's information is
   \[
   h^A_t=(s_0,\ldots,s_t;c_0,\ldots,c_{t-1};a_0,\ldots,a_{t-1});
   \]
3. (c_t\in C_t) and (a_t\in A) are committed simultaneously. In
   particular neither player sees the other's current action, and the adversary
   does not see the controller's current private random draw; and
4. only after both commitments, chance draws
   (s_{t+1}\sim T(\cdot\mid s_t,c_t,a_t)).

Entry into (F) has loss one and stops; entry into (R) has loss zero and
stops. Surviving (H) action rounds without failure has loss zero. The
controller recalls all observations and its actions, but receives neither the
hidden state nor adversary actions. The adversary recalls the true-state
history, its actions, and previously revealed controller actions.

## 2. Extensive-form construction

**Definition 2 (translated game).** For a repository game (G), (E(G)) is a
finite two-player zero-sum imperfect-information extensive-form game. Its
strategic players are controller (C) (minimizer) and adversary (A)
(maximizer), together with chance. A nonterminal round is sequentialized as

\[
  \text{controller node}\longrightarrow\text{adversary node}
  \longrightarrow\text{transition-chance node}.
\]

The tree's complete histories are alternating records generated as follows.
The root is a chance node with edge (s_0) of probability (b_0(s_0)). At a
controller node for a nonterminal history through state (s_t), the edges are
the actions (C_t). For each such edge (c_t), the child is an adversary node
whose edges are (A). For each (a_t), the child is a chance node whose edge to
(s_{t+1}) has probability (T(s_{t+1}\mid s_t,c_t,a_t)). Zero-probability
edges may be omitted without changing the induced measure. Terminal histories
are exactly initial or entered (F), initial or entered (R), and active
histories at (t=H). Their controller losses are respectively (1,0,0); the
adversary payoff is the same loss (equivalently, controller utility is its
negative), hence the game is zero-sum.

The sequential order is notation, **not observation of a leader**. All
adversary nodes following different (c_t) from the same adversary-known
history belong to one information set. Consequently an adversary strategy must
choose the same distribution at them and cannot condition on (c_t). A fresh
behavioral draw by the controller is private. Thus this construction is not a
Stackelberg game and does not leak the controller's current action.

**Definition 3 (controller information sets).** Two controller nodes (x,x')
at round (t) satisfy (x\sim_C x') exactly when

\[
 (obs(s_0),c_0,\ldots,c_{t-1},obs(s_t))
 = (obs(s'_0),c'_0,\ldots,c'_{t-1},obs(s'_t)).
\]

The key is canonically the pair
(((o_0,\ldots,o_t),(c_0,\ldots,c_{t-1}))). No state identifier or adversary
action occurs in it. In particular, distinct hidden-state histories producing
the same observation/own-action history are in the same information set.
Because the key fixes (t), every node in the set has the same available set
(C_t).

**Definition 4 (adversary information sets).** Two adversary nodes (y,y') at
round (t), although internally reached after controller edges, satisfy
(y\sim_A y') exactly when

\[
 (s_0,\ldots,s_t;c_0,\ldots,c_{t-1};a_0,\ldots,a_{t-1})
 = (s'_0,\ldots,s'_t;c'_0,\ldots,c'_{t-1};a'_0,\ldots,a'_{t-1}).
\]

Crucially, (c_t) is absent. The adversary therefore distinguishes different
true-state histories, but nodes differing only in the current unrevealed
controller action are merged. All nodes in such a set have action set (A).

These definitions specify players, histories, chance nodes and probabilities,
decision nodes, terminal histories, actions, information partitions, and
payoffs, and therefore determine a standard finite IIEFG.

## 3. Perfect recall and strategies

**Proposition 1 (perfect recall).** Both players have perfect recall in (E(G)).

**Proof.** If two round-(t) controller nodes share an information set, their
keys contain the entire ordered observation sequence and every earlier
controller action. Truncating the common key at each earlier decision gives the
same earlier controller information set, while its intervening action is also
equal. Thus the controller never forgets information once observed or an
action once chosen.

If two adversary nodes share an information set, equality of their keys gives
the entire state sequence available at every earlier decision, all earlier
controller actions, and all earlier adversary actions. Every earlier adversary
information key is the corresponding prefix, and the adversary's own
intervening action is retained. Thus it forgets neither received state/action
information nor its choices. Omitting only the *current* (c_t), which was
never observed, is not forgetting. This is precisely the perfect-recall
condition for both players. \(\square\)

**Proposition 2 (pure-strategy bijection).** A pure repository controller policy
(\pi_C:h^C_t\mapsto c_t\in C_t) maps to the pure extensive-form strategy that
assigns (pi_C(h^C_t)) to the information set keyed by (h^C_t). Conversely,
reading an action from every controller information set defines such a policy.
The identical construction with (h^A_t\mapsto a_t\) gives a bijection for the
adversary.

Here a strategy is a complete contingent plan, so assignments at unreachable
information sets are included on both sides. The explicit implementation
materializes reachable sets only; arbitrary valid assignments on omitted
unreachable keys complete either plan and cannot change realization
probabilities. Quotienting complete plans by those irrelevant assignments gives
the same reachable pure-policy space used by the oracle.

**Established result (not ours).** A pure strategy is one complete deterministic
plan. A mixed strategy is a probability distribution over such plans, with one
private draw selecting the plan. A behavioral strategy independently specifies
a distribution at each information set. Kuhn's standard perfect-recall theorem
gives realization equivalence between mixed and behavioral strategies in a
finite perfect-recall game (for every opposing strategy). It applies only after
the information partitions above have been verified; it does not repair an
incorrect information structure. The repository oracle solves mixtures over
pure perfect-recall policies in the finite normal form. Under the proposition,
those are mixed strategies of (E(G)); behavioral implementations have the
same realization distributions. Neither representation exposes a controller
private draw or current action to the adversary.

## 4. Probability and value preservation

**Lemma 1 (profile probability preservation).** Let
((\pi_C,\pi_A)) be any pure repository-policy profile and
((\sigma_C,\sigma_A)) its image under Proposition 2. The two games induce the
same probability on every state-history prefix and hence the same failure
probability.

**Proof.** Induct on the number of completed rounds.

*Base.* In both games the probability of one-state prefix ((s_0)) is exactly
(b_0(s_0)). Both compute (o_0=obs(s_0)). If (s_0\in F) or (s_0\in R),
both stop immediately with the same failure indicator; if (H=0), both stop
with zero loss.

*Step.* Assume each active prefix ((s_0,\ldots,s_t)) has the same mass. The
deterministic observation map produces the same current observation and hence
the same controller information key. Strategy correspondence selects the same
(c_t). The adversary key contains the same state prefix and earlier actions,
but not (c_t), and correspondence selects the same (a_t). Thus the action
pair is the same simultaneous pair; the tree's syntactic order has supplied no
extra conditioning information. Both then multiply prefix mass by the same
exact factor (T(s_{t+1}\mid s_t,c_t,a_t)). Therefore every extended prefix has
the same mass.

On entry to (F) or (R), both remove that mass from the active frontier and
assign respectively loss one or zero; neither applies a later transition.
After round (H-1), remaining active mass terminates at the horizon with loss
zero. These mutually exclusive stopping cases exhaust all paths. Summing the
identical masses of failure-terminal histories proves equality of failure
probability. \(\square\)

The same conclusion extends linearly to mixed profiles. By perfect-recall
realization equivalence it also holds for corresponding behavioral profiles.

**Theorem 1 (value preservation).** For every game satisfying the stated
assumptions,

\[
 V_{repo}(G)=\min_{\mu_C}\max_{\mu_A}\Pr_G(F\text{ before }R\text{ within }H)
 =V_{IIEFG}(E(G)).
\]

**Proof.** Proposition 2 identifies each player's pure contingent plans (up to
irrelevant unreachable assignments), and Lemma 1 identifies every entry of the
resulting finite normal-form payoff matrix. Therefore the two min-max problems
are the same finite zero-sum matrix game. Equivalently, Kuhn realization
equivalence permits the IIEFG side to be expressed behaviorally without
changing its value. \(\square\)

**Corollary 1 (threshold preservation).** For the schema's exact
(\epsilon\in[0,1]),

\[
 V_{repo}(G)\le\epsilon\quad\Longleftrightarrow\quad
 V_{IIEFG}(E(G))\le\epsilon.
\]

Thus repository `WINNING` (the weak inequality) and `LOSING` (its strict
negation) are preserved.

## 5. Interfaces for a later identification problem

The following are mathematical observation interfaces, not solvers or claims
that finite samples recover their population objects.

**Definition 5 (full interface (I_{full})).** (I_{full}(G)) exposes all
semantic fields needed to determine (G): finite labeled sets
(S,C,A,O), (b_0,obs,T,F,R,H), action availability, and (epsilon).
Nonsemantic display labels and legitimate rewards may be ignored for the
failure game. Its ambiguity class is a singleton modulo bijective renaming of
identifiers and omission/inclusion of zero-probability chance edges (the
explicitly permitted representational equivalences).

**Definition 6 (node-indexed interface (I_{node})).** Fix the reachable
translated tree. (I_{node}(G)) exposes, for every reachable decision/chance
history: its round, acting player, available actions, information-set identifier,
underlying state-history identifier, terminal marker/payoff, and every
state-conditioned chance law following each joint action. It also exposes the
root chance law. Accordingly data or coverage can be indexed by an underlying
node/state-conditioned information structure rather than merely a public
surface history. It need not expose unreachable schema rows or identify which
differently labeled full specifications are representationally equivalent.
Whether this interface exactly equals the assumptions of any named offline-EFG
paper is **NOT YET ESTABLISHED**.

**Definition 7 (public interface (I_{public})).** A public stopped record is

\[
 z=(o_0,c_0,a_0,o_1,\ldots,c_{\tau-1},a_{\tau-1},o_\tau,d),
\]

where (\tau\le H), (d\in\{failure,recovery,horizon\}) is the public terminal
outcome when stopped, and no (s_t) appears. (This is an offline observer's
record; logging a completed-round adversary action does not add it to the
controller's online information.) (I_{public}(G)) supplies (H,C,A,O),
round availability, (epsilon), the population law of these stopped public
records under a specified full-support collection regime, and the regime's
conditional probability of every available joint action ((c,a)) after every
public prefix in its support. “Complete publicly visible joint-action coverage”
means each available ((c,a)) has positive collection probability at each such
public prefix. It does not reveal states, posterior state labels, adversary
state-conditioned choices, or (T(\cdot\mid s,c,a)). Therefore it can leave
unknown the coupling between latent states, informed-adversary decisions, and
next public observations even with complete public joint-action coverage.

These interfaces are ordered by content in the intended sense, but no claim is
made here that a particular finite dataset realizes any one of them or that the
interfaces identify the same games.

## 6. Ambiguity and threshold certification

**Definition 8 (ambiguity class and bounds).** For an interface value (I), let

\[
 \mathcal M(I)=\{G:G\text{ is compatible with }I\},\qquad
 \underline V(I)=\inf_{G\in\mathcal M(I)}V(G),\quad
 \overline V(I)=\sup_{G\in\mathcal M(I)}V(G).
\]

**Established generic partial-identification logic (not ours).** Assuming the
ambiguity class is nonempty,

\[
\begin{array}{ll}
\overline V(I)\le\epsilon &\Rightarrow \text{certifiably WINNING},\\
\underline V(I)>\epsilon &\Rightarrow \text{certifiably LOSING},\\
\underline V(I)\le\epsilon<\overline V(I)
  &\Rightarrow \text{the threshold is not identified}.
\end{array}
\]

This section introduces notation only. No ambiguity-set search or
identifiability theorem is implemented or asserted.

## 7. Research and prior-art boundary

The status labels below are intentionally conservative.

| Area and status | Object being identified | Information supplied | Target quantity | What established machinery covers | What remains open here |
|---|---|---|---|---|---|
| Standard information sets/perfect recall — **ESTABLISHED** | A specified finite game | Full tree, chance, actions, payoffs, information partitions | Strategies, realizations, equilibrium value | Extensive-form definitions and mixed/behavioral realization equivalence | No gap for the reduction once its information partitions are accepted |
| Fully observed offline zero-sum coverage — **PROVISIONAL COMPARISON** | Values/policies in a state-observed game | State/action-conditioned offline information under coverage assumptions | Typically value or equilibrium policy | Existing machinery addresses fully observed settings under its stated assumptions | Transfer of any particular theorem to these interfaces is **NOT YET ESTABLISHED** |
| Imperfect-information offline equilibrium finding — **PROVISIONAL COMPARISON** | Equilibrium behavior/value of a specified or sampled IIEFG | Paper-specific node/information-set samples and coverage | Approximate equilibrium or exploitability | Existing work supplies algorithms/bounds under paper-specific assumptions | Exact equivalence of (I_{node}) or (I_{public}) to a named assumption set is **NOT YET ESTABLISHED** |
| One-sided asymmetric-information games — **ESTABLISHED AREA; PROVISIONAL MATCH** | Games where one side has privileged state information | Model-specific priors, dynamics, signals, and information | Value/equilibrium/strategic structure | Established theory studies asymmetric information | Which named model exactly subsumes every `stage1.v2` detail is **NOT YET ESTABLISHED** |
| Generic partial identification — **ESTABLISHED** | Identified set of a functional across compatible models | Observable restrictions defining an ambiguity class | Lower/upper bounds and identified decisions | Infimum/supremum logic in Definition 8 | Computing or characterizing these bounds for (I_{public}) is open |
| Threshold-only enforceability — **PROJECT QUESTION; NOT YET ESTABLISHED** | The bit (\mathbf1[V_H\le\epsilon]) | Candidate interfaces weaker than (I_{full}), especially (I_{public}) | WINNING/LOSING rather than full equilibrium | The reduction establishes only equivalence when (G) is fixed | Whether the bit needs less information than exact value/equilibrium/full game remains unresolved |

No row claims that another result is preempted, that its interface is identical
to ours, or that the threshold question is novel. Such conclusions require a
separate, source-specific literature comparison.

## 8. Limitations and unresolved question

The executable representation expands a tree and can grow exponentially; it
has an explicit node bound and is not a solver. Its tests compare bounded pure
profiles as regression evidence, not as the proof. Neither this note nor the
code handles ambiguity classes, sampling error, continuous spaces, alternate
online information, or equilibrium computation. The theorem depends on the
validated source semantics and must be revisited if that protocol changes.

The exact question left unresolved is:

> Can the threshold decision
> \[
> \mathbf 1[V_H\le\epsilon]
> \]
> be identified under information strictly weaker than what is needed to
> identify the exact value, equilibrium, or full game?

