"""Auditable construction of small formal corpora.

Isomorphism is equality after independent bijective renaming of states,
controller actions, adversary actions, and observations.  Every other Game
field except display_labels is preserved exactly.
"""
from __future__ import annotations

from dataclasses import asdict, dataclass
from collections.abc import Mapping
from enum import Enum
from functools import lru_cache
from fractions import Fraction
import hashlib
from itertools import permutations, product
import json
from pathlib import Path
import shutil
import time
from types import MappingProxyType
from typing import Any

from enforceability.generation import (FAMILIES, GENERATOR_VERSION, ComplexityLimits,
    GenerationError, GenerationRejected, GeneratorConfig, build_manifest,
    canonical_json, generate, game_id)
from enforceability.generation.core import _actual_estimates, _config_dict
from enforceability.schema import Game, SCHEMA_VERSION

CORPUS_SPEC_VERSION = "stage3.corpus-spec.v1"
ISOMORPHISM_VERSION = "stage3.exact-permutation.v1"
RETENTION_VERSION = "stage3.deterministic-retention.v2"
ORACLE_VERSION = "normal-form-reference.v2"
STRATIFICATION_FIELDS = frozenset({"family", "status", "horizon", "state_count", "controller_action_count", "adversary_action_count", "restoration_candidates", "stochastic"})


class CorpusBuildError(RuntimeError):
    """A corpus cannot truthfully be built from its declared provenance."""


class CandidateState(str, Enum):
    COMPLEXITY_REJECTED="COMPLEXITY_REJECTED"
    GENERATION_ERROR="GENERATION_ERROR"
    FILTERED_AFTER_SOLUTION="FILTERED_AFTER_SOLUTION"
    RETAINED="RETAINED"
    DUPLICATE_EXCLUDED="DUPLICATE_EXCLUDED"
    ISOMORPHIC_EXCLUDED="ISOMORPHIC_EXCLUDED"
    ISOMORPHISM_UNRESOLVED="ISOMORPHISM_UNRESOLVED"


class DuplicateClassification(str, Enum):
    UNIQUE="UNIQUE"
    EXACT_DUPLICATE="EXACT_DUPLICATE"
    FORMAL_ISOMORPHIC_DUPLICATE="FORMAL_ISOMORPHIC_DUPLICATE"
    ISOMORPHISM_UNRESOLVED="ISOMORPHISM_UNRESOLVED"


def _freeze(value:Any)->Any:
    if isinstance(value,Mapping): return MappingProxyType({k:_freeze(v) for k,v in value.items()})
    if isinstance(value,list): return tuple(_freeze(x) for x in value)
    if isinstance(value,tuple): return tuple(_freeze(x) for x in value)
    return value


