"""Deterministic, formal-only Stage-2 game generation."""
from __future__ import annotations

from dataclasses import asdict, dataclass, replace
from fractions import Fraction
import hashlib
import json
import random
from typing import Any

from enforceability import Restoration, optimal_restoration, solve
from enforceability.restoration import apply_restoration
from enforceability.schema import Game, InvalidGame, SCHEMA_VERSION, fraction, rational_json

GENERATOR_VERSION = "stage2.v2"
BANNED_KEYS = frozenset({"winning_case", "losing_case", "correct_action", "safe_restoration", "fatal_branch"})
FAMILIES = ("observation-conflict", "authority-limitation", "probe", "timing", "capability-restriction", "mixed-restoration")


@dataclass(frozen=True, slots=True)
class ComplexityLimits:
    max_states: int = 20
    max_horizon: int = 4
    max_controller_histories: int = 100
    max_policy_profiles: int = 100_000
    max_generated_candidates: int = 1000

    def __post_init__(self):
        if any(type(value) is not int or value < 0 for value in asdict(self).values()):
            raise ValueError("complexity limits must be nonnegative integers")


@dataclass(frozen=True, slots=True)
class GeneratorConfig:
    family: str
    seed: int
    generator_version: str = GENERATOR_VERSION
    horizon: int = 2
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
    epsilon: str | int = "0"
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
        if any(type(x) is not bool for x in (self.common_action,self.probe_available,self.probe_informative,self.stochasticity)):
            raise GenerationError("invalid_configuration",self.seed,self)
        try: e=fraction(self.epsilon,"generator epsilon")
        except InvalidGame as exc: raise GenerationError("invalid_configuration",self.seed,self) from exc
        if not 0 <= e <= 1: raise GenerationError("invalid_configuration",self.seed,self)
        modes={"observation-conflict":{"base"},"authority-limitation":{"base","robust"},
               "probe":{"base","too-late"},"timing":{"base"},
               "capability-restriction":{"base","multi","multi-absent","none"},
               "mixed-restoration":{"base","none","tie"}}
        if self.mode not in modes[self.family]: raise GenerationError("invalid_configuration",self.seed,self)
        if self.family in {"probe","timing"} and self.horizon < 2: raise GenerationError("invalid_configuration",self.seed,self)
        if self.family=="probe" and (self.probe_delay < 1 or self.horizon < self.probe_delay+1):
            raise GenerationError("invalid_configuration",self.seed,self)
        if self.family=="probe" and self.mode=="too-late" and self.probe_delay < 2:
            raise GenerationError("invalid_configuration",self.seed,self)


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
    config: GeneratorConfig | None = None
    config_fingerprint: str = ""


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
    del rng
    ca=tuple(f"c{i}" for i in range(c.controller_action_count)); aa=tuple(f"a{i}" for i in range(c.adversary_action_count)); states=("q","r","x")
    t={}
    for i,act in enumerate(ca):
        for j,adv in enumerate(aa): t["q",act,adv]="r" if c.mode=="robust" or j<c.coverage else "x"
    return GeneratedGame(_game(states=states,initial=("q",),ca=ca,aa=aa,obs={s:s for s in states},transitions=t,horizon=max(1,c.horizon),epsilon=c.epsilon))


def _probe(c: GeneratorConfig, rng: random.Random) -> GeneratedGame:
    del rng  # This family is structurally controlled but remains seed-addressed.
    delays=tuple(f"d{stage}_{hidden}" for stage in range(1,c.probe_delay) for hidden in range(2))
    states=("q0","q1")+delays+("p0","p1","r","x"); ca=("c0","c1","probe","wait")
    obs={"q0":"o","q1":"o","p0":"p0" if c.probe_informative else "p","p1":"p1" if c.probe_informative else "p","r":"r","x":"x"}
    obs.update({f"d{stage}_{hidden}":f"d{stage}" for stage in range(1,c.probe_delay) for hidden in range(2)})
    t={}
    for i in range(2):
        t[f"q{i}","probe","a0"]=f"p{i}" if c.probe_delay==1 else f"d1_{i}"
        t[f"q{i}","c{i}","a0"]="r"; t[f"q{i}",f"c{1-i}","a0"]="x"
        t[f"p{i}",f"c{i}","a0"]="r"; t[f"p{i}",f"c{1-i}","a0"]="x"
        t[f"q{i}","wait","a0"]="r" if c.common_action else "x"
        for stage in range(1,c.probe_delay):
            state=f"d{stage}_{i}"
            if c.mode=="too-late": t[state,"wait","a0"]="x"
            else: t[state,"wait","a0"]=f"p{i}" if stage==c.probe_delay-1 else f"d{stage+1}_{i}"
            for action in ("c0","c1","probe"): t[state,action,"a0"]="x"
        t[f"p{i}","wait","a0"]="x"; t[f"p{i}","probe","a0"]="x"
    if c.common_action:
        for s in ("p0","p1"): t[s,"wait","a0"]="r"
    availability={"probe":[0] if c.probe_available else [],"wait":list(range(c.horizon)),"c0":list(range(c.horizon)),"c1":list(range(c.horizon))}
    return GeneratedGame(_game(states=states,initial=("q0","q1"),ca=ca,aa=("a0",),obs=obs,transitions=t,horizon=c.horizon,availability=availability,epsilon=c.epsilon))


