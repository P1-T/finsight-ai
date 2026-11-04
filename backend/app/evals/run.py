from __future__ import annotations

import asyncio
import os
import sys

from app.config import get_settings
from app.evals.graders import deterministic_evaluator
from app.evals.judge import make_answer_judge
from app.evals.langsmith_client import create_langsmith_client, report_langsmith_error
from app.evals.target import run_target


async def _run() -> int:
    settings = get_settings()
    if not settings.llm_enabled:
        print("Set LLM_ENABLED=true to evaluate the Claude-backed workflow.", file=sys.stderr)
        return 2
    missing = [
        name
        for name, value in (
            ("ANTHROPIC_API_KEY", settings.anthropic_api_key),
            ("LANGSMITH_API_KEY", settings.langsmith_api_key),
        )
        if not value.strip()
    ]
    if missing:
        print(f"Evaluation requires these backend environment fields: {', '.join(missing)}", file=sys.stderr)
        return 2

    # LangSmith receives this benchmark's prompts, evidence, outputs, and traces.
    # The dataset contains synthetic evidence and must not be used for private user data.
    os.environ["LANGSMITH_API_KEY"] = settings.langsmith_api_key
    os.environ["LANGSMITH_PROJECT"] = settings.langsmith_project
    os.environ["LANGSMITH_ENDPOINT"] = settings.langsmith_endpoint
    os.environ["LANGSMITH_TRACING"] = "true"

    from langsmith import aevaluate

    client = create_langsmith_client(settings)
    datasets = [
        dataset
        for dataset in client.list_datasets(dataset_name=settings.langsmith_eval_dataset)
        if dataset.name == settings.langsmith_eval_dataset
    ]
    if len(datasets) != 1:
        print(
            "Expected exactly one LangSmith dataset. Sync the checked-in golden set first with "
            "python -m app.evals.sync_dataset.",
            file=sys.stderr,
        )
        return 2

    judge = make_answer_judge(
        api_key=settings.anthropic_api_key,
        model_name=settings.langsmith_eval_judge_model,
    )
    await aevaluate(
        run_target,
        data=datasets[0].id,
        evaluators=[deterministic_evaluator, judge],
        experiment_prefix="finsight-golden-v1",
        metadata={
            "dataset_version": "v1",
            "target_model": settings.anthropic_model,
            "judge_model": settings.langsmith_eval_judge_model,
            "graph": "plan-retrieve-synthesize",
            "evidence_mode": "fixed synthetic fixtures",
        },
        max_concurrency=1,
        client=client,
    )
    print("LangSmith evaluation completed. Open the LangSmith project to review the experiment and per-case feedback.")
    print(f"Project: {settings.langsmith_project}")
    return 0


def main() -> int:
    try:
        return asyncio.run(_run())
    except KeyboardInterrupt:
        print("Evaluation cancelled.", file=sys.stderr)
        return 130
    except Exception as exc:
        return report_langsmith_error(exc, "evaluation run")


if __name__ == "__main__":
    raise SystemExit(main())
