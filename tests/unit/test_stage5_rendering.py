import dataclasses, inspect, json, shutil
from types import MappingProxyType

import pytest

from enforceability.corpus import CorpusBuildError
from enforceability.rendering import (DOMAINS, PROTOCOL_TEXT, RenderCorpusSpec, RendererSpec, RestorationTaskContext,
    assign_primary_domain, build_render_plan, deep_freeze, deep_thaw, prompt_from_plan, reconstruct_game_from_clauses,
    reconstruct_surface_game_from_clauses, realize_clause, render_case, scan_direct_leakage, semantic_signature, to_model_input,
    validate_plan, validate_primary_assignment, validate_rendered_case, validate_stored_dependencies, verify_freeze)
from enforceability.rendering.freeze import ASSIGNMENT_SALT, STAGE4_FINGERPRINT, _plan_from_dict
from enforceability.schema import Game

def game():
    row=json.loads(next(__import__('pathlib').Path("artifacts/development-v1/retained").glob("*.json")).read_text())
    return Game.from_dict(row["formal_game"])

def test_deep_freeze_thaw_serializable_and_defensive():
    source={"a":[{"b":1}]}; frozen=deep_freeze(source); source["a"][0]["b"]=2
    assert isinstance(frozen,MappingProxyType) and frozen["a"][0]["b"]==1
    thawed=deep_thaw(frozen); assert json.loads(json.dumps(thawed))=={"a":[{"b":1}]}
    thawed["a"][0]["b"]=3; assert frozen["a"][0]["b"]==1
    for unsupported in ({1},frozenset({1})):
        with pytest.raises(TypeError,match="canonical JSON"): deep_freeze({"nested":[unsupported]})

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

def _large_game(kind):
    n=21; states=[f"source-state-{i}" for i in range(n)] if kind in {"states","observations"} else ["source-state"]
    controller=[f"source-control-{i}" for i in range(n)] if kind=="controller" else ["source-control"]
    adversary=[f"source-adversary-{i}" for i in range(n)] if kind=="adversary" else ["source-adversary"]
    observations=[f"source-observation-{i}" for i in range(n)] if kind=="observations" else ["source-observation"]
    transitions=[{"state":s,"controller_action":c,"adversary_action":a,"outcomes":[{"state":s,"probability":"1"}]}
                 for s in states for c in controller for a in adversary]
    raw={"schema_version":"stage1.v2","states":states,"initial_distribution":[{"state":states[0],"probability":"1"}],
      "controller_actions":controller,"adversary_actions":adversary,"observations":observations,
      "observation_map":{s:observations[i] if kind=="observations" else observations[0] for i,s in enumerate(states)},
      "transitions":transitions,"failure_states":[],"recovery_states":[],"horizon":1,"epsilon":"0",
      "action_availability":{c:[0] for c in controller},"legitimate_rewards":[],"display_labels":{}}
    return Game.from_dict(raw)

@pytest.mark.parametrize("kind",["states","observations","controller","adversary"])
def test_more_than_twenty_identifiers_are_collision_free_and_source_blind(kind):
    source=_large_game(kind); plan=build_render_plan(source,RendererSpec(),"more-than-twenty","access-control")
    validate_plan(plan,source)
    mapping={"states":plan.state_map,"observations":plan.observation_map,"controller":plan.controller_action_map,"adversary":plan.adversary_action_map}[kind]
    assert len(set(mapping.values()))==21 and not any("source-" in value for value in mapping.values())

def _fixture(name,fixture_id):
    rows=json.loads(__import__('pathlib').Path(f"artifacts/stage4-formal-v1/{name}.json").read_text())
    return Game.from_dict(next(x for x in rows if x["fixture_id"]==fixture_id)["game"])