def _timing(c: GeneratorConfig, rng: random.Random) -> GeneratedGame:
    states=("q","d","r","x"); ca=("wait","act"); t={("q","wait","a0"):"x",("q","act","a0"):"r"}
    h=c.horizon; av={"wait":list(range(h)),"act":[c.intervention_round] if c.intervention_round<h else []}
    return GeneratedGame(_game(states=states,initial=("q",),ca=ca,aa=("a0",),obs={s:s for s in states},transitions=t,horizon=h,availability=av,epsilon=c.epsilon))


def _capability(c: GeneratorConfig, rng: random.Random) -> GeneratedGame:
    states=("q","r","x"); ca=("c0",); aa=tuple(f"a{i}" for i in range(max(2,c.adversary_action_count))); t={}
    harmful=1+rng.randrange(len(aa)-1)
    for j,a in enumerate(aa): t["q","c0",a]="x" if j==harmful or (c.mode in {"multi","multi-absent"} and j>0) else "r"
    game=_game(states=states,initial=("q",),ca=ca,aa=aa,obs={s:s for s in states},transitions=t,horizon=max(1,c.horizon),epsilon=c.epsilon)
    candidates=tuple(Restoration(f"z{i}",remove_adversary_actions=frozenset({a})) for i,a in enumerate(aa[1:]))
    if c.mode=="multi": candidates += (Restoration("z_combined",remove_adversary_actions=frozenset(aa[1:])),)
    if c.mode=="none": candidates=(Restoration("z0",remove_adversary_actions=frozenset({aa[0]})),)
    return GeneratedGame(game,candidates)


def _mixed(c: GeneratorConfig, rng: random.Random) -> GeneratedGame:
    # A compact conflict with unused split observations, adversarial blocking,
    # and a dormant timed action; rewards make restoration costs endogenous.
    states=("q0","q1","r","x"); ca=("c0","c1","c2")+(('c3',) if c.mode=="tie" else ()); aa=("a0","a1")
    obs={"q0":"o","q1":"o","r":"r","x":"x"}; t={}
    for i in range(2):
        for j,a in enumerate(aa):
            t[f"q{i}",f"c{i}",a]="r" if j==0 else "x"; t[f"q{i}",f"c{1-i}",a]="x"; t[f"q{i}","c2",a]="r"
            if c.mode=="tie": t[f"q{i}","c3",a]="r"
    h=c.horizon; av={"c0":list(range(h)),"c1":list(range(h)),"c2":[]}
    if c.mode=="tie": av["c3"]=[]
    rewards={(f"q{i}",f"c{i}"):10 for i in range(2)} | {(f"q{i}","c2"):7 for i in range(2)}
    if c.mode=="tie": rewards.update({(f"q{i}","c3"):7 for i in range(2)})
    game=_game(states=states,initial=("q0","q1"),ca=ca,aa=aa,obs=obs,transitions=t,horizon=h,availability=av,rewards=rewards,epsilon=c.epsilon)
    # Add unused observations through canonical schema so refinement is legal.
    raw=game.to_dict(); raw["observations"] += ["u0","u1"]; game=Game.from_dict(raw)
    candidates=(Restoration("z0",observation_overrides=(("q0","u0"),("q1","u1"))),Restoration("z1",remove_adversary_actions=frozenset({"a1"})),Restoration("z2",availability_overrides=(("c2",tuple(range(h))),)))
    if c.mode=="tie": candidates += (Restoration("z3",availability_overrides=(("c3",tuple(range(h))),)),)
    if c.mode=="none": candidates=candidates[:1]
    return GeneratedGame(game,candidates)