def _thaw(value:Any)->Any:
    if isinstance(value,MappingProxyType): return {k:_thaw(v) for k,v in value.items()}
    if isinstance(value,tuple): return [_thaw(x) for x in value]
    return value


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
    generator_parameter_sets: tuple[Any, ...]
    complexity_limits: ComplexityLimits
    isomorphism_limits: IsomorphismLimits
    retention_policy: Any
    stratification_policy: Any
    target_counts: Any

    def __post_init__(self):
        versions=(self.corpus_spec_version==CORPUS_SPEC_VERSION,self.generator_version==GENERATOR_VERSION,
                  self.schema_version==SCHEMA_VERSION,self.oracle_version==ORACLE_VERSION,
                  self.isomorphism_version==ISOMORPHISM_VERSION,self.retention_policy_version==RETENTION_VERSION)
        if not all(versions): raise ValueError("unsupported corpus component version")
        if not self.families or len(set(self.families)) != len(self.families) or any(x not in FAMILIES for x in self.families): raise ValueError("invalid families")
        if len(self.seed_ranges)!=len(self.families) or any(type(a) is not int or type(b) is not int or a<0 or b<=a for a,b in self.seed_ranges): raise ValueError("invalid half-open seed ranges")
        if len(self.generator_parameter_sets)!=len(self.families): raise ValueError("one parameter set is required per family")
        if set(self.retention_policy)!={"exact_duplicates","isomorphic_duplicates","unresolved"}: raise ValueError("invalid retention_policy fields")
        duplicate_allowed={"retain_first","retain_all"}
        if self.retention_policy["exact_duplicates"] not in duplicate_allowed or self.retention_policy["isomorphic_duplicates"] not in duplicate_allowed or self.retention_policy["unresolved"] not in {"retain_all","exclude"}: raise ValueError("invalid retention policy")
        if set(self.stratification_policy)!={"fields","tie_break"} or self.stratification_policy["tie_break"]!="candidate_key": raise ValueError("invalid stratification policy")
        fields=self.stratification_policy["fields"]
        if not isinstance(fields,(list,tuple)) or len(set(fields))!=len(fields) or any(x not in STRATIFICATION_FIELDS for x in fields): raise ValueError("unsupported stratification field")
        if any(type(v) is not int or v<0 for v in self.target_counts.values()): raise ValueError("target counts must be nonnegative integers")
        if any(not isinstance(k,str) or len(k.split("|"))!=len(fields) for k in self.target_counts): raise ValueError("target count keys must match canonical pipe-separated strata")
        validators={"family":lambda x:x in FAMILIES,"status":lambda x:x in {"WINNING","LOSING"},"stochastic":lambda x:x in {"true","false"}}
        for key in self.target_counts:
            for field,value in zip(fields,key.split("|")):
                if field in validators and not validators[field](value): raise ValueError(f"invalid {field} stratum value")
                if field not in validators:
                    try: parsed=int(value)
                    except ValueError as exc: raise ValueError(f"invalid integer stratum value for {field}") from exc
                    if parsed<0: raise ValueError(f"invalid integer stratum value for {field}")
        for p in self.generator_parameter_sets:
            if not isinstance(p,Mapping) or "seed" in p or "family" in p or "limits" in p or "generator_version" in p: raise ValueError("parameter sets cannot override provenance")
        object.__setattr__(self,"generator_parameter_sets",tuple(_freeze(dict(x)) for x in self.generator_parameter_sets))
        object.__setattr__(self,"retention_policy",_freeze(dict(self.retention_policy)))
        object.__setattr__(self,"stratification_policy",_freeze({"fields":list(fields),"tie_break":self.stratification_policy["tie_break"]}))
        object.__setattr__(self,"target_counts",_freeze(dict(self.target_counts)))

    @classmethod
    def from_dict(cls, raw: dict[str,Any]) -> "CorpusSpec":
        required={"corpus_spec_version","generator_version","schema_version","oracle_version","isomorphism_version","retention_policy_version","families","seed_ranges","generator_parameter_sets","complexity_limits","isomorphism_limits","retention_policy","stratification_policy","target_counts"}
        if not isinstance(raw,dict) or set(raw)!=required: raise ValueError(f"CorpusSpec fields mismatch: {sorted(set(raw) ^ required)}")
        return cls(raw["corpus_spec_version"],raw["generator_version"],raw["schema_version"],raw["oracle_version"],raw["isomorphism_version"],raw["retention_policy_version"],tuple(raw["families"]),tuple(tuple(x) for x in raw["seed_ranges"]),tuple(dict(x) for x in raw["generator_parameter_sets"]),ComplexityLimits(**raw["complexity_limits"]),IsomorphismLimits(**raw["isomorphism_limits"]),dict(raw["retention_policy"]),dict(raw["stratification_policy"]),dict(raw["target_counts"]))

    @classmethod
    def load(cls,path: str|Path)->"CorpusSpec": return cls.from_dict(json.loads(Path(path).read_text()))
    def to_dict(self)->dict[str,Any]:
        return {"corpus_spec_version":self.corpus_spec_version,"generator_version":self.generator_version,"schema_version":self.schema_version,"oracle_version":self.oracle_version,"isomorphism_version":self.isomorphism_version,"retention_policy_version":self.retention_policy_version,"families":list(self.families),"seed_ranges":[list(x) for x in self.seed_ranges],"generator_parameter_sets":[_thaw(x) for x in self.generator_parameter_sets],"complexity_limits":asdict(self.complexity_limits),"isomorphism_limits":asdict(self.isomorphism_limits),"retention_policy":_thaw(self.retention_policy),"stratification_policy":_thaw(self.stratification_policy),"target_counts":_thaw(self.target_counts)}
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