def test_every_domain_supports_all_declared_representation_capabilities():
    # Together these Stage-4 fixtures cover ambiguity/useful probing/multiple
    # rounds, stochastic rationals with epsilon > 0, and both players having
    # multiple actions.  These are representation checks, not deployment claims.
    games=(_fixture("probe-fixtures","useful-long"),_fixture("probability-fixtures","third-boundary"),_fixture("probability-fixtures","minimax-half"),_fixture("timing-fixtures","last-usable"))
    assert any(len(g.initial_states)>1 and len({g.observation_map[s] for s in g.initial_states})<len(g.initial_states) for g in games)
    assert any(any(len(v)>1 for v in g.transitions.values()) for g in games) and any(g.epsilon>0 for g in games)
    assert any(len(g.controller_actions)>1 and len(g.adversary_actions)>1 for g in games) and any(g.horizon>1 for g in games)
    for domain in DOMAINS:
        for index,g in enumerate(games): validate_plan(build_render_plan(g,RendererSpec(),f"capability-{index}",domain),g)

def test_renderer_is_independent_of_oracle_entry_points(monkeypatch):
    import enforceability, enforceability.oracle
    def forbidden(*_args,**_kwargs): raise AssertionError("oracle was called")
    monkeypatch.setattr(enforceability,"solve",forbidden); monkeypatch.setattr(enforceability.oracle,"solve",forbidden)
    validate_plan(build_render_plan(game(),RendererSpec(),"answer-blind","industrial-process"),game())

def _corrupt_clause(plan,clause_type,mutation,update_text=True):
    raw=deep_thaw(plan.to_dict()); clause=next(x for x in raw["clauses"] if x["clause_type"]==clause_type); mutation(clause["semantic_payload"])
    if update_text: clause["text"]=realize_clause(clause["semantic_payload"],clause["template_id"],raw["domain"])
    return _plan_from_dict(raw)

@pytest.mark.parametrize(("clause_type","mutation"),[
 ("TransitionClause",lambda p:p["outcomes"][0].update(state="unknown-destination")),
 ("TransitionClause",lambda p:p["outcomes"][0].update(probability="0")),
 ("ObservationAliasClause",lambda p:p["states"].append("unknown-observation-member")),
 ("InitialDistributionClause",lambda p:p["entries"][0].update(probability="0")),
 ("ActionAvailabilityClause",lambda p:p["rounds"].append(999)),
 ("TerminalClause",lambda p:p["failure_states"].append(p["recovery_states"][0])),
 ("TerminalClause",lambda p:p["recovery_states"].append(p["failure_states"][0])),
 ("ParameterClause",lambda p:p.update(epsilon="2")),
 ("ParameterClause",lambda p:p.update(horizon=-1)),
])
def test_semantic_corruption_matrix_is_rejected(clause_type,mutation):
    plan=build_render_plan(game(),RendererSpec(),"corruption-matrix","warehouse-operations")
    with pytest.raises((ValueError,KeyError)): validate_plan(_corrupt_clause(plan,clause_type,mutation),game())

def test_remaining_corruption_matrix_is_rejected():
    plan=build_render_plan(game(),RendererSpec(),"remaining-corruption","service-routing")
    # text while payload stays fixed; payload while text stays fixed
    raw=deep_thaw(plan.to_dict()); raw["clauses"][0]["text"]="stale"
    with pytest.raises(ValueError): validate_plan(_plan_from_dict(raw),game())
    with pytest.raises(ValueError): validate_plan(_corrupt_clause(plan,"ParameterClause",lambda p:p.update(epsilon="1"),False),game())
    # formal/source map and template identity
    raw=deep_thaw(plan.to_dict()); raw["state_map"][next(iter(raw["state_map"]))]="wrong-surface-name"
    with pytest.raises((ValueError,KeyError)): validate_plan(_plan_from_dict(raw),game())
    raw=deep_thaw(plan.to_dict()); raw["clauses"][0]["template_id"]="access-control.state-declaration.v1"
    with pytest.raises(ValueError): validate_plan(_plan_from_dict(raw),game())
    # prompt hash and primary-domain assignment
    case=render_case(game(),RendererSpec(),"hash","formal-plain-v1"); broken=dataclasses.replace(case,prompt_text_hash="0"*64)
    with pytest.raises(ValueError): validate_rendered_case(broken)
    domain,variant=assign_primary_domain("id",RendererSpec(),ASSIGNMENT_SALT)
    with pytest.raises(ValueError): validate_primary_assignment("id",RendererSpec(),ASSIGNMENT_SALT,DOMAINS[(DOMAINS.index(domain)+1)%5],variant)

