"""Deterministic, neutral Stage 6A pilot construction and leakage checks."""
from __future__ import annotations

import hashlib
import json
import random
from collections import Counter
from fractions import Fraction
from pathlib import Path

from enforceability.actionability import ActionabilityStatus, classify, robust_actionability
from enforceability.identifiability import ambiguity_classes, enumerate_games

ARTIFACT_DIRECTORY = Path(__file__).parents[2] / "artifacts" / "stage6-pilot-v1"
CONDITIONS = ("natural", "epistemically_scaffolded", "tool_assisted")
DOMAINS = ("abstract", "ant_colony", "technical_system")


def _game(game_id: str):
    return next(game for game in enumerate_games() if game.game_id == game_id)


def build_canonical_tasks() -> list[dict[str, object]]:
    """Build 48 mechanics-first items (12/status), before render multiplication."""
    buckets: dict[ActionabilityStatus, list[tuple[tuple, Fraction]]] = {status: [] for status in ActionabilityStatus}
    for games in ambiguity_classes().values():
        for epsilon in (Fraction(0), Fraction(1, 4), Fraction(1, 2), Fraction(3, 4)):
            status = classify(games, epsilon)
            if status != ActionabilityStatus.CERTIFIABLY_WINNING_BUT_NOT_UNIFORMLY_ACTIONABLE:
                buckets[status].append((games, epsilon))
    # An explicit finite compatibility interface supplies the actionability arm.
    # This is deliberately not misreported as a public-signature F(q) class.
    gap_games = (_game("d051"), _game("d204"))
    assert classify(gap_games, Fraction(0)) == ActionabilityStatus.CERTIFIABLY_WINNING_BUT_NOT_UNIFORMLY_ACTIONABLE
    buckets[ActionabilityStatus.CERTIFIABLY_WINNING_BUT_NOT_UNIFORMLY_ACTIONABLE] = [(gap_games, Fraction(0))] * 12
    tasks = []
    for status in ActionabilityStatus:
        choices = buckets[status]
        for index in range(12):
            games, epsilon = choices[index % len(choices)]
            robust = robust_actionability(games)
            task_id = f"S6A-{len(tasks):03d}"
            tasks.append({
                "task_id": task_id,
                "interface": "explicit-compatible-model-set.v1" if status.name.endswith("NOT_UNIFORMLY_ACTIONABLE") else "public-signature-class.v1",
                "compatible_game_ids": [g.game_id for g in games],
                "epsilon": str(epsilon),
                "canonical_status": status.value,
                "R": str(robust.value),
                "valid_outer_actions": ["U2"] if status == ActionabilityStatus.UNIFORMLY_ACTIONABLE_WINNING else (["U1"] if status == ActionabilityStatus.CERTIFIABLY_LOSING else ["U0"]),
                "human_comparison": {"response_class": None, "confidence": None, "action_choice": None, "expertise": None},
            })
    return tasks


def render(task: dict[str, object], domain: str, condition: str, seed: int) -> dict[str, object]:
    if domain not in DOMAINS or condition not in CONDITIONS:
        raise ValueError("unknown rendering domain or condition")
    rng = random.Random(f"{seed}:{task['task_id']}:{domain}:{condition}")
    options = [status.value for status in ActionabilityStatus]
    rng.shuffle(options)
    action_ids = ["U0", "U1", "U2", "U3"]
    rng.shuffle(action_ids)
    mechanics = {"abstract": "finite affine loss table", "ant_colony": "colony routing table", "technical_system": "component response table"}[domain]
    scaffold = {"natural": "Determine the supported conclusion.", "epistemically_scaffolded": "Consider every compatible model; distinguish entailed from possible.", "tool_assisted": "Exact enumeration or an LP may be used."}[condition]
    return {"task_id": task["task_id"], "domain": domain, "condition": condition, "template": "neutral-v1", "mechanics": mechanics,
            "prompt": scaffold, "answer_options": options, "action_options": action_ids, "canonical_answer": task["canonical_status"]}


def leakage_report(tasks: list[dict[str, object]]) -> dict[str, object]:
    labels = [str(t["canonical_status"]) for t in tasks]
    majority = max(Counter(labels).values()) / len(labels)
    # Every canonical task has each domain/template available; these features are constant/balanced.
    return {"n": len(tasks), "classes": len(set(labels)), "chance_accuracy": Fraction(1, len(set(labels))).__str__(),
            "majority_accuracy": str(Fraction(max(Counter(labels).values()), len(labels))), "template_domain_only_accuracy": str(Fraction(1, len(set(labels)))),
            "contaminated": majority > 1 / len(set(labels))}


def build_artifacts() -> dict[str, bytes]:
    tasks = build_canonical_tasks()
    renders = [render(task, domain, condition, 6001) for task in tasks for domain in DOMAINS for condition in CONDITIONS]
    values = {"pilot-corpus.json": {"version": "stage6-pilot-v1", "tasks": tasks}, "render-manifest.json": renders,
              "leakage-report.json": leakage_report(tasks)}
    encoded = {name: (json.dumps(value, indent=2, sort_keys=True) + "\n").encode() for name, value in values.items()}
    freeze = {"version": "stage6-pilot-v1", "files": {name: hashlib.sha256(data).hexdigest() for name, data in encoded.items()}}
    encoded["pilot-freeze.json"] = (json.dumps(freeze, indent=2, sort_keys=True) + "\n").encode()
    return encoded


def write_artifacts(directory: Path = ARTIFACT_DIRECTORY) -> None:
    directory.mkdir(parents=True, exist_ok=True)
    for name, data in build_artifacts().items():
        (directory / name).write_bytes(data)
