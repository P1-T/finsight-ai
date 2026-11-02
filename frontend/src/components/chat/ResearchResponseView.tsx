"use client";

import { useState } from "react";
import { formatCurrency, formatDate, formatPercent } from "@/lib/formatters";
import type {
  CompanyAnalysisResponse,
  EvidenceClaim,
  MarketMetric,
  MarketSnapshot,
  LegacyResearchResponse,
  NewsAnalysisResponse,
  ResearchResponse,
  StockComparisonResponse,
  TechnicalAnalysisResponse,
} from "@/types/research";
import { VisualResearchAnswer } from "@/components/chat/VisualBlockRenderer";
import { CompanyResolutionPicker } from "@/components/chat/CompanyResolutionPicker";
import { ArrowRight, Check, Copy, ThumbsDown, ThumbsUp } from "lucide-react";
import type { CompanyIdentity } from "@/types/research";

const METRIC_LABELS: Partial<Record<MarketMetric["key"], string>> = {
  latest_close: "Latest close",
  daily_pct_change: "Daily change",
  return_5d: "5-session return",
  return_20d: "20-session return",
  sma20: "SMA 20",
  sma50: "SMA 50",
};

function metricValue(metric: MarketMetric): string {
  if (typeof metric.value === "string") return metric.value;
  if (metric.unit === "usd") return formatCurrency(metric.value);
  if (metric.unit === "percent") return formatPercent(metric.value);
  return metric.value.toFixed(1);
}

function EvidenceList({ title, items }: { title: string; items: EvidenceClaim[] }) {
  if (!items.length) return null;
  return <section className="response-section">
    <h3>{title}</h3>
    <ul>{items.map((item, index) => <li key={`${item.title}-${index}`}><strong>{item.title}.</strong> {item.detail}</li>)}</ul>
  </section>;
}

function MetricStrip({ snapshot }: { snapshot: MarketSnapshot }) {
  const visibleMetrics = snapshot.metrics.filter((metric) => !["rsi14", "volume_vs_average", "volatility_note"].includes(metric.key));
  if (!visibleMetrics.length) return null;
  return <section className="response-section">
    <div className="response-section-heading"><h3>Historical market snapshot</h3><span>As of {formatDate(snapshot.as_of_date)}</span></div>
    <ul className="response-metric-list">{visibleMetrics.map((metric) => <li key={metric.key}><strong>{METRIC_LABELS[metric.key] ?? metric.key}:</strong> {metricValue(metric)}</li>)}</ul>
  </section>;
}

function ResponseSources({ sources }: { sources: ResearchResponse["sources"] }) {
  if (!sources.length) return null;
  return <details className="response-sources"><summary>Sources ({sources.length})</summary>
    <ol>{sources.map((source) => <li key={source.id}>
      {source.url ? <a href={source.url} target="_blank" rel="noreferrer">{source.title}</a> : <span>{source.title}</span>}
      <small>{source.id} · {source.provider}{source.published_at ? ` · ${formatDate(source.published_at)}` : ""}</small>
    </li>)}</ol>
  </details>;
}

function CompanyAnalysis({ response }: { response: CompanyAnalysisResponse }) {
  return <>
    <p className="response-company-line">{response.company.name} · {response.company.ticker} · {response.company.exchange}</p>
    <p className="response-summary">{response.narrative.summary}</p>
    {response.market_snapshot ? <MetricStrip snapshot={response.market_snapshot} /> : null}
    <EvidenceList title="Positive drivers" items={response.narrative.positive_drivers} />
    <EvidenceList title="Risks" items={response.narrative.risks} />
  </>;
}

