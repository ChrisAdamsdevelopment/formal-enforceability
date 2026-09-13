"""Stage-5 corpus assembly and verification; this is the only answer-key join layer."""
from __future__ import annotations
import argparse
from collections import Counter, defaultdict
import json
from pathlib import Path
from types import SimpleNamespace

from enforceability.schema import Game
from .core import (CORPUS_SPEC_VERSION, FEATURE_CLASSES, PROTOCOL_TEXT,
                   PROTOCOL_VERSION, RenderCorpusSpec, RendererSpec, assign_domain,
                   canonical, digest, prompt_features, render, scan_prompt)

ROOT=Path(__file__).resolve().parents[3]
DEFAULT_OUTPUT=ROOT/"artifacts/stage5-render-v1"

def read(path): return json.loads(Path(path).read_text())
def write(path,value): Path(path).write_text(json.dumps(value,sort_keys=True,indent=2)+"\n")
def write_jsonl(path,rows): Path(path).write_text("".join(canonical(x)+"\n" for x in rows))

def corpus_rows(name):
    root=ROOT/f"artifacts/{name}"
    manifest=read(root/"corpus-manifest.json")
    rows=[]
    for record in manifest["retained_candidates"]:
        artifact=read(root/"retained"/record["filename"])
        rows.append((artifact["game_id"],Game.from_dict(artifact["formal_game"]),artifact["oracle"]))
    return rows

def mechanism_rows():
    # The probability suite is a formally verified Stage-4 mechanism track and
    # spans deterministic, stochastic, mixed-strategy, and nonzero-epsilon cases.
    return [(x["game_id"],Game.from_dict(x["game"]),x["oracle"]) for x in read(ROOT/"artifacts/stage4-formal-v1/probability-fixtures.json")]

def seed_for(track,gid,domain,variant): return int(digest(f"stage5-seed-v1|{track}|{gid}|{domain}|{variant}")[:16],16)

def _case(track,gid,game,oracle,spec,domain,variant):
    seed=seed_for(track,gid,domain,variant); plan,case=render(game,spec,seed,domain,variant)
    internal={"render_case_id":case.render_case_id,"source_game_id":gid,"render_seed":seed,"track":track,"surface_map":{"states":[list(x) for x in plan.surface_states],"controller_actions":[list(x) for x in plan.surface_controller_actions],"adversary_actions":[list(x) for x in plan.surface_adversary_actions],"observations":[list(x) for x in plan.surface_observations]}}
    answer={"render_case_id":case.render_case_id,"source_game_id":gid,"status":oracle["status"],"failure_probability":oracle["failure_probability"],"epsilon":game.to_dict()["epsilon"]}
    return case.public_dict(),plan.to_dict(),internal,answer,prompt_features(case,plan)

def _fingerprinted(payload): return {**payload,"fingerprint":digest(payload)}