def _classification_counts(entries):
    counts={"unique_resolved_count":0,"exact_duplicate_count":0,"formal_isomorphic_duplicate_count":0,"unresolved_count":0}
    names={DuplicateClassification.UNIQUE.value:"unique_resolved_count",DuplicateClassification.EXACT_DUPLICATE.value:"exact_duplicate_count",DuplicateClassification.FORMAL_ISOMORPHIC_DUPLICATE.value:"formal_isomorphic_duplicate_count"}
    for e in entries:
        if (e.get("isomorphism") or {}).get("status")=="ISOMORPHISM_UNRESOLVED": counts["unresolved_count"]+=1
        category=(e.get("duplicate_classification") or {}).get("category")
        if category in names: counts[names[category]]+=1
    return counts


def _summary(entries):
    classes=_classification_counts(entries)
    out={"attempted":len(entries),"generated":0,"complexity_rejected":0,"errors":0,"solved":0,"WINNING":0,"LOSING":0,"filtered":0,"retained":0,
         "exact_duplicates":classes["exact_duplicate_count"],"isomorphic_duplicates":classes["formal_isomorphic_duplicate_count"],"unresolved":classes["unresolved_count"],"unique_resolved":classes["unique_resolved_count"]}
    for e in entries:
        out["complexity_rejected"]+=e["state"]==CandidateState.COMPLEXITY_REJECTED.value
        out["errors"]+=e["state"]==CandidateState.GENERATION_ERROR.value
        out["generated"]+=e.get("game_id") is not None
        if e.get("oracle"):
            out["solved"]+=1; out[e["oracle"]["status"]]+=1
        out["filtered"]+=bool(e.get("retention")) and not e["retention"]["retained"]
        out["retained"]+=bool(e.get("retention")) and e["retention"]["retained"]
    return out


def _stratum(entry,fields):
    values={"family":entry["family"],"status":entry["oracle"]["status"],"horizon":entry["descriptors"]["horizon"],"state_count":entry["descriptors"]["state_count"],"controller_action_count":entry["descriptors"]["controller_action_count"],"adversary_action_count":entry["descriptors"]["adversary_action_count"],"restoration_candidates":entry["descriptors"]["restoration_candidates"],"stochastic":bool(entry["descriptors"]["stochastic_branching"])}
    return "|".join(str(values[x]).lower() if isinstance(values[x],bool) else str(values[x]) for x in fields)


def _contingencies(entries,features):
    result={}
    for feature,getter in features.items():
        bins={}
        for e in entries:
            value=str(getter(e)); row=bins.setdefault(value,{"value":value,"WINNING":0,"LOSING":0,"support":0})
            row[e["oracle"]["status"]]+=1; row["support"]+=1
        for row in bins.values(): row["status_pure_in_this_corpus"]=not (row["WINNING"] and row["LOSING"])
        result[feature]=[bins[x] for x in sorted(bins)]
    return result


def _identifier_signature(values):
    def prefix(x):
        result=""
        for c in x:
            if c.isdigit(): break
            result+=c
        return result
    return ",".join(prefix(x) for x in values)


def _leakage_audit(entries,manifests):
    solved=[e for e in entries if e.get("oracle")]
    provenance={"family":lambda e:e["family"],"mode":lambda e:e["generator_config"]["mode"]}
    structural={name:(lambda e,n=name:e["descriptors"][n]) for name in ("state_count","controller_action_count","adversary_action_count","horizon","ambiguous_controller_classes","restoration_candidates","stochastic_branching")}
    representation={
      "state_identifier_prefix_signature":lambda e:_identifier_signature(manifests[e["candidate_key"]]["formal_game"]["states"]),
      "controller_identifier_prefix_signature":lambda e:_identifier_signature(manifests[e["candidate_key"]]["formal_game"]["controller_actions"]),
      "observation_identifier_prefix_signature":lambda e:_identifier_signature(manifests[e["candidate_key"]]["formal_game"]["observations"]),
      "terminal_identifier_convention":lambda e:",".join(manifests[e["candidate_key"]]["formal_game"]["failure_states"]+manifests[e["candidate_key"]]["formal_game"]["recovery_states"]),
      "terminal_order_roles":lambda e:str([x in set(manifests[e["candidate_key"]]["formal_game"]["failure_states"]+manifests[e["candidate_key"]]["formal_game"]["recovery_states"]) for x in manifests[e["candidate_key"]]["formal_game"]["states"]]),
    }
    neutral={"neutral_state_prefix_signature":lambda e:_identifier_signature(neutralized_game(Game.from_dict(manifests[e["candidate_key"]]["formal_game"]))["states"]),"neutral_terminal_identifier_convention":lambda e:",".join(neutralized_game(Game.from_dict(manifests[e["candidate_key"]]["formal_game"]))["failure_states"]+neutralized_game(Game.from_dict(manifests[e["candidate_key"]]["formal_game"]))["recovery_states"])}
    return {"purpose":"descriptive contingencies only; purity is not proof of leakage or predictive validity","answer_direct":{"fields":["oracle","restorations"],"separated_from_correlates":True},"provenance_only":_contingencies(solved,provenance),"semantic_structural":_contingencies(solved,structural),"representational":_contingencies(solved,representation),"neutralized_representational":_contingencies(solved,neutral),"blacklist_is_not_absence_proof":True}


