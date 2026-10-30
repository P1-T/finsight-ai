import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";
import Home from "./page";
import type { ResearchResponse, StocksResponse } from "@/types/research";
import { formatCompactCurrency } from "@/lib/formatters";

vi.mock("@/lib/api", () => ({
  getStocks: vi.fn(),
  runResearch: vi.fn(),
}));
vi.mock("@/components/charts/StockPriceChart", () => ({
  StockPriceChart: ({ loading, error }: { loading: boolean; error: string | null }) => (
    <div data-testid="stock-chart">{loading ? "Loading chart" : error ?? "Chart"}</div>
  ),
}));

import { getStocks, runResearch } from "@/lib/api";

const stocks: StocksResponse = {
  stocks: [
    { ticker: "AAPL", name: "Apple Inc." },
    { ticker: "NVDA", name: "NVIDIA Corporation" },
    { ticker: "MSFT", name: "Microsoft Corporation" },
  ],
};

const unavailable = { value: null, unavailable_reason: "Not enough historical data." };
const result: ResearchResponse = {
  ticker: "AAPL",
  company_name: "Apple Inc.",
  generated_at: "2026-10-27T10:00:00Z",
  news: {
    status: "succeeded",
    error: null,
    overall_sentiment: "mixed",
    confidence: "Low confidence; headline metadata only.",
    positive_catalysts: ["Product demand reported"],
    negative_catalysts: ["Regulatory risk mentioned"],
    major_developments: ["New product cycle"],
    investor_relevance: "Headlines may affect expectations.",
    evidence_limitations: "Headlines only.",
    lookback: "Last 7 calendar days",
    articles: [{ title: "Apple product update", source: "Example News", published_at: "2026-10-26T12:00:00Z", url: "https://example.com/article" }],
  },
  technical: {
    status: "succeeded",
    error: null,
    as_of_date: "2026-10-26",
    latest_close: { value: 250.25, unavailable_reason: null },
    daily_pct_change: { value: 1.2, unavailable_reason: null },
    return_5d: unavailable,
    return_20d: unavailable,
    sma20: unavailable,
    sma50: unavailable,
    rsi14: unavailable,
    volume_vs_average: "Near the recent average.",
    volatility_note: "Historical dispersion only.",
    short_term_trend: "Above SMA20.",
    medium_term_trend: "Unavailable.",
    momentum: "Moderate.",
    caveats: ["Historical data, not a live quote."],
  },
  chart: { candles: [], sma20: [], sma50: [] },
  summary: {
    news_perspective: "News view.",
    technical_perspective: "Technical view.",
    fundamental_perspective: "Fundamental view.",
    agreement: "Agreement is descriptive.",
    disagreement: "Perspectives differ.",
    missing_information: "Headlines only.",
  },
  fundamental: {
    status: "no_evidence", error: "Latest 10-K not ingested.", filing_date: null, fiscal_year: null, filing_url: null,
    revenue: { ...unavailable, unit: null, fiscal_year: null }, revenue_yoy_growth_pct: { ...unavailable, unit: null, fiscal_year: null },
    operating_margin_pct: { ...unavailable, unit: null, fiscal_year: null }, net_margin_pct: { ...unavailable, unit: null, fiscal_year: null },
    operating_cash_flow: { ...unavailable, unit: null, fiscal_year: null }, capital_expenditures: { ...unavailable, unit: null, fiscal_year: null }, free_cash_flow: { ...unavailable, unit: null, fiscal_year: null }, cash_and_equivalents: { ...unavailable, unit: null, fiscal_year: null },
    overview: null, business_findings: [], key_risks: [], limitations: ["Run ingestion."], citations: [],
  },
  disclaimer: "Experimental research tool. Not financial advice.",
};

