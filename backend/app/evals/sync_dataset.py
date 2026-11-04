from __future__ import annotations

import json
import sys
from typing import Any

from app.config import get_settings
from app.evals.dataset import load_cases, to_langsmith_example
from app.evals.langsmith_client import create_langsmith_client, report_langsmith_error


def _canonical(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def _sync() -> int:
    settings = get_settings()
    if not settings.langsmith_api_key.strip():
        print("LANGSMITH_API_KEY is required to sync the evaluation dataset.", file=sys.stderr)
        return 2

    client = create_langsmith_client(settings)
    dataset_name = settings.langsmith_eval_dataset
    matching_datasets = [item for item in client.list_datasets(dataset_name=dataset_name) if item.name == dataset_name]
    if matching_datasets:
        dataset = matching_datasets[0]
        if len(matching_datasets) > 1:
            raise RuntimeError(f"More than one LangSmith dataset is named {dataset_name!r}.")
        print(f"Using existing LangSmith dataset: {dataset.name} ({dataset.id})")
    else:
        dataset = client.create_dataset(
            dataset_name=dataset_name,
            description=(
                "Versioned 10-case FinSight benchmark. Search and market evidence is synthetic, "
                "fixed test data; model outputs are evaluated against explicit expectations."
            ),
        )
        print(f"Created LangSmith dataset: {dataset.name} ({dataset.id})")

    desired = {example["metadata"]["case_id"]: example for example in map(to_langsmith_example, load_cases())}
    existing = {
        str(example.metadata.get("case_id")): example
        for example in client.list_examples(dataset_id=dataset.id)
        if example.metadata and example.metadata.get("case_id")
    }
    unexpected = set(existing) - set(desired)
    if unexpected:
        raise RuntimeError(
            "The remote dataset contains cases absent from the checked-in v1 benchmark: "
            f"{sorted(unexpected)}. Create a new dataset version instead of silently deleting examples."
        )

    missing = [case_id for case_id in desired if case_id not in existing]
    mismatched: list[str] = []
    for case_id, wanted in desired.items():
        if case_id not in existing:
            continue
        current = existing[case_id]
        if _canonical(current.inputs) != _canonical(wanted["inputs"]) or _canonical(current.outputs) != _canonical(wanted["outputs"]):
            mismatched.append(case_id)
    if mismatched:
        raise RuntimeError(
            "Existing LangSmith examples differ from the checked-in benchmark: "
            f"{sorted(mismatched)}. Treat golden datasets as immutable; bump LANGSMITH_EVAL_DATASET to a new version."
        )

    if missing:
        examples = [desired[case_id] for case_id in missing]
        client.create_examples(
            dataset_id=dataset.id,
            inputs=[item["inputs"] for item in examples],
            outputs=[item["outputs"] for item in examples],
            metadata=[item["metadata"] for item in examples],
        )
        print(f"Uploaded {len(missing)} golden cases.")
    else:
        print("Dataset is already synchronized; no examples were changed.")

    final_count = sum(1 for _ in client.list_examples(dataset_id=dataset.id))
    if final_count != 10:
        raise RuntimeError(f"Expected exactly 10 LangSmith examples, found {final_count}.")
    print(f"Verified {final_count} cases in {dataset_name!r}.")
    return 0


def main() -> int:
    try:
        return _sync()
    except Exception as exc:
        return report_langsmith_error(exc, "dataset synchronization")


if __name__ == "__main__":
    raise SystemExit(main())
