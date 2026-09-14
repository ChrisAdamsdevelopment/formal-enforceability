# Threshold identifiability in the canonical one-step family

## Definitions

**PROJECT DEFINITION — canonical family.** There are equiprobable latent states (s_0,s_1),
one controller observation `hidden`, controller actions (c_0,c_1), informed
adversary actions (a_0,a_1), and terminals `SAFE`,`FAIL`. The horizon is one.
A deterministic game is the eight-bit failure table in the fixed order
((s_0,c_0,a_0),(s_0,c_0,a_1),(s_0,c_1,a_0),(s_0,c_1,a_1),
(s_1,c_0,a_0),\ldots,(s_1,c_1,a_1)). Thus the family contains (2^8=256)
games; `d000` through `d255` are the binary tables in product order.

The **collection regime** is state-blind, independent of the latent state, and
assigns probability (1/4) to each public joint action. It is solely the
offline evidence generator. At deployment, the adversary observes the state
and acts strategically, as in the repository protocol.

The public interface is

\[
 I_{\rm public}(G)=(q_{00},q_{01},q_{10},q_{11}),\qquad
 q_{ca}=\tfrac12(p_{s_0ca}+p_{s_1ca}).
\]

It contains no state label. For (x=\Pr(c_0)), the strategic value is

\[
 V(G)=\min_{x\in[0,1]}\frac12\sum_s\max_a
 [x p_{sc_0a}+(1-x)p_{sc_1a}].                 \tag{1}
\]

For an interface (I), let (\underline V(I)) and (\overline V(I)) be the
minimum and maximum of (1) over its finite compatibility class. We call it
certifiably winning when (\overline V\leq\epsilon), certifiably losing when
(\underline V>\epsilon), and insufficient otherwise. This weak-boundary
rule is **ESTABLISHED PRIOR THEORY** from standard partial-identification interval logic; no novelty is claimed for it.

## Propositions and proofs

**Epistemic status of Propositions A–D:** **PROVED HERE FOR THE DECLARED FINITE FAMILY; NOVELTY NOT YET ESTABLISHED.** This distinguishes repository proofs from claims about prior literature.

### Proposition A — exact public ambiguity

Games `d006` and `d036` have the same public interface
((0,1/2,1/2,0)), but values (1/4) and (1/2), respectively.

**Proof.** In `d006`, the (s_0) table is all zero and the (s_1) table is
the off-diagonal matrix \(\left[\begin{smallmatrix}0&1\\1&0\end{smallmatrix}\right]\).
The latter has minimax failure (1/2), so equiprobable initialization gives
(V=1/4). In `d036`, the two state tables are
\(\left[\begin{smallmatrix}0&0\\1&0\end{smallmatrix}\right]\) and
\(\left[\begin{smallmatrix}0&1\\0&0\end{smallmatrix}\right]\).
For controller probability (x), the informed adversary obtains at least
(1-x) in the first state and (x) in the second, and those bounds are
attained. Their weighted sum is (1/2) for every (x). Cellwise state
averaging gives ((0,1/2,1/2,0)) in both games. ∎

### Proposition B — threshold nonidentification

At (\epsilon=1/4), `d006` is winning under (V\leq\epsilon), whereas
`d036` is losing. Their identical public interface therefore does not identify
the decision.

**Proof.** Substitute the exact values from Proposition A into the weak
inequality: (1/4\leq1/4), while (1/2\nleq1/4). ∎

### Proposition C — threshold identification without value identification

The same interface identifies a winning label at (\epsilon=1/2), although it
does not identify the value.

**Proof.** Exhaustive compatibility construction gives its exact value set
\(\{1/4,1/2\}\), so (\overline V=1/2). At (\epsilon=1/2), weak threshold
semantics give (\overline V\leq\epsilon); therefore every compatible game is
winning. Proposition A nevertheless supplies two unequal compatible values, so
the exact value is not identified. ∎

**Observation (direct application of established interval logic, not a novel
theorem).** For this same public interface, the exact ambiguity interval is
\([1/4,1/2]\). It is `CERTIFIABLY_LOSING` for (\epsilon<1/4),
`INSUFFICIENT_INFORMATION` for (1/4\leq\epsilon<1/2), and
`CERTIFIABLY_WINNING` for (\epsilon\geq1/2). Thus identifiability belongs to
the information-interface-plus-estimand/threshold pair, not to the raw public
interface alone.

