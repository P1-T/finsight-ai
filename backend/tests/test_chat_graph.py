import asyncio

import pytest
from fastapi.testclient import TestClient
from pydantic import ValidationError

from app.api.schemas import (
    ChatRequest,
    CompanyAnalysisNarrative,
    EvidenceClaim,
    MarketDataAction,
    ResearchAnswerNarrative,
    ResearchPlan,
    SearchAction,
    StockComparisonNarrative,
)
from app.graph import chat_graph as graph_module
from app.graph.chat_graph import (
    ValidatedPlan,
    _market_snapshot,
    _matches_company,
    _plan_node,
    _retrieve_node,
    _run_search_action,
    _scoped_search_query,
    _synthesize_node,
    run_chat_graph,
)
from app.providers.company_directory import Company, company_directory
from app.utils.errors import AgentError


def _directory(monkeypatch):
    records = (
        Company("AMD", "Advanced Micro Devices, Inc.", "Nasdaq"),
        Company("GOOGL", "Alphabet Inc.", "Nasdaq"),
        Company("TSLA", "Tesla, Inc.", "Nasdaq"),
    )
    monkeypatch.setattr(company_directory, "all", lambda: records)
    return records


class FakeStructuredModel:
    def __init__(self, response):
        self.response = response

    def with_structured_output(self, _schema):
        return self

    async def ainvoke(self, _messages):
        return self.response


def test_research_plan_is_strict_and_bounds_tool_calls() -> None:
    plan = ResearchPlan(
        intent="comparison",
        companies=["AMD", "Google"],
        market_data=MarketDataAction(period="3mo", metrics=["latest_close", "return_20d"]),
        news_search=[SearchAction(query="AMD and Google news", result_limit=5, recency="week")],
    )
    assert plan.market_data is not None
    assert plan.news_search[0].result_limit == 5
    with pytest.raises(ValidationError):
        ResearchPlan.model_validate({"intent": "other", "unknown_tool": "run_shell"})
    with pytest.raises(ValidationError):
        ResearchPlan.model_validate({"intent": "news", "news_search": [{"query": "news", "result_limit": 20}]})


def test_market_snapshot_contains_only_available_provider_metrics() -> None:
    snapshot = _market_snapshot({
        "id": "MKT-EXM",
        "type": "market_data",
        "ticker": "EXM",
        "as_of_date": "2026-10-30",
        "period": "6mo",
        "metrics": {
            "latest_close": {"value": 25.5},
            "rsi14": {"value": None, "unavailable_reason": "Insufficient history"},
            "volume_vs_average": "Unavailable: insufficient volume history.",
            "volatility_note": "20-session standard deviation is 1.2%.",
        },
    })
    assert [(metric.key, metric.value) for metric in snapshot.metrics] == [
        ("latest_close", 25.5),
        ("volatility_note", "20-session standard deviation is 1.2%."),
    ]


def test_finance_acronyms_do_not_accidentally_resolve_as_tickers(monkeypatch) -> None:
    company = Company("AI", "C3.ai, Inc.", "NYSE")
    monkeypatch.setattr(company_directory, "all", lambda: (company,))
    assert company_directory.mentions("How can AI improve financial analysis?") == []
    assert company_directory.mentions("Analyze $AI stock") == [company]


def test_planner_resolves_companies_and_preserves_prompt_entities(monkeypatch) -> None:
    _directory(monkeypatch)
    proposal = ResearchPlan(
        intent="comparison",
        companies=["AMD", "Google"],
        market_data=MarketDataAction(period="3mo", metrics=["latest_close"]),
        news_search=[SearchAction(query="AMD Google recent developments")],
    )
    import app.llm

    monkeypatch.setattr(app.llm, "get_chat_model", lambda **_kwargs: FakeStructuredModel(proposal))
    queue: asyncio.Queue[dict] = asyncio.Queue()
    state = asyncio.run(_plan_node({"request": ChatRequest(prompt="Compare AMD with Google"), "progress_queue": queue}))
    plan = state["plan"]
    assert [(company.ticker, company.name) for company in plan.companies] == [
        ("AMD", "Advanced Micro Devices, Inc."), ("GOOGL", "Alphabet Inc.")
    ]
    assert plan.clarification is None
    assert queue.get_nowait()["tool_count"] == 2


