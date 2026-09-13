"""Stage-5 answer-blind semantic rendering.

The renderer intentionally imports only the Stage-1 schema.  Answer material is
joined by :mod:`enforceability.rendering.freeze`, after rendering has finished.
"""
from __future__ import annotations

from dataclasses import dataclass, fields
import hashlib
import json
import random
import re
from types import MappingProxyType
from typing import Any, Mapping

from enforceability.schema import Game

RENDERER_VERSION = "stage5.semantic-render.v1"
TASK_CONTRACT_VERSION = "stage5.task-contracts.v1"
TEMPLATE_VERSION = "stage5.templates.v1"
PROTOCOL_VERSION = "stage1.information-protocol.v1"
DOMAINS = ("formal-plain-v1", "access-control", "service-routing", "warehouse-operations", "industrial-process")
TASKS = ("enforceability-classification-v1", "failure-value-v1", "restoration-selection-v1")


def deep_freeze(value: Any) -> Any:
    if isinstance(value, Mapping):
        return MappingProxyType({str(k): deep_freeze(v) for k, v in value.items()})
    if isinstance(value, (list, tuple)):
        return tuple(deep_freeze(v) for v in value)
    return value


def deep_thaw(value: Any) -> Any:
    if isinstance(value, Mapping):
        return {str(k): deep_thaw(v) for k, v in value.items()}
    if isinstance(value, tuple):
        return [deep_thaw(v) for v in value]
    return value


def canonical_json(value: Any) -> str:
    return json.dumps(deep_thaw(value), sort_keys=True, separators=(",", ":"), ensure_ascii=False)


def fingerprint(value: Any) -> str:
    return hashlib.sha256(canonical_json(value).encode()).hexdigest()


def semantic_game_dict(value: Game | Mapping[str, Any]) -> dict[str, Any]:
    raw = value.to_dict() if isinstance(value, Game) else deep_thaw(value)
    game = Game.from_dict(raw)
    result = game.to_dict()
    result.pop("display_labels")
    for key in ("states", "controller_actions", "adversary_actions", "observations", "failure_states", "recovery_states"):
        result[key] = sorted(result[key])
    result["initial_distribution"] = sorted(result["initial_distribution"], key=lambda x: x["state"])
    result["observation_map"] = dict(sorted(result["observation_map"].items()))
    result["action_availability"] = {k: sorted(v) for k, v in sorted(result["action_availability"].items())}
    result["transitions"] = sorted(result["transitions"], key=lambda x: (x["state"], x["controller_action"], x["adversary_action"]))
    for row in result["transitions"]: row["outcomes"] = sorted(row["outcomes"], key=lambda x: x["state"])
    result["legitimate_rewards"] = sorted(result["legitimate_rewards"], key=lambda x: (x["state"], x["controller_action"]))
    return result


def semantic_signature(value: Game | Mapping[str, Any]) -> str:
    return canonical_json(semantic_game_dict(value))


@dataclass(frozen=True, slots=True)
class RendererSpec:
    renderer_version: str = RENDERER_VERSION
    language: str = "en"
    task_contract_version: str = TASK_CONTRACT_VERSION
    template_version: str = TEMPLATE_VERSION
    domains: tuple[str, ...] = DOMAINS
    variants_per_game: int = 2
    ordering_policy: str = "seeded-shuffle-v1"
    identifier_policy: str = "neutral-domain-lexicon-v1"
    numeric_policy: str = "reduced-rational-v1"
    protocol_text_version: str = PROTOCOL_VERSION
    surface_randomization_version: str = "surface-map-v1"

    def __post_init__(self) -> None:
        object.__setattr__(self, "domains", tuple(self.domains))
        expected = (RENDERER_VERSION,"en",TASK_CONTRACT_VERSION,TEMPLATE_VERSION,DOMAINS,2,"seeded-shuffle-v1","neutral-domain-lexicon-v1","reduced-rational-v1",PROTOCOL_VERSION,"surface-map-v1")
        if tuple(getattr(self, f.name) for f in fields(self)) != expected:
            raise ValueError("unsupported renderer specification")

    def to_dict(self) -> dict[str, Any]:
        return {f.name: deep_thaw(getattr(self, f.name)) for f in fields(self)}

    @property
    def fingerprint(self) -> str: return fingerprint(self.to_dict())

    @classmethod
    def from_dict(cls, raw: Mapping[str, Any]) -> "RendererSpec":
        if set(raw) != {f.name for f in fields(cls)}: raise ValueError("renderer fields mismatch")
        return cls(**{**deep_thaw(raw), "domains": tuple(raw["domains"])})


