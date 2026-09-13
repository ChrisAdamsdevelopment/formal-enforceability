"""Stage-5 deterministic, answer-blind rendering API."""
from .core import (DOMAINS, PROTOCOL_TEXT, RenderCorpusSpec, RenderPlan, RenderedCase,
                   RendererSpec, audit_clauses, assign_domain, build_freeze,
                   reconstruct_game, render, scan_prompt, verify_freeze)

__all__ = ["DOMAINS", "PROTOCOL_TEXT", "RenderCorpusSpec", "RenderPlan", "RenderedCase",
           "RendererSpec", "audit_clauses", "assign_domain", "build_freeze",
           "reconstruct_game", "render", "scan_prompt", "verify_freeze"]
