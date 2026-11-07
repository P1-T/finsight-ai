# FinSight AI

FinSight AI is a visual, open-ended AI chat demo. Users can ask general finance questions, research a listed company, or compare companies. Claude returns a structured response and selects from an allowlisted set of React components; the backend fills those components with provider data or deterministic demo fixtures. Chat history stays in the browser. This is a portfolio demonstration.

## V3 request flow

```text
Next.js chat + browser-local history
                 │ prompt + recent turns (SSE)
                 ▼
FastAPI → LangGraph
                 │
                 ├─ Claude structured intent and tool plan
                 ├─ SEC company-directory validation
                 ├─ Selected tools run concurrently
                 │    ├─ yfinance historical market data + Python indicators
                 │    ├─ DDGS web/news search
                 │    └─ deterministic synthetic fixture fallback
                 ├─ Claude structured narrative + response-component selection
                 ├─ Pydantic visual-response composer with chart fixtures
                 └─ typed blocks → allowlisted FinSight React components
```

Each researched prompt uses at most two bounded Claude calls: one tool/layout planning call and one synthesis call. Set `LLM_ENABLED=false` to skip both calls and use deterministic fallback routing and copy. Provider and model failures also fall back gracefully. Tool plans are limited to six companies, two queries per search type, five results per query, and twelve total news/web results. Independent providers run concurrently. Company analysis requests a consistent bundle of price history, market metrics, and recent web/news results; each unavailable area can still render using synthetic fixtures.

The first Claude response follows a strict schema with an intent, company names, bounded provider requests, an optional fallback component selection, and optional clarification. The server does not execute arbitrary model instructions. It validates company names against the exchange-listed company directory and maps validated entries to market-data symbols. If the plan cannot resolve a company, the workflow asks for clarification rather than silently researching a different company.

The final API response is schema version 3: a versioned list of typed blocks such as `company_header`, `metric_grid`, `price_chart`, `fundamental_cards`, `fact_grid`, `data_chart`, `scenario_cards`, `news_timeline`, `comparison_table`, `takeaways`, and `answer_card`. Claude never returns JSX, HTML, or executable component code. Its synthesis output includes a strict list of component types; the backend validates that selection, constructs the final response JSON, and supplies market or fixture values to each selected block. Every response, including follow-ups and clarification responses, is composed with at least four chart blocks. Recharts renders the charts through FinSight's native React component registry. Older version 2 and browser-saved responses continue to render.

Quarterly-performance questions use a dedicated response template and fetch a separate six-month historical market snapshot for price context. Claude separates reported results from forward guidance and returns only figures explicitly present in retrieved result snippets, with source IDs and an exact supporting quote. The backend checks that cited snippets contain the quoted number and corroborate the reporting period before the fact reaches the UI. The composer renders a price chart and market snapshot, compact earnings scorecards, a visual range for numeric guidance ranges, a bar chart for comparable reported growth rates, and concise evidence-backed bull/bear cards.

The API streams planning and retrieval progress, then updates the allowlisted `data-research-layout` component selection after synthesis. It sends a typed `data-research-response` message part and a readable text representation for conversation history and fallback accessibility. The schema version allows visual response payloads to evolve without coupling the backend to React implementations.

### Visual response building blocks

- **Company research:** company hero, market metrics, price history, fundamentals, business-mix charts, four-point bull and bear cases, and recent coverage.
- **Company comparison:** a compact comparison table plus per-company price charts; the table carries the key market and fundamental fields.
- **Quarterly performance:** reported metric cards, a comparable-growth bar chart when at least two verified rates exist, and evidence-backed bull/bear cards.
- **Valuation, dividend, risk, and sector analysis:** focused metric cards plus comparison, trend, and composition charts.
- **News or technical questions:** sentiment, coverage cadence, price trends, and risk metrics are rendered as charts and timelines.
- **General and follow-up questions:** a concise response with contextual visual examples; follow-ups inherit the recent company context and receive a more detailed explanation.

The backend keeps 100 focused intent templates in `backend/app/intent_catalog.py`. Each entry has an example prompt, phrase cues, weighted keywords, a category, and a reusable response layout. These are 100 intent patterns, not 100 separate frontend implementations: the catalog maps them to a compact set of typed response schemas and React blocks. See [Intent routing and template catalog](docs/intent-routing.md) for the catalog scope and routing algorithm.