function StockComparison({ response }: { response: StockComparisonResponse }) {
  return <>
    <p className="response-company-line">{response.companies.map((company) => `${company.name} (${company.ticker})`).join(" vs. ")}</p>
    <p className="response-summary">{response.narrative.summary}</p>
    {response.market_snapshots.map((snapshot) => <MetricStrip key={snapshot.ticker} snapshot={snapshot} />)}
    {response.narrative.company_views.length ? <section className="response-section"><h3>Company views</h3><ul>{response.narrative.company_views.map((view) => <li key={view.ticker}><strong>{view.ticker}.</strong> {view.summary}</li>)}</ul></section> : null}
    <EvidenceList title="Key comparison points" items={response.narrative.comparison_points} />
  </>;
}

function NewsAnalysis({ response }: { response: NewsAnalysisResponse }) {
  return <>
    <p className="response-summary">{response.narrative.summary}</p>
    {response.narrative.company_sentiment.length ? <section className="response-section"><h3>News sentiment</h3>
      <ul>{response.narrative.company_sentiment.map((item) => <li key={item.ticker}><strong>{item.ticker} · {item.sentiment}</strong> — {item.rationale}</li>)}</ul>
    </section> : null}
  </>;
}

function TechnicalAnalysis({ response }: { response: TechnicalAnalysisResponse }) {
  return <>
    <p className="response-company-line">{response.companies.map((company) => `${company.name} (${company.ticker})`).join(" · ")}</p>
    <p className="response-summary">{response.narrative.summary}</p>
    {response.market_snapshots.map((snapshot) => <MetricStrip key={snapshot.ticker} snapshot={snapshot} />)}
    <EvidenceList title="Technical observations" items={response.narrative.observations} />
  </>;
}

function LegacyResponseView({ response }: { response: LegacyResearchResponse }) {
  return <div className={`structured-response response-${response.template}`} data-response-template={response.template}>
    <header className="response-header"><span className="response-template-label">{response.template.replaceAll("_", " ")}</span><h2>{response.title}</h2></header>
    {response.template === "company_analysis" ? <CompanyAnalysis response={response} />
      : response.template === "stock_comparison" ? <StockComparison response={response} />
        : response.template === "news_analysis" ? <NewsAnalysis response={response} />
          : response.template === "technical_analysis" ? <TechnicalAnalysis response={response} />
              : response.template === "quarterly_performance" ? <>
                <p className="response-company-line">{response.company.name} · {response.company.ticker}</p>
                <p className="response-summary"><strong>{response.narrative.period}.</strong> {response.narrative.summary}</p>
                <EvidenceList title="Bull case scenario" items={response.narrative.positive_drivers} />
                <EvidenceList title="Bear case scenario" items={response.narrative.risks} />
              </>
            : response.template === "research_answer" ? <p className="response-summary">{response.narrative.answer}</p>
              : response.template === "clarification" ? <p className="response-summary">{response.narrative.question}</p>
                : <p className="response-summary">{response.narrative.answer}</p>}
    <ResponseSources sources={response.sources} />
  </div>;
}

