"""Independent epsilon-zero classifier for tiny games.

Unlike the normal-form matrix oracle, this directly backtracks over controller
history assignments while universally expanding positive-probability outcomes.
It shares only the validated Game/CIH semantics, not profile or matrix code.
"""
from enforceability.schema import Game,UnsupportedGameClass
from enforceability.types import ControllerInformationHistory as CIH,SolveStatus

def classify_tiny(game:Game)->SolveStatus:
    if game.epsilon != 0: raise UnsupportedGameClass("tiny cross-check supports epsilon zero only")
    frontier=tuple((s,CIH((game.observation_map[s],)),0) for s,p in game.initial_distribution.items() if p)
    def search(items,policy):
        if any(s in game.failure_states for s,_,_ in items):return False
        active=[x for x in items if x[0] not in game.recovery_states and x[2]<game.horizon]
        if not active:return True
        history=active[0][1]; same=[x for x in active if x[1]==history]; rest=[x for x in active if x[1]!=history]
        choices=(policy[history],) if history in policy else game.available_actions(len(history.previous_actions))
        for action in choices:
            new_policy=dict(policy);new_policy[history]=action; successors=[];bad=False
            for state,h,t in same:
                for adversary in game.adversary_actions:
                    for nxt,p in game.transitions[(state,action,adversary)]:
                        if not p:continue
                        if nxt in game.failure_states:bad=True;break
                        successors.append((nxt,h.after(action,game.observation_map[nxt]),t+1))
                    if bad:break
                if bad:break
            if not bad and search(tuple(rest+successors),new_policy):return True
        return False
    return SolveStatus.WINNING if search(frontier,{}) else SolveStatus.LOSING