@dataclass(frozen=True, slots=True)
class RestorationTaskContext:
    candidates: tuple[Mapping[str, Any], ...]
    selection_rule: str = "minimum-cost-feasible-v1"
    def __post_init__(self) -> None:
        if not self.candidates or self.selection_rule != "minimum-cost-feasible-v1": raise ValueError("invalid restoration context")
        names = [x.get("option") for x in self.candidates]
        if any(not isinstance(x, str) or not x.startswith("option-") for x in names) or len(set(names)) != len(names): raise ValueError("invalid restoration options")
        object.__setattr__(self, "candidates", deep_freeze(self.candidates))


@dataclass(frozen=True, slots=True)
class TypedClause:
    clause_type: str
    formal_source_fields: tuple[str, ...]
    semantic_payload: Mapping[str, Any]
    template_id: str
    output_position: int
    text: str
    def __post_init__(self) -> None:
        object.__setattr__(self, "formal_source_fields", tuple(self.formal_source_fields))
        object.__setattr__(self, "semantic_payload", deep_freeze(self.semantic_payload))
    def to_dict(self) -> dict[str, Any]:
        return {"clause_type": self.clause_type, "formal_source_fields": list(self.formal_source_fields), "semantic_payload": deep_thaw(self.semantic_payload),
                "template_id": self.template_id, "output_position": self.output_position, "text": self.text}


@dataclass(frozen=True, slots=True)
class RenderPlan:
    domain: str; task_contract: str; render_seed: str
    state_map: Mapping[str, str]; controller_action_map: Mapping[str, str]; adversary_action_map: Mapping[str, str]; observation_map: Mapping[str, str]
    surface_game: Mapping[str, Any]; clauses: tuple[TypedClause, ...]; ordering: Mapping[str, Any]; template_selections: Mapping[str, Any]
    protocol_version: str; task_payload_metadata: Mapping[str, Any]
    def __post_init__(self) -> None:
        for name in ("state_map", "controller_action_map", "adversary_action_map", "observation_map", "surface_game", "ordering", "template_selections", "task_payload_metadata"):
            object.__setattr__(self, name, deep_freeze(getattr(self, name)))
        object.__setattr__(self, "clauses", tuple(self.clauses))
    def to_dict(self) -> dict[str, Any]:
        return {"domain": self.domain, "task_contract": self.task_contract, "render_seed": self.render_seed,
                "state_map": deep_thaw(self.state_map), "controller_action_map": deep_thaw(self.controller_action_map), "adversary_action_map": deep_thaw(self.adversary_action_map),
                "observation_map": deep_thaw(self.observation_map), "surface_game": deep_thaw(self.surface_game), "clauses": [x.to_dict() for x in self.clauses],
                "ordering": deep_thaw(self.ordering), "template_selections": deep_thaw(self.template_selections), "protocol_version": self.protocol_version,
                "task_payload_metadata": deep_thaw(self.task_payload_metadata)}
    @property
    def fingerprint(self) -> str: return fingerprint(self.to_dict())


@dataclass(frozen=True, slots=True)
class RenderedCase:
    render_case_id: str; renderer_spec_fingerprint: str; render_plan_fingerprint: str; domain: str; variant_index: int
    task_contract: str; prompt_text: str; prompt_text_hash: str
    def to_dict(self) -> dict[str, Any]: return {f.name: getattr(self, f.name) for f in fields(self)}


VOCAB = {
 "formal-plain-v1": ("state", "controller action", "opposing-player action", "signal"),
 "access-control": ("access configuration", "control command", "external-actor choice", "monitor reading"),
 "service-routing": ("routing configuration", "dispatch choice", "competing-routing choice", "telemetry reading"),
 "warehouse-operations": ("operational configuration", "handling command", "external scheduling choice", "scanner reading"),
 "industrial-process": ("process mode", "control setting", "external strategic choice", "sensor reading"),
}
PREFIX = {"formal-plain-v1":"formal-plain", **{d:d for d in DOMAINS if d != "formal-plain-v1"}}
WORDS = ("Amber", "Birch", "Cedar", "Flint", "Quartz", "Violet", "Willow", "Copper", "Indigo", "Maple", "Silver", "Topaz", "Elm", "Jade", "Ochre", "Pine", "Umber", "Aspen", "Coral", "Onyx")


