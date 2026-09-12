"""Canonical A--H fixtures and a strict compact builder."""
from fractions import Fraction
from itertools import product
from enforceability.schema import Game,SCHEMA_VERSION

def make_game(*,states,initial,ca,aa=("WAIT",),obs_map,transitions,failure=("FAIL",),recovery=(),horizon=1,epsilon="0",availability=None,rewards=None,labels=None):
    # ``transitions`` values are a state or {state: exact weight}.
    rows=[]
    for s,c,a in product(states,ca,aa):
        value=transitions.get((s,c,a),s); dist={value:1} if isinstance(value,str) else value
        rows.append({"state":s,"controller_action":c,"adversary_action":a,"outcomes":[{"state":n,"probability":str(p)} for n,p in dist.items()]})
    mass=Fraction(1,len(initial))
    raw={"schema_version":SCHEMA_VERSION,"states":list(states),"initial_distribution":[{"state":s,"probability":str(mass)} for s in initial],
      "controller_actions":list(ca),"adversary_actions":list(aa),"observations":sorted(set(obs_map.values())),"observation_map":obs_map,
      "transitions":rows,"failure_states":list(failure),"recovery_states":list(recovery),"horizon":horizon,"epsilon":epsilon,
      "action_availability":availability or {a:list(range(horizon)) for a in ca},
      "legitimate_rewards":[{"state":s,"controller_action":a,"reward":str(v)} for (s,a),v in (rewards or {}).items()],"display_labels":labels or {}}
    return Game.from_dict(raw)

def conflicting(distinguish=False,freeze=False):
    states=("s1","s2","SAFE","FAIL"); ca=("LEFT","RIGHT")+(("FREEZE",) if freeze else ())
    t={("s1","LEFT","WAIT"):"SAFE",("s1","RIGHT","WAIT"):"FAIL",("s2","LEFT","WAIT"):"FAIL",("s2","RIGHT","WAIT"):"SAFE"}
    if freeze:t.update({("s1","FREEZE","WAIT"):"SAFE",("s2","FREEZE","WAIT"):"SAFE"})
    return make_game(states=states,initial=("s1","s2"),ca=ca,obs_map={"s1":"one" if distinguish else "same","s2":"two" if distinguish else "same","SAFE":"safe","FAIL":"fail"},transitions=t)

def authority_nullity():
    states=("s","SAFE","FAIL"); ca=("LEFT","RIGHT"); aa=("BLOCK_LEFT","BLOCK_RIGHT")
    t={("s","LEFT","BLOCK_LEFT"):"FAIL",("s","LEFT","BLOCK_RIGHT"):"SAFE",("s","RIGHT","BLOCK_LEFT"):"SAFE",("s","RIGHT","BLOCK_RIGHT"):"FAIL"}
    return make_game(states=states,initial=("s",),ca=ca,aa=aa,obs_map={x:x for x in states},transitions=t)

def probe():
    states=("s1","s2","p1","p2","SAFE","FAIL"); ca=("PROBE","LEFT","RIGHT")
    t={("s1","PROBE","WAIT"):"p1",("s2","PROBE","WAIT"):"p2",("p1","LEFT","WAIT"):"SAFE",("p1","RIGHT","WAIT"):"FAIL",("p2","RIGHT","WAIT"):"SAFE",("p2","LEFT","WAIT"):"FAIL"}
    availability={"PROBE":[0],"LEFT":[1],"RIGHT":[1]}
    return make_game(states=states,initial=("s1","s2"),ca=ca,obs_map={"s1":"same","s2":"same","p1":"one","p2":"two","SAFE":"safe","FAIL":"fail"},transitions=t,horizon=2,availability=availability)

def irrelevant_ambiguity():
    states=("s1","s2","SAFE","FAIL"); ca=("HOLD","MOVE"); t={(s,"HOLD","WAIT"):"SAFE" for s in ("s1","s2")};t.update({(s,"MOVE","WAIT"):"FAIL" for s in ("s1","s2")})
    return make_game(states=states,initial=("s1","s2"),ca=ca,obs_map={"s1":"same","s2":"same","SAFE":"safe","FAIL":"fail"},transitions=t)

def recovery():
    states=("start","danger","RECOVERED","FAIL");ca=("RECOVER","DELAY");t={("start","RECOVER","WAIT"):"RECOVERED",("start","DELAY","WAIT"):"danger",("danger","RECOVER","WAIT"):"FAIL",("danger","DELAY","WAIT"):"FAIL"}
    return make_game(states=states,initial=("start",),ca=ca,obs_map={x:x for x in states},transitions=t,recovery=("RECOVERED",),horizon=2)

def finite_horizon(horizon):
    states=("start","doomed","FAIL");ca=("WAIT",);t={("start","WAIT","WAIT"):"doomed",("doomed","WAIT","WAIT"):"FAIL"}
    return make_game(states=states,initial=("start",),ca=ca,obs_map={x:x for x in states},transitions=t,horizon=horizon)

def capability_removal():
    states=("s","SAFE","FAIL");ca=("ACT",);aa=("ALLOW","BLOCK");t={("s","ACT","ALLOW"):"SAFE",("s","ACT","BLOCK"):"FAIL"}
    return make_game(states=states,initial=("s",),ca=ca,aa=aa,obs_map={x:x for x in states},transitions=t)

def timing(early):
    states=("urgent","SAFE","FAIL");ca=("WAIT","INTERVENE");t={("urgent","WAIT","WAIT"):"FAIL",("urgent","INTERVENE","WAIT"):"SAFE"}
    availability={"WAIT":[0,1],"INTERVENE":[0,1] if early else [1]}
    # Late case has horizon 2; the only round-0 action fails before intervention.
    return make_game(states=states,initial=("urgent",),ca=ca,obs_map={x:x for x in states},transitions=t,horizon=2,availability=availability)

def restoration_cost_game():
    states=("s","SAFE","FAIL");ca=("UNSAFE","MID_A","LOW","MID_B");t={("s","UNSAFE","WAIT"):"FAIL",("s","MID_A","WAIT"):"SAFE",("s","LOW","WAIT"):"SAFE",("s","MID_B","WAIT"):"SAFE"}
    rewards={("s","UNSAFE"):10,("s","MID_A"):7,("s","LOW"):5,("s","MID_B"):7}
    availability={"UNSAFE":[0],"MID_A":[],"LOW":[],"MID_B":[]}
    return make_game(states=states,initial=("s",),ca=ca,obs_map={x:x for x in states},transitions=t,availability=availability,rewards=rewards)
