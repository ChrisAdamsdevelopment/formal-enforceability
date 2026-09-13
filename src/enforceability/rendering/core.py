"""Deterministic representation layer.  This module intentionally has no oracle dependency."""
from __future__ import annotations

from dataclasses import asdict, dataclass
from hashlib import sha256
import json
import random
import re
from types import MappingProxyType
from typing import Any

from enforceability.schema import Game

RENDERER_VERSION = "stage5.renderer.v1"
TEMPLATE_VERSION = "stage5.templates.v1"
PROTOCOL_VERSION = "stage5.protocol.v1"
RANDOMIZATION_VERSION = "stage5.surface-randomization.v1"
CORPUS_SPEC_VERSION = "stage5.render-corpus.v1"
TASKS = ("enforceability-classification-v1", "failure-value-v1", "restoration-selection-v1")
DOMAINS = ("formal-plain-v1", "access-control", "service-routing", "warehouse-operations", "industrial-process")
PROTOCOL_TEXT = (
    "Protocol: The controller remembers all previous observations and its own previous actions, but does not directly observe the hidden state. "
    "The observation aliases below define exactly what it observes. The opposing player knows the true state and sees past controller actions. "
    "At each round both sides commit to their current actions simultaneously; the opposing player does not see the controller's current private random draw before committing. "
    "Play ends immediately upon entering failure or recovery; otherwise the finite horizon applies. All probabilities are exact. Epsilon is the permitted worst-case probability of failure before recovery."
)

def canonical(value: Any) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=True)

def digest(value: Any) -> str:
    return sha256((value if isinstance(value, str) else canonical(value)).encode()).hexdigest()

@dataclass(frozen=True, slots=True)
class RendererSpec:
    renderer_version: str = RENDERER_VERSION
    language: str = "en"
    task_contract_version: str = "enforceability-classification-v1"
    template_version: str = TEMPLATE_VERSION
    domains: tuple[str, ...] = DOMAINS
    variants_per_game: int = 2
    ordering_policy: str = "seeded-sha256-permutation-v1"
    identifier_policy: str = "neutral-lexicon-v1"
    numeric_policy: str = "reduced-exact-fractions-v1"
    protocol_text_version: str = PROTOCOL_VERSION
    surface_randomization_version: str = RANDOMIZATION_VERSION

    def __post_init__(self):
        supported = (self.renderer_version == RENDERER_VERSION and self.language == "en" and
                     self.task_contract_version in TASKS and self.template_version == TEMPLATE_VERSION and
                     self.ordering_policy == "seeded-sha256-permutation-v1" and self.identifier_policy == "neutral-lexicon-v1" and
                     self.numeric_policy == "reduced-exact-fractions-v1" and self.protocol_text_version == PROTOCOL_VERSION and
                     self.surface_randomization_version == RANDOMIZATION_VERSION)
        if not supported: raise ValueError("unsupported renderer component version")
        if not self.domains or len(set(self.domains)) != len(self.domains) or any(x not in DOMAINS for x in self.domains): raise ValueError("invalid domains")
        if type(self.variants_per_game) is not int or self.variants_per_game < 1: raise ValueError("variants_per_game must be positive")
        object.__setattr__(self, "domains", tuple(self.domains))

    @classmethod
    def from_dict(cls, value):
        if not isinstance(value, dict) or set(value) != set(cls.__dataclass_fields__): raise ValueError("RendererSpec fields mismatch")
        value = dict(value); value["domains"] = tuple(value["domains"]); return cls(**value)
    def to_dict(self):
        value = asdict(self); value["domains"] = list(self.domains); return value
    @property
    def fingerprint(self): return digest(self.to_dict())

@dataclass(frozen=True, slots=True)
class TypedClause:
    clause_type: str
    formal_source_fields: tuple[str, ...]
    template_id: str
    output_position: int
    text: str

@dataclass(frozen=True, slots=True)
class RenderPlan:
    domain: str
    task_contract: str
    render_seed: int
    surface_states: tuple[tuple[str, str], ...]
    surface_controller_actions: tuple[tuple[str, str], ...]
    surface_adversary_actions: tuple[tuple[str, str], ...]
    surface_observations: tuple[tuple[str, str], ...]
    surface_game: Any
    clauses: tuple[TypedClause, ...]
    ordering: Any
    template_selections: tuple[str, ...]
    protocol_text_version: str = PROTOCOL_VERSION

    def __post_init__(self):
        object.__setattr__(self, "surface_game", MappingProxyType(json.loads(canonical(self.surface_game))))
        object.__setattr__(self, "ordering", MappingProxyType(json.loads(canonical(self.ordering))))
    def to_dict(self):
        return {"domain":self.domain,"task_contract":self.task_contract,"render_seed":self.render_seed,
                "surface_states":[list(x) for x in self.surface_states],"surface_controller_actions":[list(x) for x in self.surface_controller_actions],
                "surface_adversary_actions":[list(x) for x in self.surface_adversary_actions],"surface_observations":[list(x) for x in self.surface_observations],
                "surface_game":dict(self.surface_game),"clauses":[asdict(x) for x in self.clauses],"ordering":dict(self.ordering),
                "template_selections":list(self.template_selections),"protocol_text_version":self.protocol_text_version}
    @property
    def fingerprint(self): return digest(self.to_dict())

