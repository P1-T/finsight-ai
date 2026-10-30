# FinSight AI

FinSight AI is a private portfolio demonstration of an AI-assisted equity research dashboard. It covers AAPL, NVDA, and MSFT with three specialist analyses: recent headline sentiment, technical interpretation of historical OHLCV, and a retrieval-grounded fundamental summary of the latest SEC 10-K. It is an educational research tool, not financial advice or a trading product.

## Architecture

```text
Next.js App Router dashboard
        │ REST /api/research
        ▼
      FastAPI ── Pydantic request / response validation
        │
        ▼
      LangGraph fan-out
       ├── News agent ── MarketNewsAPI ── Claude structured output
       ├── Technical agent ── yfinance ── pandas indicators ── Claude structured output
       └── Fundamental agent ── Pinecone retrieval ── SEC 10-K + XBRL facts ── Claude structured output
        │
        ▼
Python summary service combines results; no synthesis LLM call
```

The dashboard fetches the supported stock list from the API. Research is synchronous; independent LangGraph nodes run concurrently and each agent reports its own status. Partial results are returned when one agent fails. If all agents fail, the API returns the structured report with HTTP 502.

## Requirements

- Node.js 20.9 or newer (local project scaffold was created with Node 24)
- Python 3.13 or 3.14 recommended. Python 3.15 compatibility depends on binary wheel support for pandas and the AI libraries.
- An Anthropic API key for AI interpretations
- A free [MarketNewsAPI](https://marketnewsapi.com/) API key for news retrieval
- A free [Pinecone](https://www.pinecone.io/) account and API key for 10-K retrieval
- A contact email in `SEC_USER_AGENT` for SEC EDGAR access

The Anthropic key is read only by the backend. Cursor or Claude subscriptions do not automatically provide API access or credits.

## Local development

Open two terminals from the repository root.

### Backend

```powershell
cd backend
py -3.13 -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
Copy-Item .env.example .env
# Configure ANTHROPIC_API_KEY, MARKETNEWSAPI_KEY, PINECONE_API_KEY, and SEC_USER_AGENT in backend/.env
uvicorn app.main:app --reload --port 8000
```

The SEC `SEC_USER_AGENT` value must identify the application and include a monitored contact email. Keep all keys in `backend/.env`; never place them in frontend variables.

### Ingest the latest annual reports

Run this once after configuring Pinecone and SEC access (or again when you want to refresh the latest filing):

```powershell
cd backend
python -m app.rag.ingest --all
# Or ingest one supported company:
python -m app.rag.ingest --ticker NVDA
```

The command finds each company's latest SEC 10-K from the SEC submissions feed, downloads the filing HTML and company facts, extracts Items 1, 1A, 7, and 8, chunks each section with a small overlap, and upserts a compact set of XBRL metrics and section chunks into a ticker-specific Pinecone namespace. It verifies the new accession before removing older filing chunks. If that accession is already present, a rerun skips the embedding/upsert work. No scheduler is installed: rerun the command to refresh each company after a new 10-K is filed. The frontend reports `No evidence` until that ticker has been ingested.

Pinecone's document index performs hosted embedding on upsert and query with `llama-text-embed-v2`; the application does not generate or store vectors itself. Each text chunk is kept around 380 words (conservative relative to the model's input window), with 55 words of overlap. Five focused retrieval searches run per research request. The latest filing is small relative to the free-tier capacity, but plan quotas and hosted-model limits are controlled by Pinecone and may change. Changing the embedding model requires a new index and complete re-ingestion.

If Python 3.13 is not installed, create the environment with an installed supported interpreter (for example `python -m venv .venv`). Then open <http://localhost:8000/docs> for the API schema.

### Frontend

```powershell
cd frontend
Copy-Item .env.example .env.local
npm ci
npm run dev
```

Open <http://localhost:3000>. The frontend environment variable sets only the public backend base URL. Never put the Anthropic key in a frontend environment variable.

## API

### `GET /api/health`

Returns `{ "status": "ok" }` without exposing configuration.

### `GET /api/stocks`

Returns the three supported tickers and company names.

### `POST /api/research`

Request:

```json
{ "ticker": "AAPL" }
```

The response includes a UTC `generated_at`, per-agent status, original article metadata and links, market as-of date, chart candles and SMA overlays, technical metrics, filing facts, filing citation links, deterministic summary, and disclaimer. Unsupported tickers receive a validation error. Agent-specific errors are safe messages; backend logs retain diagnostic details for unexpected workflow failures.

## Agents and data

### News and sentiment

- Queries MarketNewsAPI for the selected stock ticker, stock news and press releases from the last seven calendar days, up to 20 articles. The API key is read from `backend/.env` and never sent to the browser.
- Normalizes and deduplicates headline metadata and drops non-HTTP(S) URLs.
- Sends only headline metadata to Claude. The model is instructed not to claim it read the full article.
- Displays the provider's original article URLs, publisher names, and available timestamps. Missing metadata stays missing.
- “No evidence” means the provider returned no matching articles; it does not prove no company news exists.
- The free MarketNewsAPI tier is intended for prototyping and currently allows 100 REST requests per day with a 15-minute delay. Availability and plan limits are controlled by the provider.

### Technical analysis

- Retrieves one year of daily OHLCV history through yfinance with its unadjusted `Close` field; the chart displays roughly the latest six months. Historical provider values can reflect corporate actions such as splits.
- Calculates daily, five-session, and 20-session returns; SMA20, SMA50, RSI14; latest volume relative to the prior 20-session mean; and 20-session return volatility in Python.
- Uses completed provider sessions and labels the latest available session date. It is not a live quote.
- Indicators display as unavailable with a reason when required history is missing.

### Model interpretation

Each specialist makes one structured Claude call. Pydantic validates the model output, and Python combines the validated results without a synthesis call. Filing citations are mapped back to retrieved Pinecone chunk IDs and the original SEC filing URL; model-generated URLs are not accepted. Fundamental metrics are derived in Python from SEC XBRL facts filtered to the exact latest 10-K accession, with comparative revenue growth only when the same filing contains both periods. Headline sentiment, technical indicators, and filing interpretation are evidence summaries, not forecasts or guaranteed signals.

## Tests and checks

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

Automated tests mock all external APIs and model responses; they do not require live market/news access or API credits.

## Known limitations

- MarketNewsAPI coverage, relevance, timestamps, and publisher metadata vary. The free tier is delayed and rate-limited; V1 does not retrieve or verify full article text. The previous GDELT provider remains in the code as an optional provider implementation, but is no longer used by default.
- SEC filings are parsed from inline HTML; scanned or atypically structured filings may need parser improvements. Only the selected sections and a compact set of XBRL facts are retrieved. This is not a complete audit of the report. Ingestion is manual and the dashboard does not automatically detect newly filed reports.
- Pinecone integrated embedding and usage limits depend on the selected account plan. The index embedding schema is fixed at creation; a model change means creating a replacement index and re-ingesting the three latest filings.
- yfinance is an unofficial interface to Yahoo Finance data; upstream availability, adjustments, and rate limits can change.
- The application has no database, login, saved reports, caching layer, streaming progress, or realtime feed.
- Synchronous research depends on upstream latency and is bounded by configured provider/model timeouts. An HTTP timeout cannot guarantee cancellation of a provider call already running in a worker thread.
- AI interpretations may be incomplete or inaccurate. The system is not validated for professional investment decisions.

## Financial disclaimer

FinSight AI is an experimental research and educational tool. Its outputs may be incomplete or inaccurate and are not financial advice or recommendations to buy or sell securities.
