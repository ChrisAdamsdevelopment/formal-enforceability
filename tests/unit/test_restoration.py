from fractions import Fraction
import pytest
from enforceability import Restoration,SolveStatus,optimal_restoration,solve
from enforceability.restoration import apply_restoration
from enforceability.schema import Game, InvalidGame
from tests.fixtures import capability_removal,restoration_cost_game
from tests.fixtures import conflicting

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


def game_with_unused_observation():
    raw = conflicting().to_dict()
    raw["observations"].append("split-s2")
    return Game.from_dict(raw)


def test_observation_refinement_accepts_valid_split():
    game = game_with_unused_observation()
    restored = apply_restoration(game, Restoration("split", observation_overrides=(("s2", "split-s2"),)))
    assert restored.observation_map["s1"] != restored.observation_map["s2"]


def test_observation_refinement_rejects_merge_of_distinct_classes():
    game = conflicting(distinguish=True)
    with pytest.raises(InvalidGame, match="may not merge"):
        apply_restoration(game, Restoration("merge", observation_overrides=(("s1", "two"),)))


def test_observation_refinement_accepts_unchanged_map():
    game = conflicting(distinguish=True)
    restored = apply_restoration(game, Restoration("unchanged", observation_overrides=(("s1", "one"),)))
    assert restored.observation_map == game.observation_map


def test_valid_refinement_makes_indistinguishability_fixture_winning():
    game = game_with_unused_observation()
    assert solve(game).status is SolveStatus.LOSING
    restored = apply_restoration(game, Restoration("split", observation_overrides=(("s2", "split-s2"),)))
    assert solve(restored).status is SolveStatus.WINNING


@pytest.mark.parametrize("belief", [
    {"s": 1},
    {"s": "1"},
    {"s": Fraction(1, 1)},
])
def test_optimal_restoration_accepts_exact_b0_types(belief):
    result = optimal_restoration(capability_removal(), (), b0=belief)
    assert result.evaluations == ()


@pytest.mark.parametrize("belief", [
    {"s": 1.0},
    {"s": True},
    {"s": -1},
    {"unknown": 1},
    {"s": "1/2"},
])
def test_optimal_restoration_rejects_invalid_or_inexact_b0(belief):
    with pytest.raises(InvalidGame):
        optimal_restoration(capability_removal(), (), b0=belief)