def test_ambiguous_entity_pauses_tool_retrieval(monkeypatch) -> None:
    _directory(monkeypatch)
    proposal = ResearchPlan(
        intent="market_data",
        companies=["Not A Listed Company"],
        market_data=MarketDataAction(),
    )
    import app.llm

    monkeypatch.setattr(app.llm, "get_chat_model", lambda **_kwargs: FakeStructuredModel(proposal))
    state = asyncio.run(_plan_node({"request": ChatRequest(prompt="Analyze Not A Listed Company shares")}))
    plan = state["plan"]
    assert plan.clarification
    assert plan.companies == ()
    result = asyncio.run(_retrieve_node({"plan": plan}))
    assert result["evidence"] == []


def test_exact_ticker_resolves_shared_company_name_after_clarification(monkeypatch) -> None:
    records = (
        Company("ORCL", "ORACLE CORP", "NYSE"),
        Company("ORCL-PD", "ORACLE CORP", "NYSE"),
    )
    monkeypatch.setattr(company_directory, "all", lambda: records)
    assert {company.ticker for company in company_directory.mentions("analyze oracle stock")} == {"ORCL", "ORCL-PD"}
    assert [company.ticker for company in company_directory.mentions("i mean ORACLE CORP (ORCL)")] == ["ORCL"]

    proposal = ResearchPlan(
        intent="market_data",
        companies=["ORACLE CORP"],
        market_data=MarketDataAction(),
        clarification_question="ORACLE CORP could not be uniquely identified.",
    )
    import app.llm

    monkeypatch.setattr(app.llm, "get_chat_model", lambda **_kwargs: FakeStructuredModel(proposal))
    request = ChatRequest(
        prompt="i mean ORACLE CORP (ORCL)",
        history=[
            {"role": "user", "text": "analyze oracle stock"},
            {"role": "assistant", "text": "Did you mean ORACLE CORP (ORCL) or ORACLE CORP (ORCL-PD)?"},
        ],
    )
    plan = asyncio.run(_plan_node({"request": request}))["plan"]
    assert [company.ticker for company in plan.companies] == ["ORCL"]
    assert plan.clarification is None


def test_selected_tools_run_concurrently_and_keep_tool_evidence(monkeypatch) -> None:
    _directory(monkeypatch)
    proposal = ResearchPlan(
        intent="comparison",
        companies=["AMD", "Google"],
        market_data=MarketDataAction(metrics=["latest_close"]),
        web_search=[SearchAction(query="company overview")],
        news_search=[SearchAction(query="recent company news")],
    )
    plan = ValidatedPlan(proposal, (Company("AMD", "Advanced Micro Devices, Inc.", "Nasdaq"),))
    monkeypatch.setattr(graph_module, "_run_market_action", lambda _plan: ([{"id": "MKT-AMD", "type": "market_data"}], None))
    monkeypatch.setattr(graph_module, "_run_search_action", lambda action, kind, _companies=(): ([{"title": action.query, "url": f"https://example.com/{kind}", "type": "news" if kind == "news" else "web_result"}], None))
    queue: asyncio.Queue[dict] = asyncio.Queue()
    state = asyncio.run(_retrieve_node({"plan": plan, "progress_queue": queue}))
    assert {item["type"] for item in state["evidence"]} == {"market_data", "news", "web_result"}
    events = []
    while not queue.empty():
        events.append(queue.get_nowait())
    assert sum(item.get("status") == "running" for item in events) == 3
    assert sum(item.get("status") == "succeeded" for item in events) == 3


def test_company_search_query_is_scoped_and_google_alias_is_retained() -> None:
    adobe = Company("ADBE", "Adobe Inc.", "Nasdaq")
    google = Company("GOOGL", "Alphabet Inc.", "Nasdaq")
    assert '"Adobe Inc."' in _scoped_search_query(SearchAction(query="analyst sentiment"), (adobe,))
    google_query = _scoped_search_query(SearchAction(query="analyst sentiment"), (google,))
    assert '"Alphabet Inc."' in google_query
    assert '"google"' in google_query
    assert _scoped_search_query(SearchAction(query="Adobe analyst sentiment"), (adobe,)) == "Adobe analyst sentiment"


