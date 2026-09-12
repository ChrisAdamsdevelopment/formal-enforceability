from copy import deepcopy

from enforceability.corpus.core import IsomorphismLimits, _renamed_dict, canonicalize_isomorphism
from enforceability.generation import GeneratorConfig, generate, game_id
from enforceability.schema import Game


def base_game():
    generated=generate(GeneratorConfig(family="observation-conflict",seed=7,horizon=1))
    return generated.game


def renamed(game, *, states=None, controller=None, adversary=None, observations=None):
    return Game.from_dict(_renamed_dict(game,states or tuple("S"+str(i) for i in range(len(game.states))),controller or tuple("C"+str(i) for i in range(len(game.controller_actions))),adversary or tuple("A"+str(i) for i in range(len(game.adversary_actions))),observations or tuple("O"+str(i) for i in range(len(game.observations)))))


def cid(game): return canonicalize_isomorphism(game).class_id


def test_each_identifier_sort_can_be_renamed():
    game=base_game()
    variants=[
        renamed(game),
        renamed(game,controller=tuple(reversed(tuple("C"+str(i) for i in range(len(game.controller_actions)))))),
        renamed(game,adversary=tuple(reversed(tuple("A"+str(i) for i in range(len(game.adversary_actions)))))),
        renamed(game,observations=tuple(reversed(tuple("O"+str(i) for i in range(len(game.observations))))))]
    assert all(cid(x)==cid(game) for x in variants)
    assert game_id(variants[0]) != game_id(game)


def mutate(game, field, operation):
    raw=deepcopy(game.to_dict()); operation(raw); return Game.from_dict(raw)


def test_safety_relevant_fields_prevent_isomorphism():
    game=base_game(); changes=[]
    changes.append(mutate(game,"failure",lambda r: r.update(failure_states=["x","q0"],recovery_states=["r"])))
    changes.append(mutate(game,"observation",lambda r: r.update(observation_map={**r["observation_map"],"q0":"r"})))
    def probability(r):
        row=next(x for x in r["transitions"] if x["state"]=="q0" and x["controller_action"]=="c0"); row["outcomes"]=[{"state":"r","probability":"1/2"},{"state":"x","probability":"1/2"}]
    changes.append(mutate(game,"probability",probability))
    changes.append(mutate(game,"availability",lambda r: r["action_availability"]["c0"].clear()))
    changes.append(mutate(game,"reward",lambda r: r["legitimate_rewards"].append({"state":"q0","controller_action":"c0","reward":"1"})))
    changes.append(mutate(game,"epsilon",lambda r: r.update(epsilon="1/2")))
    assert all(cid(x)!=cid(game) for x in changes)


def test_same_game_id_implies_same_class_and_limit_is_typed():
    game=base_game(); copy=Game.from_json(game.to_json())
    assert game_id(game)==game_id(copy) and cid(game)==cid(copy)
    unresolved=canonicalize_isomorphism(game,IsomorphismLimits(1))
    assert unresolved.status=="ISOMORPHISM_UNRESOLVED" and unresolved.class_id is None


def test_generated_metamorphic_renaming():
    for family in ("observation-conflict","authority-limitation","timing","capability-restriction","mixed-restoration"):
        kwargs={"family":family,"seed":3}
        if family=="timing": kwargs["horizon"]=2
        game=generate(GeneratorConfig(**kwargs)).game
        assert cid(game)==cid(renamed(game))
