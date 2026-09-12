"""Deterministic, formal-only Stage-2 game generation."""
from __future__ import annotations

from dataclasses import asdict, dataclass
from fractions import Fraction
import hashlib
import json
import random
from typing import Any

from enforceability import Restoration, optimal_restoration, solve
from enforceability.restoration import apply_restoration
from enforceability.schema import Game, InvalidGame, SCHEMA_VERSION, rational_json

GENERATOR_VERSION = "stage2.v1"
BANNED_KEYS = frozenset({"winning_case", "losing_case", "correct_action", "safe_restoration", "fatal_branch"})
FAMILIES = ("observation-conflict", "authority-limitation", "probe", "timing", "capability-restriction", "mixed-restoration")


@dataclass(frozen=True, slots=True)
class ComplexityLimits:
    max_states: int = 20
    max_horizon: int = 4
    max_controller_histories: int = 100
    max_policy_profiles: int = 100_000
    max_generated_candidates: int = 1000


@dataclass(frozen=True, slots=True)
class GeneratorConfig:
    family: str
    seed: int
    generator_version: str = GENERATOR_VERSION
    horizon: int = 1
    controller_action_count: int = 2
    adversary_action_count: int = 1
    ambiguous_states: int = 2
    aliasing_degree: int = 2
    common_action: bool = False
    coverage: int = 1
    probe_available: bool = True
    probe_informative: bool = True
    probe_delay: int = 1
    intervention_round: int = 0
    stochasticity: bool = False
    epsilon: str = "0"
    mode: str = "base"
    limits: ComplexityLimits = ComplexityLimits()

    def __post_init__(self):
        if self.generator_version != GENERATOR_VERSION:
            raise GenerationError("unsupported_generator_version", self.seed, self)
        if self.family not in FAMILIES or type(self.seed) is not int:
            raise GenerationError("invalid_configuration", self.seed, self)
        integers=(self.horizon,self.controller_action_count,self.adversary_action_count,self.ambiguous_states,self.aliasing_degree,self.coverage,self.probe_delay,self.intervention_round)
        if any(type(x) is not int or x < 0 for x in integers) or self.controller_action_count < 1 or self.adversary_action_count < 1:
            raise GenerationError("invalid_configuration", self.seed, self)
        try: e=Fraction(self.epsilon)
        except (ValueError, ZeroDivisionError) as exc: raise GenerationError("invalid_configuration",self.seed,self) from exc
        if not 0 <= e <= 1: raise GenerationError("invalid_configuration",self.seed,self)


class GenerationError(Exception):
    def __init__(self, reason: str, seed: int, config: Any):
        self.reason, self.seed, self.config = reason, seed, config
        super().__init__(f"{reason}; seed={seed}; config={config!r}")


@dataclass(frozen=True, slots=True)
class GenerationRejected:
    reason: str
    seed: int
    config: dict[str, Any]
    estimates: dict[str, int]


@dataclass(frozen=True, slots=True)
class TransformationRecord:
    parent_game_id: str
    child_game_id: str
    transformation_type: str
    changed_formal_fields: tuple[str, ...]
    generator_version: str
    seed: int


@dataclass(frozen=True, slots=True)
class GeneratedGame:
    game: Game
    restorations: tuple[Restoration, ...] = ()


def _game(*, states, initial, ca, aa, obs, transitions, horizon, availability=None, rewards=None, epsilon="0") -> Game:
    rows=[]
    for s in states:
        for c in ca:
            for a in aa:
                value=transitions.get((s,c,a),s)
                dist={value:1} if isinstance(value,str) else value
                rows.append({"state":s,"controller_action":c,"adversary_action":a,"outcomes":[{"state":n,"probability":str(p)} for n,p in dist.items()]})
    mass=Fraction(1,len(initial))
    raw={"schema_version":SCHEMA_VERSION,"states":list(states),"initial_distribution":[{"state":s,"probability":rational_json(mass)} for s in initial],
         "controller_actions":list(ca),"adversary_actions":list(aa),"observations":sorted(set(obs.values())),"observation_map":obs,"transitions":rows,
         "failure_states":["x"],"recovery_states":["r"],"horizon":horizon,"epsilon":epsilon,
         "action_availability":availability or {c:list(range(horizon)) for c in ca},
         "legitimate_rewards":[{"state":s,"controller_action":c,"reward":str(v)} for (s,c),v in (rewards or {}).items()],"display_labels":{}}
    return Game.from_dict(raw)


