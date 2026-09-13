import argparse, json
from .freeze import build_artifacts, verify_freeze

def main():
    parser=argparse.ArgumentParser(); sub=parser.add_subparsers(dest="command",required=True)
    for command in ("build-freeze","verify-freeze"):
        p=sub.add_parser(command); p.add_argument("--artifacts",required=True)
    args=parser.parse_args()
    result=build_artifacts(args.artifacts) if args.command=="build-freeze" else verify_freeze(args.artifacts)
    print(json.dumps(result,sort_keys=True))

if __name__=="__main__": main()