_BUILDERS={"observation-conflict":_conflict,"authority-limitation":_authority,"probe":_probe,"timing":_timing,"capability-restriction":_capability,"mixed-restoration":_mixed}


def _config_dict(c: GeneratorConfig) -> dict[str, Any]:
    value=asdict(c); value["epsilon"]=rational_json(fraction(c.epsilon,"generator epsilon")); return value


def _structural_dimensions(c: GeneratorConfig) -> tuple[int,int,int,int]:
    """Exact cheap dimensions: states, horizon, controller actions, adversary actions."""
    if c.family=="observation-conflict": return max(2,c.ambiguous_states)+2,c.horizon,max(c.controller_action_count,max(2,c.ambiguous_states))+int(c.common_action),c.adversary_action_count
    if c.family=="authority-limitation": return 3,c.horizon,c.controller_action_count,c.adversary_action_count
    if c.family=="probe": return 2*c.probe_delay+4,c.horizon,4,1
    if c.family=="timing": return 4,c.horizon,2,1
    if c.family=="capability-restriction": return 3,c.horizon,1,max(2,c.adversary_action_count)
    return 4,c.horizon,4 if c.mode=="tie" else 3,2


def _saturating_power(base: int, exponent: int, cap: int) -> int:
    """Return min(base**exponent, cap+1) without constructing huge integers."""
    result=1
    for _ in range(exponent):
        if base and result > cap//base: return cap+1
        result *= base
    return result


