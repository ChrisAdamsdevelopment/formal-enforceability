"""Command line verification for the Stage-4 formal evaluation freeze."""
import argparse
import json
from pathlib import Path

from enforceability.stage4 import MechanismCoverageSpec, audit_corpus_overlap, build_benchmark_freeze


def main() -> None:
    parser = argparse.ArgumentParser(prog="python -m enforceability.benchmark")
    sub = parser.add_subparsers(dest="command", required=True)
    audit = sub.add_parser("audit-overlap")
    verify = sub.add_parser("verify-formal-freeze")
    for command in (audit, verify):
        command.add_argument("--development", required=True)
        command.add_argument("--evaluation", required=True)
    verify.add_argument("--mechanisms", required=True)
    verify.add_argument("--freeze", required=True)
    args = parser.parse_args()
    if args.command == "audit-overlap":
        result = audit_corpus_overlap(args.development, args.evaluation)
    else:
        expected = json.loads(Path(args.freeze).read_text())
        actual = build_benchmark_freeze(args.development, args.evaluation, MechanismCoverageSpec.load(args.mechanisms))
        result = {"verified": expected == actual, "benchmark_freeze_fingerprint": actual["benchmark_freeze_fingerprint"]}
        if not result["verified"]:
            raise SystemExit("formal freeze mismatch")
    print(json.dumps(result, sort_keys=True, indent=2))


if __name__ == "__main__":
    main()
