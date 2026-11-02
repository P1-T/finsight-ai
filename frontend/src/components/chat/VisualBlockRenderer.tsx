import { formatDate } from "@/lib/formatters";
import type { VisualBlock, VisualResearchResponse } from "@/types/research";
import { DataChart, HistoricalPriceChart } from "@/components/charts/ResearchCharts";

function CompanyHeader({ block }: { block: Extract<VisualBlock, { type: "company_header" }> }) {
  const initials = block.company.name.split(/\s+/).slice(0, 2).map((part) => part[0]).join("").toUpperCase();
  return <section className="visual-company-hero">
    <div className="visual-company-mark" aria-hidden="true">{initials || block.company.ticker.slice(0, 2)}</div>
    <div className="visual-company-copy">
      <div className="visual-company-title"><h3>{block.company.name}</h3><span>{block.company.ticker}</span></div>
      {block.description ? <p>{block.description}</p> : null}
      <small>{block.company.exchange} · US listed equity</small>
    </div>
  </section>;
}

function MetricGrid({ block }: { block: Extract<VisualBlock, { type: "metric_grid" }> }) {
  return <section className="visual-block">
    <div className="visual-block-heading"><h3>{block.title}</h3></div>
    <div className="visual-fundamental-grid" style={{ gridTemplateColumns: "repeat(3, minmax(0, 1fr))" }}>{block.metrics.map((metric) => <article className="visual-metric-card" key={metric.label}>
      <span>{metric.label}</span><strong>{metric.value}</strong>{metric.detail ? <small>{metric.detail}</small> : null}
    </article>)}</div>
  </section>;
}

function PriceChart({ block }: { block: Extract<VisualBlock, { type: "price_chart" }> }) {
  const points = block.points;
  return <section className="visual-block visual-chart-block">
    <div className="visual-block-heading"><h3>{block.title}</h3></div>
    <HistoricalPriceChart points={points} />
    <div className="visual-chart-dates"><span>{points[0]?.date ? formatDate(points[0].date) : ""}</span><span>{points.at(-1)?.date ? formatDate(points.at(-1)!.date) : ""}</span></div>
  </section>;
}

function FactGrid({ block }: { block: Extract<VisualBlock, { type: "fact_grid" }> }) {
  return <section className="visual-block">
    <div className="visual-block-heading"><h3>{block.title}</h3><span className="visual-period-label">{block.period}</span></div>
    <div className="visual-fundamental-grid">{block.metrics.map((metric, index) => <article className="visual-fundamental-card" key={`${metric.label}-${index}`}>
      <span>{metric.label}</span><strong>{metric.value}</strong>
      {metric.range_low && metric.range_high ? <div className="visual-range-band" role="img" aria-label={`${metric.label} range from ${metric.range_low} to ${metric.range_high}`}><span>{metric.range_low}</span><i /><span>{metric.range_high}</span></div> : null}
      {metric.detail ? <small>{metric.detail}</small> : null}
    </article>)}</div>
  </section>;
}

function ResearchDataChart({ block }: { block: Extract<VisualBlock, { type: "data_chart" }> }) {
  return <section className="visual-block visual-chart-block">
    <div className="visual-block-heading"><h3>{block.title}</h3></div>
    <DataChart block={block} />
  </section>;
}

function Fundamentals({ block }: { block: Extract<VisualBlock, { type: "fundamental_cards" }> }) {
  return <section className="visual-block">
    <div className="visual-block-heading"><h3>{block.title}</h3></div>
    <div className="visual-fundamental-grid">{block.metrics.map((metric) => <article className="visual-fundamental-card" key={metric.label}>
      <span>{metric.label}</span><strong>{metric.value}</strong><small>{metric.detail}</small>
    </article>)}</div>
  </section>;
}

function Scenarios({ block }: { block: Extract<VisualBlock, { type: "scenario_cards" }> }) {
  if (!block.points.length) return null;
  return <section className="visual-block">
    <div className="visual-block-heading"><h3>{block.title}</h3><span className={`scenario-tag scenario-${block.scenario}`}>{block.scenario === "bull" ? "Upside" : "Risks"}</span></div>
    <div className={`visual-scenario-grid scenario-${block.scenario}`}>{block.points.map((point, index) => <article className="visual-scenario-card" key={`${point.title}-${index}`}>
      <span className="scenario-index">{String(index + 1).padStart(2, "0")}</span><div><strong>{point.title}</strong><p>{point.detail}</p></div>
    </article>)}</div>
  </section>;
}

