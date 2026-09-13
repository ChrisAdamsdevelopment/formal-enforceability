import inspect, json
from types import MappingProxyType

import pytest

from enforceability.rendering import (DOMAINS, RenderCorpusSpec, RendererSpec, RestorationTaskContext,
    assign_primary_domain, build_render_plan, deep_freeze, deep_thaw, prompt_from_plan, reconstruct_game_from_clauses,
    reconstruct_surface_game_from_clauses, render_case, scan_direct_leakage, semantic_signature, to_model_input, validate_plan)
from enforceability.rendering.freeze import STAGE4_FINGERPRINT, _plan_from_dict
from enforceability.schema import Game

def game():
    row=json.loads(next(__import__('pathlib').Path("artifacts/development-v1/retained").glob("*.json")).read_text())
    return Game.from_dict(row["formal_game"])

def test_deep_freeze_thaw_serializable_and_defensive():
    source={"a":[{"b":1}]}; frozen=deep_freeze(source); source["a"][0]["b"]=2
    assert isinstance(frozen,MappingProxyType) and frozen["a"][0]["b"]==1
    thawed=deep_thaw(frozen); assert json.loads(json.dumps(thawed))=={"a":[{"b":1}]}
    thawed["a"][0]["b"]=3; assert frozen["a"][0]["b"]==1

def test_all_domains_reconstruct_and_are_deterministic():
    g=game(); spec=RendererSpec()
    for domain in DOMAINS:
        p=build_render_plan(g,spec,"explicit-seed",domain); validate_plan(p,g)
        assert semantic_signature(reconstruct_surface_game_from_clauses(p))==semantic_signature(p.surface_game)
        assert semantic_signature(reconstruct_game_from_clauses(p))==semantic_signature(g)
        assert p.fingerprint==build_render_plan(g,spec,"explicit-seed",domain).fingerprint

def test_display_labels_are_nonsemantic_and_do_not_leak():
    raw=game().to_dict(); raw["display_labels"]={"s0":"SECRET SOURCE LABEL"}; labelled=Game.from_dict(raw)
    plan=build_render_plan(labelled,RendererSpec(),"labels","access-control"); validate_plan(plan,labelled)
    assert "SECRET SOURCE LABEL" not in prompt_from_plan(plan) and semantic_signature(labelled)==semantic_signature(game())

def test_protocol_regression_is_exactly_expressed():
    text=prompt_from_plan(build_render_plan(game(),RendererSpec(),"protocol","formal-plain-v1"))
    for phrase in ("start of every round t","current observation o_t = obs(s_t) before choosing","entire previous observation/action history","private randomization",
                   "current true state","prior state history","its own previous actions","previous controller actions","simultaneous commitment",
                   "current unrevealed action","does not observe the controller's current private random draw before committing"):
        assert phrase in text

def test_contracts_and_model_boundary():
    g=game(); spec=RendererSpec()
    classification=render_case(g,spec,"a","formal-plain-v1",task_contract="enforceability-classification-v1")
    value=render_case(g,spec,"b","formal-plain-v1",task_contract="failure-value-v1")
    assert classification.task_contract=="enforceability-classification-v1" and '"status":"WINNING"' in classification.prompt_text
    assert value.task_contract=="failure-value-v1" and "WINNING" not in value.prompt_text and "exact minimax" in value.prompt_text
    with pytest.raises(ValueError): build_render_plan(g,spec,"c","access-control",task_contract="restoration-selection-v1")
    context=RestorationTaskContext(({"option":"option-1","description":"refine a reading","cost":"1"},{"option":"option-2","description":"restrict a choice","cost":"1"}))
    restored=render_case(g,spec,"d","access-control",task_contract="restoration-selection-v1",task_payload=context)
    assert '"restorations"' in restored.prompt_text and set(to_model_input(restored))=={"prompt"}

def test_deep_immutability_and_stale_clause_rejection():
    plan=build_render_plan(game(),RendererSpec(),"immutable","service-routing"); before=(plan.fingerprint,semantic_signature(reconstruct_game_from_clauses(plan)))
    with pytest.raises(TypeError): plan.surface_game["horizon"]=9
    with pytest.raises(TypeError): plan.ordering["states"][0]="x"
    with pytest.raises(TypeError): plan.clauses[0].semantic_payload["items"]=("x",)
    raw=plan.to_dict(); raw["clauses"][0]["text"]="hand edited"; bad=_plan_from_dict(raw)
    with pytest.raises(ValueError,match="stale"): validate_plan(bad)
    assert before==(plan.fingerprint,semantic_signature(reconstruct_game_from_clauses(plan)))

def test_payload_corruption_rejected_using_thawed_copy():
    plan=build_render_plan(game(),RendererSpec(),"corrupt","warehouse-operations"); raw=deep_thaw(plan.to_dict())
    transition=next(x for x in raw["clauses"] if x["clause_type"]=="TransitionClause")
    transition["semantic_payload"]["outcomes"][0]["probability"]="0"
    with pytest.raises(ValueError): validate_plan(_plan_from_dict(raw))

def test_typed_leakage_exception_and_rejection():
    plan=build_render_plan(game(),RendererSpec(),"leak","industrial-process"); scan_direct_leakage(plan)
    raw=plan.to_dict(); raw["clauses"][0]["text"]="wInNiNg oracle game_id"; bad=_plan_from_dict(raw)
    with pytest.raises(ValueError): scan_direct_leakage(bad)

def test_assignment_api_is_answer_blind():
    assert list(inspect.signature(assign_primary_domain).parameters)==["game_id","renderer_spec","assignment_salt"]
    expected=assign_primary_domain("id",RendererSpec(),"salt")
    for unrelated_answer in ({"status":"WINNING"},{"status":"LOSING","value":"1"}):
        assert unrelated_answer and assign_primary_domain("id",RendererSpec(),"salt")==expected

def test_strict_versions_and_frozen_corpus_spec():
    with pytest.raises(ValueError): RendererSpec(renderer_version="future")
    spec=RenderCorpusSpec("stage5.render-corpus.v1",STAGE4_FINGERPRINT,RendererSpec().fingerprint,{"x":["y"]},{"x":["id"]},DOMAINS,2,"sha256-modulo-v1","salt","enforceability-classification-v1","ns","policy")
    with pytest.raises(TypeError): spec.source_tracks["x"]=("z",)
    assert spec.fingerprint==spec.fingerprint
