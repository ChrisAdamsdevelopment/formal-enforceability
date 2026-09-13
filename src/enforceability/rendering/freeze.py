"""Deterministic Stage-5 artifact assembly and verification."""
from __future__ import annotations
from dataclasses import dataclass, fields
import hashlib, json, shutil
from pathlib import Path
from typing import Any, Mapping

from enforceability.benchmark import deterministic_fixture_mismatches
from enforceability.schema import Game
from .core import (DOMAINS, PROTOCOL_TEXT, PROTOCOL_VERSION, RendererSpec, assign_primary_domain, build_render_plan, canonical_json,
                   deep_freeze, deep_thaw, fingerprint, prompt_from_plan, render_case, representation_features,
                   reconstruct_game_from_clauses, semantic_signature, to_model_input, validate_plan)

STAGE4_FINGERPRINT="0018543875ddf0c66c2ea11d6ea5ad25b7a05e472bc13abca139570139e8efbe"
CORPUS_VERSION="stage5.render-corpus.v1"
ASSIGNMENT_SALT="stage5-primary-domain-assignment-v1"

@dataclass(frozen=True, slots=True)
class RenderCorpusSpec:
    version: str; stage4_freeze_fingerprint: str; renderer_spec_fingerprint: str; source_tracks: Mapping[str,Any]; source_game_ids: Mapping[str,Any]
    domains: tuple[str,...]; development_variants: int; primary_assignment_rule: str; assignment_salt: str; task_contract: str; render_seed_namespace: str; output_policy: str
    def __post_init__(self):
        if self.version!=CORPUS_VERSION or self.stage4_freeze_fingerprint!=STAGE4_FINGERPRINT or tuple(self.domains)!=DOMAINS or self.development_variants!=2 or self.primary_assignment_rule!="sha256-modulo-v1" or self.task_contract!="enforceability-classification-v1": raise ValueError("unsupported render corpus specification")
        object.__setattr__(self,"domains",tuple(self.domains)); object.__setattr__(self,"source_tracks",deep_freeze(self.source_tracks)); object.__setattr__(self,"source_game_ids",deep_freeze(self.source_game_ids))
    def to_dict(self): return {f.name:deep_thaw(getattr(self,f.name)) for f in fields(self)}
    @property
    def fingerprint(self): return fingerprint(self.to_dict())
    @classmethod
    def from_dict(cls,raw): return cls(**{**deep_thaw(raw),"domains":tuple(raw["domains"])})

def _retained(root):
    rows=[]
    for path in sorted(Path(root,"retained").glob("*.json")):
        raw=json.loads(path.read_text()); rows.append((raw["game_id"],Game.from_dict(raw["formal_game"]),raw["oracle"]))
    return sorted(rows)

def verify_stage4(root=Path("artifacts")):
    freeze=json.loads((root/"stage4-formal-v1/formal-evaluation-freeze-v1.json").read_text())
    actual=freeze.get("benchmark_freeze_fingerprint")
    if actual!=STAGE4_FINGERPRINT: raise ValueError(f"Stage-4 fingerprint discrepancy: {actual}")
    mismatches=deterministic_fixture_mismatches(root/"stage4-formal-v1")
    if mismatches: raise ValueError(f"Stage-4 verification failed: {mismatches}")
    return actual

def _record(case): return case.to_dict()
def _seed(track,gid,domain,variant): return hashlib.sha256(f"stage5-seed-v1|{track}|{gid}|{domain}|{variant}".encode()).hexdigest()

