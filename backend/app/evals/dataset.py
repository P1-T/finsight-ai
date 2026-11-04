from __future__ import annotations

import json
from pathlib import Path
from typing import Any

EVAL_ROOT = Path(__file__).resolve().parents[2] / "evals"
CASES_PATH = EVAL_ROOT / "golden_v1.json"
FIXTURES_PATH = EVAL_ROOT / "fixtures_v1.json"


def load_cases() -> list[dict[str, Any]]:
    with CASES_PATH.open(encoding="utf-8") as file:
        cases = json.load(file)
    if not isinstance(cases, list) or len(cases) != 10:
        raise ValueError("The FinSight Golden v1 benchmark must contain exactly 10 cases.")
    case_ids = [case.get("case_id") for case in cases]
    if len(set(case_ids)) != len(case_ids) or any(not isinstance(case_id, str) for case_id in case_ids):
        raise ValueError("Golden evaluation case IDs must be unique strings.")
    return cases


def load_fixtures() -> dict[str, dict[str, Any]]:
    with FIXTURES_PATH.open(encoding="utf-8") as file:
        fixtures = json.load(file)
    if not isinstance(fixtures, dict):
        raise ValueError("Evaluation fixtures must be a JSON object keyed by fixture ID.")
    referenced = {case["fixture_id"] for case in load_cases()}
    missing = referenced - fixtures.keys()
    if missing:
        raise ValueError(f"Golden cases reference missing evidence fixtures: {sorted(missing)}")
    return fixtures


def validate_case(case: dict[str, Any]) -> None:
    required = {"case_id", "category", "prompt", "history", "fixture_id", "expectations"}
    if not required.issubset(case):
        raise ValueError(f"Evaluation case is missing fields: {sorted(required - case.keys())}")
    expected = case["expectations"]
    if not {"templates", "tickers", "required_tools", "allowed_tools", "clarification", "reference_answer", "rubric"}.issubset(expected):
        raise ValueError(f"Evaluation case {case['case_id']} has incomplete expectations.")
    if not isinstance(case["prompt"], str) or not case["prompt"].strip():
        raise ValueError(f"Evaluation case {case['case_id']} has a blank prompt.")
    if not isinstance(case["history"], list):
        raise ValueError(f"Evaluation case {case['case_id']} history must be a list.")


def to_langsmith_example(case: dict[str, Any]) -> dict[str, Any]:
    validate_case(case)
    return {
        "inputs": {
            "case_id": case["case_id"],
            "prompt": case["prompt"],
            "history": case["history"],
            "fixture_id": case["fixture_id"],
        },
        "outputs": case["expectations"],
        "metadata": {
            "case_id": case["case_id"],
            "category": case["category"],
            "fixture_kind": "synthetic_evaluation_evidence",
            "dataset_version": "v1",
        },
    }