def _conflict(c: GeneratorConfig, rng: random.Random) -> GeneratedGame:
    n=max(2,c.ambiguous_states); states=tuple(f"q{i}" for i in range(n))+("r","x")
    ca=tuple(f"c{i}" for i in range(max(c.controller_action_count,n))) + (("c_common",) if c.common_action else ())
    aa=tuple(f"a{i}" for i in range(c.adversary_action_count)); offset=rng.randrange(n)
    obs={s:(f"o{i//max(1,c.aliasing_degree)}" if s.startswith("q") else s) for i,s in enumerate(states)}
    t={}
    for i,s in enumerate(states[:n]):
        for j,a in enumerate(aa):
            required=(i+j+offset)%n
            for k,act in enumerate(ca):
                target="r" if act=="c_common" or k==required else "x"
                t[s,act,a]={target:Fraction(1,2),s:Fraction(1,2)} if c.stochasticity else target
    return GeneratedGame(_game(states=states,initial=states[:n],ca=ca,aa=aa,obs=obs,transitions=t,horizon=max(1,c.horizon),epsilon=c.epsilon))


def _authority(c: GeneratorConfig, rng: random.Random) -> GeneratedGame:
    ca=tuple(f"c{i}" for i in range(c.controller_action_count)); aa=tuple(f"a{i}" for i in range(c.adversary_action_count)); states=("q","r","x")
    shift=rng.randrange(max(1,len(ca))); t={}
    for i,act in enumerate(ca):
        for j,adv in enumerate(aa): t["q",act,adv]="r" if ((i+shift)%len(ca)) < c.coverage or c.mode=="robust" else ("x" if j>=c.coverage else "r")
    return GeneratedGame(_game(states=states,initial=("q",),ca=ca,aa=aa,obs={s:s for s in states},transitions=t,horizon=max(1,c.horizon),epsilon=c.epsilon))


def _probe(c: GeneratorConfig, rng: random.Random) -> GeneratedGame:
    states=("q0","q1","p0","p1","d","r","x"); ca=("c0","c1","probe","wait")
    obs={"q0":"o","q1":"o","p0":"p0" if c.probe_informative else "p","p1":"p1" if c.probe_informative else "p","d":"d","r":"r","x":"x"}; t={}
    for i in range(2):
        t[f"q{i}","probe","a0"]=f"p{i}" if c.probe_delay <= 1 else "d"
        t[f"q{i}","c{i}","a0"]="r"; t[f"q{i}",f"c{1-i}","a0"]="x"
        t[f"p{i}",f"c{i}","a0"]="r"; t[f"p{i}",f"c{1-i}","a0"]="x"
    if c.common_action:
        for s in ("q0","q1","p0","p1"): t[s,"wait","a0"]="r"
    availability={"probe":[0] if c.probe_available else [],"wait":list(range(max(2,c.horizon))),"c0":list(range(1,max(2,c.horizon))),"c1":list(range(1,max(2,c.horizon)))}
    return GeneratedGame(_game(states=states,initial=("q0","q1"),ca=ca,aa=("a0",),obs=obs,transitions=t,horizon=max(2,c.horizon),availability=availability,epsilon=c.epsilon))


def _timing(c: GeneratorConfig, rng: random.Random) -> GeneratedGame:
    states=("q","d","r","x"); ca=("wait","act"); t={("q","wait","a0"):"x",("q","act","a0"):"r"}
    h=max(2,c.horizon); av={"wait":list(range(h)),"act":[c.intervention_round] if c.intervention_round<h else []}
    return GeneratedGame(_game(states=states,initial=("q",),ca=ca,aa=("a0",),obs={s:s for s in states},transitions=t,horizon=h,availability=av,epsilon=c.epsilon))


