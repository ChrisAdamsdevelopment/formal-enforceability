# Independent probabilistic validation

## Purpose and algorithms

The primary oracle enumerates controller and informed-adversary pure policies,
recursively evaluates each profile with exact rational arithmetic, and solves
the resulting zero-sum matrix with the repository's exact support-enumeration
solver. It remains the source of exact benchmark labels.

The independent validator is deliberately bounded to small games. It builds an
explicit reachable history tree by traversing every positive-probability branch
and every action pair. Controller information sets contain only observation
history and prior controller actions. Adversary information sets contain state
history, prior controller actions, and prior adversary actions; they exclude the
controller's simultaneous current action. Pure policies are enumerated from
those independently collected information sets. Each profile is evaluated by
iteratively propagating exact `Fraction` mass forward, stopping at failure,
recovery, or the horizon.

The resulting exact-rational payoff entries are converted to floating point
only at the matrix-solving boundary. `scipy.optimize.linprog(method="highs")`
separately solves the controller primal and adversary dual. The validator
requires their values to agree within `1e-9`; it reports their gap and both
mixtures. SciPy/HiGHS is an external LP implementation and therefore does not
share the primary solver's support enumeration or rational linear elimination.

## Independence boundary

Shared code is limited to the validated `Game` schema and Python's generic
`Fraction` representation. The production validator does **not** import the
primary oracle. In particular, it neither calls nor copies the primary
`_controller_histories`, `_adversary_histories`, policy enumerators,
`profile_failure`, `_solve_linear`, `solve_matrix`, or `solve` path. The report
harness calls public primary `solve()` only after producing each independent
answer, solely to compare results.

The explicit tree, local Cartesian policy enumeration, iterative mass
propagation, and external primal/dual LPs can detect disagreements caused by
hidden-state leakage into controller information, loss of perfect recall,
incorrect informed-adversary histories, exposure of current private controller
randomness, terminal/recovery/horizon errors, stochastic-mass errors, and bugs
in either matrix solver. The suite covers semantic fixtures, exact values
`1/3` and `1/2`, all 256 deterministic one-step games in the declared family,
all 81 probabilistic one-step games, and a stochastic multi-round game.

Common-mode errors remain possible: both implementations consume the same
validated `Game`, may share a mistaken interpretation of the written game
definition, and run on the same Python/runtime platform. Floating-point LP
results are estimates, not rational certificates; threshold classification is
reported as numerically unresolved when tolerance bounds straddle epsilon.
Agreement between implementations does not prove that the formal model is the
correct model of a real deployment. This is independent validation, not a
second source of formal ground truth.

## Reproduction and limits

Install the test extra and run:

```console
python -m pip install -e '.[test]'
validate-independent-oracle
```

The JSON report is deterministic: it contains versions, tolerance, fixed case
counts, maximum errors and gaps, mismatch and unresolved counts, and PASS/FAIL;
it contains no timestamp or random identifier. No platform-sensitive generated
report is checked in.

Default limits are 32 combined reachable information sets, 4,096 pure policies
per player, and 65,536 payoff-matrix cells. `ValidationLimits` makes these
bounds configurable, and `ValidationLimitError` stops oversized games before
unbounded enumeration or matrix construction.