def _restoration_coverage(entries):
    tied=0; no_feasible=0
    for e in entries:
        evaluations=e.get("restorations") or []
        winning=[x for x in evaluations if x["oracle"]["status"]=="WINNING"]
        if evaluations and not winning: no_feasible+=1
        if winning:
            best=min(Fraction(x["cost"]) for x in winning)
            tied+=sum(Fraction(x["cost"])==best for x in winning)>1
    return tied,no_feasible


def _coverage(entries,matched):
    solved=[e for e in entries if e.get("oracle")]; tied,no_feasible=_restoration_coverage(solved)
    values=lambda field:sorted({e["descriptors"][field] for e in solved})
    families=sorted({e["family"] for e in solved}); statuses=sorted({e["oracle"]["status"] for e in solved})
    stochastic=[bool(x) for x in values("stochastic_branching")]
    result={"families":families,"all_six_families":set(families)==set(FAMILIES),"oracle_statuses":statuses,"both_oracle_statuses":set(statuses)=={"WINNING","LOSING"},"horizon_values":values("horizon"),"state_counts":values("state_count"),"controller_action_counts":values("controller_action_count"),"adversary_action_counts":values("adversary_action_count"),"ambiguous_observation_class_counts":values("ambiguous_controller_classes"),"transition_modes":{"deterministic":False in stochastic,"stochastic":True in stochastic},"probe_delays":sorted({e["generator_config"]["probe_delay"] for e in solved if e["family"]=="probe"}),"timing_intervention_positions":sorted({e["generator_config"]["intervention_round"] for e in solved if e["family"]=="timing"}),"adversary_capability_counts":values("adversary_action_count"),"restoration_candidate_counts":values("restoration_candidates"),"tied_optimal_restoration_cases":tied,"no_feasible_restoration_cases":no_feasible,"transformed_matched_pair_count":matched["records"],"complexity_rejected_count":sum(e["state"]==CandidateState.COMPLEXITY_REJECTED.value for e in entries),"unresolved_isomorphism_count":_classification_counts(entries)["unresolved_count"]}
    result["gaps"]=[k for k,v in (("all-six-families",result["all_six_families"]),("both-oracle-statuses",result["both_oracle_statuses"]),("stochastic-transitions",result["transition_modes"]["stochastic"]),("transformed-matched-pairs",bool(matched["records"])),("complexity-rejections",bool(result["complexity_rejected_count"])),("unresolved-isomorphism",bool(result["unresolved_isomorphism_count"])),("tied-optimal-restorations",bool(tied)),("no-feasible-restorations",bool(no_feasible))) if not v]
    return result


def _write(path:Path,value): path.write_text(json.dumps(value,sort_keys=True,indent=2)+"\n")
def _retained_filename(entry): return entry["candidate_key"].replace(":","_")+".json"


def _verify_manifest_versions(manifest,game,spec):
    actual=(manifest["generator_version"],manifest["schema_version"],manifest["oracle_version"],game.schema_version)
    expected=(spec.generator_version,spec.schema_version,spec.oracle_version,spec.schema_version)
    if actual!=expected: raise CorpusBuildError(f"solved artifact version mismatch: actual={actual!r}, expected={expected!r}")