def _capability(c: GeneratorConfig, rng: random.Random) -> GeneratedGame:
    states=("q","r","x"); ca=("c0",); aa=tuple(f"a{i}" for i in range(max(2,c.adversary_action_count))); t={}
    harmful=1+rng.randrange(len(aa)-1)
    for j,a in enumerate(aa): t["q","c0",a]="x" if j==harmful or (c.mode=="multi" and j>0) else "r"
    game=_game(states=states,initial=("q",),ca=ca,aa=aa,obs={s:s for s in states},transitions=t,horizon=max(1,c.horizon),epsilon=c.epsilon)
    candidates=tuple(Restoration(f"z{i}",remove_adversary_actions=frozenset({a})) for i,a in enumerate(aa[1:]))
    if c.mode=="none": candidates=(Restoration("z0",remove_adversary_actions=frozenset({aa[0]})),)
    return GeneratedGame(game,candidates)


def _mixed(c: GeneratorConfig, rng: random.Random) -> GeneratedGame:
    # A compact conflict with unused split observations, adversarial blocking,
    # and a dormant timed action; rewards make restoration costs endogenous.
    states=("q0","q1","r","x"); ca=("c0","c1","c2"); aa=("a0","a1")
    obs={"q0":"o","q1":"o","r":"r","x":"x"}; t={}
    for i in range(2):
        for j,a in enumerate(aa):
            t[f"q{i}",f"c{i}",a]="r" if j==0 else "x"; t[f"q{i}",f"c{1-i}",a]="x"; t[f"q{i}","c2",a]="r"
    h=max(1,c.horizon); av={"c0":list(range(h)),"c1":list(range(h)),"c2":[]}
    rewards={(f"q{i}",f"c{i}"):10 for i in range(2)} | {(f"q{i}","c2"):7 for i in range(2)}
    game=_game(states=states,initial=("q0","q1"),ca=ca,aa=aa,obs=obs,transitions=t,horizon=h,availability=av,rewards=rewards,epsilon=c.epsilon)
    # Add unused observations through canonical schema so refinement is legal.
    raw=game.to_dict(); raw["observations"] += ["u0","u1"]; game=Game.from_dict(raw)
    candidates=(Restoration("z0",observation_overrides=(("q0","u0"),("q1","u1"))),Restoration("z1",remove_adversary_actions=frozenset({"a1"})),Restoration("z2",availability_overrides=(("c2",tuple(range(h))),)))
    if c.mode=="none": candidates=candidates[:1]
    return GeneratedGame(game,candidates)


_BUILDERS={"observation-conflict":_conflict,"authority-limitation":_authority,"probe":_probe,"timing":_timing,"capability-restriction":_capability,"mixed-restoration":_mixed}


def _config_dict(c: GeneratorConfig) -> dict[str, Any]:
    value=asdict(c); return value


def _estimates(c: GeneratorConfig) -> dict[str,int]:
    states=max(3,c.ambiguous_states+2); histories=states*max(1,c.horizon); profiles=(max(1,c.controller_action_count)*max(1,c.adversary_action_count))**histories
    return {"states":states,"horizon":c.horizon,"controller_histories":histories,"policy_profiles":profiles}


def generate(c: GeneratorConfig) -> GeneratedGame | GenerationRejected:
    estimates=_estimates(c); limits=c.limits
    if estimates["states"]>limits.max_states or c.horizon>limits.max_horizon or estimates["controller_histories"]>limits.max_controller_histories or estimates["policy_profiles"]>limits.max_policy_profiles:
        return GenerationRejected("estimated_oracle_complexity",c.seed,_config_dict(c),estimates)
    try:
        generated=_BUILDERS[c.family](c,random.Random(c.seed))
        # Round-trip invokes every schema invariant and establishes canonicality.
        Game.from_json(generated.game.to_json())
        return generated
    except (InvalidGame, KeyError, ValueError) as exc:
        raise GenerationError("formal_generation_failed",c.seed,c) from exc


def canonical_game_json(game: Game) -> str:
    raw=game.to_dict(); raw["display_labels"]={}
    return json.dumps(raw,sort_keys=True,separators=(",",":"))


def game_id(game: Game) -> str:
    return hashlib.sha256(canonical_game_json(game).encode()).hexdigest()


def transform(game: Game, restoration: Restoration, transformation_type: str, seed: int) -> tuple[Game,TransformationRecord]:
    child=apply_restoration(game,restoration)
    changed=[]
    if restoration.observation_overrides: changed.append("observation_map")
    if restoration.remove_adversary_actions: changed.extend(("adversary_actions","transitions"))
    if restoration.remove_controller_actions: changed.extend(("controller_actions","transitions","action_availability","legitimate_rewards"))
    if restoration.availability_overrides: changed.append("action_availability")
    record=TransformationRecord(game_id(game),game_id(child),transformation_type,tuple(changed),GENERATOR_VERSION,seed)
    return child,record