def _rng(seed: str, domain: str, channel: str) -> random.Random:
    return random.Random(int(hashlib.sha256(f"{seed}|{domain}|{channel}".encode()).hexdigest(), 16))


def _permute(items, seed, domain, channel):
    out = list(items); _rng(seed, domain, channel).shuffle(out); return out


def _names(items, kind, seed, domain, noun):
    words = _permute(WORDS, seed, domain, kind)
    return {x: f"{noun.title()} {words[i]}" for i, x in enumerate(items)}


def _surface(game: Game, seed: str, domain: str):
    sn, cn, an, on = VOCAB[domain]
    sm=_names(game.states,"states",seed,domain,sn); cm=_names(game.controller_actions,"controller",seed,domain,cn)
    am=_names(game.adversary_actions,"adversary",seed,domain,an); om=_names(game.observations,"observations",seed,domain,on)
    raw=game.to_dict(); raw["states"]=[sm[x] for x in game.states]; raw["controller_actions"]=[cm[x] for x in game.controller_actions]
    raw["adversary_actions"]=[am[x] for x in game.adversary_actions]; raw["observations"]=[om[x] for x in game.observations]
    raw["initial_distribution"]=[{"state":sm[x["state"]],"probability":x["probability"]} for x in raw["initial_distribution"]]
    raw["observation_map"]={sm[s]:om[o] for s,o in game.observation_map.items()}
    raw["transitions"]=[{"state":sm[x["state"]],"controller_action":cm[x["controller_action"]],"adversary_action":am[x["adversary_action"]],
                         "outcomes":[{"state":sm[y["state"]],"probability":y["probability"]} for y in x["outcomes"]]} for x in raw["transitions"]]
    raw["failure_states"]=[sm[x] for x in game.failure_states]; raw["recovery_states"]=[sm[x] for x in game.recovery_states]
    raw["action_availability"]={cm[a]:v for a,v in raw["action_availability"].items()}
    raw["legitimate_rewards"]=[{"state":sm[x["state"]],"controller_action":cm[x["controller_action"]],"reward":x["reward"]} for x in raw["legitimate_rewards"]]
    raw["display_labels"]={}
    return raw,sm,cm,am,om


def _template(domain: str, category: str) -> str: return f"{PREFIX[domain]}.{category}.v1"


def realize_clause(payload: Mapping[str, Any], template_id: str, domain: str) -> str:
    p=deep_thaw(payload); category=template_id.split(".")[-2]; sn,cn,an,on=VOCAB[domain]
    if not template_id.startswith(PREFIX[domain]+"."): raise ValueError("template/domain mismatch")
    if category=="state-declaration": return f"Declared {sn}s: {', '.join(p['items'])}."
    if category=="observation-declaration": return f"Declared {on}s: {', '.join(p['items'])}."
    if category=="controller-action-declaration": return f"Available {cn}s are named: {', '.join(p['items'])}."
    if category=="adversary-action-declaration": return f"The strategic adversary's {an}s are named: {', '.join(p['items'])}."
    if category=="initial": return "Initial distribution: "+", ".join(f"{x['state']} has probability {x['probability']}" for x in p["entries"])+"."
    if category=="observation-alias": return f"{p['observation']} is received exactly in these {sn}s: {', '.join(p['states'])}."
    if category=="availability": return f"{p['action']} may be selected in rounds: {', '.join(map(str,p['rounds'])) if p['rounds'] else 'none'}."
    if category=="transition": return f"From {p['state']}, if {p['controller_action']} and {p['adversary_action']} are committed, the next-{sn} distribution is "+", ".join(f"{x['state']} with probability {x['probability']}" for x in p["outcomes"])+"."
    if category=="terminal": return f"Failure {sn}s: {', '.join(p['failure_states']) or 'none'}. Recovery {sn}s: {', '.join(p['recovery_states']) or 'none'}."
    if category=="parameters": return f"The horizon is {p['horizon']} rounds and epsilon is {p['epsilon']}."
    if category=="reward": return f"Legitimate reward for {p['state']} with {p['controller_action']} is {p['reward']}."
    if category=="protocol": return ("At the start of every round t, the current hidden state is s_t and the controller receives the current observation o_t = obs(s_t) before choosing its round-t action. "
      "The controller has perfect recall of its entire previous observation/action history and may use private randomization. The strategic adversary knows the current true state, the prior state history available under the formal model, its own previous actions, previous controller actions, and the game and protocol, with perfect recall. "
      "Current controller and adversary actions are selected by simultaneous commitment: neither may condition on the other's current unrevealed action, and the adversary does not observe the controller's current private random draw before committing.")
    if category=="objective": return p["text"]
    if category=="answer-format": return p["text"]
    if category=="restoration-context": return "Candidate restorations: "+"; ".join(f"{x['option']}: {x['description']} (cost {x['cost']})" for x in p["candidates"])+"."
    raise ValueError(f"unsupported template {template_id}")


