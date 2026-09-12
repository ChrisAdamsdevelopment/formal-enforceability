"""Additional generated cross-checks, enabled when the test extra is installed."""
import pytest

hypothesis = pytest.importorskip("hypothesis")
from hypothesis import given, settings, strategies as st  # noqa: E402

from enforceability import solve  # noqa: E402
from enforceability.oracle.tiny import classify_tiny  # noqa: E402
from tests.fixtures import make_game  # noqa: E402


@settings(max_examples=40, deadline=None)
@given(st.lists(st.sampled_from(("s0", "s1", "FAIL")), min_size=4, max_size=4))
def test_generated_transition_tables_match_independent_solver(successors):
    keys = (("s0", "A", "X"), ("s0", "B", "X"), ("s1", "A", "X"), ("s1", "B", "X"))
    game = make_game(
        states=("s0", "s1", "FAIL"),
        initial=("s0", "s1"),
        ca=("A", "B"),
        aa=("X",),
        obs_map={"s0": "same", "s1": "same", "FAIL": "fail"},
        transitions=dict(zip(keys, successors)),
    )
    assert solve(game).status is classify_tiny(game)
