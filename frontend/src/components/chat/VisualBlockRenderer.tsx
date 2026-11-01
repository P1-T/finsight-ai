import { formatDate } from "@/lib/formatters";
import type { VisualBlock, VisualResearchResponse } from "@/types/research";

function CompanyHeader({ block }: { block: Extract<VisualBlock, { type: "company_header" }> }) {
  const initials = block.company.name.split(/\s+/).slice(0, 2).map((part) => part[0]).join("").toUpperCase();
  return <section className="visual-company-hero">
    <div className="visual-company-mark" aria-hidden="true">{initials || block.company.ticker.slice(0, 2)}</div>
    <div className="visual-company-copy">
      <div className="visual-company-title"><h3>{block.company.name}</h3><span>{block.company.ticker}</span></div>
      <p>{block.description}</p>
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
  const values = points.map((point) => point.close);
  const min = Math.min(...values);
  const max = Math.max(...values);
  const span = max - min || 1;
  const width = 760;
  const height = 180;
  const plotted = points.map((point, index) => ({
    x: points.length < 2 ? width / 2 : index / (points.length - 1) * width,
    y: height - ((point.close - min) / span * (height - 20) + 10),
  }));
  const path = plotted.map((point) => `${point.x.toFixed(1)},${point.y.toFixed(1)}`).join(" ");
  const firstDate = points[0]?.date;
  const lastDate = points.at(-1)?.date;
  return <section className="visual-block visual-chart-block">
    <div className="visual-block-heading"><h3>{block.title}</h3></div>
    <div className="visual-chart-wrap">
      <svg viewBox={`0 0 ${width} ${height}`} role="img" aria-label={`${block.title}, ${points.length} daily observations`} preserveAspectRatio="none">
        <line x1="0" y1="45" x2={width} y2="45" className="chart-grid-line" />
        <line x1="0" y1="90" x2={width} y2="90" className="chart-grid-line" />
        <line x1="0" y1="135" x2={width} y2="135" className="chart-grid-line" />
        <polyline points={path} fill="none" className="chart-line" />
      </svg>
      <div className="visual-chart-scale"><span>${min.toFixed(2)}</span><span>${max.toFixed(2)}</span></div>
      <div className="visual-chart-dates"><span>{firstDate ? formatDate(firstDate) : ""}</span><span>{lastDate ? formatDate(lastDate) : ""}</span></div>
    </div>
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
    case "takeaways": return <Takeaways block={block} />;
    case "answer_card": return <AnswerCard block={block} />;
  }
}

export function VisualResearchAnswer({ response }: { response: VisualResearchResponse }) {
  const includesSummary = response.blocks.some((block) => block.type === "company_header" || block.type === "answer_card");
  const hasIllustrativeData = response.blocks.some((block) => {
    if ("provenance" in block && (block.provenance.kind === "illustrative" || block.provenance.kind === "mixed")) return true;
    return block.type === "scenario_cards" && block.points.some((point) => point.provenance.kind === "illustrative");
  });
  return <div className="visual-response" data-generated-by={response.generated_by}>
    <header className="visual-response-header"><span>{response.template.replaceAll("_", " ")}</span><h2>{response.title}</h2></header>
    {!includesSummary && response.summary ? <p className="visual-response-summary">{response.summary}</p> : null}
    <div className="visual-block-stack">{response.blocks.map((block, index) => <VisualBlockRenderer key={`${block.type}-${index}`} block={block} />)}</div>
    {response.sources.length ? <details className="response-sources visual-sources"><summary>Sources ({response.sources.length})</summary><ol>{response.sources.map((source) => <li key={source.id}>
      {source.url ? <a href={source.url} target="_blank" rel="noreferrer">{source.title}</a> : <span>{source.title}</span>}
      <small>{source.id} · {source.provider}{source.published_at ? ` · ${formatDate(source.published_at)}` : ""}</small>
    </li>)}</ol></details> : null}
    {hasIllustrativeData ? <p className="visual-demo-disclosure">Some figures and scenario details are simulated for demonstration and may not reflect actual company data.</p> : null}
  </div>;
}