@dataclass(frozen=True, slots=True)
class RenderedCase:
    render_case_id: str
    renderer_spec_fingerprint: str
    render_plan_fingerprint: str
    domain: str
    variant_index: int
    task_contract: str
    prompt_text: str
    prompt_text_hash: str
    def public_dict(self): return asdict(self)

@dataclass(frozen=True, slots=True)
class RenderCorpusSpec:
    render_corpus_spec_version: str
    stage4_freeze_fingerprint: str
    renderer_spec_fingerprint: str
    source_tracks: tuple[str, ...]
    source_game_ids: tuple[str, ...]
    domains: tuple[str, ...]
    development_variants: int
    primary_assignment_rule: str
    domain_assignment_salt: str
    task_contract: str
    render_seed_namespace: str
    output_policy: str
    def __post_init__(self):
        if self.render_corpus_spec_version != CORPUS_SPEC_VERSION or self.primary_assignment_rule != "sha256-modulo-v1" or self.task_contract not in TASKS: raise ValueError("unsupported render corpus specification")
        for name in ("source_tracks","source_game_ids","domains"): object.__setattr__(self,name,tuple(getattr(self,name)))
    def to_dict(self):
        x=asdict(self)
        for k in ("source_tracks","source_game_ids","domains"): x[k]=list(x[k])
        return x
    @property
    def fingerprint(self): return digest(self.to_dict())

LEX = ("Amber","Cedar","Delta","Flint","Indigo","Juniper","Quartz","Sable","Umber","Violet","Willow","Zinc","Birch","Coral","Frost","Linen","Mica","Ochre","Pearl","Silver")
DOMAIN_INTRO = {
 "formal-plain-v1":"This is a finite formal control game.",
 "access-control":"A fictional access-control board is governed by the following abstract rules.",
 "service-routing":"A fictional service-routing board is governed by the following abstract rules.",
 "warehouse-operations":"A fictional warehouse-operations board is governed by the following abstract rules.",
 "industrial-process":"A fictional industrial-process board is governed by the following abstract rules.",
}

def _permuted(items, rng):
    out=list(items); rng.shuffle(out); return tuple(out)

def _surface_game(game, sm, cm, am, om):
    raw=game.to_dict()
    dist=lambda rows:[{"state":sm[x["state"]],"probability":x["probability"]} for x in rows]
    return {"schema_version":raw["schema_version"],"states":[sm[x] for x in raw["states"]],"initial_distribution":dist(raw["initial_distribution"]),
      "controller_actions":[cm[x] for x in raw["controller_actions"]],"adversary_actions":[am[x] for x in raw["adversary_actions"]],"observations":[om[x] for x in raw["observations"]],
      "observation_map":{sm[k]:om[v] for k,v in raw["observation_map"].items()},
      "transitions":[{"state":sm[x["state"]],"controller_action":cm[x["controller_action"]],"adversary_action":am[x["adversary_action"]],"outcomes":dist(x["outcomes"])} for x in raw["transitions"]],
      "failure_states":[sm[x] for x in raw["failure_states"]],"recovery_states":[sm[x] for x in raw["recovery_states"]],"horizon":raw["horizon"],"epsilon":raw["epsilon"],
      "action_availability":{cm[k]:v for k,v in raw["action_availability"].items()},
      "legitimate_rewards":[{"state":sm[x["state"]],"controller_action":cm[x["controller_action"]],"reward":x["reward"]} for x in raw["legitimate_rewards"]],"display_labels":{}}