### Proposition D — complete public joint-action coverage is insufficient

Under the family and collection assumptions above, even four equal visible
conditionals and positive coverage of every public joint action do not identify
deployment enforceability.

**Proof.** `d015` has a zero (s_0) table and a one (s_1) table, hence value
(1/2). In `d090`, adversary action (a_1) forces failure in (s_0) and
(a_0) forces failure in (s_1), independently of the controller, hence value
(1). Both public signatures are ((1/2,1/2,1/2,1/2)). At
(\epsilon=1/2) their labels are winning and losing. Every joint action has
collection probability (1/4). ∎

**Corollary.** In this finite setting, complete passive public coverage is
strictly weaker than observing the latent state-conditioned transition table.
This statement does not extend the proposition to arbitrary offline-game
interfaces.

## Exhaustive results

The 256 games form 81 public classes. Their values are
\(\{0,1/4,1/2,3/4,1\}\); 66 classes identify one value and 15 are
value-ambiguous. Sweep counts are:

| epsilon | winning | losing | insufficient |
|---:|---:|---:|---:|
| 0 | 17 | 64 | 0 |
| 1/4 | 17 | 62 | 2 |
| 1/3 | 17 | 62 | 2 |
| 1/2 | 47 | 23 | 11 |
| 2/3 | 47 | 23 | 11 |
| 3/4 | 55 | 17 | 9 |
| 1 | 81 | 0 | 0 |

The robustness extension replaces each bit by (0,1/2,1). Its 6,561 games
form 625 signatures, with 297 value-ambiguous classes and values
\(\{0,1/8,1/6,1/4,1/3,3/8,5/12,1/2,7/12,5/8,2/3,3/4,5/6,7/8,1\}\).
Value nonidentification, threshold nonidentification, and threshold
identification without value identification all persist.

## Structural characterization attempt

Equation (1) gives a concise value calculation for a *known* table: the
piecewise-linear convex objective need only be checked at 0, 1, and the two
within-state adversary-line intersections. A public deterministic cell fixes
the state pair when its marginal is 0 or 1, but a marginal (1/2) leaves its
orientation unresolved. Ambiguity bounds are therefore exactly the min/max of
(1) over the jointly consistent orientations of all (1/2) cells.

This is a finite latent-orientation enumeration, not a useful closed form in
the four marginals. No stronger structural characterization was found. The
scientific classification is therefore **Outcome B — finite-family theorem
package only**.

## Limitations

The propositions are existential and restricted to two equiprobable states,
two actions per player, one coarse observation, horizon one, the declared
passive regime, and an informed deployment adversary. They are neither a
necessary-and-sufficient theorem nor an active-data result. The probabilistic
extension is bounded robustness evidence, not an unrestricted theorem.

## Prior-art status

* **PROJECT DEFINITION:** the canonical family, collection regime, versioned
  public signature, and canonical IDs are definitions made by this project.
* **PROVED HERE FOR THE DECLARED FINITE FAMILY; NOVELTY NOT YET ESTABLISHED:**
  Propositions A–D and the bounded probabilistic persistence checks are exact
  consequences of the displayed tables and exhaustive enumeration.
* **ESTABLISHED PRIOR THEORY:** perfect-recall game theory and generic
  partial-identification interval logic, including the three-way threshold
  classification used here.
* **PROVISIONAL COMPARISON:** these results instantiate familiar
  partial-identification distinctions; comparison to BOMB, Cui–Du, and
  offline-IIEFG results remains provisional.
* **NOT YET ESTABLISHED:** novelty or non-collision relative to BOMB, Cui–Du,
  offline-IIEFG results, asymmetric-information game theory, or generic partial
  identification. No source-specific collision review is attempted here.
* **PROJECT QUESTION:** whether useful general conditions identify only
  \(\mathbf1[V_H\leq\epsilon]\) from passive public evidence.

## Open generalization

The next theoretical task is to characterize interfaces for which an ambiguity
interval avoids a threshold without reconstructing all latent couplings, and
then perform a source-by-source prior-art collision review. No manuscript
should present the finite existence claims as novel before that review.
