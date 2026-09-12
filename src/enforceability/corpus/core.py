"""Auditable construction of small formal corpora.

Isomorphism is equality after independent bijective renaming of states,
controller actions, adversary actions, and observations.  Every other Game
field except display_labels is preserved exactly.
"""
from __future__ import annotations

from dataclasses import asdict, dataclass
from enum import Enum
from functools import lru_cache
import hashlib
from itertools import permutations, product
import json
from pathlib import Path
import shutil
import time
from typing import Any

from enforceability.generation import (FAMILIES, GENERATOR_VERSION, ComplexityLimits,
    GenerationError, GenerationRejected, GeneratorConfig, build_manifest,
    canonical_json, generate, game_id)
from enforceability.generation.core import _actual_estimates
from enforceability.schema import Game, SCHEMA_VERSION

CORPUS_SPEC_VERSION = "stage3.corpus-spec.v1"
ISOMORPHISM_VERSION = "stage3.exact-permutation.v1"
RETENTION_VERSION = "stage3.deterministic-retention.v1"
ORACLE_VERSION = "normal-form-reference.v2"


class CandidateState(str, Enum):
    COMPLEXITY_REJECTED="COMPLEXITY_REJECTED"
    GENERATION_ERROR="GENERATION_ERROR"
    FILTERED_AFTER_SOLUTION="FILTERED_AFTER_SOLUTION"
    RETAINED="RETAINED"
    DUPLICATE_EXCLUDED="DUPLICATE_EXCLUDED"
    ISOMORPHIC_EXCLUDED="ISOMORPHIC_EXCLUDED"
    ISOMORPHISM_UNRESOLVED="ISOMORPHISM_UNRESOLVED"


@dataclass(frozen=True, slots=True)
class IsomorphismLimits:
    max_permutations: int = 2_000_000
    def __post_init__(self):
        if type(self.max_permutations) is not int or self.max_permutations < 1:
            raise ValueError("max_permutations must be a positive integer")


@dataclass(frozen=True, slots=True)
class CorpusSpec:
    corpus_spec_version: str
    generator_version: str
    schema_version: str
    oracle_version: str
    isomorphism_version: str
    retention_policy_version: str
    families: tuple[str, ...]
    seed_ranges: tuple[tuple[int, int], ...]
    generator_parameter_sets: tuple[dict[str, Any], ...]
    complexity_limits: ComplexityLimits
    isomorphism_limits: IsomorphismLimits
    retention_policy: dict[str, Any]
    stratification_policy: dict[str, Any]
    target_counts: dict[str, int]

    def __post_init__(self):
        versions=(self.corpus_spec_version==CORPUS_SPEC_VERSION,self.generator_version==GENERATOR_VERSION,
                  self.schema_version==SCHEMA_VERSION,self.oracle_version==ORACLE_VERSION,
                  self.isomorphism_version==ISOMORPHISM_VERSION,self.retention_policy_version==RETENTION_VERSION)
        if not all(versions): raise ValueError("unsupported corpus component version")
        if not self.families or len(set(self.families)) != len(self.families) or any(x not in FAMILIES for x in self.families): raise ValueError("invalid families")
        if len(self.seed_ranges)!=len(self.families) or any(type(a) is not int or type(b) is not int or a<0 or b<=a for a,b in self.seed_ranges): raise ValueError("invalid half-open seed ranges")
        if len(self.generator_parameter_sets)!=len(self.families): raise ValueError("one parameter set is required per family")
        if set(self.retention_policy)!={"exact_duplicates","isomorphic_duplicates","unresolved"}: raise ValueError("invalid retention_policy fields")
        allowed={"retain_first","retain_all"}
        if any(v not in allowed for v in self.retention_policy.values()): raise ValueError("invalid retention policy")
        if set(self.stratification_policy)!={"fields","tie_break"} or self.stratification_policy["tie_break"]!="candidate_key": raise ValueError("invalid stratification policy")
        if not isinstance(self.stratification_policy["fields"],list): raise ValueError("stratification fields must be a list")
        if any(type(v) is not int or v<0 for v in self.target_counts.values()): raise ValueError("target counts must be nonnegative integers")
        for p in self.generator_parameter_sets:
            if not isinstance(p,dict) or "seed" in p or "family" in p or "limits" in p or "generator_version" in p: raise ValueError("parameter sets cannot override provenance")

    @classmethod
    def from_dict(cls, raw: dict[str,Any]) -> "CorpusSpec":
        required={"corpus_spec_version","generator_version","schema_version","oracle_version","isomorphism_version","retention_policy_version","families","seed_ranges","generator_parameter_sets","complexity_limits","isomorphism_limits","retention_policy","stratification_policy","target_counts"}
        if not isinstance(raw,dict) or set(raw)!=required: raise ValueError(f"CorpusSpec fields mismatch: {sorted(set(raw) ^ required)}")
        return cls(raw["corpus_spec_version"],raw["generator_version"],raw["schema_version"],raw["oracle_version"],raw["isomorphism_version"],raw["retention_policy_version"],tuple(raw["families"]),tuple(tuple(x) for x in raw["seed_ranges"]),tuple(dict(x) for x in raw["generator_parameter_sets"]),ComplexityLimits(**raw["complexity_limits"]),IsomorphismLimits(**raw["isomorphism_limits"]),dict(raw["retention_policy"]),dict(raw["stratification_policy"]),dict(raw["target_counts"]))

    @classmethod
    def load(cls,path: str|Path)->"CorpusSpec": return cls.from_dict(json.loads(Path(path).read_text()))
    def to_dict(self)->dict[str,Any]:
        d=asdict(self); d["families"]=list(self.families); d["seed_ranges"]=[list(x) for x in self.seed_ranges]; d["generator_parameter_sets"]=[x for x in self.generator_parameter_sets]; return d
    def canonical_json(self)->str: return canonical_json(self.to_dict())
    @property
    def fingerprint(self)->str: return _hash(self.canonical_json())