def build_artifacts(output: str|Path, repository_root: str|Path=".") -> dict[str,Any]:
    repo=Path(repository_root); verify_stage4(repo/"artifacts"); spec=RendererSpec()
    dev=_retained(repo/"artifacts/development-v1"); eva=_retained(repo/"artifacts/evaluation-v1")
    mechanism_raw=json.loads((repo/"artifacts/stage4-formal-v1/probability-fixtures.json").read_text())
    mech=sorted((x["game_id"],Game.from_dict(x["game"]),x["oracle"]) for x in mechanism_raw)
    corpus=RenderCorpusSpec(CORPUS_VERSION,STAGE4_FINGERPRINT,spec.fingerprint,
      {"development":"stage4-development-retained","evaluation":"stage4-evaluation-retained","mechanism_diagnostics":"stage4-probability-fixtures"},
      {"development":[x[0] for x in dev],"evaluation":[x[0] for x in eva],"mechanism_diagnostics":[x[0] for x in mech]},DOMAINS,2,"sha256-modulo-v1",ASSIGNMENT_SALT,
      "enforceability-classification-v1","stage5-seed-v1","canonical-json-and-jsonl-v1")
    cases={"development":[],"evaluation_primary":[],"evaluation_cross_domain":[],"mechanism_diagnostic":[]}; plans=[]; answers=[]; features=[]
    def add(track,row,domain,variant):
        gid,game,oracle=row; seed=_seed(track,gid,domain,variant); plan=build_render_plan(game,spec,seed,domain); validate_plan(plan,game)
        case=render_case(game,spec,seed,domain,variant); cases[track].append(case)
        plans.append({"render_case_id":case.render_case_id,"source_game_id":gid,"track":track,"render_seed":seed,"plan":plan.to_dict()})
        answers.append({"render_case_id":case.render_case_id,"source_game_id":gid,"status":oracle["status"],"failure_probability":oracle["failure_probability"],"epsilon":str(game.epsilon)})
        features.append({"render_case_id":case.render_case_id,"oracle_status":oracle["status"],**representation_features(case,plan)})
    for row in dev:
        for d in DOMAINS:
            for v in range(2): add("development",row,d,v)
    for row in eva:
        d,v=assign_primary_domain(row[0],spec,ASSIGNMENT_SALT); add("evaluation_primary",row,d,v)
        for d in DOMAINS: add("evaluation_cross_domain",row,d,0)
    for row in mech:
        for d in DOMAINS: add("mechanism_diagnostic",row,d,0)
    # Every evaluation skin must invert to one semantic formal game.
    cross=[]
    for gid,game,_ in eva:
        signatures=[]
        for x in plans:
            if x["source_game_id"]==gid and x["track"]=="evaluation_cross_domain":
                p=_plan_from_dict(x["plan"]); signatures.append(semantic_signature(reconstruct_game_from_clauses(p)))
        count=len(set(signatures));
        if count!=1 or signatures[0]!=semantic_signature(game): raise ValueError("cross-domain equivalence failure")
        cross.append({"source_game_id":gid,"formal_reconstruction_count":count,"domains":list(DOMAINS)})
    categories=("StateDeclarationClause","ObservationAliasClause","ActionDeclarationClause","AdversaryActionDeclarationClause","ActionAvailabilityClause","TransitionClause","TerminalClause")
    nontrivial={d:{c:sorted({x["template_id"] for p in plans if p["plan"]["domain"]==d for x in p["plan"]["clauses"] if x["clause_type"]==c}) for c in categories} for d in DOMAINS}
    if any(not all(v.values()) for v in nontrivial.values()): raise ValueError("domain nontriviality failure")
    report={"version":"stage5.representation-audit.v1","binning":"fixed-width-50-v1","feature_records":features,"direct_leakage_findings":[],"descriptive_status_crosstabs":_crosstabs(features),"claims_statistical_significance":False}
    cross_report={"version":"stage5.cross-domain.v1","cases":cross,"permitted_variation":["domain vocabulary","surface identifiers","presentation order","approved template IDs"],"repeated_domains_are_independent":False}
    domain_report={"version":"stage5.domain-nontriviality.v1","minimum_categories":list(categories),"templates":nontrivial,"passed":True}
    out=Path(output); shutil.rmtree(out,ignore_errors=True); out.mkdir(parents=True)
    def write(name,obj): (out/name).write_text(json.dumps(obj,sort_keys=True,indent=2)+"\n")
    write("renderer-spec.json",{**spec.to_dict(),"fingerprint":spec.fingerprint}); write("render-corpus-spec.json",{**corpus.to_dict(),"fingerprint":corpus.fingerprint})
    write("development-render-manifest.json",{"count":len(cases["development"]),"cases":[_record(x) for x in cases["development"]]})
    for track,name in (("evaluation_primary","evaluation-primary-prompts.jsonl"),("evaluation_cross_domain","evaluation-cross-domain-prompts.jsonl"),("mechanism_diagnostic","mechanism-diagnostic-prompts.jsonl")):
        (out/name).write_text("".join(canonical_json(_record(x))+"\n" for x in cases[track]))
    write("render-plan-manifest.json",{"plans":plans}); write("answer-key.json",{"visibility":"PRIVATE ANSWER KEY","answers":answers})
    write("representation-leakage-report.json",report); write("cross-domain-equivalence-report.json",cross_report); write("domain-nontriviality-report.json",domain_report)
    components={"stage4_benchmark_freeze_fingerprint":STAGE4_FINGERPRINT,"renderer_spec_fingerprint":spec.fingerprint,"render_corpus_spec_fingerprint":corpus.fingerprint,
      "protocol_version":PROTOCOL_VERSION,"protocol_hash":fingerprint(PROTOCOL_TEXT),"task_contract_version":spec.task_contract_version,"ordered_render_case_ids":[x.render_case_id for v in cases.values() for x in v],
      "prompt_hashes":[x.prompt_text_hash for v in cases.values() for x in v],"render_plan_fingerprints":[x.render_plan_fingerprint for v in cases.values() for x in v],"answer_key_fingerprint":fingerprint(answers),
      "representation_leakage_fingerprint":fingerprint(report),"cross_domain_equivalence_fingerprint":fingerprint(cross_report),"domain_nontriviality_fingerprint":fingerprint(domain_report)}
    freeze={**components,"stage5_freeze_fingerprint":fingerprint(components),"counts":{k:len(v) for k,v in cases.items()}}
    write("render-freeze.json",freeze); return freeze

