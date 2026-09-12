import argparse, json
from .core import CorpusSpec, build_corpus, verify_corpus

def main():
    p=argparse.ArgumentParser(prog="python -m enforceability.corpus"); sub=p.add_subparsers(dest="command",required=True)
    for name in ("build","verify"):
        q=sub.add_parser(name); q.add_argument("--spec",required=True); q.add_argument("--output" if name=="build" else "--corpus",required=True)
    a=p.parse_args(); spec=CorpusSpec.load(a.spec)
    result=build_corpus(spec,a.output) if a.command=="build" else verify_corpus(spec,a.corpus)
    print(json.dumps(result,sort_keys=True,indent=2))
if __name__=="__main__": main()