@dataclass(frozen=True, slots=True)
class IsomorphismResult:
    status: str
    class_id: str|None
    signature: str|None
    permutations_examined: int
    version: str=ISOMORPHISM_VERSION


def _hash(value: str)->str: return hashlib.sha256(value.encode()).hexdigest()


def _renamed_dict(g: Game, sp, cp, ap, op) -> dict[str,Any]:
    sm=dict(zip(g.states,sp)); cm=dict(zip(g.controller_actions,cp)); am=dict(zip(g.adversary_actions,ap)); om=dict(zip(g.observations,op))
    def dist(d): return sorted(({"state":sm[s],"probability":str(p.numerator) if p.denominator==1 else f"{p.numerator}/{p.denominator}"} for s,p in d),key=lambda x:x["state"])
    return {"schema_version":g.schema_version,"states":sorted(sm.values()),"initial_distribution":dist(g.initial_distribution.items()),
      "controller_actions":sorted(cm.values()),"adversary_actions":sorted(am.values()),"observations":sorted(om.values()),"observation_map":{sm[s]:om[g.observation_map[s]] for s in g.states},
      "transitions":sorted(({"state":sm[s],"controller_action":cm[c],"adversary_action":am[a],"outcomes":dist(out)} for (s,c,a),out in g.transitions.items()),key=lambda x:(x["state"],x["controller_action"],x["adversary_action"])),
      "failure_states":sorted(sm[s] for s in g.failure_states),"recovery_states":sorted(sm[s] for s in g.recovery_states),"horizon":g.horizon,
      "epsilon":str(g.epsilon.numerator) if g.epsilon.denominator==1 else f"{g.epsilon.numerator}/{g.epsilon.denominator}",
      "action_availability":{cm[a]:sorted(v) for a,v in g.action_availability.items()},
      "legitimate_rewards":sorted(({"state":sm[s],"controller_action":cm[a],"reward":str(v.numerator) if v.denominator==1 else f"{v.numerator}/{v.denominator}"} for (s,a),v in g.legitimate_rewards.items() if v),key=lambda x:(x["state"],x["controller_action"])),"display_labels":{}}


@lru_cache(maxsize=256)
def _canonicalize_cached(game_json:str, max_permutations:int)->IsomorphismResult:
    game=Game.from_json(game_json); limits=IsomorphismLimits(max_permutations)
    """Return exact lexicographic canonical form, or typed unresolved (never unequal)."""
    # Terminal roles are safe invariant partitions and greatly reduce enumeration.
    roles=[tuple(s for s in game.states if s in group) for group in (game.failure_states,game.recovery_states)]
    roles.append(tuple(s for s in game.states if s not in game.failure_states|game.recovery_states))
    count=1
    for group in roles:
        for n in range(2,len(group)+1): count*=n
    for n in (len(game.controller_actions),len(game.adversary_actions),len(game.observations)):
        for x in range(2,n+1): count*=x
    if count>limits.max_permutations: return IsomorphismResult("ISOMORPHISM_UNRESOLVED",None,None,0)
    targets=[]; offset=0
    for group in roles: targets.append(tuple(f"s{i}" for i in range(offset,offset+len(group)))); offset+=len(group)
    best=None; examined=0
    state_perms=(sum(x,()) for x in product(*(permutations(t) for t in targets)))
    for sp,cp,ap,op in product(state_perms,permutations(tuple(f"c{i}" for i in range(len(game.controller_actions)))),permutations(tuple(f"a{i}" for i in range(len(game.adversary_actions)))),permutations(tuple(f"o{i}" for i in range(len(game.observations))))):
        value=canonical_json(_renamed_dict(game,sp,cp,ap,op)); examined+=1
        if best is None or value<best: best=value
    assert best is not None
    return IsomorphismResult("RESOLVED",_hash(ISOMORPHISM_VERSION+"\n"+best),best,examined)