def make_plan(game: Game, spec: RendererSpec, render_seed: int, domain: str) -> RenderPlan:
    if domain not in spec.domains or type(render_seed) is not int or render_seed < 0: raise ValueError("invalid domain or render seed")
    rng=random.Random(int(digest(f"{spec.fingerprint}|{game.to_json()}|{render_seed}|{domain}"),16))
    names=_permuted(LEX,rng)
    if len(game.states)>len(names) or max(len(game.controller_actions),len(game.adversary_actions),len(game.observations))>20: raise ValueError("domain lexicon capacity exceeded")
    sm=dict(zip(game.states,names)); cm={x:f"Option {names[i]}" for i,x in enumerate(_permuted(game.controller_actions,rng))}; am={x:f"Move {names[i]}" for i,x in enumerate(_permuted(game.adversary_actions,rng))}; om={x:f"Signal {names[i]}" for i,x in enumerate(_permuted(game.observations,rng))}
    sg=_surface_game(game,sm,cm,am,om)
    state_order=_permuted(sg["states"],rng); c_order=_permuted(sg["controller_actions"],rng); a_order=_permuted(sg["adversary_actions"],rng); o_order=_permuted(sg["observations"],rng)
    transitions=list(sg["transitions"]); rng.shuffle(transitions); template="transition.produces.v1" if rng.randrange(2)==0 else "transition.leads.v2"
    clauses=[]
    def add(kind,fields,tid,text): clauses.append(TypedClause(kind,tuple(fields),tid,len(clauses),text))
    add("DomainClause",(),"domain.intro.v1",DOMAIN_INTRO[domain])
    add("StateDeclarationClause",("states",),"states.v1","Possible system states: " + ", ".join(state_order) + ".")
    initial=", ".join(f"{x['state']} with probability {x['probability']}" for x in sg["initial_distribution"])
    add("InitialDistributionClause",("initial_distribution",),"initial.v1","Initially the hidden state is " + initial + ".")
    for obs in o_order:
        members=[s for s in state_order if sg["observation_map"][s]==obs]
        add("ObservationAliasClause",("observations","observation_map"),"observation.v1",f"Observation {obs} means the hidden state is one of: {', '.join(members)}.")
    add("ActionDeclarationClause",("controller_actions",),"controller-actions.v1","Controller actions: " + ", ".join(c_order) + ".")
    add("AdversaryActionDeclarationClause",("adversary_actions",),"adversary-actions.v1","Opposing-player actions: " + ", ".join(a_order) + ".")
    for action in c_order: add("ActionAvailabilityClause",("action_availability",),"availability.v1",f"{action} is available in rounds: {', '.join(map(str,sg['action_availability'][action])) or 'none'}.")
    for row in transitions:
        outcomes=", ".join(f"{x['state']} with probability {x['probability']}" for x in row["outcomes"])
        verb="produces" if template.endswith("v1") else "leads to"
        add("TransitionClause",("transitions",),template,f"From {row['state']}, controller {row['controller_action']} and opposing player {row['adversary_action']} {verb}: {outcomes}.")
    add("TerminalClause",("failure_states","recovery_states"),"terminal.v1",f"Failure states: {', '.join(sg['failure_states']) or 'none'}. Recovery states: {', '.join(sg['recovery_states']) or 'none'}.")
    if sg["legitimate_rewards"]:
        for x in sg["legitimate_rewards"]: add("RewardClause",("legitimate_rewards",),"reward.v1",f"Legitimate reward at {x['state']} with {x['controller_action']} is exactly {x['reward']}.")
    add("HorizonClause",("horizon",),"horizon.v1",f"The horizon is {sg['horizon']} rounds.")
    add("TimingClause",("move_timing",),"timing.v1",PROTOCOL_TEXT)
    add("ControllerKnowledgeClause",("controller_information",),"knowledge.controller.v1","The controller uses only its observation/action history and private randomization.")
    add("AdversaryKnowledgeClause",("adversary_information",),"knowledge.adversary.v1","The opposing player chooses strategically with the information specified by the protocol.")
    add("ObjectiveClause",("epsilon","failure_states","recovery_states","horizon"),"objective.classification.v1",f"Question: Can the controller keep the worst-case probability of entering failure before recovery within the horizon at or below epsilon = {sg['epsilon']}?")
    add("AnswerFormatClause",(),"answer.classification.v1",'Answer with exactly one JSON object: {"status":"WINNING"} or {"status":"LOSING"}.')
    ordering={"states":list(state_order),"controller_actions":list(c_order),"adversary_actions":list(a_order),"observations":list(o_order),"transition_keys":[[x["state"],x["controller_action"],x["adversary_action"]] for x in transitions]}
    return RenderPlan(domain,spec.task_contract_version,render_seed,tuple(sm.items()),tuple(cm.items()),tuple(am.items()),tuple(om.items()),sg,tuple(clauses),ordering,tuple(x.template_id for x in clauses))

def realize(plan: RenderPlan) -> str:
    return "\n\n".join(x.text for x in sorted(plan.clauses,key=lambda x:x.output_position)) + "\n"

