"""Deterministic generated transformations (Hypothesis is intentionally optional)."""
from enforceability import solve
from enforceability.schema import Game
from tests.fixtures import conflicting,irrelevant_ambiguity

def relabel(game):
    raw=game.to_dict();sm={x:f"s{i}" for i,x in enumerate(game.states)};cm={x:f"c{i}" for i,x in enumerate(game.controller_actions)};am={x:f"a{i}" for i,x in enumerate(game.adversary_actions)};om={x:f"o{i}" for i,x in enumerate(game.observations)}
    raw["states"]=[sm[x] for x in raw["states"]];raw["controller_actions"]=[cm[x] for x in raw["controller_actions"]];raw["adversary_actions"]=[am[x] for x in raw["adversary_actions"]];raw["observations"]=[om[x] for x in raw["observations"]]
    raw["initial_distribution"]=[{"state":sm[x["state"]],"probability":x["probability"]} for x in raw["initial_distribution"]];raw["observation_map"]={sm[k]:om[v] for k,v in raw["observation_map"].items()}
    for key in ("failure_states","recovery_states"):raw[key]=[sm[x] for x in raw[key]]
    raw["transitions"]=[{"state":sm[r["state"]],"controller_action":cm[r["controller_action"]],"adversary_action":am[r["adversary_action"]],"outcomes":[{"state":sm[x["state"]],"probability":x["probability"]} for x in r["outcomes"]]} for r in raw["transitions"]]
    raw["action_availability"]={cm[k]:v for k,v in raw["action_availability"].items()};raw["legitimate_rewards"]=[{"state":sm[x["state"]],"controller_action":cm[x["controller_action"]],"reward":x["reward"]} for x in raw["legitimate_rewards"]]
    return Game.from_dict(raw)

def test_rename_and_display_labels_invariant():
    for game in (conflicting(),conflicting(freeze=True),irrelevant_ambiguity()):
        assert solve(relabel(game)).failure_probability==solve(game).failure_probability
        raw=game.to_dict();raw["display_labels"]={"anything":"arbitrary prose"};assert solve(Game.from_dict(raw)).failure_probability==solve(game).failure_probability

def test_adding_and_removing_controller_actions_directions():
    base=irrelevant_ambiguity();raw=base.to_dict();raw["controller_actions"].append("BAD");raw["action_availability"]["BAD"]=[0]
    for s in raw["states"]:raw["transitions"].append({"state":s,"controller_action":"BAD","adversary_action":"WAIT","outcomes":[{"state":"FAIL","probability":"1"}]})
    added=Game.from_dict(raw);assert solve(added).failure_probability<=solve(base).failure_probability
    raw=base.to_dict();raw["controller_actions"]=["MOVE"];raw["action_availability"]={"MOVE":[0]};raw["transitions"]=[x for x in raw["transitions"] if x["controller_action"]=="MOVE"]
    assert solve(Game.from_dict(raw)).failure_probability>=solve(base).failure_probability

def test_adding_and_removing_adversary_actions_directions():
    base=irrelevant_ambiguity();raw=base.to_dict();raw["adversary_actions"].append("EXTRA")
    raw["transitions"] += [{**r,"adversary_action":"EXTRA"} for r in list(raw["transitions"])]
    added=Game.from_dict(raw);assert solve(added).failure_probability>=solve(base).failure_probability
    reduced=added.to_dict();reduced["adversary_actions"]=["WAIT"];reduced["transitions"]=[x for x in reduced["transitions"] if x["adversary_action"]=="WAIT"]
    assert solve(Game.from_dict(reduced)).failure_probability<=solve(added).failure_probability

def test_refinement_and_unreachable_state_do_not_worsen():
    base=irrelevant_ambiguity();raw=base.to_dict();raw["observations"].append("refined");raw["observation_map"]["s2"]="refined"
    assert solve(Game.from_dict(raw)).failure_probability<=solve(base).failure_probability
    raw=base.to_dict();raw["states"].append("u");raw["observations"].append("ou");raw["observation_map"]["u"]="ou"
    for c in raw["controller_actions"]:raw["transitions"].append({"state":"u","controller_action":c,"adversary_action":"WAIT","outcomes":[{"state":"u","probability":"1"}]})
    assert solve(Game.from_dict(raw)).failure_probability==solve(base).failure_probability


def test_perfect_information_does_not_improve_existing_zero_value():
    base = irrelevant_ambiguity()
    raw = base.to_dict()
    raw["observations"].append("perfect-s2")
    raw["observation_map"]["s2"] = "perfect-s2"
    assert solve(base).failure_probability == solve(Game.from_dict(raw)).failure_probability == 0