def _actual_estimates(game: Game, history_limit: int, profile_limit: int) -> dict[str,int]:
    # Traverse actual nonterminal structure, retaining only information-history
    # keys. Sets stop growing once the saturation limit has been crossed.
    current={(s,(game.observation_map[s],),()) for s in game.initial_states}; controller_keys=[]
    adversary_current={(s,(s,),(),()) for s in game.initial_states}; adversary_histories=0
    for t in range(game.horizon):
        active={(s,o,a) for s,o,a in current if s not in game.failure_states|game.recovery_states}
        keys={(o,a) for _,o,a in active}; controller_keys.append((keys,len(game.available_actions(t))))
        nxt=set()
        for s,o,prior in active:
            for action in game.available_actions(t):
                for adversary in game.adversary_actions:
                    for n,p in game.transitions[s,action,adversary]:
                        if p and n not in game.failure_states|game.recovery_states and len(nxt)<=history_limit:
                            nxt.add((n,o+(game.observation_map[n],),prior+(action,)))
        current=nxt
        adv_active={h for h in adversary_current if h[0] not in game.failure_states|game.recovery_states}
        adversary_histories=min(history_limit+1,adversary_histories+len(adv_active)); adv_next=set()
        for s,states,cs,ads in adv_active:
            for action in game.available_actions(t):
                for adversary in game.adversary_actions:
                    for n,p in game.transitions[s,action,adversary]:
                        if p and len(adv_next)<=history_limit: adv_next.add((n,states+(n,),cs+(action,),ads+(adversary,)))
        adversary_current=adv_next
    histories=min(history_limit+1,sum(len(keys) for keys,_ in controller_keys))
    controller=1
    for keys,choices in controller_keys:
        controller=min(profile_limit+1,controller*_saturating_power(choices,len(keys),profile_limit))
    adversary=_saturating_power(len(game.adversary_actions),adversary_histories,profile_limit)
    profiles=profile_limit+1 if controller>profile_limit or adversary>profile_limit or (adversary and controller>profile_limit//adversary) else controller*adversary
    return {"states":len(game.states),"horizon":game.horizon,"controller_actions":len(game.controller_actions),"adversary_actions":len(game.adversary_actions),"controller_histories":histories,"policy_profiles":profiles}


def generate(c: GeneratorConfig) -> GeneratedGame | GenerationRejected:
    limits=c.limits
    dimensions=_structural_dimensions(c)
    cheap={"states":dimensions[0],"horizon":dimensions[1],"controller_actions":dimensions[2],"adversary_actions":dimensions[3]}
    # Reject before allocation; notably no exponentiation occurs on huge horizons.
    if cheap["states"]>limits.max_states or cheap["horizon"]>limits.max_horizon:
        return GenerationRejected("estimated_oracle_complexity",c.seed,_config_dict(c),cheap)
    try:
        generated=_BUILDERS[c.family](c,random.Random(c.seed))
        # Round-trip invokes every schema invariant and establishes canonicality.
        Game.from_json(generated.game.to_json())
        estimates=_actual_estimates(generated.game,limits.max_controller_histories,limits.max_policy_profiles)
        if estimates["controller_histories"]>limits.max_controller_histories or estimates["policy_profiles"]>limits.max_policy_profiles:
            return GenerationRejected("estimated_oracle_complexity",c.seed,_config_dict(c),estimates)
        config_json=canonical_json(_config_dict(c))
        return replace(generated,config=c,config_fingerprint=hashlib.sha256(config_json.encode()).hexdigest())
    except (InvalidGame, KeyError, ValueError) as exc:
        raise GenerationError("formal_generation_failed",c.seed,c) from exc


def canonical_game_json(game: Game) -> str:
    raw=game.to_dict(); raw["display_labels"]={}
    return json.dumps(raw,sort_keys=True,separators=(",",":"))


def game_id(game: Game) -> str:
    return hashlib.sha256(canonical_game_json(game).encode()).hexdigest()


def transform(game: Game, restoration: Restoration, seed: int | str, legacy_seed: int | None = None) -> tuple[Game,TransformationRecord]:
    """Apply a restoration and derive truthful provenance from its operation.

    The legacy four-argument form is accepted only when its claimed category
    exactly matches the derived canonical category.
    """
    child=apply_restoration(game,restoration)
    operations=[]
    if restoration.observation_overrides: operations.append("observation-refinement")
    if restoration.remove_adversary_actions: operations.append("adversary-capability-removal")
    if restoration.remove_controller_actions: operations.append("controller-capability-removal")
    if restoration.availability_overrides: operations.append("controller-availability-change")
    if not operations: raise GenerationError("empty_transformation",legacy_seed if legacy_seed is not None else seed,{})
    derived=operations[0] if len(operations)==1 else "compound"
    if isinstance(seed,str):
        if seed != derived: raise GenerationError("mislabelled_transformation",legacy_seed if legacy_seed is not None else -1,{"claimed":seed,"derived":derived})
        actual_seed=legacy_seed
    else: actual_seed=seed
    if type(actual_seed) is not int: raise GenerationError("invalid_transformation_seed",-1,{})
    before=game.to_dict(); after=child.to_dict()
    changed=tuple(key for key in before if key!="display_labels" and before[key]!=after[key])
    record=TransformationRecord(game_id(game),game_id(child),derived,changed,GENERATOR_VERSION,actual_seed)
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


def build_manifest(generated: GeneratedGame | GeneratorConfig, compatibility_generated: GeneratedGame | None=None, transformation: TransformationRecord|None=None) -> dict[str,Any]:
    """Solve and serialize a generated artifact using its bound provenance.

    ``build_manifest(config, generated)`` remains as a checked compatibility
    form: any mismatch is rejected rather than written to a manifest.
    """
    if isinstance(generated,GeneratorConfig):
        supplied=generated; generated=compatibility_generated
        if not isinstance(generated,GeneratedGame) or generated.config != supplied:
            raise GenerationError("provenance_mismatch",supplied.seed,supplied)
    if not isinstance(generated,GeneratedGame) or generated.config is None:
        raise GenerationError("missing_provenance",-1,{})
    c=generated.config
    expected=hashlib.sha256(canonical_json(_config_dict(c)).encode()).hexdigest()
    if generated.config_fingerprint != expected: raise GenerationError("provenance_mismatch",c.seed,c)
    result=solve(generated.game)
    restoration_result=optimal_restoration(generated.game,generated.restorations) if generated.restorations else None
    manifest={"game_id":game_id(generated.game),"generator_version":GENERATOR_VERSION,"schema_version":generated.game.schema_version,"oracle_version":result.oracle_version,"seed":c.seed,"family":c.family,"config":_config_dict(c),"formal_game":generated.game.to_dict(),"oracle":result.to_dict(),"restorations":[] if restoration_result is None else [_restoration_dict(e) for e in restoration_result.evaluations],"descriptors":structural_descriptors(generated.game,result.explored_profiles,len(generated.restorations)),"parent_game_id":None if transformation is None else transformation.parent_game_id,"transformation":None if transformation is None else asdict(transformation)}
    validate_no_leakage(manifest); return manifest


def canonical_json(value: Any) -> str:
    return json.dumps(value,sort_keys=True,separators=(",",":"))
