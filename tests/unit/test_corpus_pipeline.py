import json
from dataclasses import replace

import pytest

from enforceability.corpus import CorpusSpec, build_corpus, verify_corpus


def spec(): return CorpusSpec.load("corpus_specs/regression-v1.json")


def test_spec_is_strict_and_fingerprint_sensitive():
    s=spec(); raw=s.to_dict(); raw["unexpected"]=1
    with pytest.raises(ValueError): CorpusSpec.from_dict(raw)
    assert replace(s,seed_ranges=((0,3),)+s.seed_ranges[1:]).fingerprint != s.fingerprint
    assert replace(s,generator_parameter_sets=({**s.generator_parameter_sets[0],"common_action":True},)+s.generator_parameter_sets[1:]).fingerprint != s.fingerprint
    assert replace(s,retention_policy={**s.retention_policy,"exact_duplicates":"retain_all"}).fingerprint != s.fingerprint
    with pytest.raises(ValueError): replace(s,isomorphism_version="future")


def test_build_is_reproducible_and_frozen_corpus_verifies(tmp_path):
    one=tmp_path/"one"; two=tmp_path/"two"; a=build_corpus(spec(),one); b=build_corpus(spec(),two)
    assert a==b
    assert (one/"candidate-ledger.json").read_bytes()==(two/"candidate-ledger.json").read_bytes()
    assert all(verify_corpus(spec(),"artifacts/regression-corpus-v1").values())
    ledger=json.loads((one/"candidate-ledger.json").read_text())
    assert len(ledger)==12 and all("reason" in row and "generator_config" in row for row in ledger)