def build_render_plan(game: Game, spec: RendererSpec, render_seed: str, domain: str,
                      task_contract: str = "enforceability-classification-v1", task_payload: RestorationTaskContext | None = None) -> RenderPlan:
    if domain not in spec.domains or task_contract not in TASKS or not isinstance(render_seed, str) or not render_seed: raise ValueError("unsupported render request")
    if task_contract == "restoration-selection-v1" and task_payload is None: raise ValueError("restoration-selection-v1 requires restoration task context")
    surface,sm,cm,am,om=_surface(game,render_seed,domain); sg=Game.from_dict(surface)
    ordering={k:_permute(list(v),render_seed,domain,k) for k,v in {"states":sg.states,"controller_actions":sg.controller_actions,"adversary_actions":sg.adversary_actions,"observations":sg.observations,
              "initial_distribution":list(sg.initial_distribution),"failure_states":list(sg.failure_states),"recovery_states":list(sg.recovery_states)}.items()}
    trs=list(sg.to_dict()["transitions"]); trs=_permute(trs,render_seed,domain,"transitions")
    for i,row in enumerate(trs): row["outcomes"]=_permute(row["outcomes"],render_seed,domain,f"outcomes:{i}")
    clauses=[]
    def add(typ, fields_, payload, category):
        tid=_template(domain,category); clauses.append(TypedClause(typ,tuple(fields_),payload,tid,len(clauses),realize_clause(payload,tid,domain)))
    add("StateDeclarationClause",("states",),{"items":ordering["states"]},"state-declaration")
    add("ObservationDeclarationClause",("observations",),{"items":ordering["observations"]},"observation-declaration")
    add("ActionDeclarationClause",("controller_actions",),{"items":ordering["controller_actions"]},"controller-action-declaration")
    add("AdversaryActionDeclarationClause",("adversary_actions",),{"items":ordering["adversary_actions"]},"adversary-action-declaration")
    add("InitialDistributionClause",("initial_distribution",),{"entries":[next(x for x in surface["initial_distribution"] if x["state"]==s) for s in ordering["initial_distribution"]]},"initial")
    for o in ordering["observations"]: add("ObservationAliasClause",("observation_map",),{"observation":o,"states":[s for s in ordering["states"] if sg.observation_map[s]==o]},"observation-alias")
    for a in ordering["controller_actions"]: add("ActionAvailabilityClause",("action_availability",),{"action":a,"rounds":sorted(sg.action_availability[a])},"availability")
    for row in trs: add("TransitionClause",("transitions",),row,"transition")
    add("TerminalClause",("failure_states","recovery_states"),{"failure_states":ordering["failure_states"],"recovery_states":ordering["recovery_states"]},"terminal")
    add("ParameterClause",("horizon","epsilon"),{"horizon":sg.horizon,"epsilon":str(sg.epsilon)},"parameters")
    rewards=_permute(surface["legitimate_rewards"],render_seed,domain,"legitimate_rewards")
    ordering["legitimate_rewards"]=rewards
    for row in rewards: add("LegitimateRewardClause",("legitimate_rewards",),row,"reward")
    add("ProtocolClause",("controller_information_protocol","adversary_information_protocol","move_timing"),{"version":PROTOCOL_VERSION},"protocol")
    if task_contract=="enforceability-classification-v1":
        objective="Can the controller keep the worst-case probability of entering failure before recovery within the horizon at or below epsilon?"
        answer='Answer with exactly one JSON object: {"status":"WINNING"} or {"status":"LOSING"}.'
    elif task_contract=="failure-value-v1":
        objective="What is the exact minimax probability of entering failure before recovery within the horizon?"
        answer='Answer with one JSON object using a reduced rational string, for example {"failure_probability":"1/3"}.'
    else:
        add("RestorationContextClause",("task_payload",),{"candidates":deep_thaw(task_payload.candidates)},"restoration-context")
        objective="Which candidate restorations have minimum cost among those that keep the stated failure probability at or below epsilon? Include every tie."
        answer='Answer with one JSON object, for example {"restorations":["option-2","option-4"]}.'
    add("TaskObjectiveClause",("task_objective",),{"text":objective},"objective"); add("AnswerFormatClause",("answer_format",),{"text":answer},"answer-format")
    return RenderPlan(domain,task_contract,render_seed,sm,cm,am,om,surface,tuple(clauses),ordering,{x.clause_type:x.template_id for x in clauses},PROTOCOL_VERSION,
                      {"restoration_context": deep_thaw(task_payload.candidates) if task_payload else None})


