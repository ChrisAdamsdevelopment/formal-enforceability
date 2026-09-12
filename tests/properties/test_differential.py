"""Generated tiny deterministic games cross-checked with independent DFS."""
from itertools import product
from enforceability import solve
from enforceability.oracle.tiny import classify_tiny
from tests.fixtures import make_game

def generated_games():
    states=("s0","s1","FAIL");ca=("A","B");aa=("X",)
    keys=list(product(("s0","s1"),ca,aa))
    # 3^4 = 81 complete transition patterns, under coarse and fine observations.
    for successors in product(states,repeat=len(keys)):
        transitions=dict(zip(keys,successors))
        for coarse in (True,False):
            obs={"s0":"same" if coarse else "zero","s1":"same" if coarse else "one","FAIL":"fail"}
            yield make_game(states=states,initial=("s0","s1"),ca=ca,aa=aa,obs_map=obs,transitions=transitions,horizon=1)

def test_primary_matches_independent_tiny_solver():
    for game in generated_games():assert solve(game).status is classify_tiny(game)
