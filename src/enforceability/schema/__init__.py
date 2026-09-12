"""Strict versioned schema for finite probabilistic games."""
from __future__ import annotations

from dataclasses import dataclass
from fractions import Fraction
import json
from itertools import product
from typing import Any, NewType

StateId = NewType("StateId", str)
ControllerActionId = NewType("ControllerActionId", str)
AdversaryActionId = NewType("AdversaryActionId", str)
ObservationId = NewType("ObservationId", str)
SCHEMA_VERSION = "stage1.v2"


class InvalidGame(ValueError): pass
class UnsupportedGameClass(Exception): pass


def fraction(value: Any, field: str) -> Fraction:
    """Parse an exact JSON number. Floats are rejected to avoid hidden rounding."""
    if isinstance(value, bool) or isinstance(value, float):
        raise InvalidGame(f"{field} must be an integer or rational string")
    try:
        result = Fraction(value)
    except (ValueError, TypeError, ZeroDivisionError) as exc:
        raise InvalidGame(f"invalid rational in {field}") from exc
    return result


def rational_json(value: Fraction) -> str:
    return str(value.numerator) if value.denominator == 1 else f"{value.numerator}/{value.denominator}"


def _ids(value: Any, field: str, nonempty: bool = True) -> tuple[str, ...]:
    if not isinstance(value, list) or (nonempty and not value):
        raise InvalidGame(f"{field} must be a{' nonempty' if nonempty else ''} list")
    if any(not isinstance(x, str) or not x for x in value) or len(set(value)) != len(value):
        raise InvalidGame(f"{field} must contain unique nonempty strings")
    return tuple(value)