Intent selection is a two-stage, bounded process. First, the server scores all catalog entries using exact phrase matches (4–6 points), rarity-weighted keyword overlap (scaled by template size), and recent-turn context at 25% weight. Company-count evidence gives a comparison intent a 3-point boost when multiple companies resolve, and penalizes an unsupported multi-company layout when only one resolves. Claude receives the top eight candidates and selects one using the question's meaning; its valid shortlist choice contributes at most 1.6 points. The server then reconciles the choice with resolved company identities and structural rules, so the model cannot introduce a company or override a validated single-company result. The response includes the selected `intent_id` and a confidence score based on evidence strength and the margin over the runner-up. This confidence describes routing confidence only; it is not confidence in an investment conclusion.

The 100 patterns include company and competitive analysis, financial performance, valuation, shareholder returns, balance sheet, technical analysis, macro and sector questions, news, events, expectations, ownership, and derivatives. Follow-ups use recent company context only when the prompt is context-dependent; a new explicit company in the current message takes precedence.

Each response is composed with at least four Recharts visualizations. The chart types are selected from line, bar, and donut blocks, using provider values where available and stable demo fixtures for the remaining visual fields.

The fundamental cards and business-mix charts use deterministic fixture values when those fields are not retrieved from providers. Saved popular-company fixtures live in `backend/app/data/demo_company_fixtures.json`; other symbols receive stable per-ticker fallback values. General finance prompts use a small built-in example chart when company data does not apply. No dummy URL, article, or source citation is created.

## Sources and limitations

- **Market data:** yfinance daily OHLCV; pandas calculates price returns, moving averages, RSI, volume comparison, and historical volatility. The latest date is the last available provider session, not a live quote. Yahoo Finance credentials are not required. Fixture price history fills gaps when retrieval fails.
- **News and web search:** DDGS DuckDuckGo search; news and web are separate selectable tools over the same free, no-key provider. Results contain titles, metadata, and short snippets, not full article text. DDGS is best-effort and may be throttled or change behavior.
- **Company resolution:** SEC's public exchange-listed company directory. This supports broad US-exchange coverage, not guaranteed coverage of every symbol by every upstream provider. A ticker may be used internally to call yfinance; users do not select a ticker to establish chat context.
- **Visual fixtures:** fundamental figures, fallback price history, scenario points, business-mix charts, and generic finance examples can come from deterministic fixtures.
- **Model:** `ANTHROPIC_MODEL` selects Claude; `ANTHROPIC_API_KEY` stays on the backend. Claude API usage is billed separately from IDE subscriptions. `LLM_ENABLED=false` disables model calls and uses deterministic demo composition.
- **Chat history:** saved only in browser `localStorage`; it is not synchronized or stored on the backend.
- **Public API request limits:** the backend allows 10 chat stream requests and 60 company-search requests per minute per client IP. The in-memory limiter is intended for the single-task demo deployment; it resets on restart and is not shared across multiple tasks. Set `TRUST_PROXY_HEADERS=true` only when ECS security groups restrict the task to the ECS Gateway load balancer, so the limiter can use the load balancer's appended client IP.

## Requirements

- Node.js 22 or newer
- Python 3.13 recommended
- A contact email in `SEC_USER_AGENT` for SEC directory requests
- An Anthropic API key and separate API billing for Claude-composed responses (optional when `LLM_ENABLED=false`)

DDGS and yfinance do not require API keys. Provider coverage and availability can vary.

## Run locally

Open two PowerShell terminals from the repository root.

### Backend

```powershell
cd backend
py -3.13 -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
Copy-Item .env.example .env
# Set ANTHROPIC_API_KEY, ANTHROPIC_MODEL, and SEC_USER_AGENT in backend/.env
uvicorn app.main:app --reload --port 8000
```

If PowerShell blocks activation, call the virtual-environment interpreter directly:

```powershell
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\python.exe -m uvicorn app.main:app --reload --port 8000
```

### Frontend

```powershell
cd frontend
npm ci
npm run dev
```

Open <http://localhost:3000>. The default backend URL is <http://localhost:8000>. If needed, set `NEXT_PUBLIC_API_BASE_URL` in `frontend/.env.local`. Never put Claude credentials in frontend environment variables.

