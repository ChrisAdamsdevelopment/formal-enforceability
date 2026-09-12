import json
from enforceability.generation.__main__ import main


def test_batch_is_reproducible_and_never_overwrites(tmp_path):
    one=tmp_path/"one"; two=tmp_path/"two"
    args=lambda path:["--family","observation-conflict","--seed-start","0","--count","3","--output",str(path)]
    main(args(one)); main(args(two))
    assert [(p.name,p.read_bytes()) for p in sorted(one.iterdir())]==[(p.name,p.read_bytes()) for p in sorted(two.iterdir())]
    summary=json.loads((one/"summary.json").read_text())
    assert sum(summary["counts"].values())==3
    try: main(args(one))
    except FileExistsError: pass
    else: raise AssertionError("batch silently overwrote output")
