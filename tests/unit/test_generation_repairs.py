from dataclasses import asdict, replace
from fractions import Fraction

import pytest

from enforceability import SolveStatus, optimal_restoration, solve
from enforceability.generation import (ComplexityLimits, GeneratedGame, GenerationError,
    GenerationRejected, GeneratorConfig, build_manifest, canonical_game_json, generate, transform)


def made(config):
    result=generate(config)
    assert isinstance(result,GeneratedGame)
    return result


def test_effective_probe_dimensions_and_horizon_are_limited():
    rejected=generate(GeneratorConfig(family="probe",seed=0,limits=ComplexityLimits(max_states=5)))
    assert isinstance(rejected,GenerationRejected) and rejected.estimates["states"]==6
    rejected=generate(GeneratorConfig(family="probe",seed=0,horizon=3,probe_delay=2,limits=ComplexityLimits(max_horizon=2)))
    assert isinstance(rejected,GenerationRejected) and rejected.estimates["horizon"]==3
    rejected=generate(GeneratorConfig(family="timing",seed=0,horizon=2,limits=ComplexityLimits(max_horizon=1)))
    assert isinstance(rejected,GenerationRejected) and rejected.estimates["horizon"]==2


def test_fixed_action_counts_feed_actual_profile_estimate():
    rejected=generate(GeneratorConfig(family="probe",seed=0,controller_action_count=1,
        limits=ComplexityLimits(max_policy_profiles=1)))
    assert isinstance(rejected,GenerationRejected)
    assert rejected.estimates["controller_actions"]==4


def test_huge_values_reject_before_power_or_structural_allocation():
    huge=10**100
    rejected=generate(GeneratorConfig(family="observation-conflict",seed=3,horizon=huge,
        ambiguous_states=huge,limits=ComplexityLimits(max_states=10,max_horizon=4)))
    assert isinstance(rejected,GenerationRejected)
    assert rejected.reason=="estimated_oracle_complexity" and not hasattr(rejected,"status")


def test_artifact_bound_provenance_and_reproduction():
    config=GeneratorConfig(family="observation-conflict",seed=9,ambiguous_states=3)
    artifact=made(config)
    assert build_manifest(artifact)==build_manifest(GeneratorConfig(**{**asdict(config),"limits":config.limits}),artifact)
    for other in (replace(config,seed=10),GeneratorConfig(family="authority-limitation",seed=9),replace(config,ambiguous_states=4)):
        with pytest.raises(GenerationError,match="provenance_mismatch"): build_manifest(other,artifact)
    manifest=build_manifest(artifact); raw=manifest["config"]
    reconstructed=GeneratorConfig(**{**raw,"limits":ComplexityLimits(**raw["limits"])})
    assert canonical_game_json(made(reconstructed).game)==canonical_game_json(artifact.game)


@pytest.mark.parametrize("epsilon",[0.5,True,"bad","2"])
def test_epsilon_contract_is_strict(epsilon):
    with pytest.raises(GenerationError): GeneratorConfig(family="timing",seed=0,epsilon=epsilon)


@pytest.mark.parametrize("field",["common_action","probe_available","probe_informative","stochasticity"])
@pytest.mark.parametrize("value",[1,"true",None])
def test_boolean_contract_is_strict(field,value):
    with pytest.raises(GenerationError): GeneratorConfig(family="timing",seed=0,**{field:value})


def test_modes_and_family_minima_are_strict():
    with pytest.raises(GenerationError): GeneratorConfig(family="capability-restriction",seed=0,mode="mutli")
    with pytest.raises(GenerationError): GeneratorConfig(family="timing",seed=0,mode="robust")
    with pytest.raises(GenerationError): GeneratorConfig(family="probe",seed=0,horizon=1)
    with pytest.raises(GenerationError): GeneratorConfig(family="probe",seed=0,horizon=2,probe_delay=2)
    assert GeneratorConfig(family="timing",seed=0,epsilon=Fraction(1,3)).epsilon==Fraction(1,3)


