"""Exact normal-form oracle for finite probabilistic games.

Pure perfect-recall strategies are enumerated, trajectory probabilities form an
exact rational zero-sum matrix, and a support-enumeration matrix-game solver
finds the controller minimax mixture.
"""
from __future__ import annotations
from fractions import Fraction
from itertools import combinations, product

from enforceability.schema import Game
from enforceability.types import ControllerInformationHistory as CIH, OracleResult, PolicyEntry, SolveStatus, WeightedPolicy

AdversaryHistory=tuple[tuple[str,...],tuple[str,...],tuple[str,...]]

def _controller_histories(game:Game)->tuple[CIH,...]:
    current={(s,CIH((game.observation_map[s],))) for s in game.initial_states}; all_h=[]
    for t in range(game.horizon):
        active={(state,h) for state,h in current if state not in game.failure_states|game.recovery_states}
        histories={h for _,h in active};all_h.extend(sorted(histories,key=lambda h:(h.observations,h.previous_actions)))
        nxt=set()
        for state,h in active:
            for a in game.available_actions(t):
                for adversary in game.adversary_actions:
                    for state2,p in game.transitions[(state,a,adversary)]:
                        if p and state2 not in game.failure_states|game.recovery_states:nxt.add((state2,h.after(a,game.observation_map[state2])))
        current=nxt
    return tuple(dict.fromkeys(all_h))

def enumerate_controller_policies(game:Game):
    histories=_controller_histories(game)
    choices=[game.available_actions(len(h.previous_actions)) for h in histories]
    for actions in product(*choices): yield dict(zip(histories,actions))

def _adversary_histories(game:Game)->tuple[AdversaryHistory,...]:
    current={( (s,),(),() ) for s in game.initial_states}; all_h=[]
    for t in range(game.horizon):
        active={h for h in current if h[0][-1] not in game.failure_states|game.recovery_states}
        all_h.extend(sorted(active))
        nxt=set()
        for states,cs,ads in active:
            for c in game.available_actions(t):
                for a in game.adversary_actions:
                    for state,_ in game.transitions[(states[-1],c,a)]: nxt.add((states+(state,),cs+(c,),ads+(a,)))
        current=nxt
    return tuple(all_h)

def enumerate_adversary_policies(game:Game):
    histories=_adversary_histories(game)
    for actions in product(game.adversary_actions,repeat=len(histories)): yield dict(zip(histories,actions))

def profile_failure(game:Game,cp:dict[CIH,str],ap:dict[AdversaryHistory,str])->Fraction:
    def rec(state,cih,ah,left):
        if state in game.failure_states:return Fraction(1)
        if state in game.recovery_states or left==0:return Fraction(0)
        c=cp[cih]; a=ap[ah]; total=Fraction(0)
        for nxt,p in game.transitions[(state,c,a)]:
            total+=p*rec(nxt,cih.after(c,game.observation_map[nxt]),(ah[0]+(nxt,),ah[1]+(c,),ah[2]+(a,)),left-1)
        return total
    return sum((p*rec(s,CIH((game.observation_map[s],)),((s,),(),()),game.horizon) for s,p in game.initial_distribution.items()),Fraction(0))

def _solve_linear(a:list[list[Fraction]],b:list[Fraction]):
    n=len(a); aug=[row[:]+[b[i]] for i,row in enumerate(a)]
    for col in range(n):
        pivot=next((r for r in range(col,n) if aug[r][col]),None)
        if pivot is None:return None
        aug[col],aug[pivot]=aug[pivot],aug[col]; q=aug[col][col]; aug[col]=[x/q for x in aug[col]]
        for r in range(n):
            if r!=col and aug[r][col]:
                q=aug[r][col]; aug[r]=[x-q*y for x,y in zip(aug[r],aug[col])]
    return [aug[i][-1] for i in range(n)]

def solve_matrix(matrix:list[list[Fraction]])->tuple[Fraction,tuple[Fraction,...]]:
    """Min-row/max-column zero-sum solution by exact equal-size support enumeration."""
    m,n=len(matrix),len(matrix[0]); best=None
    for k in range(1,min(m,n)+1):
      for rows in combinations(range(m),k):
       for cols in combinations(range(n),k):
        # p makes supported columns indifferent: sum p_i M_ij=v, sum p=1.
        eq=[[matrix[rows[i]][cols[j]] for i in range(k)]+[Fraction(-1)] for j in range(k)]
        eq.append([Fraction(1)]*k+[Fraction(0)])
        sol=_solve_linear(eq,[Fraction(0)]*k+[Fraction(1)])
        if sol is None: continue
        p,v=sol[:-1],sol[-1]
        if any(x<0 for x in p):continue
        full=[Fraction(0)]*m
        for i,x in zip(rows,p):full[i]=x
        if any(sum(full[i]*matrix[i][j] for i in range(m))>v for j in range(n)):continue
        # dual q verifies no omitted row can lower v.
        eq2=[[matrix[rows[i]][cols[j]] for j in range(k)]+[Fraction(-1)] for i in range(k)]
        eq2.append([Fraction(1)]*k+[Fraction(0)])
        dual=_solve_linear(eq2,[Fraction(0)]*k+[Fraction(1)])
        if dual is None or any(x<0 for x in dual[:-1]) or any(sum(dual[j]*matrix[i][cols[j]] for j in range(k))<v for i in range(m)):continue
        if best is None or v<best[0]:best=(v,tuple(full))
    if best is None: raise RuntimeError("exact matrix solver failed")
    return best

def solve(game:Game)->OracleResult:
    cps=list(enumerate_controller_policies(game)); aps=list(enumerate_adversary_policies(game))
    matrix=[[profile_failure(game,c,a) for a in aps] for c in cps]
    value,mix=solve_matrix(matrix); ok=value<=game.epsilon
    witness=None
    if ok:
        witness=tuple(WeightedPolicy(p,tuple(PolicyEntry(h,a) for h,a in sorted(cps[i].items(),key=lambda x:(len(x[0].previous_actions),x[0].observations,x[0].previous_actions)))) for i,p in enumerate(mix) if p)
    return OracleResult(SolveStatus.WINNING if ok else SolveStatus.LOSING,value,ok,witness,len(cps)*len(aps),game.schema_version)

def validate_witness(game:Game,witness)->bool:
    if witness is None:return False
    aps=list(enumerate_adversary_policies(game)); total=sum((w.probability for w in witness),Fraction(0))
    if total!=1 or any(w.probability<0 for w in witness):return False
    policies=[{e.history:e.action for e in w.entries} for w in witness]
    try:return max(sum(w.probability*profile_failure(game,p,ap) for w,p in zip(witness,policies)) for ap in aps)<=game.epsilon
    except (KeyError,ValueError):return False