describe("FinSight dashboard", () => {
  beforeEach(() => {
    vi.mocked(getStocks).mockResolvedValue(stocks);
    vi.mocked(runResearch).mockResolvedValue(result);
  });

  it("loads supported stock options from the API", async () => {
    render(<Home />);
    await waitFor(() => expect(screen.getByRole("option", { name: /NVIDIA Corporation/ })).toBeInTheDocument());
  });

  it("keeps company choices visible when the backend list cannot be loaded", async () => {
    vi.mocked(getStocks).mockRejectedValue(new Error("Could not load the supported stocks."));
    render(<Home />);
    expect(screen.getByRole("option", { name: /Apple Inc/ })).toBeInTheDocument();
    expect(screen.getByRole("option", { name: /NVIDIA Corporation/ })).toBeInTheDocument();
    expect(screen.getByRole("option", { name: /Microsoft Corporation/ })).toBeInTheDocument();
    expect(await screen.findByText("Could not load the supported stocks.")).toBeInTheDocument();
    expect(screen.getByRole("combobox", { name: "Company" })).toBeEnabled();
  });

  it("shows an explicit loading state while research runs", async () => {
    let resolveResearch: (value: ResearchResponse) => void = () => undefined;
    vi.mocked(runResearch).mockReturnValue(new Promise((resolve) => { resolveResearch = resolve; }));
    render(<Home />);
    await screen.findByRole("option", { name: /Apple Inc/ });
    fireEvent.click(screen.getByRole("button", { name: /Run research/i }));
    expect(screen.getByRole("button", { name: /Researching/i })).toBeDisabled();
    expect(screen.getByText("Reviewing recent news headlines…")).toBeInTheDocument();
    resolveResearch(result);
  });

  it("renders analysis, original article link, and unavailable metrics", async () => {
    render(<Home />);
    await screen.findByRole("option", { name: /Apple Inc/ });
    fireEvent.click(screen.getByRole("button", { name: /Run research/i }));
    expect(await screen.findByText("Low confidence; headline metadata only.")).toBeInTheDocument();
    const link = screen.getByRole("link", { name: /Apple product update/ });
    expect(link).toHaveAttribute("href", "https://example.com/article");
    expect(link).toHaveAttribute("target", "_blank");
    expect(screen.getAllByText("Unavailable").length).toBeGreaterThan(0);
    expect(screen.getByText("Combined perspective")).toBeInTheDocument();
  });

  it("shows agent failure alongside the successful agent's result", async () => {
    vi.mocked(runResearch).mockResolvedValue({
      ...result,
      news: { ...result.news, status: "failed", error: "GDELT unavailable." },
    });
    render(<Home />);
    await screen.findByRole("option", { name: /Apple Inc/ });
    fireEvent.click(screen.getByRole("button", { name: /Run research/i }));
    expect(await screen.findByText("GDELT unavailable.")).toBeInTheDocument();
    expect(screen.getByText("Above SMA20.")).toBeInTheDocument();
  });

  it("renders the fundamental filing metrics and original SEC citation", async () => {
    vi.mocked(runResearch).mockResolvedValue({
      ...result,
      fundamental: {
        ...result.fundamental,
        status: "succeeded",
        error: null,
        filing_date: "2026-02-01",
        fiscal_year: 2025,
        filing_url: "https://www.sec.gov/Archives/edgar/data/1/filing.htm",
        revenue: { value: 125000000, unit: "USD", fiscal_year: 2025, unavailable_reason: null },
        overview: "The filing describes the operating business and principal risks.",
        business_findings: [{ topic: "Business", finding: "Revenue comes from reported product sales.", citation_urls: ["https://www.sec.gov/Archives/edgar/data/1/filing.htm"] }],
        citations: [{ section: "Item 1. Business", excerpt: "The company describes its products.", url: "https://www.sec.gov/Archives/edgar/data/1/filing.htm" }],
      },
    });
    render(<Home />);
    await screen.findByRole("option", { name: /Apple Inc/ });
    fireEvent.click(screen.getByRole("button", { name: /Run research/i }));
    expect(await screen.findByText("The filing describes the operating business and principal risks.")).toBeInTheDocument();
    expect(screen.getByText("Revenue")).toBeInTheDocument();
    expect(screen.getAllByRole("link", { name: /Open source 10-K on SEC/ })).toHaveLength(1);
    expect(screen.queryByText("Retrieved filing excerpts")).not.toBeInTheDocument();
    expect(screen.queryByText("Evidence limits")).not.toBeInTheDocument();
    expect(screen.queryByText("Limitations")).not.toBeInTheDocument();
    expect(screen.getByText("$125.0M")).toBeInTheDocument();
  });

  it("shows six news articles and findings initially, with view more controls", async () => {
    vi.mocked(runResearch).mockResolvedValue({
      ...result,
      news: { ...result.news, articles: Array.from({ length: 8 }, (_, index) => ({
        title: `Article ${index + 1}`, source: "Example", published_at: null, url: `https://example.com/${index + 1}`,
      })) },
      fundamental: {
        ...result.fundamental,
        status: "succeeded",
        filing_url: "https://www.sec.gov/Archives/edgar/data/1/filing.htm",
        business_findings: Array.from({ length: 8 }, (_, index) => ({ topic: `Finding ${index + 1}`, finding: `Detail ${index + 1}`, citation_urls: [] })),
      },
    });
    render(<Home />);
    await screen.findByRole("option", { name: /Apple Inc/ });
    fireEvent.click(screen.getByRole("button", { name: /Run research/i }));
    expect(await screen.findByRole("link", { name: /Article 1/ })).toBeInTheDocument();
    expect(screen.getByRole("link", { name: /Article 6/ })).toBeInTheDocument();
    expect(screen.queryByRole("link", { name: /Article 7/ })).not.toBeInTheDocument();
    expect(screen.getByText("Finding 6")).toBeInTheDocument();
    expect(screen.queryByText("Finding 7")).not.toBeInTheDocument();

    fireEvent.click(screen.getByRole("button", { name: "View all 8 articles" }));
    fireEvent.click(screen.getByRole("button", { name: "View all 8 findings" }));
    expect(screen.getByRole("link", { name: /Article 8/ })).toBeInTheDocument();
    expect(screen.getByText("Finding 8")).toBeInTheDocument();
  });

  it("formats large financial values in millions or billions", () => {
    expect(formatCompactCurrency(1_250_000_000)).toBe("$1.3B");
    expect(formatCompactCurrency(125_000_000)).toBe("$125.0M");
  });

  it("shows API request errors with retry action", async () => {
    vi.mocked(runResearch).mockRejectedValue(new Error("Backend is unreachable."));
    render(<Home />);
    await screen.findByRole("option", { name: /Apple Inc/ });
    fireEvent.click(screen.getByRole("button", { name: /Run research/i }));
    expect(await screen.findByRole("alert")).toHaveTextContent("Backend is unreachable.");
    expect(screen.getByRole("button", { name: "Retry" })).toBeInTheDocument();
  });

  it("changes the ticker sent to research when the selector changes", async () => {
    render(<Home />);
    await screen.findByRole("option", { name: /NVIDIA Corporation/ });
    fireEvent.change(screen.getByLabelText("Company"), { target: { value: "NVDA" } });
    fireEvent.click(screen.getByRole("button", { name: /Run research/i }));
    await waitFor(() => expect(runResearch).toHaveBeenCalledWith("NVDA"));
  });
});
