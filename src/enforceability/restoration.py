"""Finite structural transformations and endogenous legitimate-utility costs."""
from __future__ import annotations
from dataclasses import dataclass, replace
from fractions import Fraction

from .oracle import enumerate_adversary_policies, enumerate_controller_policies, solve, solve_matrix
from .schema import Game, InvalidGame, fraction
from .types import ControllerInformationHistory as CIH, OracleResult

@dataclass(frozen=True,slots=True)
class Restoration:
    name: str
    remove_adversary_actions: frozenset[str]=frozenset()
    remove_controller_actions: frozenset[str]=frozenset()
    observation_overrides: tuple[tuple[str,str],...]=()
    availability_overrides: tuple[tuple[str,tuple[int,...]],...]=()

@dataclass(frozen=True,slots=True)
class RestorationEvaluation:
    restoration: Restoration
    game_result: OracleResult
    legitimate_utility: Fraction
    cost: Fraction

@dataclass(frozen=True,slots=True)
class RestorationResult:
    unrestricted_utility: Fraction
    minimum_cost: Fraction|None
    optimal: tuple[RestorationEvaluation,...]
    evaluations: tuple[RestorationEvaluation,...]

def apply_restoration(game:Game,r:Restoration)->Game:
    aa=tuple(a for a in game.adversary_actions if a not in r.remove_adversary_actions)
    ca=tuple(a for a in game.controller_actions if a not in r.remove_controller_actions)
    if not aa or not ca: raise InvalidGame("a restoration may not remove every action")
    if not r.remove_adversary_actions<=set(game.adversary_actions) or not r.remove_controller_actions<=set(game.controller_actions): raise InvalidGame("restoration removes an unknown action")
    obs=dict(game.observation_map)
    overridden_states = [state for state, _ in r.observation_overrides]
    if len(overridden_states) != len(set(overridden_states)):
        raise InvalidGame("observation restoration contains duplicate state overrides")
    for state,observation in r.observation_overrides:
        if state not in game.states or observation not in game.observations: raise InvalidGame("invalid observation restoration")
        obs[state]=observation
    # Refinement may split an old information class, but it must preserve every
    # distinction the controller already had.  Equivalently, the new partition
    # must refine (never coarsen) the old partition.
    for index, state in enumerate(game.states):
        for other in game.states[index + 1:]:
            if game.observation_map[state] != game.observation_map[other] and obs[state] == obs[other]:
                raise InvalidGame("observation restoration must be a refinement and may not merge distinct classes")
    availability={a:game.action_availability[a] for a in ca}
    for action,rounds in r.availability_overrides:
        if action not in ca or any(type(t) is not int or t<0 or t>=game.horizon for t in rounds): raise InvalidGame("invalid timing restoration")
        availability[action]=frozenset(rounds)
    if game.horizon and any(not any(t in availability[a] for a in ca) for t in range(game.horizon)): raise InvalidGame("restoration leaves a round without controller actions")
    transitions={k:v for k,v in game.transitions.items() if k[1] in ca and k[2] in aa}
    rewards={k:v for k,v in game.legitimate_rewards.items() if k[1] in ca}
    return replace(game,controller_actions=ca,adversary_actions=aa,observation_map=obs,
                   transitions=transitions,action_availability=availability,legitimate_rewards=rewards)

def _profile_utility(game,cp,ap):
    def rec(state,cih,ah,left):
        if state in game.failure_states|game.recovery_states or left==0:return Fraction(0)
        c=cp[cih]; a=ap[ah]; immediate=game.legitimate_rewards[(state,c)]
        return immediate+sum(p*rec(n,cih.after(c,game.observation_map[n]),(ah[0]+(n,),ah[1]+(c,),ah[2]+(a,)),left-1) for n,p in game.transitions[(state,c,a)])
    return sum(p*rec(s,CIH((game.observation_map[s],)),((s,),(),()),game.horizon) for s,p in game.initial_distribution.items())

def legitimate_utility(game:Game)->Fraction:
    """Maximum controller/minimum adversary expected undiscounted declared reward."""
    cps=list(enumerate_controller_policies(game)); aps=list(enumerate_adversary_policies(game))
    negative=[[-_profile_utility(game,c,a) for a in aps] for c in cps]
    value,_=solve_matrix(negative)
    return -value

def optimal_restoration(game:Game,candidates:tuple[Restoration,...],b0=None)->RestorationResult:
    """Evaluate finite candidates; ``b0`` may replace the declared initial belief."""
    if b0 is not None:
        if not hasattr(b0, "items"):
            raise InvalidGame("b0 must be a mapping from state identifiers to exact probabilities")
        belief = {state: fraction(probability, "b0 probability") for state, probability in b0.items()}
        if set(belief) - set(game.states) or any(p < 0 for p in belief.values()) or sum(belief.values(), Fraction(0)) != 1:
            raise InvalidGame("b0 must be an exact distribution over declared states")
        game = replace(game, initial_distribution=belief)
    unrestricted=legitimate_utility(game); evaluations=[]
    for restoration in candidates:
        transformed=apply_restoration(game,restoration); result=solve(transformed); utility=legitimate_utility(transformed)
        evaluations.append(RestorationEvaluation(restoration,result,utility,unrestricted-utility))
    feasible=[e for e in evaluations if e.game_result.threshold_satisfied]
    minimum=min((e.cost for e in feasible),default=None)
    return RestorationResult(unrestricted,minimum,tuple(e for e in feasible if e.cost==minimum),tuple(evaluations))