def test_company_search_discards_unrelated_results_and_keeps_google_alias(monkeypatch) -> None:
    from types import SimpleNamespace

    adobe = Company("ADBE", "Adobe Inc.", "Nasdaq")
    requested_query = SearchAction(query="Adobe analyst sentiment")

    class FakeSearchProvider:
        def search(self, query, **_kwargs):
            assert query == "Adobe analyst sentiment"
            return [
                SimpleNamespace(title="Adobe outlook improves", source="Example", published_at=None, url="https://example.com/adobe", excerpt="Adobe analysts discuss demand"),
                SimpleNamespace(title="NVIDIA outlook improves", source="Example", published_at=None, url="https://example.com/nvidia", excerpt="NVIDIA analysts discuss demand"),
            ]

    monkeypatch.setattr(graph_module, "DDGSWebSearchProvider", FakeSearchProvider)
    rows, error = _run_search_action(requested_query, "news", (adobe,))
    assert error is None
    assert [row["title"] for row in rows] == ["Adobe outlook improves"]
    assert rows[0]["query"] == "Adobe analyst sentiment"

    google = Company("GOOGL", "Alphabet Inc.", "Nasdaq")
    assert _matches_company({"title": "Google unveils new product"}, (google,))


def test_synthesis_context_marks_unavailable_news_and_prompt_forbids_price_based_sentiment(monkeypatch) -> None:
    import app.llm

    captured = {}

    class CaptureModel(FakeStructuredModel):
        async def ainvoke(self, messages):
            captured["system"] = messages[0].content
            captured["context"] = messages[1].content
            return self.response

    def get_model(**kwargs):
        captured["max_tokens"] = kwargs.get("max_tokens")
        return CaptureModel(CompanyAnalysisNarrative(
            summary="News sentiment is unavailable.",
            risks=[EvidenceClaim(title="Sharp decline", detail="The share price fell sharply.", source_ids=["MKT-ADBE"])],
        ))

    monkeypatch.setattr(app.llm, "get_chat_model", get_model)
    plan = ValidatedPlan(
        ResearchPlan(
            intent="company_research",
            response_template="company_analysis",
            news_search=[SearchAction(query="Adobe analyst news")],
            unsupported_data_needs=["Financial statements and earnings history", "Valuation multiples such as P/E", "Options data"],
        ),
        (Company("ADBE", "Adobe Inc.", "Nasdaq"),),
    )
    result = asyncio.run(_synthesize_node({
        "request": ChatRequest(prompt="What is Adobe news sentiment?"),
        "plan": plan,
        "evidence": [{"type": "market_data", "id": "MKT-ADBE", "ticker": "ADBE", "company": "Adobe Inc.", "as_of_date": "2026-10-30", "period": "6mo", "metrics": {"latest_close": {"value": 101.2}}}],
    }))
    assert '"news_evidence_status":"no_relevant_news_retrieved"' in captured["context"]
    assert "market-price interpretation separate from news analysis" in captured["system"]
    assert captured["max_tokens"] == 2400
    assert '"response_template":"company_analysis"' in captured["context"]
    assert "MKT-ADBE" not in captured["context"]
    assert result["response"]["template"] == "company_analysis"
    assert result["response"]["company"] == {"ticker": "ADBE", "name": "Adobe Inc.", "exchange": "Nasdaq"}
    assert result["response"]["market_snapshot"]["metrics"] == [{"key": "latest_close", "value": 101.2, "unit": "usd"}]
    assert "market_cap" not in result["response"]
    assert result["response"]["narrative"]["risks"] == []
    assert not any("Valuation" in note or "Options" in note for note in result["response"]["limitations"])


def test_comparison_synthesis_exposes_partial_news_coverage_by_company(monkeypatch) -> None:
    import app.llm

    captured = {}

    class CaptureModel(FakeStructuredModel):
        async def ainvoke(self, messages):
            captured["system"] = messages[0].content
            captured["context"] = messages[1].content
            return self.response

    monkeypatch.setattr(app.llm, "get_chat_model", lambda **_kwargs: CaptureModel(StockComparisonNarrative(summary="News coverage is partial.")))
    intel = Company("INTC", "Intel Corporation", "Nasdaq")
    amd = Company("AMD", "Advanced Micro Devices, Inc.", "Nasdaq")
    plan = ValidatedPlan(
        ResearchPlan(intent="comparison", response_template="stock_comparison", news_search=[SearchAction(query="Intel AMD news")]),
        (intel, amd),
    )
    result = asyncio.run(_synthesize_node({
        "request": ChatRequest(prompt="Compare Intel and AMD stocks now"),
        "plan": plan,
        "evidence": [
            {"id": "MKT-INTC", "type": "market_data", "ticker": "INTC", "company": "Intel Corporation", "as_of_date": "2026-10-30", "period": "6mo", "metrics": {}},
            {"id": "MKT-AMD", "type": "market_data", "ticker": "AMD", "company": "Advanced Micro Devices, Inc.", "as_of_date": "2026-10-30", "period": "6mo", "metrics": {}},
            {"id": "SRC-1", "type": "news", "title": "AMD expands data center products", "matched_companies": ["AMD"]},
        ],
    }))
    assert '"news_evidence_status":"partial_company_coverage"' in captured["context"]
    assert '"ticker":"INTC","relevant_news_result_count":0' in captured["context"]
    assert '"ticker":"AMD","relevant_news_result_count":1' in captured["context"]
    assert "per-company news coverage" in captured["system"]
    assert result["response"]["news_coverage"] == [
        {"ticker": "INTC", "relevant_result_count": 0},
        {"ticker": "AMD", "relevant_result_count": 1},
    ]


