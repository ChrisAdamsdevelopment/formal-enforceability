"""Reproducible development-batch command line entry point."""
import argparse
from collections import Counter
from dataclasses import asdict, replace
from pathlib import Path

from .core import FAMILIES, GENERATOR_VERSION, GenerationRejected, GeneratorConfig, build_manifest, canonical_json, generate


def main(argv=None):
    parser=argparse.ArgumentParser()
    parser.add_argument("--family",choices=FAMILIES,required=True); parser.add_argument("--seed-start",type=int,default=0)
    parser.add_argument("--count",type=int,required=True); parser.add_argument("--output",type=Path,required=True)
    args=parser.parse_args(argv)
    if args.count < 0: parser.error("--count must be nonnegative")
    base=GeneratorConfig(family=args.family,seed=args.seed_start)
    if args.count > base.limits.max_generated_candidates: parser.error("count exceeds max_generated_candidates")
    args.output.mkdir(parents=True,exist_ok=True); counts=Counter()
    for seed in range(args.seed_start,args.seed_start+args.count):
        config=replace(base,seed=seed); generated=generate(config); path=args.output/f"{seed:08d}.json"
        if path.exists(): raise FileExistsError(f"refusing to overwrite {path}")
        if isinstance(generated,GenerationRejected): payload={"rejection":asdict(generated)}; counts["rejected"]+=1
        else: payload=build_manifest(generated); counts[payload["oracle"]["status"]]+=1
        path.write_text(canonical_json(payload)+"\n",encoding="utf-8")
    summary={"generator_version":GENERATOR_VERSION,"family":args.family,"seed_start":args.seed_start,"requested":args.count,"counts":dict(sorted(counts.items()))}
    summary_path=args.output/"summary.json"
    if summary_path.exists(): raise FileExistsError(f"refusing to overwrite {summary_path}")
    summary_path.write_text(canonical_json(summary)+"\n",encoding="utf-8"); print(canonical_json(summary))


if __name__ == "__main__": main()