def canonicalize_isomorphism(game: Game, limits: IsomorphismLimits=IsomorphismLimits())->IsomorphismResult:
    """Return exact lexicographic canonical form, or typed unresolved (never unequal)."""
    raw=game.to_dict(); raw["display_labels"]={}
    return _canonicalize_cached(canonical_json(raw),limits.max_permutations)


def neutralized_game(game: Game)->dict[str,Any]:
    """Audit-only input-order neutral IDs; it never consults an oracle result."""
    return _renamed_dict(game,tuple(f"s{i}" for i in range(len(game.states))),tuple(f"c{i}" for i in range(len(game.controller_actions))),tuple(f"a{i}" for i in range(len(game.adversary_actions))),tuple(f"o{i}" for i in range(len(game.observations))))


def audit_matched_pairs(manifests: dict[str,dict[str,Any]], external_parent_ids:frozenset[str]=frozenset())->dict[str,Any]:
    """Mechanically validate Stage-2 transformation records and changed fields."""
    canonical={"observation-refinement","adversary-capability-removal","controller-capability-removal","controller-availability-change","controller-capability-addition","compound"}
    by_id={m["game_id"]:m for m in manifests.values()}; failures=[]; records=0
    for child in manifests.values():
        record=child.get("transformation")
        if record is None: continue
        records+=1; prefix=child["game_id"]
        if record.get("child_game_id")!=child["game_id"] or game_id(Game.from_dict(child["formal_game"]))!=child["game_id"]: failures.append(f"{prefix}: child ID mismatch")
        if record.get("generator_version")!=child["generator_version"]: failures.append(f"{prefix}: generator version mismatch")
        if record.get("transformation_type") not in canonical: failures.append(f"{prefix}: noncanonical transformation category")
        parent=by_id.get(record.get("parent_game_id"))
        if parent is None:
            if record.get("parent_game_id") not in external_parent_ids: failures.append(f"{prefix}: parent unavailable and not external")
            continue
        before=parent["formal_game"]; after=child["formal_game"]
        actual=sorted(k for k in before if k!="display_labels" and before[k]!=after[k])
        if actual!=sorted(record.get("changed_formal_fields",[])): failures.append(f"{prefix}: changed fields mismatch")
    return {"records":records,"failures":failures,"passed":not failures}


def _summary(entries):
    out={k:0 for k in ("attempted","generated","complexity_rejected","errors","solved","WINNING","LOSING","exact_duplicates","isomorphic_duplicates","filtered","retained","unresolved")}
    out["attempted"]=len(entries)
    for e in entries:
        state=e["state"]; out["complexity_rejected"]+=state==CandidateState.COMPLEXITY_REJECTED.value; out["errors"]+=state==CandidateState.GENERATION_ERROR.value
        if e.get("game_id"): out["generated"]+=1
        if e.get("oracle"): out["solved"]+=1; out[e["oracle"]["status"]]+=1
        out["exact_duplicates"]+=state==CandidateState.DUPLICATE_EXCLUDED.value; out["isomorphic_duplicates"]+=state==CandidateState.ISOMORPHIC_EXCLUDED.value
        out["filtered"]+=state in {CandidateState.FILTERED_AFTER_SOLUTION.value,CandidateState.DUPLICATE_EXCLUDED.value,CandidateState.ISOMORPHIC_EXCLUDED.value}
        out["retained"]+=state==CandidateState.RETAINED.value; out["unresolved"]+=state==CandidateState.ISOMORPHISM_UNRESOLVED.value
    return out


def _write(path:Path,value): path.write_text(json.dumps(value,sort_keys=True,indent=2)+"\n")