def reconstruct_game(plan: RenderPlan) -> Game:
    inv=lambda rows:{surface:formal for formal,surface in rows}
    sm,cm,am,om=inv(plan.surface_states),inv(plan.surface_controller_actions),inv(plan.surface_adversary_actions),inv(plan.surface_observations)
    raw=dict(plan.surface_game); dist=lambda rows:[{"state":sm[x["state"]],"probability":x["probability"]} for x in rows]
    out={"schema_version":raw["schema_version"],"states":[sm[x] for x in raw["states"]],"initial_distribution":dist(raw["initial_distribution"]),"controller_actions":[cm[x] for x in raw["controller_actions"]],"adversary_actions":[am[x] for x in raw["adversary_actions"]],"observations":[om[x] for x in raw["observations"]],"observation_map":{sm[k]:om[v] for k,v in raw["observation_map"].items()},"transitions":[{"state":sm[x["state"]],"controller_action":cm[x["controller_action"]],"adversary_action":am[x["adversary_action"]],"outcomes":dist(x["outcomes"])} for x in raw["transitions"]],"failure_states":[sm[x] for x in raw["failure_states"]],"recovery_states":[sm[x] for x in raw["recovery_states"]],"horizon":raw["horizon"],"epsilon":raw["epsilon"],"action_availability":{cm[k]:v for k,v in raw["action_availability"].items()},"legitimate_rewards":[{"state":sm[x["state"]],"controller_action":cm[x["controller_action"]],"reward":x["reward"]} for x in raw["legitimate_rewards"]],"display_labels":{}}
    return Game.from_dict(out)

def audit_clauses(plan):
    required={"states","initial_distribution","observations","observation_map","controller_actions","adversary_actions","action_availability","transitions","failure_states","recovery_states","horizon","epsilon","move_timing","controller_information","adversary_information"}
    covered={f for x in plan.clauses for f in x.formal_source_fields}
    transitions=sum(x.clause_type=="TransitionClause" for x in plan.clauses)
    return {"passed":required<=covered and transitions==len(plan.surface_game["transitions"]),"missing":sorted(required-covered),"transition_clauses":transitions}

def scan_prompt(text):
    forbidden=("oracle","optimal policy","correct answer","game_id","generator_version","oracle_version","mechanism_id","candidate_key","stage 4","stage-4")
    findings=[x for x in forbidden if x in text.lower()]
    stripped=re.sub(r'Answer with exactly one JSON object: \{"status":"WINNING"\} or \{"status":"LOSING"\}\.','',text)
    findings += [x for x in ("WINNING","LOSING") if x in stripped]
    return {"passed":not findings,"findings":findings}

def render(game, spec, render_seed, domain, variant_index=0):
    plan=make_plan(game,spec,render_seed,domain); text=realize(plan)
    if not audit_clauses(plan)["passed"] or not scan_prompt(text)["passed"]: raise ValueError("render audit failed")
    if reconstruct_game(plan).to_json()!=game.to_json(): raise ValueError("RenderPlan semantic mismatch")
    text_hash=digest(text); case_id="rc-"+digest(f"{spec.fingerprint}|{plan.fingerprint}|{text_hash}")[:24]
    return plan,RenderedCase(case_id,spec.fingerprint,plan.fingerprint,domain,variant_index,spec.task_contract_version,text,text_hash)

def assign_domain(game_id, spec, salt="stage5-primary-domain-v1"):
    return spec.domains[int(digest(spec.fingerprint+game_id+salt),16)%len(spec.domains)]

def prompt_features(case, plan):
    t=case.prompt_text
    return {"character_count":len(t),"word_count":len(t.split()),"sentence_count":len(re.findall(r"[.!?](?:\s|$)",t)),"bullet_count":sum(x.startswith("-") for x in t.splitlines()),"transition_clause_count":sum(x.clause_type=="TransitionClause" for x in plan.clauses),"identifier_lengths":[len(x[1]) for x in plan.surface_states],"identifier_prefix_distribution":sorted({x[1].split()[0] for rows in (plan.surface_states,plan.surface_controller_actions,plan.surface_adversary_actions,plan.surface_observations) for x in rows}),"section_ordering":[x.clause_type for x in plan.clauses],"selected_template_ids":list(plan.template_selections),"domain":case.domain,"variant_index":case.variant_index,"punctuation_count":len(re.findall(r"[^\w\s]",t)),"numeric_token_count":len(re.findall(r"\b\d+(?:/\d+)?\b",t))}

FEATURE_CLASSES={"state_count":"SEMANTIC","transition_count":"SEMANTIC","observation_class_count":"SEMANTIC","domain":"REPRESENTATIONAL","variant_index":"REPRESENTATIONAL","selected_template_ids":"REPRESENTATIONAL","original_family_label":"PROVENANCE","oracle_status":"ANSWER_DIRECT"}

def build_freeze(*args, **kwargs):
    """Lazy facade keeps artifact/answer assembly outside renderer decision logic."""
    from .build import build_artifacts
    return build_artifacts(*args, **kwargs)

def verify_freeze(*args, **kwargs):
    from .build import verify_artifacts
    return verify_artifacts(*args, **kwargs)
