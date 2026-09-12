# Formal game core (`stage1.v2`)

This package is a deliberately finite **reference oracle**, not a scalable
solver. It makes no broad AI-safety claim.

## Exact game

The machine-readable object is

\[
G=(S,b_0,A_C,A_A,O_C,obs,T,F,R,H,\epsilon,L,\rho).
\]

`S`, `A_C`, `A_A`, and `O_C` are finite nonempty identifier sets. `b0` is an
exact rational probability distribution on `S`. `obs:S -> O_C` is deterministic.
`T(s,c,a)` is a finite exact rational distribution on `S`, including point
masses for deterministic games. `F` and `R` are disjoint terminal sets. `H` is
a nonnegative count of action rounds and epsilon is an exact rational in `[0,1]`.
`L(c)` declares the rounds in which a controller permission is available.
`rho(s,c)` is an optional exact legitimate-task reward (zero when omitted).
Display labels are explicitly non-semantic.

Rationals serialize as integers or strings such as `"2/3"`; JSON floats are
rejected. Every distribution must have nonnegative mass summing **exactly** to
one. Transition tables are total. Invalid data raises `InvalidGame`; an unknown
version raises `UnsupportedGameClass`; neither becomes `LOSING`.
Canonical serialization preserves every state entry explicitly supplied in
`b0`, including zero-mass entries, in declared state order. It does not invent
omitted zero-mass entries.

## Information and move order

At round `t`, the controller observes `obs(s_t)` and remembers exactly
`(o0,c0,o1,...,o_t)`. It never receives a hidden state, posterior, adversary
action, or debug field. The adversary observes the complete state history, its
own past actions, and revealed past controller actions. Both know the game and
protocol. At the current round they commit simultaneously: the adversary cannot
observe the controller's current private draw. The transition distribution is
then sampled. Entering `F` fails; entering `R` succeeds and terminates; otherwise
play continues. Avoiding failure for `H` rounds succeeds. Initial failure and
recovery are terminal with the same meanings.

A controller strategy is observation-compatible iff identical controller
information histories induce the same action distribution. The adversary may
condition only on its declared history above. Perfect recall and finite games
allow behavioral and mixed normal-form strategies to realize the same outcome
distributions. Randomization is unnecessary for epsilon-zero sure safety, but
can be necessary for a nonzero minimax probability under simultaneous play.

The robust value is

\[
V^*(b_0,H)=\min_{\sigma_C}\max_{\sigma_A}
  \Pr_{b_0,T,\sigma_C,\sigma_A}(F\text{ before }R\text{ within }H).
\]

The result reports this exact value and `threshold_satisfied = (V* <= epsilon)`;
`WINNING` is precisely threshold satisfaction and `LOSING` its negation.

## Primary exact algorithm

The primary implementation enumerates all reachable pure perfect-recall
controller strategies and all reachable pure state-informed adversary strategies.
It exhaustively propagates rational trajectory mass for every strategy pair,
forming the normal-form failure matrix. An exact rational support-enumeration
solver computes its min/max value and a mixed controller witness. The independent
witness checker reevaluates that mixture against every pure adversary strategy.

If `N_C` and `N_A` are the numbers of pure strategies, matrix construction costs
`O(N_C N_A B^H)` for stochastic branching factor `B`; support enumeration adds
combinatorial time in the matrix dimensions and cubic rational elimination per
candidate support. Space includes `O(N_C N_A)`. This is intentionally terrible
but transparent, and suitable only for tiny games.

## Independent tiny cross-check

`oracle.tiny.classify_tiny` supports epsilon zero. It does not consume a primary
witness, normal-form profiles, payoff matrices, or matrix-solver code. Instead it
backtracks directly over shared controller-history action assignments and
universally expands every adversary action and every positive-probability edge.
Generated tiny games compare its classification with the primary oracle.

The two implementations still share the validated `Game` and controller-history
types, terminal/move semantics as documented here, and the same Python runtime;
therefore this is structural implementation independence, not an independently
specified or independently audited semantics.

## Structural restorations and legitimate cost

A `Restoration` is finite data that can remove declared adversary capabilities,
remove controller permissions, refine observations using already declared
observation IDs, or replace declared per-round action availability. It cannot run
arbitrary code or carry a hand-authored cost. Topology is not a component of this
schema, so topology edits are not represented.

An observation override must be a true partition refinement: whenever two states
had different observations before the transformation, they must still have
different observations afterward. An override may leave the map unchanged or
split one old class using a declared observation ID (including a previously
unused ID), but it may never merge two old classes.

For any game `G`, legitimate utility uses the same initial distribution,
information, timing, transition, and adversary assumptions, but solves

\[
U_G^*=\max_{\sigma_C}\min_{\sigma_A}
E[\sum_{t<\tau\wedge H}\rho(s_t,c_t)],
\]

with undiscounted rewards and stopping time `tau` at failure or recovery. The
unrestricted baseline is the untransformed game. A candidate's endogenous cost
is `C(r)=U_G* - U_{r(G)}*`. `optimal_restoration` solves every explicitly supplied
candidate, filters on `V*_r <= epsilon`, and returns **all** feasible candidates
at the exact minimum cost. Callers must choose candidates whose effects make this
opportunity-loss convention meaningful; the schema does not force costs to be
nonnegative.

## Tested transformation preconditions

Identifier renaming is bijective. Added/removed actions preserve all retained
rows and receive/remove complete transition rows. Observation refinement is
deterministic and free of time or utility effects. An added unreachable state has
zero initial mass and no incoming reachable edge. Display labels are ignored by
both objectives. Under these conditions tests check both directions of controller
and adversary action monotonicity, observation refinement, renaming, labels, and
unreachable-state invariance.

## Limits that matter scientifically

Observations remain deterministic. The adversary has perfect state observation.
Actions, observations, state, horizon, and restoration candidates must be finite;
the exhaustive solvers become unusable quickly. Rewards are undiscounted and
state/controller-action based. No topology object exists. There are no continuous
spaces, sequence-form optimization, belief compression, stochastic observations,
chance-constraint approximations, LLM/model integrations, natural-language
renderer, Inspect, ControlArena, dashboards, monitoring, certification UI, or
statistical claims.

The normal-form support enumerator and both semantic implementations have not
been externally audited. State explosion can prevent obtaining a result; such a
resource failure must be reported as an exception, never interpreted as losing.
