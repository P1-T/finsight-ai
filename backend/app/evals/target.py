from __future__ import annotations

import copy
import json
from time import perf_counter
from typing import Any
from unittest.mock import patch

from app.api.schemas import ChatRequest, VisualResearchResponse
from app.evals.dataset import load_fixtures
from app.graph import chat_graph as graph_module
from app.providers.company_directory import Company, company_directory


def _history_payload(value: Any) -> list[dict[str, str]]:
    if not isinstance(value, list):
        return []
    return [
        {"role": str(turn["role"]), "text": str(turn["text"])}
        for turn in value
        if isinstance(turn, dict) and turn.get("role") in {"user", "assistant"} and isinstance(turn.get("text"), str)
    ]


def _plan_view(plan: Any, template: str | None) -> dict[str, Any]:
    proposal = plan.proposal
    tools: list[str] = []
    if proposal.market_data:
        tools.append("market_data")
    if proposal.web_search:
        tools.append("web_search")
    if proposal.news_search:
        tools.append("news_search")
    return {
        "tickers": [company.ticker for company in plan.companies],
        "tools": tools,
        "template": "clarification" if plan.clarification else template,
        "intent_id": plan.intent_id,
        "clarification": bool(plan.clarification),
    }


async def run_target(inputs: dict[str, Any]) -> dict[str, Any]:
    """Run the production LangGraph with frozen external evidence and live Claude calls."""
    fixtures = load_fixtures()
    fixture_id = str(inputs.get("fixture_id") or "")
    if fixture_id not in fixtures:
        raise ValueError(f"Unknown evaluation fixture: {fixture_id!r}")
    fixture = fixtures[fixture_id]
    companies = tuple(Company(**item) for item in fixture.get("companies", []))
    request = ChatRequest(prompt=str(inputs["prompt"]), history=_history_payload(inputs.get("history")))

    def market_action(_plan: Any) -> tuple[list[dict[str, Any]], str | None]:
        return copy.deepcopy(fixture.get("market_data", [])), None

    def search_action(_action: Any, search_kind: str, _companies: Any = ()) -> tuple[list[dict[str, Any]], str | None]:
        key = "news_search" if search_kind == "news" else "web_search"
        rows = copy.deepcopy(fixture.get(key, []))
        if _companies:
            requested_tickers = {company.ticker for company in _companies}
            rows = [
                row for row in rows
                if requested_tickers.intersection(row.get("matched_companies", []))
            ]
        return rows, None

    # LangSmith evaluates one example at a time (max_concurrency=1), so these
    # scoped patches cannot cross-contaminate concurrent requests.
    started = perf_counter()
    with (
        patch.object(company_directory, "all", return_value=companies),
        patch.object(graph_module, "_run_market_action", side_effect=market_action),
        patch.object(graph_module, "_run_search_action", side_effect=search_action),
    ):
        state = await graph_module.run_chat_graph(request)
    elapsed_ms = round((perf_counter() - started) * 1000, 1)

    plan = state.get("plan")
    raw_response = state.get("response") or {}
    try:
        parsed_response = VisualResearchResponse.model_validate(raw_response)
        response_data = parsed_response.model_dump(mode="json", exclude_none=True)
        schema_valid = True
    except Exception:
        response_data = raw_response if isinstance(raw_response, dict) else {}
        schema_valid = False

    evidence = state.get("evidence", [])
    evidence_ids = [str(item["id"]) for item in evidence if isinstance(item, dict) and item.get("id")]
    return {
        "answer": str(state.get("answer") or response_data.get("summary") or ""),
        "plan": _plan_view(plan, response_data.get("template")) if plan else {},
        "visual_response": response_data,
        "schema_valid": schema_valid,
        "fallback_used": bool(plan and plan.planner_fallback) or response_data.get("generated_by") == "fallback",
        "evidence_ids": evidence_ids,
        "evidence_context": json.dumps(evidence, ensure_ascii=False, separators=(",", ":")),
        "latency_ms": elapsed_ms,
    }
