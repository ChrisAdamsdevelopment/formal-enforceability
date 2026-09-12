"""Terminal states never create post-terminal controller decisions."""
from enforceability import SolveStatus, solve
from enforceability.oracle import _controller_histories, enumerate_controller_policies
from enforceability.types import ControllerInformationHistory
from tests.fixtures import make_game


def terminal_game(*, initial, terminal, successor):
    states = ("start", "FAIL", "RECOVERED")
    actions = ("A", "B")
    transitions = {(state, action, "WAIT"): successor for state in terminal for action in actions}
    return make_game(
        states=states,
        initial=initial,
        ca=actions,
        obs_map={"start": "start-observation", "FAIL": "failure-observation", "RECOVERED": "recovery-observation"},
        transitions=transitions,
        failure=("FAIL",),
        recovery=("RECOVERED",),
        horizon=3,
    )


def test_initial_failure_has_no_controller_policy_decision():
    game = terminal_game(initial=("FAIL",), terminal=("FAIL",), successor="start")
    assert _controller_histories(game) == ()
    assert list(enumerate_controller_policies(game)) == [{}]
    assert solve(game).status is SolveStatus.LOSING


def test_initial_recovery_has_no_controller_policy_decision():
    game = terminal_game(initial=("RECOVERED",), terminal=("RECOVERED",), successor="start")
    assert _controller_histories(game) == ()
    assert list(enumerate_controller_policies(game)) == [{}]
    assert solve(game).status is SolveStatus.WINNING


def test_entering_failure_stops_before_post_terminal_history():
    game = terminal_game(initial=("start",), terminal=("start",), successor="FAIL")
    assert _controller_histories(game) == (ControllerInformationHistory(("start-observation",)),)
    assert len(list(enumerate_controller_policies(game))) == 2
    assert solve(game).status is SolveStatus.LOSING


def test_entering_recovery_stops_before_post_terminal_history():
    game = terminal_game(initial=("start",), terminal=("start",), successor="RECOVERED")
    assert _controller_histories(game) == (ControllerInformationHistory(("start-observation",)),)
    assert len(list(enumerate_controller_policies(game))) == 2
    assert solve(game).status is SolveStatus.WINNING


def test_irrelevant_terminal_transition_rows_do_not_change_policy_space():
    failure_self_loops = terminal_game(initial=("start",), terminal=("start",), successor="FAIL")
    raw = failure_self_loops.to_dict()
    for row in raw["transitions"]:
        if row["state"] == "FAIL":
            row["outcomes"] = [{"state": "start", "probability": "1"}]
    failure_returns = type(failure_self_loops).from_dict(raw)
    assert _controller_histories(failure_returns) == _controller_histories(failure_self_loops)
    assert len(list(enumerate_controller_policies(failure_returns))) == len(list(enumerate_controller_policies(failure_self_loops)))