def validate_plan(plan: RenderPlan, source_game: Game | None = None) -> None:
    if [x.output_position for x in plan.clauses] != list(range(len(plan.clauses))): raise ValueError("clause positions")
    if any(realize_clause(x.semantic_payload,x.template_id,plan.domain)!=x.text for x in plan.clauses): raise ValueError("stale clause text or payload")
    surface=reconstruct_surface_game_from_clauses(plan)
    if semantic_signature(surface)!=semantic_signature(plan.surface_game): raise ValueError("surface reconstruction mismatch")
    if source_game is not None and semantic_signature(reconstruct_game_from_clauses(plan))!=semantic_signature(source_game): raise ValueError("formal reconstruction mismatch")
    required={"states","initial_distribution","controller_actions","adversary_actions","observations","observation_map","transitions","failure_states","recovery_states","horizon","epsilon","action_availability","controller_information_protocol","adversary_information_protocol","move_timing","task_objective","answer_format"}
    covered={x for c in plan.clauses for x in c.formal_source_fields}
    if not required<=covered: raise ValueError("clause coverage incomplete")
    transitions=[x for x in plan.clauses if x.clause_type=="TransitionClause"]
    if len(transitions)!=len(surface.transitions): raise ValueError("transition coverage")
    scan_direct_leakage(plan)


def reconstruct_surface_game_from_clauses(plan: RenderPlan) -> Game:
    by={}; many={}
    for c in plan.clauses: many.setdefault(c.clause_type,[]).append(deep_thaw(c.semantic_payload))
    for k,v in many.items():
        if len(v)==1: by[k]=v[0]
    raw={"schema_version":"stage1.v2","states":by["StateDeclarationClause"]["items"],"controller_actions":by["ActionDeclarationClause"]["items"],
      "adversary_actions":by["AdversaryActionDeclarationClause"]["items"],"observations":by["ObservationDeclarationClause"]["items"],
      "initial_distribution":by["InitialDistributionClause"]["entries"],"observation_map":{s:x["observation"] for x in many["ObservationAliasClause"] for s in x["states"]},
      "transitions":many["TransitionClause"],"failure_states":by["TerminalClause"]["failure_states"],"recovery_states":by["TerminalClause"]["recovery_states"],
      "horizon":by["ParameterClause"]["horizon"],"epsilon":by["ParameterClause"]["epsilon"],"action_availability":{x["action"]:x["rounds"] for x in many["ActionAvailabilityClause"]},
      "legitimate_rewards":many.get("LegitimateRewardClause",[]),"display_labels":{}}
    return Game.from_dict(raw)


def reconstruct_game_from_clauses(plan: RenderPlan) -> Game:
    surface=reconstruct_surface_game_from_clauses(plan); raw=surface.to_dict()
    maps=[deep_thaw(plan.state_map),deep_thaw(plan.controller_action_map),deep_thaw(plan.adversary_action_map),deep_thaw(plan.observation_map)]
    si,ci,ai,oi=({v:k for k,v in x.items()} for x in maps)
    raw["states"]=[si[x] for x in raw["states"]]; raw["controller_actions"]=[ci[x] for x in raw["controller_actions"]]; raw["adversary_actions"]=[ai[x] for x in raw["adversary_actions"]]; raw["observations"]=[oi[x] for x in raw["observations"]]
    raw["initial_distribution"]=[{"state":si[x["state"]],"probability":x["probability"]} for x in raw["initial_distribution"]]
    raw["observation_map"]={si[s]:oi[o] for s,o in raw["observation_map"].items()}
    raw["transitions"]=[{"state":si[x["state"]],"controller_action":ci[x["controller_action"]],"adversary_action":ai[x["adversary_action"]],"outcomes":[{"state":si[y["state"]],"probability":y["probability"]} for y in x["outcomes"]]} for x in raw["transitions"]]
    raw["failure_states"]=[si[x] for x in raw["failure_states"]]; raw["recovery_states"]=[si[x] for x in raw["recovery_states"]]
    raw["action_availability"]={ci[a]:v for a,v in raw["action_availability"].items()}; raw["legitimate_rewards"]=[{"state":si[x["state"]],"controller_action":ci[x["controller_action"]],"reward":x["reward"]} for x in raw["legitimate_rewards"]]
    return Game.from_dict(raw)


