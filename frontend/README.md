# FinSight AI frontend

Visual Next.js App Router chat using the Vercel AI SDK. The UI streams research stages and active tool status, then renders a versioned, typed response composition through an allowlisted React block registry: company hero, metric cards, price chart, fundamental cards, bull/bear scenario cards, news timeline, comparison table, and takeaways. The API also sends a text representation for conversation history. Chat history remains in browser `localStorage`.

The `VisualResearchResponse` type in `src/types/research.ts` mirrors the backend's Pydantic contract. `VisualBlockRenderer` maps each validated block type to a fixed React component; it never renders model-provided HTML or code. Synthetic values are disclosed once after the consolidated source list. `ResearchResponseView` also supports older saved response payloads and hides RSI, volume-versus-average, and volatility from historical market snapshots.

Run from this directory:

```powershell
npm ci
npm run dev
```

Open <http://localhost:3000>. The default backend URL is `http://localhost:8000`. Set `NEXT_PUBLIC_API_BASE_URL` in `.env.local` only if the backend runs elsewhere. The frontend has no API credentials. See the repository README for server setup and provider details.

Checks: `npm test`, `npm run lint`, `npm run typecheck`, and `npm run build`.