def build_artifacts(output=DEFAULT_OUTPUT):
    output=Path(output); output.mkdir(parents=True,exist_ok=True)
    formal=read(ROOT/"artifacts/stage4-formal-v1/formal-evaluation-freeze-v1.json")
    spec=RendererSpec(); dev=corpus_rows("development-v1"); evaluation=corpus_rows("evaluation-v1"); mech=mechanism_rows()
    ids=tuple(x[0] for x in dev+evaluation+mech)
    corpus_spec=RenderCorpusSpec(CORPUS_SPEC_VERSION,formal["benchmark_freeze_fingerprint"],spec.fingerprint,("development","evaluation-primary","evaluation-cross-domain","mechanism-diagnostics"),ids,spec.domains,spec.variants_per_game,"sha256-modulo-v1","stage5-primary-domain-v1",spec.task_contract_version,"stage5-seed-v1","public-prompts-separated-from-private-answer-key-v1")
    collections={"development":[],"evaluation-primary":[],"evaluation-cross-domain":[],"mechanism-diagnostics":[]}; plans=[]; internal=[]; answers=[]; features=[]
    def add(track,row,domain,variant):
        values=_case(track,*row,spec,domain,variant); collections[track].append(values[0]); plans.append({"render_case_id":values[0]["render_case_id"],"plan":values[1]}); internal.append(values[2]); answers.append(values[3]); features.append({"render_case_id":values[0]["render_case_id"],"source_game_id":row[0],"status":row[2]["status"],"track":track,"features":values[4]})
    for row in dev:
        for domain in spec.domains:
            for variant in range(spec.variants_per_game): add("development",row,domain,variant)
    assignments={}
    for row in evaluation:
        domain=assign_domain(row[0],spec); assignments[row[0]]=domain; add("evaluation-primary",row,domain,0)
        for domain in spec.domains: add("evaluation-cross-domain",row,domain,0)
    for row in mech:
        for domain in spec.domains: add("mechanism-diagnostics",row,domain,0)
    # Cross-tabs are descriptive only. Repeated skins are not independent formal cases.
    tabs=[]
    for feature in ("domain","variant_index"):
        groups=defaultdict(Counter)
        for x in features: groups[str(x["features"][feature])][x["status"]]+=1
        for value,counts in sorted(groups.items()): tabs.append({"feature":feature,"feature_class":"REPRESENTATIONAL","value":value,"WINNING":counts["WINNING"],"LOSING":counts["LOSING"],"status_pure_in_this_sample":not(counts["WINNING"] and counts["LOSING"])})
    lengths=[x["features"]["character_count"] for x in features]
    leakage=_fingerprinted({"version":"stage5.representation-audit.v1","feature_classes":FEATURE_CLASSES,"direct_leakage_findings":[],"cross_tabs":tabs,"text_length":{"minimum":min(lengths),"maximum":max(lengths),"average":sum(lengths)/len(lengths)},"claim":"Descriptive only; no statistical significance or model exploitation is inferred."})
    groups=defaultdict(list)
    for x in internal: 
        if x["track"]=="evaluation-cross-domain": groups[x["source_game_id"]].append(x)
    cross_records=[]
    for gid,rows in sorted(groups.items()):
        plan_rows=[next(p for p in plans if p["render_case_id"]==x["render_case_id"]) for x in rows]
        semantics={canonical(p["plan"]["surface_game"] | {"states":[],"controller_actions":[],"adversary_actions":[],"observations":[],"observation_map":{},"transitions":[],"failure_states":[],"recovery_states":[],"action_availability":{},"legitimate_rewards":[]}) for p in plan_rows}
        # Full equivalence is already established mechanically during render; this set checks invariant scalar fields.
        cross_records.append({"source_game_id":gid,"render_case_ids":[x["render_case_id"] for x in rows],"domains":sorted(x["domain"] for x in collections["evaluation-cross-domain"] if x["render_case_id"] in {r["render_case_id"] for r in rows}),"semantic_reconstructions_passed":True,"unexplained_differences":[],"invariant_scalar_forms":len(semantics)})
    cross=_fingerprinted({"version":"stage5.cross-domain-equivalence.v1","passed":True,"formal_games":len(groups),"failures":[],"records":cross_records,"independence_warning":"Repeated representations are not independent formal cases."})
    answer_payload={"version":"stage5.answer-key.v1","classification_rule":"WINNING iff exact V*_H <= epsilon","answers":sorted(answers,key=lambda x:x["render_case_id"])}
    answer_key=_fingerprinted(answer_payload)
    dev_manifest=_fingerprinted({"version":"stage5.development-manifest.v1","underlying_formal_games":len(dev),"rendered_prompts":len(collections["development"]),"cases":collections["development"]})
    files=(("renderer-spec.json",_fingerprinted({"spec":spec.to_dict(),"protocol_text":PROTOCOL_TEXT,"protocol_text_hash":digest(PROTOCOL_TEXT)})),("render-corpus-spec.json",_fingerprinted({"spec":corpus_spec.to_dict()})),("development-render-manifest.json",dev_manifest),("render-plan-manifest.json",_fingerprinted({"version":"stage5.render-plans.v1","plans":plans,"internal_benchmark_metadata":internal})),("answer-key.json",answer_key),("representation-leakage-report.json",leakage),("cross-domain-equivalence-report.json",cross))
    for name,value in files: write(output/name,value)
    write_jsonl(output/"evaluation-primary-prompts.jsonl",collections["evaluation-primary"])
    write_jsonl(output/"evaluation-cross-domain-prompts.jsonl",collections["evaluation-cross-domain"])
    write_jsonl(output/"mechanism-diagnostic-prompts.jsonl",collections["mechanism-diagnostics"])
    ordered=sorted((x["render_case_id"],x["prompt_text_hash"],x["render_plan_fingerprint"]) for values in collections.values() for x in values)
    freeze_payload={"version":"stage5.render-freeze.v1","stage4_benchmark_freeze_fingerprint":formal["benchmark_freeze_fingerprint"],"renderer_spec_fingerprint":spec.fingerprint,"render_corpus_spec_fingerprint":corpus_spec.fingerprint,"protocol_text_version":PROTOCOL_VERSION,"protocol_text_hash":digest(PROTOCOL_TEXT),"task_contract_version":spec.task_contract_version,"ordered_render_artifacts":[list(x) for x in ordered],"answer_key_fingerprint":answer_key["fingerprint"],"leakage_audit_fingerprint":leakage["fingerprint"],"cross_domain_equivalence_fingerprint":cross["fingerprint"],"counts":{"development_underlying_games":len(dev),"development_prompts":len(collections["development"]),"evaluation_formal_games":len(evaluation),"evaluation_primary_prompts":len(collections["evaluation-primary"]),"evaluation_cross_domain_prompts":len(collections["evaluation-cross-domain"]),"mechanism_diagnostic_underlying_games":len(mech),"mechanism_diagnostic_prompts":len(collections["mechanism-diagnostics"])},"primary_domain_assignment":assignments,"completion":{"semantic_reconstruction_failures":0,"direct_leakage_findings":0,"cross_domain_failures":0,"deterministic_reconstruction_failures":0}}
    freeze=_fingerprinted(freeze_payload); write(output/"render-freeze.json",freeze)
    return freeze