function Timeline({ block }: { block: Extract<VisualBlock, { type: "news_timeline" }> }) {
  if (!block.items.length) return null;
  return <section className="visual-block">
    <div className="visual-block-heading"><h3>{block.title}</h3></div>
    <div className="visual-timeline">{block.items.map((item, index) => <article className="visual-timeline-item" key={`${item.title}-${index}`}>
      <span className={`timeline-dot timeline-${item.provenance.kind}`} />
      <div className="visual-timeline-content">
        <div className="visual-timeline-title"><strong>{item.title}</strong></div>
        {item.date ? <small>{formatDate(item.date)}</small> : null}<p>{item.detail}</p>
      </div>
    </article>)}</div>
  </section>;
}

function Comparison({ block }: { block: Extract<VisualBlock, { type: "comparison_table" }> }) {
  return <section className="visual-block">
    <div className="visual-block-heading"><h3>{block.title}</h3></div>
    <div className="visual-table-scroll"><table className="visual-comparison-table"><thead><tr><th>Company</th><th>Close</th><th>Daily</th><th>20 sessions</th><th>Revenue growth</th><th>Operating margin</th></tr></thead>
      <tbody>{block.rows.map((row) => <tr key={row.ticker}><th scope="row"><strong>{row.ticker}</strong><small>{row.name}</small></th><td>{row.latest_close}</td><td>{row.daily_change}</td><td>{row.period_return}</td><td>{row.revenue_growth}</td><td>{row.margin}</td></tr>)}</tbody>
    </table></div>
  </section>;
}

function Takeaways({ block }: { block: Extract<VisualBlock, { type: "takeaways" }> }) {
  return <section className="visual-takeaways"><h3>{block.title}</h3><ul>{block.items.map((item, index) => <li key={`${item}-${index}`}>{item}</li>)}</ul></section>;
}

function AnswerCard({ block }: { block: Extract<VisualBlock, { type: "answer_card" }> }) {
  return <section className="visual-answer-card"><h3>{block.title}</h3><p>{block.body}</p></section>;
}

export function VisualBlockRenderer({ block }: { block: VisualBlock }) {
  switch (block.type) {
    case "company_header": return <CompanyHeader block={block} />;
    case "metric_grid": return <MetricGrid block={block} />;
    case "price_chart": return <PriceChart block={block} />;
    case "fundamental_cards": return <Fundamentals block={block} />;
    case "scenario_cards": return <Scenarios block={block} />;
    case "news_timeline": return <Timeline block={block} />;
    case "comparison_table": return <Comparison block={block} />;
    case "fact_grid": return <FactGrid block={block} />;
    case "data_chart": return <ResearchDataChart block={block} />;
    case "takeaways": return <Takeaways block={block} />;
    case "answer_card": return <AnswerCard block={block} />;
  }
}

export function VisualResearchAnswer({ response }: { response: VisualResearchResponse }) {
  const includesSummary = response.blocks.some((block) => block.type === "company_header" || block.type === "answer_card");
  return <div className="visual-response" data-generated-by={response.generated_by}>
    <header className="visual-response-header"><span>{response.template.replaceAll("_", " ")}</span><h2>{response.title}</h2></header>
    {!includesSummary && response.summary ? <p className="visual-response-summary">{response.summary}</p> : null}
    <div className="visual-block-stack">{response.blocks.map((block, index) => <VisualBlockRenderer key={`${block.type}-${index}`} block={block} />)}</div>
    {response.sources.length ? <details className="response-sources visual-sources"><summary>Sources ({response.sources.length})</summary><ol>{response.sources.map((source) => <li key={source.id}>
      {source.url ? <a href={source.url} target="_blank" rel="noreferrer">{source.title}</a> : <span>{source.title}</span>}
      <small>{source.id} · {source.provider}{source.published_at ? ` · ${formatDate(source.published_at)}` : ""}</small>
    </li>)}</ol></details> : null}
  </div>;
}
