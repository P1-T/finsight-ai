"use client";

import { useEffect, useState } from "react";
import type { ReactNode } from "react";
import { Activity, ArrowDownRight, ArrowUpRight, BarChart3, BookOpenText, ChevronDown, ChevronUp, CircleAlert, ExternalLink, Newspaper, ShieldCheck, Sparkles, TrendingUp } from "lucide-react";
import { StockPriceChart } from "@/components/charts/StockPriceChart";
import { formatCompactCurrency, formatCurrency, formatDate, formatPercent } from "@/lib/formatters";
import { getStocks, runResearch } from "@/lib/api";
import { FALLBACK_STOCKS } from "@/lib/constants";
import type { ResearchResponse, StockInfo, Ticker } from "@/types/research";

function MetricCard({ label, value, detail, positive }: { label: string; value: ReactNode; detail?: string | null; positive?: boolean | null }) {
  return <div className="metric-card"><span className="metric-label">{label}</span><strong className={positive === true ? "text-positive" : positive === false ? "text-negative" : ""}>{value}</strong>{detail ? <span className="metric-detail">{detail}</span> : null}</div>;
}

function AgentBadge({ status }: { status: string | null }) {
  const label = status === "succeeded" ? "Complete" : status === "no_evidence" ? "No evidence" : status === "failed" ? "Unavailable" : status === "running" ? "Analyzing" : "Waiting";
  return <span className={`status-pill status-${status ?? "waiting"}`}><span className="status-dot" />{label}</span>;
}

function MetricValue({ value, format = "number", unavailable }: { value: number | null; format?: "number" | "currency" | "compactCurrency" | "percent"; unavailable: string | null }) {
  if (value === null) return <span title={unavailable ?? undefined}>Unavailable</span>;
  if (format === "currency") return <>{formatCurrency(value)}</>;
  if (format === "compactCurrency") return <>{formatCompactCurrency(value)}</>;
  if (format === "percent") return <>{formatPercent(value)}</>;
  return <>{value.toFixed(2)}</>;
}

