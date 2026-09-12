"""Controller-visible policies and exact oracle results."""
from __future__ import annotations
from dataclasses import dataclass
from enum import Enum
from fractions import Fraction
import json

@dataclass(frozen=True,slots=True)
class ControllerInformationHistory:
    observations: tuple[str,...]
    previous_actions: tuple[str,...]=()
    def __post_init__(self):
        if len(self.observations)!=len(self.previous_actions)+1: raise ValueError("history must end in an observation")
    def after(self,action,observation): return type(self)(self.observations+(observation,),self.previous_actions+(action,))
    def to_controller_json(self):
        return json.dumps({"observations":list(self.observations),"previous_actions":list(self.previous_actions)},sort_keys=True,separators=(",",":"))

class SolveStatus(str,Enum): WINNING="WINNING"; LOSING="LOSING"

@dataclass(frozen=True,slots=True)
class PolicyEntry:
    history: ControllerInformationHistory
    action: str

@dataclass(frozen=True,slots=True)
class WeightedPolicy:
    probability: Fraction
    entries: tuple[PolicyEntry,...]

@dataclass(frozen=True,slots=True)
class OracleResult:
    status: SolveStatus
    failure_probability: Fraction
    threshold_satisfied: bool
    witness: tuple[WeightedPolicy,...]|None
    explored_profiles: int
    schema_version: str
    oracle_version: str="normal-form-reference.v2"
    @property
    def explored_nodes(self): return self.explored_profiles
    def to_dict(self):
        rat=lambda x: str(x.numerator) if x.denominator==1 else f"{x.numerator}/{x.denominator}"
        return {"status":self.status.value,"failure_probability":rat(self.failure_probability),"threshold_satisfied":self.threshold_satisfied,
          "witness":None if self.witness is None else [{"probability":rat(w.probability),"policy":[{"history":{"observations":list(e.history.observations),"previous_actions":list(e.history.previous_actions)},"action":e.action} for e in w.entries]} for w in self.witness],
          "explored_profiles":self.explored_profiles,"schema_version":self.schema_version,"oracle_version":self.oracle_version}