def add_controller_action(game: Game, action: str, outcomes: dict[tuple[str,str],tuple[tuple[str,Fraction],...]], rounds: tuple[int,...], seed: int) -> tuple[Game,TransformationRecord]:
    """Add one capability; callers explicitly supply every state/adversary outcome."""
    if action in game.controller_actions or set(outcomes)!={(s,a) for s in game.states for a in game.adversary_actions}:
        raise GenerationError("invalid_controller_capability",seed,{"action":action})
    raw=game.to_dict(); raw["controller_actions"].append(action); raw["action_availability"][action]=list(rounds)
    for (s,a),dist in outcomes.items():
        raw["transitions"].append({"state":s,"controller_action":action,"adversary_action":a,"outcomes":[{"state":n,"probability":rational_json(p)} for n,p in dist]})
    child=Game.from_dict(raw)
    record=TransformationRecord(game_id(game),game_id(child),"controller-capability-addition",("controller_actions","transitions","action_availability"),GENERATOR_VERSION,seed)
    return child,record


@dataclass(frozen=True, slots=True)
class SamplingDecision:
    retained: bool
    reason: str
    game_id: str
    oracle: dict[str,Any]


def filter_after_solution(manifest: dict[str,Any], predicate, reason: str="declared_sampling_rule") -> SamplingDecision:
    """Apply a declared dataset filter only after retaining the oracle result."""
    return SamplingDecision(bool(predicate(manifest["oracle"])),reason,manifest["game_id"],manifest["oracle"])


def structural_descriptors(game: Game, explored_profiles: int, restoration_count: int) -> dict[str,Any]:
    reachable=set(game.initial_states)
    for _ in range(game.horizon):
        reachable |= {n for (s,_,_),out in game.transitions.items() if s in reachable for n,p in out if p}
    classes={o:sum(v==o for v in game.observation_map.values()) for o in game.observations}
    branching=sum(len(out)>1 for out in game.transitions.values())
    return {"state_count":len(game.states),"reachable_states":len(reachable),"horizon":game.horizon,"controller_action_count":len(game.controller_actions),"adversary_action_count":len(game.adversary_actions),"observation_class_sizes":classes,"ambiguous_controller_classes":sum(n>1 for n in classes.values()),"stochastic_branching":branching,"restoration_candidates":restoration_count,"oracle_explored_profiles":explored_profiles}


def _restoration_dict(e) -> dict[str,Any]:
    return {"candidate_id":e.restoration.name,"oracle":e.game_result.to_dict(),"legitimate_utility":rational_json(e.legitimate_utility),"cost":rational_json(e.cost)}


def validate_no_leakage(value: Any) -> None:
    if isinstance(value,dict):
        bad=BANNED_KEYS & set(value)
        if bad: raise GenerationError("answer_bearing_metadata",-1,{"keys":sorted(bad)})
        for child in value.values(): validate_no_leakage(child)
    elif isinstance(value,list):
        for child in value: validate_no_leakage(child)


def build_manifest(c: GeneratorConfig, generated: GeneratedGame, transformation: TransformationRecord|None=None) -> dict[str,Any]:
    result=solve(generated.game)
    restoration_result=optimal_restoration(generated.game,generated.restorations) if generated.restorations else None
    manifest={"game_id":game_id(generated.game),"generator_version":GENERATOR_VERSION,"schema_version":generated.game.schema_version,"oracle_version":result.oracle_version,"seed":c.seed,"family":c.family,"config":_config_dict(c),"formal_game":generated.game.to_dict(),"oracle":result.to_dict(),"restorations":[] if restoration_result is None else [_restoration_dict(e) for e in restoration_result.evaluations],"descriptors":structural_descriptors(generated.game,result.explored_profiles,len(generated.restorations)),"parent_game_id":None if transformation is None else transformation.parent_game_id,"transformation":None if transformation is None else asdict(transformation)}
    validate_no_leakage(manifest); return manifest


def canonical_json(value: Any) -> str:
    return json.dumps(value,sort_keys=True,separators=(",",":"))
