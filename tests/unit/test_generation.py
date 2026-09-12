from dataclasses import replace
from fractions import Fraction
import json
import pytest

from enforceability import Restoration, solve
from enforceability.generation import (FAMILIES, ComplexityLimits, GeneratedGame, GenerationError,
    GenerationRejected, GeneratorConfig, add_controller_action, build_manifest, canonical_game_json,
    canonical_json, filter_after_solution, game_id, generate, transform, validate_no_leakage)


def made(config):
    value=generate(config); assert isinstance(value,GeneratedGame); return value


@pytest.mark.parametrize("family",FAMILIES)
def test_every_family_round_trips_and_is_solved_only_in_manifest(family):
    c=GeneratorConfig(family=family,seed=17)
    generated=made(c)
    assert generated.game.from_json(generated.game.to_json()) == generated.game
    # Structural output has no result field.  Labelling is the subsequent call.
    assert not hasattr(generated,"oracle")
    assert build_manifest(c,generated)["oracle"] == solve(generated.game).to_dict()


def test_seed_reproducibility_and_deterministic_diversity():
    c=GeneratorConfig(family="observation-conflict",seed=2,ambiguous_states=3)
    a=made(c); b=made(c)
    assert canonical_game_json(a.game)==canonical_game_json(b.game)
    assert game_id(a.game)==game_id(b.game)
    assert solve(a.game).to_dict()==solve(b.game).to_dict()
    ids={game_id(made(replace(c,seed=s)).game) for s in range(8)}
    assert len(ids)>=3


def test_fingerprint_ignores_display_only_but_tracks_formal_fields():
    game=made(GeneratorConfig(family="timing",seed=1)).game
    raw=game.to_dict(); raw["display_labels"]={"q":"anything"}; displayed=game.from_dict(raw)
    assert game_id(game)==game_id(displayed)
    raw=game.to_dict(); raw["epsilon"]="1"; changed=game.from_dict(raw)
    assert game_id(game)!=game_id(changed)


def test_exact_rational_stochastic_generation():
    game=made(GeneratorConfig(family="observation-conflict",seed=0,stochasticity=True)).game
    assert any(p==Fraction(1,2) for out in game.transitions.values() for _,p in out)
    assert all(sum((p for _,p in out),Fraction())==1 for out in game.transitions.values())


def test_refinement_zero_and_positive_value_and_record():
    base=made(GeneratorConfig(family="observation-conflict",seed=0,common_action=True)).game
    raw=base.to_dict(); raw["observations"].append("split"); base=base.from_dict(raw)
    refined,record=transform(base,Restoration("z",observation_overrides=(("q1","split"),)),5)
    assert solve(refined).failure_probability==solve(base).failure_probability==0
    assert record.parent_game_id==game_id(base) and record.child_game_id==game_id(refined)
    base=made(GeneratorConfig(family="observation-conflict",seed=0)).game
    raw=base.to_dict(); raw["observations"].append("split"); base=base.from_dict(raw)
    refined,_=transform(base,Restoration("z",observation_overrides=(("q1","split"),)),5)
    assert solve(refined).failure_probability < solve(base).failure_probability


def test_restriction_zero_positive_and_both_required():
    generated=made(GeneratorConfig(family="capability-restriction",seed=0,adversary_action_count=3))
    base=generated.game
    irrelevant,_=transform(base,Restoration("z",remove_adversary_actions=frozenset({"a0"})),0)
    assert solve(irrelevant).failure_probability==solve(base).failure_probability
    harmful=next(r for r in generated.restorations if solve(transform(base,r,0)[0]).failure_probability < solve(base).failure_probability)
    restricted,_=transform(base,harmful,0)
    assert solve(restricted).failure_probability < solve(base).failure_probability
    mixed=made(GeneratorConfig(family="mixed-restoration",seed=0)).game
    rs=Restoration("r",observation_overrides=(("q0","u0"),("q1","u1")))
    rr=Restoration("a",remove_adversary_actions=frozenset({"a1"}))
    assert solve(transform(mixed,rs,0)[0]).failure_probability>0
    assert solve(transform(mixed,rr,0)[0]).failure_probability>0
    both=transform(transform(mixed,rs,0)[0],rr,0)[0]
    assert solve(both).failure_probability==0


def test_controller_addition_cannot_hurt():
    base=made(GeneratorConfig(family="observation-conflict",seed=0)).game
    outcomes={(s,a):(("r",Fraction(1)),) for s in base.states for a in base.adversary_actions}
    child,record=add_controller_action(base,"c_added",outcomes,(0,),9)
    assert solve(child).failure_probability<=solve(base).failure_probability
    assert record.transformation_type=="controller-capability-addition"


def test_restoration_tie_and_no_feasible_library():
    tied=build_manifest(GeneratorConfig(family="mixed-restoration",seed=0),made(GeneratorConfig(family="mixed-restoration",seed=0)))
    assert len(tied["restorations"])==3
    none=build_manifest(GeneratorConfig(family="mixed-restoration",seed=0,mode="none"),made(GeneratorConfig(family="mixed-restoration",seed=0,mode="none")))
    assert not any(x["oracle"]["threshold_satisfied"] for x in none["restorations"])


def test_complexity_rejection_is_typed_and_not_labelled():
    c=GeneratorConfig(family="observation-conflict",seed=4,limits=ComplexityLimits(max_states=2))
    rejected=generate(c); assert isinstance(rejected,GenerationRejected)
    assert rejected.reason=="estimated_oracle_complexity" and not hasattr(rejected,"status")


def test_leakage_guard_and_post_solution_filter():
    with pytest.raises(GenerationError,match="answer_bearing_metadata"):
        validate_no_leakage({"nested":{"correct_action":"c0"}})
    c=GeneratorConfig(family="timing",seed=1); manifest=build_manifest(c,made(c))
    decision=filter_after_solution(manifest,lambda oracle: oracle["threshold_satisfied"])
    assert decision.oracle==manifest["oracle"]


def test_manifest_canonical_serialization():
    c=GeneratorConfig(family="probe",seed=3); a=canonical_json(build_manifest(c,made(c))); b=canonical_json(build_manifest(c,made(c)))
    assert a==b and json.loads(a)["formal_game"]
