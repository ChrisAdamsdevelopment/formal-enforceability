from fractions import Fraction
from enforceability import Restoration,SolveStatus,optimal_restoration,solve
from enforceability.restoration import apply_restoration
from tests.fixtures import capability_removal,restoration_cost_game

def test_declared_capability_removal_changes_loss_to_win():
    game=capability_removal();assert solve(game).status is SolveStatus.LOSING
    transformed=apply_restoration(game,Restoration("remove block",remove_adversary_actions=frozenset({"BLOCK"})))
    assert solve(transformed).status is SolveStatus.WINNING

def test_endogenous_cost_selects_all_tied_minima():
    game=restoration_cost_game()
    candidates=tuple(Restoration(name,availability_overrides=(("UNSAFE",()),(action,(0,)))) for name,action in (("mid-a","MID_A"),("low","LOW"),("mid-b","MID_B")))
    result=optimal_restoration(game,candidates)
    assert result.unrestricted_utility==10
    assert {e.restoration.name:e.cost for e in result.evaluations}=={"mid-a":Fraction(3),"low":Fraction(5),"mid-b":Fraction(3)}
    assert result.minimum_cost==3
    assert {e.restoration.name for e in result.optimal}=={"mid-a","mid-b"}
    assert all(e.game_result.threshold_satisfied for e in result.evaluations)
