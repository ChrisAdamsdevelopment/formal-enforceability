from fractions import Fraction
import pytest
from enforceability import SolveStatus,solve,validate_witness
from tests.fixtures import authority_nullity,conflicting,finite_horizon,irrelevant_ambiguity,probe,recovery,timing

@pytest.mark.parametrize(("game","expected"),[(conflicting(),SolveStatus.LOSING),(conflicting(freeze=True),SolveStatus.WINNING),
 (authority_nullity(),SolveStatus.LOSING),(probe(),SolveStatus.WINNING),(irrelevant_ambiguity(),SolveStatus.WINNING),
 (recovery(),SolveStatus.WINNING),(finite_horizon(1),SolveStatus.WINNING),(finite_horizon(2),SolveStatus.LOSING),
 (timing(False),SolveStatus.LOSING),(timing(True),SolveStatus.WINNING)])
def test_canonical_games(game,expected):
    result=solve(game);assert result.status is expected;assert result.threshold_satisfied is (expected is SolveStatus.WINNING)
    assert (result.witness is not None) is result.threshold_satisfied
    if result.witness:assert validate_witness(game,result.witness)

def test_exact_probabilistic_value_and_epsilon():
    # One unavoidable action, one response: exact one-third failure.
    game=conflicting(freeze=True);raw=game.to_dict();raw["epsilon"]="1/3"
    for row in raw["transitions"]:
        if row["state"] in ("s1","s2") and row["controller_action"]=="FREEZE":
            row["outcomes"]=[{"state":"SAFE","probability":"2/3"},{"state":"FAIL","probability":"1/3"}]
    result=solve(type(game).from_dict(raw));assert result.failure_probability==Fraction(1,3);assert result.status is SolveStatus.WINNING

def test_simultaneous_private_randomization_can_be_necessary():
    # Matching pennies: adversary does not see the future controller draw.
    game=authority_nullity();raw=game.to_dict();raw["epsilon"]="1/2";game=type(game).from_dict(raw)
    result=solve(game);assert result.failure_probability==Fraction(1,2);assert len(result.witness)==2

def test_repeatability_and_zero_horizon():
    assert solve(probe())==solve(probe())
    result=solve(finite_horizon(0));assert result.failure_probability==0 and validate_witness(finite_horizon(0),result.witness)
