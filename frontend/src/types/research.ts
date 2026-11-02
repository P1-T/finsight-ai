import type { UIMessage } from "ai";

export type ResearchStage = { stage: "planning" | "research" | "synthesis"; label: string };
export type ResearchLayout = { template: string; components: string[] };
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

export type QuarterlyPerformanceResponse = ResponseBase & {
  template: "quarterly_performance";
  company: CompanyIdentity;
  market_snapshot?: MarketSnapshot | null;
  narrative: {
    summary: string;
    period: string;
    reported_facts: {
      label: string;
      value: number;
      range_end?: number | null;
      unit: "percent" | "USD" | "EUR" | "USD_billions" | "EUR_billions" | "USD_millions" | "EUR_millions" | "count";
      fact_kind: "reported" | "guidance";
      comparison_value?: number | null;
      comparison_label?: string | null;
      period: string;
      source_ids: string[];
      evidence_quote: string;
    }[];
    positive_drivers: EvidenceClaim[];
    risks: EvidenceClaim[];
    source_ids: string[];
  };
};

export type ResearchAnswerResponse = ResponseBase & {
  template: SpecificResearchTemplate;
  narrative: { answer: string; source_ids: string[] };
};

export type SpecificResearchTemplate =
  | "research_answer" | "valuation_analysis" | "dividend_analysis" | "risk_analysis" | "sector_analysis"
  | "forward_outlook" | "earnings_preview" | "revenue_analysis" | "growth_analysis"
  | "profitability_analysis" | "cash_flow_analysis" | "balance_sheet_analysis" | "valuation_comparison"
  | "price_momentum" | "trend_analysis" | "support_resistance" | "volume_analysis" | "market_reaction"
  | "catalyst_analysis" | "analyst_sentiment" | "insider_activity" | "institutional_ownership"
  | "short_interest" | "options_activity" | "macro_sensitivity";

export type VisualResponseTemplate =
  | "company_analysis" | "stock_comparison" | "news_analysis" | "technical_analysis"
  | "quarterly_performance" | SpecificResearchTemplate | "clarification";

export type ClarificationResponse = ResponseBase & {
  template: "clarification";
  narrative: { question: string };
  unresolved_company_query?: string | null;
  company_suggestions?: CompanyIdentity[];
};

export type DataProvenance = { kind: "live" | "illustrative" | "mixed" | "unavailable"; label: string; as_of?: string | null };
export type VisualMetric = { label: string; value: string; detail?: string | null };
export type DataChartBlock = {
  type: "data_chart";
  chart_type: "line" | "bar" | "donut";
  title: string;
  unit: "percent" | "USD" | "EUR" | "USD_billions" | "EUR_billions" | "USD_millions" | "EUR_millions" | "count";
  data: { label: string; value: number; source_ids: string[] }[];
  provenance: DataProvenance;
  source_ids: string[];
};
export type VisualBlock =
  | { type: "company_header"; company: CompanyIdentity; description: string; provenance: DataProvenance }
  | { type: "metric_grid"; title: string; metrics: VisualMetric[]; provenance: DataProvenance }
  | { type: "price_chart"; title: string; points: PricePoint[]; provenance: DataProvenance }
  | { type: "fundamental_cards"; title: string; metrics: { label: string; value: string; detail: string }[]; provenance: DataProvenance }
  | { type: "scenario_cards"; scenario: "bull" | "bear"; title: string; points: { title: string; detail: string; provenance: DataProvenance; source_ids: string[] }[] }
  | { type: "news_timeline"; title: string; items: { title: string; detail: string; date?: string | null; url?: string | null; provenance: DataProvenance }[] }
  | { type: "comparison_table"; title: string; rows: { ticker: string; name: string; latest_close: string; daily_change: string; period_return: string; revenue_growth: string; margin: string }[]; provenance: DataProvenance }
  | { type: "fact_grid"; title: string; period: string; metrics: { label: string; value: string; detail?: string | null; range_low?: string | null; range_high?: string | null; source_ids: string[] }[]; provenance: DataProvenance }
  | DataChartBlock
  | { type: "takeaways"; title: string; items: string[] }
  | { type: "answer_card"; title: string; body: string };

export type VisualResearchResponseV2 = {
  schema_version: 2;
  template: Exclude<VisualResponseTemplate, "quarterly_performance">;
  intent_id?: string | null;
  intent_confidence?: number | null;
  title: string;
  summary: string;
  blocks: VisualBlock[];
  sources: SourceReference[];
  unresolved_company_query?: string | null;
  company_suggestions?: CompanyIdentity[];
  generated_by: "claude" | "fallback";
};

export type VisualResearchResponseV3 = {
  schema_version: 3;
  template: VisualResponseTemplate;
  intent_id?: string | null;
  intent_confidence?: number | null;
  title: string;
  summary: string;
  blocks: VisualBlock[];
  sources: SourceReference[];
  unresolved_company_query?: string | null;
  company_suggestions?: CompanyIdentity[];
  generated_by: "claude" | "fallback";
};
export type VisualResearchResponse = VisualResearchResponseV2 | VisualResearchResponseV3;

export type LegacyResearchResponse =
  | CompanyAnalysisResponse
  | StockComparisonResponse
  | NewsAnalysisResponse
  | TechnicalAnalysisResponse
  | QuarterlyPerformanceResponse
  | ResearchAnswerResponse
  | ClarificationResponse;
export type ResearchResponse = VisualResearchResponse | LegacyResearchResponse;

export type ChatData = {
  "research-stage": ResearchStage;
  "research-layout": ResearchLayout;
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
