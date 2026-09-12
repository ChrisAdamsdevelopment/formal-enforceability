import inspect,json
from enforceability import SolveStatus,solve
from enforceability.types import ControllerInformationHistory
from tests.fixtures import conflicting

def test_policy_input_has_only_visible_fields():
    assert set(ControllerInformationHistory.__slots__)=={"observations","previous_actions"};assert "state" not in inspect.signature(ControllerInformationHistory).parameters
def test_same_observation_produces_identical_interface_even_probabilistically():
    game=conflicting(); histories=[ControllerInformationHistory((game.observation_map[s],)) for s in game.initial_states]
    assert histories[0]==histories[1];assert histories[0].to_controller_json()==histories[1].to_controller_json()
def test_serialization_excludes_hidden_and_debug_fields():
    payload=json.loads(ControllerInformationHistory(("same",)).to_controller_json())
    assert payload=={"observations":["same"],"previous_actions":[]};assert not {"state","hidden_state","debug","metadata"}&payload.keys()
def test_fixture_a_loss_is_information_boundary():
    assert solve(conflicting()).status is SolveStatus.LOSING;assert solve(conflicting(distinguish=True)).status is SolveStatus.WINNING