def test_protocol_hash_binds_text_not_only_version():
    from enforceability.rendering.core import fingerprint
    frozen=json.loads(__import__('pathlib').Path("artifacts/stage5-render-v1/render-freeze.json").read_text())
    assert frozen["protocol_hash"]==fingerprint(PROTOCOL_TEXT)
    assert frozen["protocol_hash"]!=fingerprint(PROTOCOL_TEXT+" mutation")

@pytest.mark.parametrize(("file_name","mutation"),[
 ("answer-key.json",lambda x:x["answers"][0].update(status="CORRUPTED")),
 ("renderer-spec.json",lambda x:x.update(renderer_version="future")),
 ("render-freeze.json",lambda x:x.update(stage4_benchmark_freeze_fingerprint="0"*64)),
 ("render-freeze.json",lambda x:x.update(protocol_hash="0"*64)),
])
def test_frozen_dependency_corruption_is_rejected(tmp_path,file_name,mutation):
    target=tmp_path/"stage5"; shutil.copytree("artifacts/stage5-render-v1",target)
    path=target/file_name; raw=json.loads(path.read_text()); mutation(raw); path.write_text(json.dumps(raw))
    with pytest.raises(ValueError): validate_stored_dependencies(target)

def test_canonical_spec_artifacts_round_trip_and_validate_fingerprints():
    renderer=RendererSpec(); renderer_artifact={**renderer.to_dict(),"fingerprint":renderer.fingerprint}
    assert RendererSpec.from_artifact(renderer_artifact)==renderer
    corpus_raw=json.loads(__import__('pathlib').Path("artifacts/stage5-render-v1/render-corpus-spec.json").read_text())
    corpus=RenderCorpusSpec.from_artifact(corpus_raw)
    assert RenderCorpusSpec.from_artifact({**corpus.to_dict(),"fingerprint":corpus.fingerprint})==corpus
    for corrupt in ({**renderer_artifact,"fingerprint":"0"*64},{**renderer_artifact,"language":"fr"}):
        with pytest.raises(ValueError): RendererSpec.from_artifact(corrupt)
    corrupt=deep_thaw(corpus_raw); corrupt["assignment_salt"]="altered-without-new-fingerprint"
    with pytest.raises(ValueError): RenderCorpusSpec.from_artifact(corrupt)
    with pytest.raises(ValueError): RendererSpec.from_artifact({**renderer_artifact,"unknown_metadata":True})

def test_stage5_rejects_changed_stage4_corpus_behind_unchanged_freeze(tmp_path):
    repository=tmp_path/"repository"
    shutil.copytree("artifacts",repository/"artifacts")
    shutil.copytree("corpus_specs",repository/"corpus_specs")
    retained=next((repository/"artifacts/development-v1/retained").glob("*.json"))
    raw=json.loads(retained.read_text()); raw["formal_game"]["display_labels"]={"tampered":"underlying Stage-4 state"}; retained.write_text(json.dumps(raw))
    # The attacker deliberately leaves formal-evaluation-freeze-v1.json and its
    # old fingerprint untouched.  Stage 5 must still invoke the authoritative
    # Stage-4 verifier and reject the altered retained corpus.
    with pytest.raises(CorpusBuildError,match="corpus verification mismatch"):
        verify_freeze(
            repository/"artifacts/stage5-render-v1",
            repository,
        )
