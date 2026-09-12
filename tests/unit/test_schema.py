import json,pytest
from enforceability.schema import Game,InvalidGame,UnsupportedGameClass
from enforceability.types import SolveStatus
from tests.fixtures import conflicting

def raw():return conflicting().to_dict()
def test_deterministic_round_trip():
    game=conflicting();assert Game.from_json(game.to_json())==game;assert Game.from_json(game.to_json()).to_json()==game.to_json()


def test_explicit_zero_mass_initial_state_round_trips_exactly():
    value = raw()
    value["initial_distribution"] = [
        {"state": "s1", "probability": "1"},
        {"state": "s2", "probability": "0"},
    ]
    game = Game.from_dict(value)
    assert game.to_dict()["initial_distribution"] == value["initial_distribution"]
    restored = Game.from_json(game.to_json())
    assert restored == game
    assert restored.to_json() == game.to_json()
@pytest.mark.parametrize("change",[("states",[]),("initial_distribution",[]),("horizon",-1),("epsilon","2"),("recovery_states",["FAIL"])])
def test_invalid(change):
    value=raw();value[change[0]]=change[1]
    with pytest.raises(InvalidGame):Game.from_dict(value)
@pytest.mark.parametrize("probabilities",[["1/2","1/3"],["4/3","-1/3"],[0.1,0.9]])
def test_probabilities_must_be_exact_nonnegative_unit_mass(probabilities):
    value=raw();value["initial_distribution"]=[{"state":"s1","probability":probabilities[0]},{"state":"s2","probability":probabilities[1]}]
    with pytest.raises(InvalidGame):Game.from_dict(value)
def test_missing_unknown_transition_and_observation_fail():
    value=raw();value["transitions"].pop()
    with pytest.raises(InvalidGame):Game.from_dict(value)
    value=raw();value["transitions"][0]["outcomes"][0]["state"]="ghost"
    with pytest.raises(InvalidGame):Game.from_dict(value)
    value=raw();value["observation_map"]["s1"]="ghost"
    with pytest.raises(InvalidGame):Game.from_dict(value)
def test_unsupported_and_error_are_not_losing():
    value=raw();value["schema_version"]="future"
    with pytest.raises(UnsupportedGameClass):Game.from_dict(value)
    with pytest.raises(ValueError):SolveStatus("SOLVER_ERROR")
    with pytest.raises(TypeError):json.dumps(InvalidGame("boom"))