export default function Home() {
  const [stocks, setStocks] = useState<StockInfo[]>(FALLBACK_STOCKS);
  const [ticker, setTicker] = useState<Ticker>("AAPL");
  const [stocksError, setStocksError] = useState<string | null>(null);
  const [result, setResult] = useState<ResearchResponse | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    const controller = new AbortController();
    getStocks(controller.signal).then((data) => {
      if (data.stocks.length === 0) {
        setStocksError("The backend returned an empty company list. Showing the supported companies built into the dashboard.");
        return;
      }
      setStocks(data.stocks);
      setTicker(data.stocks[0].ticker);
    }).catch((reason: unknown) => {
      if (!controller.signal.aborted) setStocksError(reason instanceof Error ? reason.message : "Could not load supported stocks.");
    });
    return () => controller.abort();
  }, []);

  const selectedStock = stocks.find((stock) => stock.ticker === ticker);
  const news = result?.news;
  const technical = result?.technical;
  const fundamental = result?.fundamental;
  const [showAllNews, setShowAllNews] = useState(false);
  const [showAllFindings, setShowAllFindings] = useState(false);
  const newsBusy = loading && !result;
  const marketBusy = loading && !result;
  const allFindings = fundamental
    ? [...fundamental.business_findings, ...fundamental.key_risks]
    : [];
  const visibleFindings = showAllFindings ? allFindings : allFindings.slice(0, 6);
  const visibleArticles = showAllNews ? news?.articles ?? [] : (news?.articles ?? []).slice(0, 6);
  const dataNotes = [...new Set([
    news?.evidence_limitations,
    news?.lookback ? `News search window: ${news.lookback}.` : null,
    ...(technical?.caveats ?? []),
    ...(fundamental?.limitations ?? []),
  ].filter((note): note is string => Boolean(note)))];

  async function handleResearch() {
    setLoading(true);
    setError(null);
    setResult(null);
    setShowAllNews(false);
    setShowAllFindings(false);
    try {
      const data = await runResearch(ticker);
      setResult(data);
    } catch (reason: unknown) {
      setError(reason instanceof Error ? reason.message : "Research could not be completed.");
    } finally {
      setLoading(false);
    }
  }

  return (
    <main className="app-frame">
      <header className="topbar">
        <a className="brand" href="#top" aria-label="FinSight AI home"><span className="brand-mark"><Activity size={19} strokeWidth={2.4} /></span><span>FinSight<span className="brand-ai"> AI</span></span></a>
        <div className="topbar-right"><span className="private-badge"><ShieldCheck size={14} /> Research workspace</span><span className="topbar-divider" /><span className="topbar-caption">Market data is delayed</span></div>
      </header>

      <div className="dashboard" id="top">
        <section className="welcome-row">
          <div><div className="eyebrow"><span className="eyebrow-line" /> EQUITY RESEARCH</div><h1>Market research, made clearer.</h1><p className="intro-copy">Explore recent company coverage and historical price trends with AI assisted analysis.</p></div>
          <div className="updated-chip"><span className="live-dot" />{result ? `Report generated ${formatDate(result.generated_at, true)} UTC` : "Analysis runs on demand"}</div>
        </section>

        <section className="control-panel" aria-label="Research controls">
          <div className="stock-control"><label htmlFor="stock-select">Company</label><div className="select-wrap"><select id="stock-select" value={ticker} onChange={(event) => { setTicker(event.target.value as Ticker); setResult(null); setError(null); setShowAllNews(false); setShowAllFindings(false); }} disabled={loading || stocks.length === 0}>
            {stocks.map((stock) => <option key={stock.ticker} value={stock.ticker}>{stock.name} · {stock.ticker}</option>)}
          </select><ChevronDown size={16} /></div>{stocksError ? <span className="field-error">{stocksError}</span> : selectedStock ? <span className="field-hint">Ticker: {selectedStock.ticker}</span> : null}</div>
          <div className="control-spacer" />
          <button className="primary-button" onClick={handleResearch} disabled={loading || !selectedStock}>
            {loading ? <><span className="spinner spinner-light" /> Researching…</> : <><Sparkles size={17} /> Run research <span className="button-arrow">→</span></>}
          </button>
        </section>

        {error ? <div className="global-error" role="alert"><CircleAlert size={18} /><div><strong>Research request failed</strong><span>{error}</span></div><button onClick={handleResearch}>Retry</button></div> : null}

        <div className="section-heading"><div><span className="section-kicker">01 / PRICE ACTION</span><h2>{selectedStock?.name ?? "Select a company"}<span className="ticker-tag">{ticker}</span></h2></div><div className="market-date">{technical?.as_of_date ? <><span className="date-label">Latest session</span><strong>{formatDate(technical.as_of_date)}</strong></> : <span className="date-label">Historical daily data · not a live quote</span>}</div></div>

        <section className="market-grid">
          <div className="panel chart-panel"><div className="panel-heading"><div><div className="panel-title"><BarChart3 size={17} /> Historical price</div><div className="panel-subtitle">Daily OHLC · roughly six months</div></div><span className="period-pill">6M VIEW</span></div>
            <StockPriceChart series={result?.chart ?? null} loading={marketBusy} error={technical?.status === "failed" && !result?.chart.candles.length ? technical.error : null} />
          </div>
          <div className="panel metrics-panel"><div className="panel-heading"><div><div className="panel-title"><TrendingUp size={17} /> Key indicators</div><div className="panel-subtitle">Calculated from historical sessions</div></div><span className="quiet-icon"><Activity size={17} /></span></div>
            {!technical && !loading ? <div className="metrics-empty">Run research to calculate technical indicators.</div> : null}
            {loading ? <div className="metrics-empty"><span className="spinner" /> Calculating market metrics…</div> : null}
            {technical ? <div className="metrics-grid">
              <MetricCard label="Latest close" value={<MetricValue value={technical.latest_close.value} format="currency" unavailable={technical.latest_close.unavailable_reason} />} detail={technical.as_of_date ? `As of ${formatDate(technical.as_of_date)}` : technical.latest_close.unavailable_reason} />
              <MetricCard label="Daily change" value={<MetricValue value={technical.daily_pct_change.value} format="percent" unavailable={technical.daily_pct_change.unavailable_reason} />} detail={technical.daily_pct_change.value === null ? technical.daily_pct_change.unavailable_reason : null} positive={technical.daily_pct_change.value === null ? null : technical.daily_pct_change.value >= 0} />
              <MetricCard label="5 trading days" value={<MetricValue value={technical.return_5d.value} format="percent" unavailable={technical.return_5d.unavailable_reason} />} detail={technical.return_5d.value === null ? technical.return_5d.unavailable_reason : null} positive={technical.return_5d.value === null ? null : technical.return_5d.value >= 0} />
              <MetricCard label="20 trading days" value={<MetricValue value={technical.return_20d.value} format="percent" unavailable={technical.return_20d.unavailable_reason} />} detail={technical.return_20d.value === null ? technical.return_20d.unavailable_reason : null} positive={technical.return_20d.value === null ? null : technical.return_20d.value >= 0} />
              <MetricCard label="SMA 20" value={<MetricValue value={technical.sma20.value} format="currency" unavailable={technical.sma20.unavailable_reason} />} detail={technical.sma20.value === null ? technical.sma20.unavailable_reason : null} />
              <MetricCard label="SMA 50" value={<MetricValue value={technical.sma50.value} format="currency" unavailable={technical.sma50.unavailable_reason} />} detail={technical.sma50.value === null ? technical.sma50.unavailable_reason : null} />
              <MetricCard label="RSI 14" value={<MetricValue value={technical.rsi14.value} unavailable={technical.rsi14.unavailable_reason} />} detail={technical.rsi14.value === null ? technical.rsi14.unavailable_reason : "Momentum indicator · 0–100"} />
            </div> : null}
          </div>
        </section>

        <div className="analysis-grid">
          <section className="panel analysis-panel"><div className="panel-heading"><div><div className="panel-title"><Newspaper size={17} /> News &amp; sentiment</div><div className="panel-subtitle">AI interpretation of retrieved headlines</div></div><AgentBadge status={news?.status ?? (newsBusy ? "running" : null)} /></div>
            {loading ? <div className="analysis-empty"><span className="spinner" /> Reviewing recent news headlines…</div> : null}
            {!loading && !news ? <div className="analysis-empty">Run research to retrieve and assess recent company coverage.</div> : null}
            {news?.status === "failed" ? <div className="inline-error"><CircleAlert size={16} /><span>{news.error ?? "News analysis could not be completed."}</span></div> : null}
            {news?.status === "no_evidence" ? <div className="empty-evidence"><strong>No relevant articles returned</strong></div> : null}
            {news?.status === "succeeded" ? <>
              <div className="sentiment-row"><div className={`sentiment-mark sentiment-${news.overall_sentiment ?? "neutral"}`}><span>{news.overall_sentiment ?? "neutral"}</span><small>AI sentiment</small></div><div className="sentiment-explanation"><strong>{news.confidence ?? "Qualitative assessment"}</strong><p>{news.investor_relevance ?? "No additional investor relevance explanation was provided."}</p></div></div>
              <div className="catalyst-columns"><div><h3><ArrowUpRight size={15} /> Positive catalysts</h3>{news.positive_catalysts.length ? <ul>{news.positive_catalysts.map((item, index) => <li key={`${index}-${item}`}>{item}</li>)}</ul> : <p className="muted-copy">None identified in returned headlines.</p>}</div><div><h3 className="risk-heading"><ArrowDownRight size={15} /> Risks &amp; negative catalysts</h3>{news.negative_catalysts.length ? <ul>{news.negative_catalysts.map((item, index) => <li key={`${index}-${item}`}>{item}</li>)}</ul> : <p className="muted-copy">None identified in returned headlines.</p>}</div></div>
              {news.major_developments.length ? <div className="developments"><h3>Developments mentioned</h3><ul>{news.major_developments.map((item, index) => <li key={`${index}-${item}`}>{item}</li>)}</ul></div> : null}
            </> : null}
          </section>

          <section className="panel analysis-panel"><div className="panel-heading"><div><div className="panel-title"><Activity size={17} /> Technical view</div><div className="panel-subtitle">Model interpretation of calculated metrics</div></div><AgentBadge status={technical?.status ?? (marketBusy ? "running" : null)} /></div>
            {loading ? <div className="analysis-empty"><span className="spinner" /> Reading price action and indicators…</div> : null}
            {!loading && !technical ? <div className="analysis-empty">Run research to see trend, momentum, and volume context.</div> : null}
            {technical ? <>
              {technical.status === "failed" ? <div className="inline-error"><CircleAlert size={16} /><span>{technical.error ?? "Technical interpretation could not be completed."}{technical.latest_close.value !== null ? " Calculated metrics are still available." : ""}</span></div> : null}
              <div className="interpretation-list">
                <div><span className="interpretation-label">Short-term trend</span><p>{technical.short_term_trend ?? "Unavailable"}</p></div>
                <div><span className="interpretation-label">Medium-term trend</span><p>{technical.medium_term_trend ?? "Unavailable"}</p></div>
                <div><span className="interpretation-label">Momentum</span><p>{technical.momentum ?? "Unavailable"}</p></div>
                <div><span className="interpretation-label">Volume observation</span><p>{technical.volume_vs_average ?? "Unavailable"}</p></div>
                <div><span className="interpretation-label">Volatility</span><p>{technical.volatility_note ?? "Unavailable"}</p></div>
              </div>
            </> : null}
          </section>
        </div>

        <section className="panel articles-panel fundamental-panel">
          <div className="panel-heading"><div><div className="panel-title"><BookOpenText size={17} /> Fundamental view · latest 10-K</div><div className="panel-subtitle">SEC filing retrieval with cited passages and filing-specific XBRL metrics</div></div><AgentBadge status={fundamental?.status ?? (loading ? "running" : null)} /></div>
          {loading ? <div className="analysis-empty"><span className="spinner" /> Retrieving the latest indexed 10-K…</div> : null}
          {!loading && !fundamental ? <div className="analysis-empty">Run research to review the latest indexed SEC 10-K. If missing, ingest it using the documented backend command.</div> : null}
          {fundamental?.status === "failed" || fundamental?.status === "no_evidence" ? <div className="inline-error"><CircleAlert size={16} /><span>{fundamental.error ?? "Fundamental analysis is unavailable."}</span></div> : null}
          {fundamental ? <>
            {fundamental.status === "succeeded" ? <div className="filing-meta">{fundamental.filing_date ? `Filed ${formatDate(fundamental.filing_date)}` : "Latest indexed SEC filing"}{fundamental.fiscal_year ? ` · FY ${fundamental.fiscal_year}` : ""}</div> : null}
            <div className="metrics-grid fundamental-metrics">
              {([
                ["Revenue", fundamental.revenue, "compactCurrency"], ["Revenue YoY", fundamental.revenue_yoy_growth_pct, "percent"],
                ["Operating margin", fundamental.operating_margin_pct, "percent"], ["Net margin", fundamental.net_margin_pct, "percent"],
                ["Operating cash flow", fundamental.operating_cash_flow, "compactCurrency"], ["Capital expenditures", fundamental.capital_expenditures, "compactCurrency"],
                ["Free cash flow", fundamental.free_cash_flow, "compactCurrency"], ["Cash & equivalents", fundamental.cash_and_equivalents, "compactCurrency"],
              ] as const).map(([label, metric, format]) => <MetricCard key={label} label={label} value={<MetricValue value={metric.value} format={format} unavailable={metric.unavailable_reason} />} detail={metric.value === null ? metric.unavailable_reason : metric.fiscal_year ? `FY ${metric.fiscal_year}${metric.unit && metric.unit !== "USD" ? ` · ${metric.unit}` : ""}` : metric.unit} />)}
            </div>
            {fundamental.overview ? <p className="fundamental-overview">{fundamental.overview}</p> : null}
            {visibleFindings.length ? <div className="fundamental-findings">
              {visibleFindings.map((finding, index) => <article key={`${finding.topic}-${index}`}><strong>{finding.topic}</strong><p>{finding.finding}</p></article>)}
            </div> : null}
            {allFindings.length > 6 ? <button className="text-toggle" onClick={() => setShowAllFindings((shown) => !shown)}>{showAllFindings ? <>Show fewer findings <ChevronUp size={14} /></> : <>View all {allFindings.length} findings <ChevronDown size={14} /></>}</button> : null}
            {fundamental.filing_url ? <div className="filing-source"><a href={fundamental.filing_url} target="_blank" rel="noopener noreferrer">Open source 10-K on SEC <ExternalLink size={13} /></a></div> : null}
          </> : null}
        </section>

        <section className="panel articles-panel"><div className="panel-heading"><div><div className="panel-title"><Newspaper size={17} /> Retrieved articles</div><div className="panel-subtitle">Original links and available publication metadata</div></div><span className="count-pill">{news?.articles.length ?? 0} items</span></div>
          {visibleArticles.length ? <><div className="article-list">{visibleArticles.map((article, index) => <article className="article-row" key={`${article.url}-${index}`}><div className="article-index">{String(index + 1).padStart(2, "0")}</div><div className="article-content"><a href={article.url} target="_blank" rel="noopener noreferrer">{article.title}<ExternalLink size={13} /></a><div className="article-meta"><span>{article.source ?? "Source unavailable"}</span><span className="meta-dot">·</span><span>{formatDate(article.published_at)}</span></div></div></article>)}</div>{(news?.articles.length ?? 0) > 6 ? <button className="text-toggle" onClick={() => setShowAllNews((shown) => !shown)}>{showAllNews ? <>Show fewer articles <ChevronUp size={14} /></> : <>View all {news?.articles.length} articles <ChevronDown size={14} /></>}</button> : null}</> : <div className="articles-empty">{news?.status === "no_evidence" ? "No relevant articles were returned for this search." : news?.status === "failed" ? "Article retrieval failed. See the news analysis status above." : "Articles will appear here after research runs."}</div>}
        </section>

        <section className="summary-panel"><div className="summary-title"><span className="summary-icon"><Sparkles size={17} /></span><div><span className="section-kicker">RESEARCH BRIEF</span><h2>Combined perspective</h2></div></div>
          {result ? <div className="summary-columns"><div><h3>News perspective</h3><p>{result.summary.news_perspective}</p></div><div><h3>Technical perspective</h3><p>{result.summary.technical_perspective}</p></div><div><h3>Fundamental perspective</h3><p>{result.summary.fundamental_perspective}</p></div><div><h3>Where they align</h3><p>{result.summary.agreement}</p></div><div><h3>Differences &amp; missing information</h3><p>{result.summary.disagreement} {result.summary.missing_information}</p></div></div> : <p className="summary-placeholder">The news, technical, and fundamental perspectives will be summarized here with missing evidence identified explicitly.</p>}
        </section>

        <footer className="disclaimer" role="note"><span className="disclaimer-icon"><ShieldCheck size={17} /></span><div className="disclaimer-copy"><strong>Research &amp; data notice</strong><p>{result?.disclaimer ?? "FinSight AI is an experimental research and educational tool. Its outputs may be incomplete or inaccurate and are not financial advice or recommendations to buy or sell securities."}</p>{dataNotes.length ? <p className="data-notes">{dataNotes.join(" · ")}</p> : null}</div><span className="footer-version">FINSIGHT AI · V1</span></footer>
        <div className="page-footer"><span>Market data via yfinance. News via MarketNewsAPI. Fundamentals use SEC EDGAR 10-K filings and Pinecone retrieval.</span><span>Historical data may be delayed or incomplete.</span></div>
      </div>
    </main>
  );
}
