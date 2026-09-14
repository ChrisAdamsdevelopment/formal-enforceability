import hashlib
from collections import Counter

from enforceability.actionability import ActionabilityStatus
from enforceability.stage6_pilot import ARTIFACT_DIRECTORY, CONDITIONS, DOMAINS, build_artifacts, build_canonical_tasks, leakage_report, render


def test_balanced_48_task_pilot_and_outer_actions():
    tasks = build_canonical_tasks()
    assert len(tasks) == 48
    assert Counter(t["canonical_status"] for t in tasks) == {status.value: 12 for status in ActionabilityStatus}
    assert {action for task in tasks for action in task["valid_outer_actions"]} == {"U0", "U1", "U2"}
    assert all(set(task["human_comparison"]) == {"response_class", "confidence", "action_choice", "expertise"} for task in tasks)


def test_equivalent_renderings_and_seeded_permutations_canonicalize():
    task = build_canonical_tasks()[0]
    rendered = [render(task, domain, condition, 6001) for domain in DOMAINS for condition in CONDITIONS]
    assert {item["canonical_answer"] for item in rendered} == {task["canonical_status"]}
    assert len({tuple(item["answer_options"]) for item in rendered}) > 1
    assert len({tuple(item["action_options"]) for item in rendered}) > 1
    assert rendered == [render(task, domain, condition, 6001) for domain in DOMAINS for condition in CONDITIONS]


def test_representation_only_baselines_are_at_chance():
    report = leakage_report(build_canonical_tasks())
    assert report == {"n": 48, "classes": 4, "chance_accuracy": "1/4", "majority_accuracy": "1/4", "template_domain_only_accuracy": "1/4", "contaminated": False}


def test_artifacts_are_deterministic_and_frozen_files_match():
    expected = build_artifacts()
    assert set(expected) == {path.name for path in ARTIFACT_DIRECTORY.glob("*.json")}
    assert all((ARTIFACT_DIRECTORY / name).read_bytes() == data for name, data in expected.items())
    assert build_artifacts() == expected
    assert len(__import__("json").loads(expected["render-manifest.json"]) ) == 48 * 3 * 3


def test_previous_identifiability_freeze_is_untouched():
    expected = {
        "deterministic-family-report.json": "1a2ce0d51bd7b713bee9b6363c0c0b59975892f70f04213748372aac236fca97",
        "identifiability-freeze.json": "79befa8db92a4df526c3e5f8158b6ef3f98eaab1a54f487d7c61f580e91a5f2d",
        "probabilistic-family-report.json": "bbbe523748e6113d7aae08aa920771620aa462a2cb1670a6a1bacf2e4b9ed585",
        "witnesses.json": "9c49995e6686ed2d3cbc3646f7c701e392a99f7767b5a30789ca611740e72730",
    }
    root = ARTIFACT_DIRECTORY.parent / "identifiability-v1"
    assert {path.name: hashlib.sha256(path.read_bytes()).hexdigest() for path in root.glob("*.json")} == expected
