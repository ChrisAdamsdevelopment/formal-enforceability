"""Deterministic Stage-3 formal corpus construction and audit."""
from .core import (
    CORPUS_SPEC_VERSION, ISOMORPHISM_VERSION, RETENTION_VERSION,
    CandidateState, CorpusBuildError, CorpusSpec, DuplicateClassification, IsomorphismLimits, IsomorphismResult,
    audit_matched_pairs, build_corpus, canonicalize_isomorphism, neutralized_game, verify_corpus,
)

__all__ = ["CORPUS_SPEC_VERSION", "ISOMORPHISM_VERSION", "RETENTION_VERSION",
           "CandidateState", "CorpusBuildError", "CorpusSpec", "DuplicateClassification", "IsomorphismLimits", "IsomorphismResult",
           "audit_matched_pairs", "build_corpus", "canonicalize_isomorphism", "neutralized_game", "verify_corpus"]
