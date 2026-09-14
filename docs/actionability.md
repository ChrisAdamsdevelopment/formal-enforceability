# Uniform actionability in the one-step interface

## Status and scope

This note applies standard partial-identification and convex/robust-optimization
machinery to the project's **finite, one-step, affine-payoff** interface. It is
not a new general identifiability or convexity theorem. A compatible-model set
is written \(\mathcal M(I)\), or \(\mathcal F(q)\) for the canonical public
signature. For a known game,

\[
L(\pi,G)=\max_{\pi_A}P_G^{\pi,\pi_A}(\mathrm{failure}),\qquad
V(G)=\min_\pi L(\pi,G).
\]

The standard partially identified bounds are
\(\underline V=\inf_{G\in\mathcal M(I)}V(G)\) and
\(\overline V=\sup_{G\in\mathcal M(I)}V(G)\). Thus lower greater than
\(\epsilon\) is certifiably losing, a cutoff strictly between the bounds is
insufficient information, and upper at most \(\epsilon\) is certifiably
winning. This is standard partial-identification logic, not a new theorem.

## Wait-and-see and here-and-now

Define
\[
W(I)=\sup_G\min_\pi L(\pi,G),\qquad
R(I)=\min_\pi\sup_G L(\pi,G).
\]

**Lemma.** \(W(I)=\overline V(I)\). For each fixed \(G\), the definition of
\(L\) gives \(\min_\pi L(\pi,G)=V(G)\). Substitution gives
\(W=\sup_GV(G)=\overline V\).

**Standard order inequality.** For every fixed \(G\) and \(\pi\),
\(\min_{\pi'}L(\pi',G)\le L(\pi,G)\). Taking \(\sup_G\) and then
\(\min_\pi\) gives \(W\le R\). This is the familiar wait-and-see versus
here-and-now gap (and static versus adjustable/adaptive robust choice), with
the outer worst case also reflecting ambiguity-averse/maxmin choice.

The hierarchy is therefore:

```text
lower V > epsilon? --yes--> CERTIFIABLY_LOSING
       |
       no
upper V > epsilon? --yes--> INSUFFICIENT_INFORMATION
       |
       no  (certifiably winning)
 R > epsilon?      --yes--> CERTIFIABLY_WINNING_BUT_NOT_UNIFORMLY_ACTIONABLE
       |
       no ----------------> UNIFORMLY_ACTIONABLE_WINNING
```

Actionability is a refinement only within the certifiably-winning branch
because \(\overline V=W\le R\).

## Vertex Sufficiency for Uniform Strategic Enforceability

For fixed controller mixture \(\sigma\) and pure state-contingent adversary
strategy \(\alpha\), \(L(\sigma,\alpha,p)\) is affine in the uncertain table
\(p\). Hence \(g_\sigma(p)=\max_\alpha L(\sigma,\alpha,p)\) is convex as a
pointwise maximum of affine functions. Every point of compact polytope
\(\mathcal F(q)\) is a convex combination of its vertices; convexity bounds
its value by the corresponding convex combination of vertex values. Therefore

\[
\sup_{p\in\mathcal F(q)}g_\sigma(p)
=\max_{v\in\operatorname{Vert}(\mathcal F(q))}g_\sigma(v),
\quad
R(q)=\min_\sigma\max_{v,\alpha}L(\sigma,\alpha,v).
\]

For finite controller actions \(C\), the exact LP is

\[
\min_{z,\sigma}z\quad\text{s.t.}\quad
z\ge\sum_{c\in C}\sigma_c L(c,\alpha,v)
\ \forall(v,\alpha),\quad
\sum_c\sigma_c=1,\quad\sigma_c\ge0.
\]

The implementation solves its two-action epigraph with exact rationals by
enumerating line intersections. No invalid exchange of
\(\min_p\max_{\alpha\text{ pure}}\) and
\(\max_{\alpha\text{ pure}}\min_p\) is used or licensed.

