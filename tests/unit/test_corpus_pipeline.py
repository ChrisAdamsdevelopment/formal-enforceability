import json
import shutil
from dataclasses import replace

import pytest

import enforceability.corpus.core as corpus_core
from enforceability.corpus import CorpusBuildError, CorpusSpec, build_corpus, verify_corpus
from enforceability.corpus.core import IsomorphismLimits
from enforceability.generation import ComplexityLimits


def spec(): return CorpusSpec.load("corpus_specs/regression-v1.json")


def ledger(path): return json.loads((path/"candidate-ledger.json").read_text())


def test_spec_is_strict_deeply_immutable_and_fingerprint_sensitive(tmp_path):
    raw=spec().to_dict(); supplied=raw["retention_policy"]; s=CorpusSpec.from_dict(raw); fingerprint=s.fingerprint
    supplied["exact_duplicates"]="retain_all"; raw["generator_parameter_sets"][0]["common_action"]=True
    assert s.fingerprint==fingerprint and s.retention_policy["exact_duplicates"]=="retain_first" and not s.generator_parameter_sets[0]["common_action"]
    with pytest.raises(TypeError): s.retention_policy["exact_duplicates"]="retain_all"
    changed=replace(s,seed_ranges=((0,3),)+s.seed_ranges[1:]); assert changed.fingerprint!=fingerprint
    changed=replace(s,generator_parameter_sets=({**s.generator_parameter_sets[0],"common_action":True},)+s.generator_parameter_sets[1:]); assert changed.fingerprint!=fingerprint
    changed=replace(s,retention_policy={**s.retention_policy,"exact_duplicates":"retain_all"}); assert changed.fingerprint!=fingerprint
    with pytest.raises(ValueError): replace(s,isomorphism_version="future")
    with pytest.raises(ValueError): replace(s,stratification_policy={"fields":["statuz"],"tie_break":"candidate_key"})
    with pytest.raises(ValueError): replace(s,target_counts={"wrong|WINNING":1})
    before=build_corpus(s,tmp_path/"before"); assert before["corpus_spec_fingerprint"]==fingerprint


def test_build_is_reproducible_and_frozen_corpus_verifies(tmp_path):
    one=tmp_path/"one"; two=tmp_path/"two"; a=build_corpus(spec(),one); b=build_corpus(spec(),two)
    assert a==b and (one/"candidate-ledger.json").read_bytes()==(two/"candidate-ledger.json").read_bytes()
    assert all(verify_corpus(spec(),"artifacts/regression-corpus-v1").values())


@pytest.mark.parametrize("corruption",["ledger","delete_retained","formal_game","unexpected_retained","spec"])
def test_verify_detects_actual_frozen_corruption(tmp_path,corruption):
    target=tmp_path/"corpus"; shutil.copytree("artifacts/regression-corpus-v1",target)
    if corruption=="ledger":
        value=json.loads((target/"candidate-ledger.json").read_text()); value[0]["reason"]="corrupt"; (target/"candidate-ledger.json").write_text(json.dumps(value))
    elif corruption=="delete_retained": next((target/"retained").glob("*.json")).unlink()
    elif corruption=="formal_game":
        path=next((target/"retained").glob("*.json")); value=json.loads(path.read_text()); value["formal_game"]["display_labels"]={"x":"corrupt"}; path.write_text(json.dumps(value))
    elif corruption=="unexpected_retained": (target/"retained"/"unexpected.json").write_text("{}")
    else:
        value=json.loads((target/"corpus-spec.json").read_text()); value["seed_ranges"][0][1]=3; (target/"corpus-spec.json").write_text(json.dumps(value))
    with pytest.raises((CorpusBuildError,ValueError)): verify_corpus(spec(),target)


def test_raw_classification_independent_of_quota_and_tie_break_order(tmp_path):
    s=spec(); quota=replace(s,target_counts={"observation-conflict|LOSING":0})
    build_corpus(s,tmp_path/"normal"); build_corpus(quota,tmp_path/"quota")
    raw=lambda p:{e["candidate_key"]:e["duplicate_classification"] for e in ledger(p) if e["oracle"]}
    assert raw(tmp_path/"normal")==raw(tmp_path/"quota")
    reverse=replace(s,families=tuple(reversed(s.families)),seed_ranges=tuple(reversed(s.seed_ranges)),generator_parameter_sets=tuple(reversed(s.generator_parameter_sets)))
    build_corpus(reverse,tmp_path/"reverse")
    assert raw(tmp_path/"normal")==raw(tmp_path/"reverse")
    for rows in (ledger(tmp_path/"normal"),ledger(tmp_path/"reverse")):
        for e in rows:
            d=e.get("duplicate_classification")
            if d and d["category"]!="UNIQUE" and d["representative_candidate_key"]: assert d["representative_candidate_key"]<e["candidate_key"]


