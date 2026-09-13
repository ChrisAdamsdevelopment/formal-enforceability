import ast
from dataclasses import FrozenInstanceError
import json
from pathlib import Path

import pytest

from enforceability.rendering import (DOMAINS, RendererSpec, assign_domain,
    audit_clauses, reconstruct_game, render, scan_prompt)
from enforceability.rendering.build import build_artifacts, corpus_rows, verify_artifacts


def game(): return corpus_rows("development-v1")[0][1]

def test_spec_strict_deeply_immutable_and_fingerprinted():
    domains=[*DOMAINS]; spec=RendererSpec(domains=domains); domains.pop()
    assert spec.domains==DOMAINS and spec.fingerprint==RendererSpec.from_dict(spec.to_dict()).fingerprint
    with pytest.raises(FrozenInstanceError): spec.language="fr"
    with pytest.raises(ValueError): RendererSpec(renderer_version="future")

@pytest.mark.parametrize("domain",DOMAINS)
def test_every_domain_is_reproducible_reversible_complete_and_blind(domain):
    spec=RendererSpec(); source=game()
    p1,c1=render(source,spec,7,domain); p2,c2=render(source,spec,7,domain)
    assert c1.prompt_text.encode()==c2.prompt_text.encode()
    assert p1.fingerprint==p2.fingerprint and reconstruct_game(p1).to_json()==source.to_json()
    assert audit_clauses(p1)["passed"] and scan_prompt(c1.prompt_text)["passed"]
    assert "simultaneously" in c1.prompt_text and "private random draw" in c1.prompt_text
    assert source.to_dict()["epsilon"] in c1.prompt_text

def test_fixed_seed_variation_and_assignment_answer_independence():
    spec=RendererSpec(); source=game()
    assert render(source,spec,1,DOMAINS[0])[1].prompt_text != render(source,spec,2,DOMAINS[0])[1].prompt_text
    gid="a"*64
    assert assign_domain(gid,spec)==assign_domain(gid,spec)  # API accepts no answer/status/value.

@pytest.mark.parametrize("leak",["oracle", "optimal policy", "correct answer", "game_id", "generator_version", "oracle_version", "mechanism_id", "candidate_key", "WINNING leaked"])
def test_direct_leaks_are_rejected(leak): assert not scan_prompt("Prompt " + leak)["passed"]

def test_renderer_source_has_no_oracle_or_solver_imports():
    source=Path("src/enforceability/rendering/core.py").read_text(); tree=ast.parse(source)
    imports=[n for n in ast.walk(tree) if isinstance(n,(ast.Import,ast.ImportFrom))]
    assert all("oracle" not in ast.unparse(n) and "solve" not in ast.unparse(n) and "restoration" not in ast.unparse(n) for n in imports)

def test_rendering_succeeds_when_oracle_entry_points_disabled(monkeypatch):
    import enforceability.oracle as oracle
    monkeypatch.setattr(oracle,"solve",lambda *_: (_ for _ in ()).throw(AssertionError("solver called")))
    render(game(),RendererSpec(),10,DOMAINS[0])

def test_frozen_corpus_rules_and_answer_separation():
    root=Path("artifacts/stage5-render-v1"); freeze=json.loads((root/"render-freeze.json").read_text())
    assert freeze["counts"]["evaluation_primary_prompts"]==freeze["counts"]["evaluation_formal_games"]
    assert freeze["counts"]["evaluation_cross_domain_prompts"]==freeze["counts"]["evaluation_formal_games"]*len(DOMAINS)
    prompts=(root/"evaluation-primary-prompts.jsonl").read_text()
    assert "source_game_id" not in prompts and "failure_probability" not in prompts
    answers=json.loads((root/"answer-key.json").read_text())
    assert all(set(x)=={"render_case_id","source_game_id","status","failure_probability","epsilon"} for x in answers["answers"])

def test_build_and_verify_reproducibly(tmp_path):
    build_artifacts(tmp_path); assert verify_artifacts(tmp_path,verify_stage4=False)["verified"]

@pytest.mark.parametrize("filename,mutation",[
 ("evaluation-primary-prompts.jsonl",lambda s:s.replace("Possible system states","Possible altered states",1)),
 ("answer-key.json",lambda s:s.replace('"WINNING"','"LOSING"',1)),
 ("render-plan-manifest.json",lambda s:s.replace('"probability": "1"','"probability": "0"',1)),
 ("render-plan-manifest.json",lambda s:s.replace('"observation_map": {','"observation_map": {"altered":"Signal Amber",',1)),
 ("render-plan-manifest.json",lambda s:s.replace('"template_id": "','"template_id": "altered-',1)),
 ("render-plan-manifest.json",lambda s:s.replace('"source_game_id": "','"source_game_id": "altered-',1)),
 ("evaluation-primary-prompts.jsonl",lambda s:s.replace('"prompt_text_hash":"','"prompt_text_hash":"0',1)),
 ("evaluation-primary-prompts.jsonl",lambda s:s.replace('"domain":"','"domain":"altered-',1)),
 ("renderer-spec.json",lambda s:s.replace('stage5.renderer.v1','stage5.renderer.v2',1)),
 ("render-freeze.json",lambda s:s.replace('0018543875ddf0c66c2ea11d6ea5ad25b7a05e472bc13abca139570139e8efbe','0'*64,1)),
])
def test_corruption_is_detected(tmp_path,filename,mutation):
    build_artifacts(tmp_path); path=tmp_path/filename; path.write_text(mutation(path.read_text()))
    with pytest.raises(ValueError): verify_artifacts(tmp_path,verify_stage4=False)