def _crosstabs(rows):
    out={}
    for row in rows:
        for k,v in row["representational"].items():
            key=f"{k}={canonical_json(v)}"; out.setdefault(key,{"WINNING":0,"LOSING":0})[row["oracle_status"]]+=1
    return out

def _plan_from_dict(raw):
    from .core import RenderPlan,TypedClause
    return RenderPlan(raw["domain"],raw["task_contract"],raw["render_seed"],raw["state_map"],raw["controller_action_map"],raw["adversary_action_map"],raw["observation_map"],raw["surface_game"],
      tuple(TypedClause(x["clause_type"],tuple(x["formal_source_fields"]),x["semantic_payload"],x["template_id"],x["output_position"],x["text"]) for x in raw["clauses"]),raw["ordering"],raw["template_selections"],raw["protocol_version"],raw["task_payload_metadata"])

def verify_freeze(artifacts: str|Path, repository_root: str|Path="."):
    target=Path(artifacts); temp=target.parent/(target.name+".verification-tmp")
    try:
        validate_stored_dependencies(target)
        expected=build_artifacts(temp,repository_root)
        names=sorted(x.name for x in target.iterdir() if x.is_file()); rebuilt=sorted(x.name for x in temp.iterdir() if x.is_file())
        if names!=rebuilt: raise ValueError("artifact file set mismatch")
        for name in names:
            if (target/name).read_bytes()!=(temp/name).read_bytes(): raise ValueError(f"artifact mismatch: {name}")
        plans=json.loads((target/"render-plan-manifest.json").read_text())["plans"]
        for x in plans:
            plan=_plan_from_dict(x["plan"]); validate_plan(plan)
            if to_model_input(next_case(target,x["render_case_id"]))!={"prompt":prompt_from_plan(plan)}: raise ValueError("model-input boundary")
        return expected
    finally: shutil.rmtree(temp,ignore_errors=True)

def validate_stored_dependencies(root: str|Path) -> None:
    root=Path(root); frozen=json.loads((root/"render-freeze.json").read_text())
    if frozen["stage4_benchmark_freeze_fingerprint"]!=STAGE4_FINGERPRINT: raise ValueError("Stage-4 dependency fingerprint")
    renderer=json.loads((root/"renderer-spec.json").read_text()); declared=renderer.pop("fingerprint")
    spec=RendererSpec.from_dict(renderer)
    if declared!=spec.fingerprint or frozen["renderer_spec_fingerprint"]!=declared: raise ValueError("renderer specification fingerprint")
    corpus=json.loads((root/"render-corpus-spec.json").read_text()); declared_corpus=corpus.pop("fingerprint")
    if declared_corpus!=RenderCorpusSpec.from_dict(corpus).fingerprint or frozen["render_corpus_spec_fingerprint"]!=declared_corpus: raise ValueError("render corpus specification fingerprint")
    answers=json.loads((root/"answer-key.json").read_text())["answers"]
    if fingerprint(answers)!=frozen["answer_key_fingerprint"]: raise ValueError("answer-key fingerprint")
    if frozen["protocol_hash"]!=fingerprint(PROTOCOL_TEXT): raise ValueError("protocol-text fingerprint")

def next_case(root,case_id):
    from .core import RenderedCase
    dev=json.loads((root/"development-render-manifest.json").read_text())["cases"]
    rows=dev
    for name in ("evaluation-primary-prompts.jsonl","evaluation-cross-domain-prompts.jsonl","mechanism-diagnostic-prompts.jsonl"):
        rows += [json.loads(x) for x in (root/name).read_text().splitlines()]
    raw=next(x for x in rows if x["render_case_id"]==case_id); return RenderedCase(**raw)