## API

- `GET /api/health` — safe health status.
- `POST /api/chat/stream` — Vercel AI SDK UI Message SSE endpoint. Request body:

```json
{
  "prompt": "Compare recent performance and news for AMD and Google",
  "history": []
}
```

The server streams planning/research stages and active tool status, followed by a `data-research-response` part with `schema_version: 3`, ordered block payloads, provenance labels, and consolidated sources. Version 2 responses saved in browser history remain supported by the frontend. The request has no selected-ticker field. Unsupported extra request fields are rejected.

When company resolution is ambiguous, the clarification response carries the unresolved name and any candidate matches. The chat then shows a company-name/ticker autocomplete backed by `GET /api/companies/search?q=...`; selecting a match submits the user's original request with the chosen company identified. This picker is absent from ordinary research responses and non-company clarifications.

## Checks

Backend (from `backend/`):

```powershell
pytest
ruff check app tests
```

Frontend (from `frontend/`):

```powershell
npm test
npm run lint
npm run typecheck
npm run build
```

Automated tests mock LLMs and external providers. They do not require live data or paid API calls.

## LangSmith evaluation pipeline

FinSight includes an opt-in, versioned LangSmith benchmark with exactly 10 golden prompts. It exercises the real LangGraph planner, retrieval routing, synthesis, and typed visual response contract. The target still calls Claude, while company lookup and web/news/market tools are replaced with checked-in, fixed synthetic evidence. This keeps results repeatable and avoids SEC, Yahoo Finance, and DuckDuckGo variability during a run.

The evaluation records deterministic scores for template selection, entity resolution, tool selection/policy, clarification behavior, response-schema validity, fallback use, and citation integrity. An OpenEvals LLM judge scores answer relevance, evidence support, completeness, and uncertainty handling against each case's reference expectations. The judge does not reward longer answers or formatting. LangSmith records the examples, run outputs, feedback, and traces for comparison across model or prompt changes.

### Configure and run

Add these values to `backend/.env` (the example file lists the same fields). Keep both API keys private and backend-only:

```dotenv
ANTHROPIC_API_KEY=your-anthropic-key
LANGSMITH_API_KEY=your-langsmith-key
LANGSMITH_PROJECT=finsight-evals
LANGSMITH_ENDPOINT=https://api.smith.langchain.com
LANGSMITH_WORKSPACE_ID=
LANGSMITH_EVAL_DATASET=FinSight Golden Evaluation v1
LANGSMITH_EVAL_JUDGE_MODEL=claude-haiku-4-5-20251001
```

Use the LangSmith workspace that owns the API key. If the key is organization-scoped, set `LANGSMITH_WORKSPACE_ID` to the target workspace ID. For an EU-hosted workspace, set `LANGSMITH_ENDPOINT=https://eu.api.smith.langchain.com`; the default endpoint is for the standard US instance.

From PowerShell, install the updated backend dependencies, sync the immutable dataset once, then run the benchmark:

```powershell
cd backend
.\.venv313\Scripts\python.exe -m pip install -r requirements.txt
.\.venv313\Scripts\python.exe -m app.evals.sync_dataset
.\.venv313\Scripts\python.exe -m app.evals.run
```

The sync command is idempotent. It creates the named LangSmith dataset and its 10 examples if absent. If a remote dataset with that name has changed or contains unexpected cases, the command stops instead of overwriting/deleting examples; choose a new `LANGSMITH_EVAL_DATASET` name for a new benchmark version.

A full run makes approximately 20 application Claude calls (planner and synthesis for each case) plus 10 judge calls. The model and judge use separate configuration fields but the same Anthropic API key/account by default. LangSmith tracing is enabled only inside the evaluation runner; normal application startup remains untraced unless separately configured. Evaluation prompts, synthetic evidence, outputs, and traces are sent to LangSmith, so do not add private user conversations or secrets to the golden set.

The checked-in benchmark is a starter baseline, not proof of production quality. Review case-level comments and deterministic failures before changing prompts. Expand or revise the golden set deliberately, version it, and compare experiments before accepting changes. These fixtures and their `example.com` links are evaluation-only; they are not real market evidence and are never used by ordinary chat requests.