def test_synthesis_is_claude_authored_and_only_uses_valid_citations(monkeypatch) -> None:
    import app.llm

    answer = ResearchAnswerNarrative(answer="Revenue is unavailable in the retrieved evidence.", source_ids=["SRC-1", "FAKE"])
    monkeypatch.setattr(app.llm, "get_chat_model", lambda **_kwargs: FakeStructuredModel(answer))
    plan = ValidatedPlan(ResearchPlan(intent="company_research", response_template="research_answer"), ())
    state = asyncio.run(_synthesize_node({
        "request": ChatRequest(prompt="What is the company's revenue?"),
        "plan": plan,
        "evidence": [{"id": "SRC-1", "title": "Example filing", "url": "https://example.com/report", "type": "web_result"}],
    }))
    assert state["response"]["template"] == "research_answer"
    assert "Revenue is unavailable in the retrieved evidence." in state["answer"]
    assert "FAKE" not in state["answer"]
    assert state["response"]["narrative"]["source_ids"] == ["SRC-1"]


def test_synthesis_does_not_fall_back_to_a_deterministic_answer(monkeypatch) -> None:
    import app.llm

    def unavailable(**_kwargs):
        raise AgentError("Anthropic API key is not configured on the server.")

    monkeypatch.setattr(app.llm, "get_chat_model", unavailable)
    plan = ValidatedPlan(ResearchPlan(intent="educational"), ())
    with pytest.raises(AgentError, match="Anthropic API key"):
        asyncio.run(_synthesize_node({"request": ChatRequest(prompt="Explain market capitalization"), "plan": plan, "evidence": []}))


def test_graph_invokes_planner_then_final_answer_without_deterministic_answer(monkeypatch) -> None:
    _directory(monkeypatch)
    import app.llm

    proposal = ResearchPlan(intent="educational", response_template="research_answer")
    class SequentialModel:
        def __init__(self):
            self.calls = 0

        def with_structured_output(self, _schema):
            return self

        async def ainvoke(self, _messages):
            self.calls += 1
            return proposal if self.calls == 1 else ResearchAnswerNarrative(answer="A cash flow statement tracks cash movements.")

    model = SequentialModel()
    monkeypatch.setattr(app.llm, "get_chat_model", lambda **_kwargs: model)
    queue: asyncio.Queue[dict] = asyncio.Queue()
    state = asyncio.run(run_chat_graph(ChatRequest(prompt="Explain a cash flow statement"), queue))
    assert state["response"]["template"] == "research_answer"
    assert "A cash flow statement tracks cash movements." in state["answer"]
    assert model.calls == 2
    assert any(item.get("event") == "final_response" for item in list(queue._queue))


def test_chat_stream_rejects_ticker_selection_context(client: TestClient) -> None:
    response = client.post("/api/chat/stream", json={"ticker": "AMD", "prompt": "Explain market cap"})
    assert response.status_code == 422


def test_chat_stream_emits_claude_answer_and_no_visual_blocks(client: TestClient, monkeypatch) -> None:
    async def fake_graph(_request, queue):
        queue.put_nowait({"event": "plan", "intent": "educational", "company_count": 0, "tool_count": 0})
        queue.put_nowait({"event": "stage", "stage": "synthesis", "label": "Writing an evidence-grounded answer"})
        queue.put_nowait({"event": "final_response", "answer": "## Research answer\n\nCash flow measures money moving in and out.", "response": {"template": "research_answer"}})
        return {"answer": "## Research answer\n\nCash flow measures money moving in and out.", "response": {"template": "research_answer"}}

    monkeypatch.setattr("app.api.routes.run_chat_graph", fake_graph)
    response = client.post("/api/chat/stream", json={"prompt": "Explain cash flow"})
    assert response.status_code == 200
    assert "Cash flow measures money moving in and out." in response.text
    assert "data-research-response" in response.text
    assert "data-tool-status" not in response.text