export function ResearchResponseView({
  response,
  copyText,
  onFollowUp,
  onResolveCompany,
}: {
  response: ResearchResponse;
  copyText?: string;
  onFollowUp?: (question: string) => void;
  onResolveCompany?: (company: CompanyIdentity) => void;
}) {
  const [reaction, setReaction] = useState<"like" | "dislike" | null>(null);
  const [copied, setCopied] = useState(false);
  const clarification = response.template === "clarification";
  const unresolvedQuery = "unresolved_company_query" in response ? response.unresolved_company_query : null;
  const suggestions = "company_suggestions" in response ? response.company_suggestions : [];
  const summary = responseSummary(response);
  const followUps = responseFollowUps(response);

  async function copyResponse() {
    if (!summary || !navigator.clipboard) return;
    try {
      await navigator.clipboard.writeText(copyText?.trim() || summary);
      setCopied(true);
    } catch {
      setCopied(false);
    }
  }

  return <>
    {"blocks" in response
      ? <VisualResearchAnswer response={response} />
      : <LegacyResponseView response={response} />}
    {clarification && unresolvedQuery && onResolveCompany ? <CompanyResolutionPicker
      key={`${response.title}-${unresolvedQuery}`}
      initialQuery={unresolvedQuery}
      initialSuggestions={suggestions}
      onResolve={onResolveCompany}
    /> : null}
    <footer className="response-closing">
      {summary ? <section className="response-closing-summary" aria-label="Summary">
        <span className="response-closing-eyebrow">SUMMARY</span>
        <p>{summary}</p>
      </section> : null}
      <div className="response-actions" aria-label="Response actions">
        <button type="button" className={reaction === "like" ? "is-selected" : ""} aria-label="Like response" aria-pressed={reaction === "like"} title="Like response" onClick={() => setReaction(reaction === "like" ? null : "like")}><ThumbsUp size={16} /></button>
        <button type="button" className={reaction === "dislike" ? "is-selected" : ""} aria-label="Dislike response" aria-pressed={reaction === "dislike"} title="Dislike response" onClick={() => setReaction(reaction === "dislike" ? null : "dislike")}><ThumbsDown size={16} /></button>
        <button type="button" aria-label={copied ? "Response copied" : "Copy response"} title={copied ? "Copied" : "Copy response"} onClick={copyResponse}>{copied ? <Check size={16} /> : <Copy size={16} />}</button>
      </div>
      <section className="response-followups" aria-label="Follow-up questions">
        <h3>Continue exploring</h3>
        <div className="response-followup-list">
          {followUps.map((question) => <button key={question} type="button" onClick={() => onFollowUp?.(question)} disabled={!onFollowUp}>
            <ArrowRight size={15} aria-hidden="true" /> <span>{question}</span>
          </button>)}
        </div>
      </section>
    </footer>
  </>;
}

function responseSummary(response: ResearchResponse): string {
  let value = "";
  if ("blocks" in response) return (response.closing_summary || response.summary).trim();
  else if ("summary" in response.narrative) value = response.template === "quarterly_performance"
    ? `${response.narrative.period}. ${response.narrative.summary}`
    : response.narrative.summary;
  else if ("answer" in response.narrative) value = response.narrative.answer;
  else if ("question" in response.narrative) value = response.narrative.question;
  const concise = value.trim().split(/(?<=[.!?])\s+/)[0] ?? "";
  return concise.length > 280 ? `${concise.slice(0, 277).trimEnd()}…` : concise;
}

function responseFollowUps(response: ResearchResponse): string[] {
  if ("blocks" in response && response.follow_up_questions?.length) return response.follow_up_questions.slice(0, 3);
  const companies: CompanyIdentity[] = "blocks" in response ? [] : response.companies;
  const entity = companies.slice(0, 2).map((company) => `${company.name} (${company.ticker})`).join(" and ") || "this company";
  const defaults: Record<string, string[]> = {
    company_analysis: [`What drove ${entity}'s latest quarterly results?`, `What recent developments could affect ${entity}?`, `How does ${entity} compare with its closest peers?`],
    stock_comparison: ["Which company has stronger recent momentum?", "How do their latest quarterly results compare?", "What are the main risks that differ between them?"],
    quarterly_performance: [`What drove ${entity}'s reported results?`, `How did the quarter compare with the prior year?`, `What should I watch in ${entity}'s next results?`],
    news_analysis: ["Which recent catalysts matter most?", "How has the market reacted to these developments?", "What upcoming events could change this view?"],
    technical_analysis: [`How has ${entity}'s trend changed over the past six months?`, "Which price levels mattered most recently?", "How does the recent move compare with its peers?"],
    clarification: ["Would you like to focus on company fundamentals or share performance?", "Should I include recent news?", "Would a comparison with another company help?"],
  };
  return defaults[response.template] ?? [`What are the main risks and counterpoints for ${entity}?`, `How does recent evidence compare with ${entity}'s longer-term trend?`, `Which upcoming developments should I watch for ${entity}?`];
}