def prompt_from_plan(plan: RenderPlan) -> str: return "\n\n".join(x.text for x in plan.clauses)+"\n"


def render_case(game: Game, spec: RendererSpec, render_seed: str, domain: str, variant_index: int=0, task_contract: str="enforceability-classification-v1", task_payload=None) -> RenderedCase:
    plan=build_render_plan(game,spec,render_seed,domain,task_contract,task_payload); validate_plan(plan,game); prompt=prompt_from_plan(plan)
    opaque=hashlib.sha256(f"case|{plan.fingerprint}".encode()).hexdigest()[:24]
    return RenderedCase(opaque,spec.fingerprint,plan.fingerprint,domain,variant_index,task_contract,prompt,hashlib.sha256(prompt.encode()).hexdigest())


def to_model_input(case: RenderedCase) -> dict[str,str]: return {"prompt":case.prompt_text}


PROVENANCE=("oracle","optimal policy","correct answer","game_id","candidate_key","generator_version","oracle_version","mechanism_id","stage 4","stage-4")
def scan_direct_leakage(plan: RenderPlan) -> None:
    for c in plan.clauses:
        low=c.text.lower()
        if any(x in low for x in PROVENANCE): raise ValueError(f"provenance leakage in {c.clause_type}")
        if re.search(r"\b(winning|losing)\b",low) and not (plan.task_contract=="enforceability-classification-v1" and c.clause_type=="AnswerFormatClause"):
            raise ValueError(f"answer leakage in {c.clause_type}")


def representation_features(case: RenderedCase, plan: RenderPlan) -> dict[str,Any]:
    text=case.prompt_text; ids=[*plan.state_map.values(),*plan.controller_action_map.values(),*plan.adversary_action_map.values(),*plan.observation_map.values()]
    def bin_(n): return f"{(n//50)*50}-{(n//50)*50+49}"
    return {"feature_classes":{"semantic":"SEMANTIC","representational":"REPRESENTATIONAL","provenance":"PROVENANCE","answer_direct":"ANSWER_DIRECT"},
      "representational":{"domain":case.domain,"variant_index":case.variant_index,"template_signature":fingerprint([x.template_id for x in plan.clauses]),"section_order_signature":fingerprint([x.clause_type for x in plan.clauses]),
       "identifier_length_signature":fingerprint([len(x) for x in ids]),"identifier_length_bin":bin_(sum(map(len,ids))),"identifier_prefix_pattern":sorted({x.rsplit(" ",1)[0] for x in ids}),
       "character_count_bin":bin_(len(text)),"word_count_bin":bin_(len(text.split())),"sentence_count_bin":bin_(text.count(".")),"punctuation_count_bin":bin_(len(re.findall(r"[^\w\s]",text))),"numeric_token_count_bin":bin_(len(re.findall(r"\b\d+(?:/\d+)?\b",text)))},
      "semantic":{"state_count":len(plan.state_map),"controller_action_count":len(plan.controller_action_map),"adversary_action_count":len(plan.adversary_action_map),"observation_count":len(plan.observation_map),"transition_count":sum(x.clause_type=="TransitionClause" for x in plan.clauses),"horizon":deep_thaw(plan.surface_game)["horizon"]}}


def assign_primary_domain(game_id: str, renderer_spec: RendererSpec, assignment_salt: str) -> tuple[str,int]:
    digest=int(hashlib.sha256(f"{renderer_spec.fingerprint}|{game_id}|{assignment_salt}".encode()).hexdigest(),16)
    return renderer_spec.domains[digest%len(renderer_spec.domains)], (digest//len(renderer_spec.domains))%renderer_spec.variants_per_game