def build_corpus(spec: CorpusSpec, output: str|Path)->dict[str,Any]:
    output=Path(output)
    if output.exists(): raise FileExistsError(f"refusing to overwrite {output}")
    output.mkdir(parents=True); (output/"retained").mkdir()
    entries=[]; manifests={}; exact={}; iso={}; timings=[]
    for family,seeds,params in zip(spec.families,spec.seed_ranges,spec.generator_parameter_sets):
      for seed in range(*seeds):
        key=f"{family}:{seed}:{_hash(canonical_json(params))}"; base={"candidate_key":key,"family":family,"seed":seed,"generator_version":spec.generator_version,"generator_config":None,"config_fingerprint":None,"game_id":None,"oracle":None,"descriptors":None,"restorations":None,"isomorphism":None,"retention":None}
        try:
          cfg=GeneratorConfig(family=family,seed=seed,limits=spec.complexity_limits,**params); base["generator_config"]=asdict(cfg)
          started=time.perf_counter(); generated=generate(cfg)
          if isinstance(generated,GenerationRejected):
            base.update(state=CandidateState.COMPLEXITY_REJECTED.value,reason=generated.reason,complexity={"estimate":generated.estimates,"threshold":asdict(spec.complexity_limits)}); entries.append(base); continue
          manifest=build_manifest(generated); runtime=time.perf_counter()-started; gid=manifest["game_id"]
          estimate=_actual_estimates(generated.game,spec.complexity_limits.max_controller_histories,spec.complexity_limits.max_policy_profiles)
          base.update(config_fingerprint=generated.config_fingerprint,game_id=gid,oracle=manifest["oracle"],descriptors=manifest["descriptors"],restorations=manifest["restorations"],complexity={"estimated_controller_histories":estimate["controller_histories"],"estimated_profiles":estimate["policy_profiles"],"actual_controller_histories":None,"actual_explored_profiles":manifest["oracle"]["explored_profiles"],"profile_overestimate_ratio":estimate["policy_profiles"]/max(1,manifest["oracle"]["explored_profiles"]),"estimate_saturated":estimate["policy_profiles"]>spec.complexity_limits.max_policy_profiles,"threshold":asdict(spec.complexity_limits)})
          timings.append({"candidate_key":key,"wall_clock_seconds":runtime,"diagnostic_only":True})
          ir=canonicalize_isomorphism(generated.game,spec.isomorphism_limits); base["isomorphism"]=asdict(ir); manifests[key]=manifest
          stratum="|".join(str(manifest.get(x,manifest["oracle"].get(x,manifest["descriptors"].get(x)))) for x in spec.stratification_policy["fields"])
          retention={"rule":spec.retention_policy,"retained":False,"tie_break":key,"stratum":stratum,"reason":""}
          if gid in exact and spec.retention_policy["exact_duplicates"]=="retain_first": state=CandidateState.DUPLICATE_EXCLUDED; retention["reason"]="same_game_id_as:"+exact[gid]
          elif ir.status!="RESOLVED": state=CandidateState.ISOMORPHISM_UNRESOLVED; retention["reason"]="canonicalization_resource_limit"
          elif ir.class_id in iso and spec.retention_policy["isomorphic_duplicates"]=="retain_first": state=CandidateState.ISOMORPHIC_EXCLUDED; retention["reason"]="same_isomorphism_class_as:"+iso[ir.class_id]
          elif spec.target_counts.get(stratum,10**18) <= sum(e.get("retention",{}).get("stratum")==stratum and e["state"]==CandidateState.RETAINED.value for e in entries): state=CandidateState.FILTERED_AFTER_SOLUTION; retention["reason"]="deterministic_stratum_quota"
          else: state=CandidateState.RETAINED; retention.update(retained=True,reason="selected_by_declared_policy"); exact.setdefault(gid,key); iso.setdefault(ir.class_id,key)
          base.update(state=state.value,reason=retention["reason"],retention=retention); entries.append(base)
        except Exception as exc:
          if not isinstance(exc,GenerationError): raise
          base.update(state=CandidateState.GENERATION_ERROR.value,reason=exc.reason,error=str(exc)); entries.append(base)
    retained=sorted((e for e in entries if e["state"]==CandidateState.RETAINED.value),key=lambda x:x["candidate_key"])
    for e in retained: _write(output/"retained"/(e["candidate_key"].replace(":","_")+".json"),manifests[e["candidate_key"]])
    ledger_fp=_hash(canonical_json(entries)); raw=_summary(entries); by_family={f:_summary([e for e in entries if e["family"]==f]) for f in spec.families}
    coverage={"families":sorted({e["family"] for e in retained}),"oracle_statuses":sorted({e["oracle"]["status"] for e in retained}),"horizons":sorted({e["descriptors"]["horizon"] for e in retained}),"state_counts":sorted({e["descriptors"]["state_count"] for e in retained}),"controller_action_counts":sorted({e["descriptors"]["controller_action_count"] for e in retained}),"adversary_action_counts":sorted({e["descriptors"]["adversary_action_count"] for e in retained}),"observation_aliasing":any(e["descriptors"]["ambiguous_controller_classes"] for e in retained),"stochastic":any(e["descriptors"]["stochastic_branching"] for e in retained),"gaps":[x for x,ok in (("all-six-families",set(spec.families)==set(FAMILIES)),("both-oracle-statuses",len({e["oracle"]["status"] for e in retained})==2),("stochastic-transitions",any(e["descriptors"]["stochastic_branching"] for e in retained))) if not ok]}
    leakage={"risks":[{"category":"ANSWER-DIRECT","feature":"oracle/restoration fields","scope":"solution section only"},{"category":"PROVENANCE-ONLY","feature":"family and mode labels","risk":"may correlate with status"},{"category":"REPRESENTATIONAL","feature":"systematic identifier names and fixed ordering","risk":"generator convention shortcut"},{"category":"SEMANTIC","feature":"counts, aliasing, availability and transitions","risk":"legitimate formal predictors"}],"blacklist_is_not_absence_proof":True,"neutralized_view_available":True}
    duplicate={"exact_duplicate_count":raw["exact_duplicates"],"formal_isomorphic_duplicate_count":raw["isomorphic_duplicates"],"unresolved_count":raw["unresolved"],"template_relative_similarity_counts":{f:sum(e["family"]==f and e.get("game_id") is not None for e in entries) for f in spec.families},"isomorphism_version":spec.isomorphism_version}
    retained_ids=[e["game_id"] for e in retained]
    fp_payload={"corpus_spec":json.loads(spec.canonical_json()),"retained_game_ids":retained_ids,"generator_version":spec.generator_version,"schema_version":spec.schema_version,"oracle_version":spec.oracle_version,"isomorphism_version":spec.isomorphism_version,"retention_policy_version":spec.retention_policy_version}
    corpus_fp=_hash(canonical_json(fp_payload))
    report={"raw_candidates":raw,"retained_corpus":_summary(retained),"by_family":by_family,"structural_coverage":coverage,"leakage_audit":leakage,"complexity_calibration":{"samples":len([e for e in entries if e.get("oracle")]),"note":"runtime is an engineering diagnostic; estimates are not conceptual difficulty"},"matched_pair_audit":{"records":0,"failures":[],"note":"no transformation records declared by this spec"}}
    manifest={"corpus_fingerprint":corpus_fp,"corpus_spec_fingerprint":spec.fingerprint,"candidate_ledger_fingerprint":ledger_fp,"retained_game_ids":retained_ids,"aggregate_counts":raw,"versions":{"generator":spec.generator_version,"schema":spec.schema_version,"oracle":spec.oracle_version,"isomorphism":spec.isomorphism_version,"retention":spec.retention_policy_version},"fingerprint_security_attestation":False}
    _write(output/"corpus-spec.json",spec.to_dict()); _write(output/"candidate-ledger.json",entries); _write(output/"corpus-manifest.json",manifest); _write(output/"audit-report.json",report); _write(output/"duplicate-isomorphism-report.json",duplicate); _write(output/"retention-report.json",[e["retention"]|{"candidate_key":e["candidate_key"],"oracle":e["oracle"]} for e in entries if e["retention"]]); _write(output/"complexity-timing-diagnostics.json",timings); return manifest


def verify_corpus(spec:CorpusSpec, corpus:str|Path)->dict[str,Any]:
    corpus=Path(corpus); temporary=corpus.parent/("."+corpus.name+".verification")
    if temporary.exists(): shutil.rmtree(temporary)
    try:
      actual=build_corpus(spec,temporary); expected=json.loads((corpus/"corpus-manifest.json").read_text())
      # Runtime diagnostics are intentionally excluded from all verified fingerprints.
      checks={k:actual[k]==expected[k] for k in ("candidate_ledger_fingerprint","retained_game_ids","corpus_fingerprint","aggregate_counts")}
      for name in ("audit-report.json","duplicate-isomorphism-report.json","retention-report.json"):
        checks[name]=json.loads((temporary/name).read_text())==json.loads((corpus/name).read_text())
      if not all(checks.values()): raise ValueError("corpus verification mismatch: "+str(checks))
      return checks
    finally:
      if temporary.exists(): shutil.rmtree(temporary)
