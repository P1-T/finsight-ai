from __future__ import annotations

from typing import Any
from urllib.parse import urlparse


def deterministic_evaluator(
    *,
    outputs: dict[str, Any],
    reference_outputs: dict[str, Any],
    **_: Any,
) -> list[dict[str, Any]]:
    """Hard, reproducible checks for routing, entities, schema, and citations."""
    actual_plan = outputs.get("plan") or {}
    actual_tickers = set(actual_plan.get("tickers") or [])
    expected_tickers = set(reference_outputs.get("tickers") or [])
    actual_tools = set(actual_plan.get("tools") or [])
    required_tools = set(reference_outputs.get("required_tools") or [])
    allowed_tools = set(reference_outputs.get("allowed_tools") or [])
    template = (outputs.get("visual_response") or {}).get("template")
    expected_templates = set(reference_outputs.get("templates") or [])
    expected_clarification = bool(reference_outputs.get("clarification"))
    actual_clarification = template == "clarification"

    if not required_tools:
        tool_precision = 1.0 if not actual_tools else 0.0
        tool_recall = 1.0
    else:
        overlap = len(actual_tools & required_tools)
        tool_precision = overlap / len(actual_tools) if actual_tools else 0.0
        tool_recall = overlap / len(required_tools)
    tool_f1 = (
        2 * tool_precision * tool_recall / (tool_precision + tool_recall)
        if tool_precision + tool_recall
        else 0.0
    )

    response = outputs.get("visual_response") or {}
    sources = response.get("sources") or []
    source_ids = [str(source.get("id")) for source in sources if source.get("id")]
    source_ids_unique = len(source_ids) == len(set(source_ids))
    evidence_ids = set(outputs.get("evidence_ids") or [])
    urls_valid = all(
        not source.get("url")
        or (urlparse(str(source["url"])).scheme in {"http", "https"} and bool(urlparse(str(source["url"])).hostname))
        for source in sources
    )
    evidence_sources_present = set(source_ids).issubset(evidence_ids)
    citation_integrity = source_ids_unique and urls_valid and evidence_sources_present

    return [
        {"key": "template_match", "score": float(template in expected_templates)},
        {"key": "ticker_resolution", "score": float(actual_tickers == expected_tickers)},
        {"key": "tool_selection_f1", "score": round(tool_f1, 4)},
        {"key": "tool_policy", "score": float(actual_tools.issubset(allowed_tools))},
        {"key": "clarification_match", "score": float(actual_clarification == expected_clarification)},
        {"key": "response_schema_valid", "score": float(bool(outputs.get("schema_valid")))},
        {"key": "live_model_path", "score": float(not outputs.get("fallback_used", True))},
        {"key": "citation_integrity", "score": float(citation_integrity)},
    ]
