export type Ticker = "AAPL" | "NVDA" | "MSFT";
export type AgentStatus = "succeeded" | "failed" | "no_evidence";
export type SentimentLabel = "positive" | "neutral" | "negative" | "mixed";

export type StockInfo = {
  ticker: Ticker;
  name: string;
};

export type StocksResponse = {
  stocks: StockInfo[];
};

export type NewsArticle = {
  title: string;
  source: string | null;
  published_at: string | null;
  url: string;
};

export type NewsAnalysis = {
  status: AgentStatus;
  error: string | null;
  overall_sentiment: SentimentLabel | null;
  confidence: string | null;
  positive_catalysts: string[];
  negative_catalysts: string[];
  major_developments: string[];
  investor_relevance: string | null;
  evidence_limitations: string | null;
  lookback: string | null;
  articles: NewsArticle[];
};

export type MetricValue = {
  value: number | null;
  unavailable_reason: string | null;
};

export type TechnicalAnalysis = {
  status: AgentStatus;
  error: string | null;
  as_of_date: string | null;
  latest_close: MetricValue;
  daily_pct_change: MetricValue;
  return_5d: MetricValue;
  return_20d: MetricValue;
  sma20: MetricValue;
  sma50: MetricValue;
  rsi14: MetricValue;
  volume_vs_average: string | null;
  volatility_note: string | null;
  short_term_trend: string | null;
  medium_term_trend: string | null;
  momentum: string | null;
  caveats: string[];
};

export type FundamentalMetric = {
  value: number | null;
  unit: string | null;
  fiscal_year: number | null;
  unavailable_reason: string | null;
};

export type FilingCitation = { section: string; excerpt: string; url: string };
export type FundamentalFinding = { topic: string; finding: string; citation_urls: string[] };
export type FundamentalAnalysis = {
  status: AgentStatus;
  error: string | null;
  filing_date: string | null;
  fiscal_year: number | null;
  filing_url: string | null;
  revenue: FundamentalMetric;
  revenue_yoy_growth_pct: FundamentalMetric;
  operating_margin_pct: FundamentalMetric;
  net_margin_pct: FundamentalMetric;
  operating_cash_flow: FundamentalMetric;
  capital_expenditures: FundamentalMetric;
  free_cash_flow: FundamentalMetric;
  cash_and_equivalents: FundamentalMetric;
  overview: string | null;
  business_findings: FundamentalFinding[];
  key_risks: FundamentalFinding[];
  limitations: string[];
  citations: FilingCitation[];
};

export type ChartPoint = {
  time: string;
  open: number;
  high: number;
  low: number;
  close: number;
  volume: number;
};

export type OverlayPoint = {
  time: string;
  value: number;
};

export type ChartSeries = {
  candles: ChartPoint[];
  sma20: OverlayPoint[];
  sma50: OverlayPoint[];
};

export type ResearchSummaryModel = {
  news_perspective: string;
  technical_perspective: string;
  fundamental_perspective: string;
  agreement: string;
  disagreement: string;
  missing_information: string;
};

export type ResearchResponse = {
  ticker: Ticker;
  company_name: string;
  generated_at: string;
  news: NewsAnalysis;
  technical: TechnicalAnalysis;
  fundamental: FundamentalAnalysis;
  chart: ChartSeries;
  summary: ResearchSummaryModel;
  disclaimer: string;
};
