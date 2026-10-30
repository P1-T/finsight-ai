import type { ResearchResponse, StocksResponse, Ticker } from "@/types/research";

const API_BASE = process.env.NEXT_PUBLIC_API_BASE_URL ?? "http://localhost:8000";

export async function getStocks(signal?: AbortSignal): Promise<StocksResponse> {
  const response = await fetch(`${API_BASE}/api/stocks`, { signal, cache: "no-store" });
  if (!response.ok) throw new Error("Could not load the supported stocks.");
  return (await response.json()) as StocksResponse;
}

export async function runResearch(ticker: Ticker, signal?: AbortSignal): Promise<ResearchResponse> {
  const response = await fetch(`${API_BASE}/api/research`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ ticker }),
    signal,
    cache: "no-store",
  });
  const payload: unknown = await response.json().catch(() => null);
  if (!response.ok) {
    const detail =
      typeof payload === "object" && payload !== null && "detail" in payload &&
      typeof payload.detail === "string"
        ? payload.detail
        : `Research request failed (${response.status}).`;
    if (typeof payload === "object" && payload !== null && "news" in payload && "technical" in payload) {
      return payload as ResearchResponse;
    }
    throw new Error(detail);
  }
  return payload as ResearchResponse;
}