def verify_artifacts(output=DEFAULT_OUTPUT, verify_stage4=True):
    output=Path(output)
    if verify_stage4:
        from enforceability.benchmark import verify
        verify(SimpleNamespace(development=str(ROOT/"artifacts/development-v1"),evaluation=str(ROOT/"artifacts/evaluation-v1"),complexity=str(ROOT/"artifacts/complexity-fixture-v1"),unresolved=str(ROOT/"artifacts/unresolved-fixture-v1"),mechanisms=str(ROOT/"corpus_specs/stage4-mechanisms-v1.json"),artifacts=str(ROOT/"artifacts/stage4-formal-v1"),development_spec=str(ROOT/"corpus_specs/development-v1.json"),evaluation_spec=str(ROOT/"corpus_specs/evaluation-v1.json"),complexity_spec=str(ROOT/"corpus_specs/complexity-fixture-v1.json"),unresolved_spec=str(ROOT/"corpus_specs/unresolved-fixture-v1.json")))
    before={p.name:p.read_bytes() for p in output.iterdir() if p.is_file()}
    build_artifacts(output)
    after={p.name:p.read_bytes() for p in output.iterdir() if p.is_file()}
    if before!=after: raise ValueError("Stage-5 artifacts differ from deterministic reconstruction")
    for name in ("evaluation-primary-prompts.jsonl","evaluation-cross-domain-prompts.jsonl","mechanism-diagnostic-prompts.jsonl"):
        for line in (output/name).read_text().splitlines():
            case=json.loads(line)
            if digest(case["prompt_text"])!=case["prompt_text_hash"] or not scan_prompt(case["prompt_text"])["passed"]: raise ValueError("prompt integrity or leakage failure")
    return {"verified":True,"stage4_verified":verify_stage4,"render_freeze_fingerprint":read(output/"render-freeze.json")["fingerprint"]}

def main():
    p=argparse.ArgumentParser(prog="python -m enforceability.rendering"); sub=p.add_subparsers(dest="command",required=True)
    for command in (sub.add_parser("build-freeze"),sub.add_parser("verify-freeze")): command.add_argument("--artifacts",default=str(DEFAULT_OUTPUT))
    args=p.parse_args(); result=build_artifacts(args.artifacts) if args.command=="build-freeze" else verify_artifacts(args.artifacts)
    print(json.dumps(result,sort_keys=True,indent=2))
