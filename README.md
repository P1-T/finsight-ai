# FinSight AI

FinSight AI is a visual, open-ended AI chat demo. Users can ask general finance questions, research a listed company, or compare companies. Claude can choose the response layout from an allowlisted set of React components; the backend fills those components with available provider data or clearly labeled synthetic demo values. Chat history stays in the browser. This is a portfolio demonstration, not an investment research or trading product.

## V3 request flow

```text
Next.js chat + browser-local history
                 │ prompt + recent turns (SSE)
                 ▼
FastAPI → LangGraph
                 │
                 ├─ Claude structured intent, tool, and visual-component plan
                 ├─ SEC company-directory validation
                 ├─ Selected tools run concurrently
                 │    ├─ yfinance historical market data + Python indicators
                 │    ├─ DDGS web/news search
                 │    └─ deterministic synthetic fixture fallback
                 ├─ Claude structured narrative (or local fallback)
                 ├─ Pydantic visual-response composer
                 └─ typed blocks streamed to the React component registry
```

Each researched prompt uses at most two bounded Claude calls: one tool/layout planning call and one synthesis call. Set `LLM_ENABLED=false` to skip both calls and use deterministic fallback routing and copy. Provider and model failures also fall back gracefully. Tool plans are limited to six companies, two queries per search type, five results per query, and twelve total news/web results. Independent providers run concurrently. Company analysis requests a consistent bundle of price history, market metrics, and recent web/news results; each unavailable area can still render using synthetic fixtures.

The first Claude response follows a strict schema with an intent, company names, bounded provider requests, an ordered visual-component selection, and optional clarification. The server does not execute arbitrary model instructions. It validates company names against the exchange-listed company directory and maps validated entries to market-data symbols. If the plan cannot resolve a company, the workflow asks for clarification rather than silently researching a different company.

The final API response is a versioned list of typed blocks such as `company_header`, `metric_grid`, `price_chart`, `fundamental_cards`, `scenario_cards`, `news_timeline`, `comparison_table`, `takeaways`, and `answer_card`. The React registry maps only these allowlisted block types; Claude never returns JSX, HTML, or executable component code. Numeric market data and chart series are supplied by the backend. Stored company fixtures and deterministic fallback data populate fundamentals and bull/bear scenarios when live data is unavailable; a single disclosure appears at the bottom of the response, after the consolidated sources. Older browser-saved responses continue to render through the legacy template renderer.

The API streams progress, a typed `data-research-response` message part, and a readable text representation for conversation history and fallback accessibility. The schema version allows visual response payloads to evolve without coupling the backend to React implementations.

### Visual response building blocks

- **Company research:** company hero, market metrics, a six-month price chart, fundamental cards, four-point bull and bear case scenarios, and recent coverage.
- **Company comparison:** a compact comparison table plus per-company price charts; the table carries the key market and fundamental fields.
- **News or technical questions:** the planner selects focused timeline, metric, chart, and takeaway blocks.
- **General questions:** a concise answer card.

The fundamental cards currently contain synthetic revenue, growth, margins, free cash flow, cash, and debt fields to demonstrate realistic-looking visual building blocks. They are not fetched company facts. The saved popular-company fixtures live in `backend/app/data/demo_company_fixtures.json`; other symbols receive stable per-ticker fallback values. No dummy URL, article, or source citation is created.

## Sources and limitations

- **Market data:** yfinance daily OHLCV; pandas calculates price returns, moving averages, RSI, volume comparison, and historical volatility. The latest date is the last available provider session, not a live quote. Yahoo Finance credentials are not required. Synthetic price history is used and labeled if retrieval fails.
- **News and web search:** DDGS DuckDuckGo search; news and web are separate selectable tools over the same free, no-key provider. Results contain titles, metadata, and short snippets, not full article text. DDGS is best-effort and may be throttled or change behavior.
- **Company resolution:** SEC's public exchange-listed company directory. This supports broad US-exchange coverage, not guaranteed coverage of every symbol by every upstream provider. A ticker may be used internally to call yfinance; users do not select a ticker to establish chat context.
- **Illustrative financial data:** fundamental figures, fallback price history, and scenario points may be synthetic. They exist to populate the visual demo, not to describe the named company. The interface shows one disclosure after the source list rather than repeating labels on every card.
- **Model:** `ANTHROPIC_MODEL` selects Claude; `ANTHROPIC_API_KEY` stays on the backend. Claude API usage is billed separately from IDE subscriptions. `LLM_ENABLED=false` disables model calls and uses deterministic demo composition.
- **Chat history:** saved only in browser `localStorage`; it is not synchronized or stored on the backend.

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

The server streams planning/research stages and active tool status, followed by a `data-research-response` part with `schema_version: 2`, ordered block payloads, provenance labels, and consolidated sources. The request has no selected-ticker field. Unsupported extra request fields are rejected.

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

## Disclaimer

FinSight AI is an experimental research and educational tool. Its output may be incomplete or inaccurate and is not financial advice or a recommendation to buy or sell securities.