@dataclass(frozen=True, slots=True)
class Game:
    states: tuple[str, ...]
    initial_distribution: dict[str, Fraction]
    controller_actions: tuple[str, ...]
    adversary_actions: tuple[str, ...]
    observations: tuple[str, ...]
    observation_map: dict[str, str]
    transitions: dict[tuple[str, str, str], tuple[tuple[str, Fraction], ...]]
    failure_states: frozenset[str]
    recovery_states: frozenset[str]
    horizon: int
    epsilon: Fraction
    action_availability: dict[str, frozenset[int]]
    legitimate_rewards: dict[tuple[str, str], Fraction]
    display_labels: dict[str, str]
    schema_version: str = SCHEMA_VERSION

    @property
    def initial_states(self) -> tuple[str, ...]:
        return tuple(s for s in self.states if self.initial_distribution.get(s, 0) > 0)

    def available_actions(self, round_index: int) -> tuple[str, ...]:
        return tuple(a for a in self.controller_actions if round_index in self.action_availability[a])

    @classmethod
    def from_dict(cls, raw: dict[str, Any]) -> "Game":
        if not isinstance(raw, dict): raise InvalidGame("game must be an object")
        required={"schema_version","states","initial_distribution","controller_actions","adversary_actions",
                  "observations","observation_map","transitions","failure_states","recovery_states","horizon","epsilon"}
        optional={"action_availability","legitimate_rewards","display_labels"}
        if required-set(raw) or set(raw)-required-optional:
            raise InvalidGame(f"schema fields mismatch; missing={sorted(required-set(raw))}, extra={sorted(set(raw)-required-optional)}")
        if raw["schema_version"] != SCHEMA_VERSION: raise UnsupportedGameClass(f"only {SCHEMA_VERSION!r} is supported")
        states=_ids(raw["states"],"states"); ca=_ids(raw["controller_actions"],"controller_actions"); aa=_ids(raw["adversary_actions"],"adversary_actions")
        observations=_ids(raw["observations"],"observations"); horizon=raw["horizon"]
        if type(horizon) is not int or horizon < 0: raise InvalidGame("horizon must be a nonnegative integer")
        epsilon=fraction(raw["epsilon"],"epsilon")
        if not 0 <= epsilon <= 1: raise InvalidGame("epsilon must be in [0,1]")
        initial=_distribution(raw["initial_distribution"], states, "initial_distribution")
        obs=raw["observation_map"]
        if not isinstance(obs,dict) or set(obs)!=set(states) or any(x not in observations for x in obs.values()):
            raise InvalidGame("observation_map must map every state exactly once to a declared observation")
        failure=_subset(raw["failure_states"],states,"failure_states"); recovery=_subset(raw["recovery_states"],states,"recovery_states")
        if failure & recovery: raise InvalidGame("failure and recovery states must be disjoint")
        transitions={}
        if not isinstance(raw["transitions"],list): raise InvalidGame("transitions must be a list")
        for row in raw["transitions"]:
            if not isinstance(row,dict) or set(row)!={"state","controller_action","adversary_action","outcomes"}: raise InvalidGame("invalid transition row")
            key=(row["state"],row["controller_action"],row["adversary_action"])
            if key[0] not in states or key[1] not in ca or key[2] not in aa: raise InvalidGame("transition references unknown identifier")
            if key in transitions: raise InvalidGame("duplicate transition")
            dist=_distribution(row["outcomes"],states,"transition outcomes")
            transitions[key]=tuple((s,dist[s]) for s in states if dist.get(s,0)>0)
        expected=set(product(states,ca,aa))
        if set(transitions)!=expected: raise InvalidGame("transition function must be total")
        availability_raw=raw.get("action_availability",{a:list(range(horizon)) for a in ca})
        if not isinstance(availability_raw,dict) or set(availability_raw)!=set(ca): raise InvalidGame("availability must specify every controller action")
        availability={a:frozenset(_rounds(v,horizon,a)) for a,v in availability_raw.items()}
        if horizon and any(not any(t in availability[a] for a in ca) for t in range(horizon)): raise InvalidGame("at least one controller action must be available each round")
        rewards={(s,a):Fraction(0) for s in states for a in ca}
        for row in raw.get("legitimate_rewards",[]):
            if not isinstance(row,dict) or set(row)!={"state","controller_action","reward"}: raise InvalidGame("invalid legitimate reward")
            key=(row["state"],row["controller_action"])
            if key not in rewards: raise InvalidGame("reward references unknown identifier")
            rewards[key]=fraction(row["reward"],"reward")
        labels=raw.get("display_labels",{})
        if not isinstance(labels,dict) or any(not isinstance(k,str) or not isinstance(v,str) for k,v in labels.items()): raise InvalidGame("display_labels must map strings to strings")
        return cls(states,initial,ca,aa,observations,dict(obs),transitions,failure,recovery,horizon,epsilon,availability,rewards,dict(labels))

    def to_dict(self) -> dict[str,Any]:
        return {"schema_version":self.schema_version,"states":list(self.states),
          # Preserve explicitly supplied zero-mass entries.  Their presence is
          # part of the validated representation, even though it has no effect
          # on the induced probability measure.
          "initial_distribution":[{"state":s,"probability":rational_json(self.initial_distribution[s])} for s in self.states if s in self.initial_distribution],
          "controller_actions":list(self.controller_actions),"adversary_actions":list(self.adversary_actions),"observations":list(self.observations),
          "observation_map":{s:self.observation_map[s] for s in self.states},
          "transitions":[{"state":s,"controller_action":c,"adversary_action":a,"outcomes":[{"state":n,"probability":rational_json(p)} for n,p in self.transitions[(s,c,a)]]} for s,c,a in product(self.states,self.controller_actions,self.adversary_actions)],
          "failure_states":sorted(self.failure_states),"recovery_states":sorted(self.recovery_states),"horizon":self.horizon,"epsilon":rational_json(self.epsilon),
          "action_availability":{a:sorted(self.action_availability[a]) for a in self.controller_actions},
          "legitimate_rewards":[{"state":s,"controller_action":a,"reward":rational_json(self.legitimate_rewards[(s,a)])} for s in self.states for a in self.controller_actions if self.legitimate_rewards[(s,a)]],
          "display_labels":dict(sorted(self.display_labels.items()))}

    def to_json(self)->str: return json.dumps(self.to_dict(),sort_keys=True,separators=(",",":"))
    @classmethod
    def from_json(cls,value:str)->"Game":
        try: return cls.from_dict(json.loads(value))
        except (json.JSONDecodeError,TypeError) as exc: raise InvalidGame("invalid JSON") from exc


def _distribution(rows:Any,states:tuple[str,...],field:str)->dict[str,Fraction]:
    if not isinstance(rows,list) or not rows: raise InvalidGame(f"{field} must be nonempty")
    result={}
    for row in rows:
        if not isinstance(row,dict) or set(row)!={"state","probability"} or row["state"] not in states or row["state"] in result: raise InvalidGame(f"invalid {field}")
        p=fraction(row["probability"],field)
        if p < 0: raise InvalidGame(f"{field} probabilities must be nonnegative")
        result[row["state"]]=p
    if sum(result.values(),Fraction(0)) != 1: raise InvalidGame(f"{field} probabilities must sum exactly to 1")
    return result

def _subset(value,states,field):
    values=_ids(value,field,False)
    if not set(values)<=set(states): raise InvalidGame(f"{field} contains unknown state")
    return frozenset(values)

def _rounds(value,horizon,action):
    if not isinstance(value,list) or any(type(x) is not int or x<0 or x>=horizon for x in value) or len(set(value))!=len(value): raise InvalidGame(f"invalid availability for {action}")
    return value