The same vertex proof does **not** transfer to
\(\overline V(q)=\sup_p\min_\sigma g_\sigma(p)\): a pointwise minimum of
convex functions need not be convex. For example,
\(\min(p,1-p)\) is maximized at the interior point \(p=1/2\) of \([0,1]\).
This defeats this vertex-sufficiency argument; it does not prove that no other
compact formula can exist.

## Canonical search result and layers

Exhaustive exact search covered all 81 public classes of the 256 deterministic
tables and all 625 public classes of the 6,561 bounded probabilistic tables.
No gap was found in those 81 frozen deterministic or 625 frozen
bounded-probabilistic public-signature classes. This finite enumeration does
not settle the continuous public fiber, because exact continuous
\(\sup_{p\in\mathcal F(q)}V(p)\) remains unresolved. The generic solver has a
regression case on the explicitly declared set `{d051,d204}`: both worlds have
value zero and require opposite pure controllers, while the common-policy value
is \(1/2\). Those games have different public signatures and are **not** passed
off as a canonical-signature witness.

For the continuous two-state uniform-prior fiber, the implementation now
constructs every vertex exactly. In each public cell, the state-zero coordinate
ranges from \(\max(0,2q-1)\) to \(\min(1,2q)\), with the other coordinate
equal to \(2q-p_0\); Cartesian endpoint choices give the full product-fiber
vertex set. This mechanically validates fixed-policy vertex sufficiency and
continuous-fiber robust \(R\), but not adaptive \(\overline V\).

The **inner game** is precisely the one-step object governed by
\(V,\underline V,\overline V,R\). The **outer decision wrapper** asks whether
to commit to an inner controller, defer, terminate, or request evidence. A
request may update \(I\to I'\), but the vertex proposition does not cover that
sequential acquisition process; a dynamic analysis would be required.

## Focused collision and terminology record

The primary-source collision targets are deliberately narrow:

* Gilboa and Schmeidler, “Maxmin Expected Utility with Non-Unique Prior,”
  *Journal of Mathematical Economics* 18(2), 1989, pp. 141–153,
  DOI `10.1016/0304-4068(89)90018-9`: axiomatizes maxmin expected utility over
  a set of priors. Multiple-prior worst-case choice is known; our finite safety
  loss/interface is only an instantiation.
* Ben-Tal, Goryashko, Guslitzer, and Nemirovski, “Adjustable Robust Solutions
  of Uncertain Linear Programs,” *Mathematical Programming* 99, 2004,
  pp. 351–376, DOI `10.1007/s10107-003-0454-y`: separates decisions fixed
  before uncertainty from adjustable decisions and develops tractable
  approximations. The here-and-now/wait-and-see distinction is known.
* Iyengar, “Robust Dynamic Programming,” *Mathematics of Operations Research*
  30(2), 2005, pp. 257–280, DOI `10.1287/moor.1040.0129`, and Nilim and El
  Ghaoui, “Robust Control of Markov Decision Processes with Uncertain
  Transition Matrices,” *Operations Research* 53(5), 2005, pp. 780–798,
  DOI `10.1287/opre.1050.0216`: establish robust-MDP dynamic programming under
  structured uncertainty. Our proposition is only finite one-step affine
  robust optimization and does not generalize to uncertain multi-round
  transitions.
* Russell and Wefald, *Do the Right Thing: Studies in Limited Rationality*, MIT
  Press, 1991: develops metareasoning about computation/action choice. Nelson
  and Narens, “Metamemory: A Theoretical Framework and New Findings,” in
  *The Psychology of Learning and Motivation* 26, 1990, pp. 125–173, separates
  monitoring and control in a metacognitive loop. These precedents are why the
  benchmark uses **epistemic-to-action consistency**, not unqualified
  “meta-control.”

Epistemic-to-action consistency means that a downstream action respects a
correctly inferred epistemic status: for example, an insufficient-information
answer followed by an information-dependent commitment is inconsistent,
whereas justified deferral is consistent. This operational metric is informed
by metareasoning and metacognitive monitoring-to-control framings; it is not a
claim to have discovered them.