def build_corpus(spec: CorpusSpec, output: str|Path)->dict[str,Any]:
    output=Path(output)
    if output.exists(): raise FileExistsError(f"refusing to overwrite {output}")
    output.mkdir(parents=True); (output/"retained").mkdir()
    entries=[]; manifests={}; timings=[]
    # Phase 1: attempt, generate, solve, and canonicalize. No retention occurs here.
    for family,seeds,frozen_params in zip(spec.families,spec.seed_ranges,spec.generator_parameter_sets):
      params=_thaw(frozen_params)
      for seed in range(*seeds):
        attempted={"family":family,"seed":seed,"generator_version":spec.generator_version,"complexity_limits":asdict(spec.complexity_limits),"generator_parameters":params}
        attempted_fp=_hash(canonical_json(attempted)); key=f"{family}:{seed}:{_hash(canonical_json(params))}"
        base={"candidate_key":key,"family":family,"seed":seed,"generator_version":spec.generator_version,"attempted_config":attempted,"attempted_config_fingerprint":attempted_fp,"generator_config":None,"config_fingerprint":None,"game_id":None,"oracle":None,"descriptors":None,"restorations":None,"isomorphism":None,"duplicate_classification":None,"retention":None}
        try:
          cfg=GeneratorConfig(family=family,seed=seed,limits=spec.complexity_limits,**params); normalized=_config_dict(cfg); config_fp=_hash(canonical_json(normalized)); base.update(generator_config=normalized,config_fingerprint=config_fp)
          started=time.perf_counter(); generated=generate(cfg)
          if isinstance(generated,GenerationRejected):
            base.update(state=CandidateState.COMPLEXITY_REJECTED.value,reason=generated.reason,complexity={"estimate":generated.estimates,"threshold":asdict(spec.complexity_limits)}); entries.append(base); continue
          manifest=build_manifest(generated); runtime=time.perf_counter()-started; _verify_manifest_versions(manifest,generated.game,spec)
          estimate=_actual_estimates(generated.game,spec.complexity_limits.max_controller_histories,spec.complexity_limits.max_policy_profiles)
          base.update(game_id=manifest["game_id"],oracle=manifest["oracle"],descriptors=manifest["descriptors"],restorations=manifest["restorations"],isomorphism=asdict(canonicalize_isomorphism(generated.game,spec.isomorphism_limits)),complexity={"estimated_controller_histories":estimate["controller_histories"],"estimated_profiles":estimate["policy_profiles"],"actual_controller_histories":None,"actual_explored_profiles":manifest["oracle"]["explored_profiles"],"profile_overestimate_ratio":estimate["policy_profiles"]/max(1,manifest["oracle"]["explored_profiles"]),"estimate_saturated":estimate["policy_profiles"]>spec.complexity_limits.max_policy_profiles,"threshold":asdict(spec.complexity_limits)})
          manifests[key]=manifest; timings.append({"candidate_key":key,"wall_clock_seconds":runtime,"diagnostic_only":True}); entries.append(base)
        except (GenerationError,TypeError,ValueError) as exc:
          reason=exc.reason if isinstance(exc,GenerationError) else "configuration_validation_error"
          base.update(state=CandidateState.GENERATION_ERROR.value,reason=reason,error=str(exc)); entries.append(base)
    # Phase 2: raw duplicate classification in the declared tie-break order.
    exact={}; iso={}
    for e in sorted((x for x in entries if x.get("oracle")),key=lambda x:x["candidate_key"]):
        gid=e["game_id"]; ir=e["isomorphism"]
        if gid in exact: category=DuplicateClassification.EXACT_DUPLICATE; representative=exact[gid]
        elif ir["status"]!="RESOLVED": category=DuplicateClassification.ISOMORPHISM_UNRESOLVED; representative=None
        elif ir["class_id"] in iso: category=DuplicateClassification.FORMAL_ISOMORPHIC_DUPLICATE; representative=iso[ir["class_id"]]
        else: category=DuplicateClassification.UNIQUE; representative=e["candidate_key"]
        e["duplicate_classification"]={"category":category.value,"representative_candidate_key":representative}
        exact.setdefault(gid,e["candidate_key"])
        if ir["status"]=="RESOLVED": iso.setdefault(ir["class_id"],e["candidate_key"])
    # Phase 3: policy and quota selection, also in tie-break order.
    strata={}; fields=spec.stratification_policy["fields"]
    for e in sorted((x for x in entries if x.get("oracle")),key=lambda x:x["candidate_key"]):
        classification=e["duplicate_classification"]["category"]; stratum=_stratum(e,fields); retained=True; reason="selected_by_declared_policy"
        if classification==DuplicateClassification.EXACT_DUPLICATE.value and spec.retention_policy["exact_duplicates"]=="retain_first": retained=False; reason="exact_duplicate_excluded"
        elif classification==DuplicateClassification.FORMAL_ISOMORPHIC_DUPLICATE.value and spec.retention_policy["isomorphic_duplicates"]=="retain_first": retained=False; reason="formal_isomorphic_duplicate_excluded"
        elif classification==DuplicateClassification.ISOMORPHISM_UNRESOLVED.value and spec.retention_policy["unresolved"]=="exclude": retained=False; reason="unresolved_isomorphism_excluded"
        if retained and strata.get(stratum,0)>=spec.target_counts.get(stratum,10**18): retained=False; reason="deterministic_stratum_quota"
        if retained: strata[stratum]=strata.get(stratum,0)+1
        state=CandidateState.RETAINED if retained else (CandidateState.DUPLICATE_EXCLUDED if classification==DuplicateClassification.EXACT_DUPLICATE.value else CandidateState.ISOMORPHIC_EXCLUDED if classification==DuplicateClassification.FORMAL_ISOMORPHIC_DUPLICATE.value else CandidateState.ISOMORPHISM_UNRESOLVED if classification==DuplicateClassification.ISOMORPHISM_UNRESOLVED.value else CandidateState.FILTERED_AFTER_SOLUTION)
        e.update(state=state.value,reason=reason,retention={"rule":_thaw(spec.retention_policy),"retained":retained,"tie_break":{"field":"candidate_key","value":e["candidate_key"]},"stratum":stratum,"reason":reason})
    retained=sorted((e for e in entries if e.get("retention") and e["retention"]["retained"]),key=lambda x:x["candidate_key"])
    for e in retained: _write(output/"retained"/_retained_filename(e),manifests[e["candidate_key"]])
    ledger_fp=_hash(canonical_json(entries)); raw=_summary(entries); by_family={f:_summary([e for e in entries if e["family"]==f]) for f in spec.families}; duplicate=_classification_counts(entries)
    duplicate.update({"template_relative_similarity_counts":{f:sum(e["family"]==f and e.get("game_id") is not None for e in entries) for f in spec.families},"isomorphism_version":spec.isomorphism_version})
    retained_ids=[e["game_id"] for e in retained]; matched=audit_matched_pairs(manifests)
    report={"raw_candidates":raw,"retained_corpus":_summary(retained),"by_family":by_family,"structural_coverage":_coverage(entries,matched),"leakage_audit":_leakage_audit(entries,manifests),"complexity_calibration":{"samples":len([e for e in entries if e.get("oracle")]),"note":"runtime is an engineering diagnostic; estimates are not conceptual difficulty"},"matched_pair_audit":matched}
    fp_payload={"corpus_spec":json.loads(spec.canonical_json()),"retained_game_ids":retained_ids,"generator_version":spec.generator_version,"schema_version":spec.schema_version,"oracle_version":spec.oracle_version,"isomorphism_version":spec.isomorphism_version,"retention_policy_version":spec.retention_policy_version}
    manifest={"corpus_fingerprint":_hash(canonical_json(fp_payload)),"corpus_spec_fingerprint":spec.fingerprint,"candidate_ledger_fingerprint":ledger_fp,"retained_game_ids":retained_ids,"retained_candidates":[{"candidate_key":e["candidate_key"],"game_id":e["game_id"],"filename":_retained_filename(e)} for e in retained],"aggregate_counts":raw,"versions":{"generator":spec.generator_version,"schema":spec.schema_version,"oracle":spec.oracle_version,"isomorphism":spec.isomorphism_version,"retention":spec.retention_policy_version},"fingerprint_security_attestation":False}
    _write(output/"corpus-spec.json",spec.to_dict()); _write(output/"candidate-ledger.json",entries); _write(output/"corpus-manifest.json",manifest); _write(output/"audit-report.json",report); _write(output/"duplicate-isomorphism-report.json",duplicate); _write(output/"retention-report.json",[e["retention"]|{"candidate_key":e["candidate_key"],"oracle":e["oracle"],"duplicate_classification":e["duplicate_classification"]} for e in entries if e["retention"]]); _write(output/"complexity-timing-diagnostics.json",timings)
    return manifest


