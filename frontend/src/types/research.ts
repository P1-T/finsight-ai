import type { UIMessage } from "ai";

export type ResearchStage = { stage: "planning" | "research" | "synthesis"; label: string };
export type ResearchTool = "market_data" | "web_search" | "news_search";
export type ResearchToolStatus = {
  tool: ResearchTool;
  status: "running" | "succeeded" | "failed" | "no_evidence";
  detail?: string | null;
};
export type ChatHistoryTurn = { role: "user" | "assistant"; text: string };

export type CompanyIdentity = { ticker: string; name: string; exchange: string };
export type CompanySearchResponse = { companies: CompanyIdentity[] };
export type SourceReference = {
  id: string;
  title: string;
  provider: string;
  url?: string | null;
  published_at?: string | null;
  company_tickers: string[];
};
export type NewsArticle = {
  source_id: string;
  title: string;
  source?: string | null;
  published_at?: string | null;
  url: string;
  snippet?: string | null;
  company_tickers: string[];
};
export type NewsCoverage = { ticker: string; relevant_result_count: number };
export type MetricKey =
  | "latest_close"
  | "daily_pct_change"
  | "return_5d"
  | "return_20d"
  | "sma20"
  | "sma50"
  | "rsi14"
  | "volume_vs_average"
  | "volatility_note";
export type MarketMetric = { key: MetricKey; value: number | string; unit: "usd" | "percent" | "index" | "text" };
export type PricePoint = { date: string; close: number };
export type MarketSnapshot = { ticker: string; as_of_date: string; period: "1mo" | "3mo" | "6mo" | "1y"; metrics: MarketMetric[]; source_id: string; price_series?: PricePoint[] };
export type EvidenceClaim = { title: string; detail: string; source_ids: string[] };
export type CompanyInsight = { ticker: string; summary: string; source_ids: string[] };
export type SentimentInsight = {
  ticker: string;
  sentiment: "positive" | "neutral" | "negative" | "mixed";
  rationale: string;
  source_ids: string[];
};

type ResponseBase = {
  schema_version: 1;
  title: string;
  companies: CompanyIdentity[];
  sources: SourceReference[];
  limitations: string[];
};

export type CompanyAnalysisResponse = ResponseBase & {
  template: "company_analysis";
  company: CompanyIdentity;
  market_snapshot?: MarketSnapshot | null;
  news_articles: NewsArticle[];
  news_coverage: NewsCoverage[];
  narrative: {
    summary: string;
    source_ids: string[];
    positive_drivers: EvidenceClaim[];
    risks: EvidenceClaim[];
  };
};

export type StockComparisonResponse = ResponseBase & {
  template: "stock_comparison";
  market_snapshots: MarketSnapshot[];
  news_articles: NewsArticle[];
  news_coverage: NewsCoverage[];
  narrative: { summary: string; source_ids: string[]; company_views: CompanyInsight[]; comparison_points: EvidenceClaim[] };
};

export type NewsAnalysisResponse = ResponseBase & {
  template: "news_analysis";
  news_articles: NewsArticle[];
  news_coverage: NewsCoverage[];
  narrative: { summary: string; source_ids: string[]; company_sentiment: SentimentInsight[] };
};

export type TechnicalAnalysisResponse = ResponseBase & {
  template: "technical_analysis";
  market_snapshots: MarketSnapshot[];
  narrative: { summary: string; source_ids: string[]; observations: EvidenceClaim[] };
};

export type ResearchAnswerResponse = ResponseBase & {
  template: "research_answer";
  narrative: { answer: string; source_ids: string[] };
};

export type ClarificationResponse = ResponseBase & {
  template: "clarification";
  narrative: { question: string };
  unresolved_company_query?: string | null;
  company_suggestions?: CompanyIdentity[];
};

export type DataProvenance = { kind: "live" | "illustrative" | "mixed" | "unavailable"; label: string; as_of?: string | null };
export type VisualMetric = { label: string; value: string; detail?: string | null };
export type VisualBlock =
  | { type: "company_header"; company: CompanyIdentity; description: string; provenance: DataProvenance }
  | { type: "metric_grid"; title: string; metrics: VisualMetric[]; provenance: DataProvenance }
  | { type: "price_chart"; title: string; points: PricePoint[]; provenance: DataProvenance }
  | { type: "fundamental_cards"; title: string; metrics: { label: string; value: string; detail: string }[]; provenance: DataProvenance }
  | { type: "scenario_cards"; scenario: "bull" | "bear"; title: string; points: { title: string; detail: string; provenance: DataProvenance; source_ids: string[] }[] }
  | { type: "news_timeline"; title: string; items: { title: string; detail: string; date?: string | null; url?: string | null; provenance: DataProvenance }[] }
  | { type: "comparison_table"; title: string; rows: { ticker: string; name: string; latest_close: string; daily_change: string; period_return: string; revenue_growth: string; margin: string }[]; provenance: DataProvenance }
  | { type: "takeaways"; title: string; items: string[] }
  | { type: "answer_card"; title: string; body: string };

export type VisualResearchResponse = {
  schema_version: 2;
  template: "company_analysis" | "stock_comparison" | "news_analysis" | "technical_analysis" | "research_answer" | "clarification";
  title: string;
  summary: string;
  blocks: VisualBlock[];
  sources: SourceReference[];
  unresolved_company_query?: string | null;
  company_suggestions?: CompanyIdentity[];
  generated_by: "claude" | "fallback";
};

export type LegacyResearchResponse =
  | CompanyAnalysisResponse
  | StockComparisonResponse
  | NewsAnalysisResponse
  | TechnicalAnalysisResponse
  | ResearchAnswerResponse
  | ClarificationResponse;
export type ResearchResponse = VisualResearchResponse | LegacyResearchResponse;

export type ChatData = {
  "research-stage": ResearchStage;
  "tool-status": ResearchToolStatus;
  "research-response": ResearchResponse;
};
export type ResearchChatMessage = UIMessage<Record<string, never>, ChatData>;
export type SavedConversation = {
  id: string;
  title: string;
  updatedAt: string;
  messages: ResearchChatMessage[];
};