@pytest.mark.parametrize("exact,isomorphic",[("retain_all","retain_first"),("retain_first","retain_all"),("retain_first","retain_first"),("retain_all","retain_all")])
def test_disjoint_duplicate_policy_combinations(tmp_path,exact,isomorphic):
    s=replace(spec(),retention_policy={"exact_duplicates":exact,"isomorphic_duplicates":isomorphic,"unresolved":"retain_all"}); path=tmp_path/(exact+isomorphic); build_corpus(s,path); rows=ledger(path)
    assert sum(e.get("duplicate_classification",{}).get("category")=="EXACT_DUPLICATE" for e in rows)==4
    assert sum(e.get("duplicate_classification",{}).get("category")=="FORMAL_ISOMORPHIC_DUPLICATE" for e in rows)==2
    for e in rows:
        if e.get("duplicate_classification",{}).get("category")=="EXACT_DUPLICATE": assert e["retention"]["retained"]==(exact=="retain_all")


@pytest.mark.parametrize("policy,retained",[("retain_all",True),("exclude",False)])
def test_unresolved_policy_is_explicit(tmp_path,policy,retained):
    s=replace(spec(),isomorphism_limits=IsomorphismLimits(1),retention_policy={"exact_duplicates":"retain_all","isomorphic_duplicates":"retain_all","unresolved":policy}); path=tmp_path/policy; build_corpus(s,path)
    rows=[e for e in ledger(path) if e["oracle"]]; unresolved=[e for e in rows if e["duplicate_classification"]["category"]=="ISOMORPHISM_UNRESOLVED"]
    assert unresolved and all(e["isomorphism"]["status"]=="ISOMORPHISM_UNRESOLVED" for e in rows)
    assert all(e["retention"]["retained"] is retained for e in unresolved)


def test_rejection_and_invalid_attempt_provenance(tmp_path):
    s=spec(); rejected=replace(s,complexity_limits=ComplexityLimits(max_states=1,max_horizon=4,max_controller_histories=100,max_policy_profiles=100000,max_generated_candidates=1000)); build_corpus(rejected,tmp_path/"rejected")
    row=ledger(tmp_path/"rejected")[0]; assert row["state"]=="COMPLEXITY_REJECTED" and row["config_fingerprint"] and row["attempted_config_fingerprint"] and row["generator_config"]
    params=list(s.to_dict()["generator_parameter_sets"]); params[0]["controller_action_count"]=0
    invalid=replace(s,generator_parameter_sets=tuple(params)); build_corpus(invalid,tmp_path/"invalid")
    row=ledger(tmp_path/"invalid")[0]; assert row["state"]=="GENERATION_ERROR" and row["generator_config"] is None and row["attempted_config"]["generator_parameters"]["controller_action_count"]==0 and row["attempted_config_fingerprint"]


def test_actual_manifest_version_mismatch_fails(monkeypatch,tmp_path):
    original=corpus_core.build_manifest
    def mismatch(generated):
        value=original(generated); value["oracle_version"]="wrong"; return value
    monkeypatch.setattr(corpus_core,"build_manifest",mismatch)
    with pytest.raises(CorpusBuildError): build_corpus(spec(),tmp_path/"bad-version")


@pytest.mark.parametrize("limit",[12,13])
def test_candidate_count_at_or_below_limit_is_accepted(tmp_path,limit):
    s=replace(spec(),complexity_limits=replace(spec().complexity_limits,max_generated_candidates=limit))
    result=build_corpus(s,tmp_path/str(limit))
    assert result["aggregate_counts"]["attempted"]==12


def test_candidate_count_above_limit_fails_before_output(tmp_path):
    output=tmp_path/"must-not-exist"
    s=replace(spec(),complexity_limits=replace(spec().complexity_limits,max_generated_candidates=11))
    with pytest.raises(CorpusBuildError,match=r"requested candidate count 12 exceeds max_generated_candidates limit 11"):
        build_corpus(s,output)
    assert not output.exists()


@pytest.mark.parametrize(("field","value"),[("versions",{"generator":"corrupt"}),("fingerprint_security_attestation",True)])
def test_verify_detects_complete_manifest_corruption(tmp_path,field,value):
    target=tmp_path/"corpus"; shutil.copytree("artifacts/regression-corpus-v1",target)
    path=target/"corpus-manifest.json"; manifest=json.loads(path.read_text()); manifest[field]=value; path.write_text(json.dumps(manifest))
    with pytest.raises(CorpusBuildError): verify_corpus(spec(),target)


def test_candidate_key_tie_break_is_lexicographic_for_multi_digit_seeds(tmp_path):
    base=spec(); authority_index=base.families.index("authority-limitation")
    s=replace(base,families=("authority-limitation",),seed_ranges=((2,11),),generator_parameter_sets=(base.generator_parameter_sets[authority_index],),stratification_policy={"fields":["status"],"tie_break":"candidate_key"},target_counts={"WINNING":1},retention_policy={"exact_duplicates":"retain_all","isomorphic_duplicates":"retain_all","unresolved":"retain_all"})
    output=tmp_path/"multidigit"; build_corpus(s,output)
    retained=[e for e in ledger(output) if e["retention"]["retained"]]
    assert len(retained)==1 and retained[0]["seed"]==10
    assert retained[0]["candidate_key"]==min(e["candidate_key"] for e in ledger(output))