def _load_json(path):
    try: return json.loads(path.read_text())
    except (OSError,json.JSONDecodeError) as exc: raise CorpusBuildError(f"invalid or missing frozen artifact: {path}") from exc


def verify_corpus(spec:CorpusSpec, corpus:str|Path)->dict[str,bool]:
    corpus=Path(corpus); temporary=corpus.parent/("."+corpus.name+".verification")
    if temporary.exists(): shutil.rmtree(temporary)
    try:
      regenerated=build_corpus(spec,temporary); frozen_manifest=_load_json(corpus/"corpus-manifest.json"); checks={}
      frozen_spec=CorpusSpec.from_dict(_load_json(corpus/"corpus-spec.json")); checks["frozen_spec"]=frozen_spec.canonical_json()==spec.canonical_json() and frozen_spec.fingerprint==frozen_manifest.get("corpus_spec_fingerprint")
      frozen_ledger=_load_json(corpus/"candidate-ledger.json"); frozen_ledger_fp=_hash(canonical_json(frozen_ledger)); checks["candidate_ledger_fingerprint"]=frozen_ledger_fp==frozen_manifest.get("candidate_ledger_fingerprint")==regenerated["candidate_ledger_fingerprint"]
      checks["corpus_fingerprint"]=frozen_manifest.get("corpus_fingerprint")==regenerated["corpus_fingerprint"]
      checks["aggregate_counts"]=frozen_manifest.get("aggregate_counts")==regenerated["aggregate_counts"]
      checks["retained_game_ids"]=frozen_manifest.get("retained_game_ids")==regenerated["retained_game_ids"]
      checks["retained_candidates"]=frozen_manifest.get("retained_candidates")==regenerated["retained_candidates"]
      expected={x["filename"]:x for x in frozen_manifest.get("retained_candidates",[])}; regenerated_files={p.name:p for p in (temporary/"retained").glob("*.json")}; frozen_files={p.name:p for p in (corpus/"retained").glob("*.json")}
      checks["retained_file_set"]=set(frozen_files)==set(regenerated_files)==set(expected)
      ledger_by_key={e["candidate_key"]:e for e in frozen_ledger}; retained_ok=checks["retained_file_set"]
      if retained_ok:
        for name,declared in expected.items():
          frozen=_load_json(frozen_files[name]); regenerated_artifact=_load_json(regenerated_files[name]); ledger=ledger_by_key.get(declared["candidate_key"])
          retained_ok &= ledger is not None and ledger.get("retention",{}).get("retained") and ledger.get("game_id")==declared["game_id"]==frozen.get("game_id")
          try: retained_ok &= game_id(Game.from_dict(frozen["formal_game"]))==frozen["game_id"]
          except Exception: retained_ok=False
          retained_ok &= canonical_json(frozen)==canonical_json(regenerated_artifact)
      checks["retained_artifacts"]=retained_ok
      for name in ("audit-report.json","duplicate-isomorphism-report.json","retention-report.json"): checks[name]=canonical_json(_load_json(corpus/name))==canonical_json(_load_json(temporary/name))
      diagnostics=_load_json(corpus/"complexity-timing-diagnostics.json"); solved_keys={e["candidate_key"] for e in frozen_ledger if e.get("oracle")}; diagnostic_keys={x.get("candidate_key") for x in diagnostics if isinstance(x,dict) and type(x.get("wall_clock_seconds")) in (int,float) and x.get("diagnostic_only") is True}
      checks["timing_diagnostics_schema"]=isinstance(diagnostics,list) and diagnostic_keys==solved_keys and len(diagnostics)==len(diagnostic_keys)
      if not all(checks.values()): raise CorpusBuildError("corpus verification mismatch: "+str(checks))
      return checks
    finally:
      if temporary.exists(): shutil.rmtree(temporary)