def test_transformation_categories_are_derived_and_mislabels_rejected():
    artifact=made(GeneratorConfig(family="capability-restriction",seed=0))
    restoration=artifact.restorations[0]
    _,record=transform(artifact.game,restoration,7)
    assert record.transformation_type=="adversary-capability-removal"
    assert set(record.changed_formal_fields)=={"adversary_actions","transitions"}
    with pytest.raises(GenerationError,match="mislabelled_transformation"):
        transform(artifact.game,restoration,"observation-refinement",7)


def test_observation_and_authority_family_semantics():
    conflict=made(GeneratorConfig(family="observation-conflict",seed=0))
    common=made(GeneratorConfig(family="observation-conflict",seed=0,common_action=True))
    assert solve(conflict.game).status is SolveStatus.LOSING
    assert solve(common.game).status is SolveStatus.WINNING
    weak=made(GeneratorConfig(family="authority-limitation",seed=0,adversary_action_count=2,coverage=1))
    robust=made(GeneratorConfig(family="authority-limitation",seed=0,adversary_action_count=2,coverage=1,mode="robust"))
    assert solve(weak.game).status is SolveStatus.LOSING
    assert solve(robust.game).status is SolveStatus.WINNING


def test_probe_four_semantic_cases_and_distinct_delays():
    valuable=made(GeneratorConfig(family="probe",seed=0,horizon=2,probe_delay=1))
    baseline=made(GeneratorConfig(family="probe",seed=0,horizon=2,probe_delay=1,probe_available=False))
    useless=made(GeneratorConfig(family="probe",seed=0,horizon=2,probe_delay=1,probe_informative=False))
    late=made(GeneratorConfig(family="probe",seed=0,horizon=3,probe_delay=2,mode="too-late"))
    common=made(GeneratorConfig(family="probe",seed=0,horizon=2,probe_delay=1,common_action=True,probe_available=False))
    assert solve(valuable.game).status is SolveStatus.WINNING
    assert all(solve(x.game).status is SolveStatus.LOSING for x in (baseline,useless,late))
    assert solve(common.game).status is SolveStatus.WINNING
    delay2=made(GeneratorConfig(family="probe",seed=0,horizon=3,probe_delay=2))
    delay3=made(GeneratorConfig(family="probe",seed=0,horizon=4,probe_delay=3,limits=ComplexityLimits(max_policy_profiles=10_000_000)))
    assert ("d1_0",Fraction(1)) in delay2.game.transitions[("q0","probe","a0")]
    assert ("d2_0",Fraction(1)) in delay3.game.transitions[("d1_0","wait","a0")]
    assert canonical_game_json(delay2.game)!=canonical_game_json(delay3.game)


def test_timing_and_capability_family_semantics():
    early=made(GeneratorConfig(family="timing",seed=0,intervention_round=0))
    late=made(GeneratorConfig(family="timing",seed=0,intervention_round=1))
    assert solve(early.game).status is SolveStatus.WINNING and solve(late.game).status is SolveStatus.LOSING
    multiple=made(GeneratorConfig(family="capability-restriction",seed=0,adversary_action_count=3,mode="multi"))
    result=optimal_restoration(multiple.game,multiple.restorations)
    assert any(e.restoration.name=="z_combined" and e.game_result.threshold_satisfied for e in result.evaluations)
    absent=made(GeneratorConfig(family="capability-restriction",seed=0,adversary_action_count=3,mode="multi-absent"))
    assert optimal_restoration(absent.game,absent.restorations).minimum_cost is None
    none=made(GeneratorConfig(family="capability-restriction",seed=0,mode="none"))
    assert optimal_restoration(none.game,none.restorations).minimum_cost is None


def test_mixed_combination_and_endogenous_tie():
    artifact=made(GeneratorConfig(family="mixed-restoration",seed=0,mode="tie"))
    refinement,restriction=artifact.restorations[:2]
    assert not solve(transform(artifact.game,refinement,0)[0]).threshold_satisfied
    assert not solve(transform(artifact.game,restriction,0)[0]).threshold_satisfied
    both=transform(transform(artifact.game,refinement,0)[0],restriction,0)[0]
    assert solve(both).threshold_satisfied
    result=optimal_restoration(artifact.game,artifact.restorations)
    assert {e.restoration.name for e in result.optimal}=={"z2","z3"}
    assert len({e.cost for e in result.optimal})==1
