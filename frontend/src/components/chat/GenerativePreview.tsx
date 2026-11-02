"use client";

import { useState } from "react";
import { ArrowDownRight, ArrowUpRight, Braces, Check, ChevronDown, LockKeyhole, MoveUpRight, Sparkles } from "lucide-react";
import {
  CartesianGrid,
  Line,
  LineChart,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";
import { Badge, Card, Input, Table, TableBody, TableCell, TableHead, TableRow } from "@/components/ui/primitives";

const marginData = [
  { year: "2021", aapl: 41.8, msft: 68.9, aaplEstimate: null, msftEstimate: null },
  { year: "2022", aapl: 43.3, msft: 68.4, aaplEstimate: null, msftEstimate: null },
  { year: "2023", aapl: 44.1, msft: 69.3, aaplEstimate: null, msftEstimate: null },
  { year: "2024", aapl: 46.2, msft: 69.8, aaplEstimate: null, msftEstimate: null },
  { year: "2025", aapl: 46.8, msft: 68.7, aaplEstimate: null, msftEstimate: null },
  { year: "2026", aapl: 47.2, msft: 68.1, aaplEstimate: 47.2, msftEstimate: 68.1 },
  { year: "2027E", aapl: null, msft: null, aaplEstimate: 48.1, msftEstimate: 68.8 },
  { year: "2028E", aapl: null, msft: null, aaplEstimate: 48.8, msftEstimate: 69.4 },
];

const tickerRows = [
  { ticker: "AAPL", price: "$247.80", margin: "47.2%", change: "+0.84%", positive: true },
  { ticker: "MSFT", price: "$508.42", margin: "68.1%", change: "−0.21%", positive: false },
];

export function GenerativePreview({ onUsePrompt }: { onUsePrompt: (prompt: string) => void }) {
  const [side, setSide] = useState<"buy" | "sell">("buy");

  return <div className="showcase-stack">
    <Card className="generative-preview-card">
      <div className="preview-toolbar">
        <div className="preview-window-dots" aria-hidden="true"><i /><i /><i /></div>
        <span>FIN SIGHT <b>/</b> RESPONSE PREVIEW</span>
        <Badge className="preview-mode-badge"><span /> COMPONENT STREAM</Badge>
      </div>
      <div className="preview-columns">
        <div className="preview-query-panel">
          <div className="preview-query-top"><Badge>YOU</Badge><span>Prompt</span></div>
          <p>Compare <b>$AAPL</b> and <b>$MSFT</b> gross margins over 5 years and show a projection chart.</p>
          <div className="preview-query-tags"><Badge>COMPANY COMPARISON</Badge><Badge>5Y · ANNUAL</Badge></div>
          <button className="preview-use-prompt" onClick={() => onUsePrompt("Compare AAPL and MSFT gross margins over 5 years and show a projection chart.")}>
            Run this prompt <MoveUpRight size={14} />
          </button>
          <div className="preview-pipeline"><span className="pipeline-mark"><Sparkles size={13} /></span><span><strong>Intent resolved</strong><small>financial_comparison</small></span><Check size={14} /></div>
        </div>

        <div className="preview-output-panel">
          <div className="preview-output-heading">
            <div><span className="eyebrow">COMPARISON · GROSS MARGIN</span><h3>Operating scale, visualized.</h3></div>
            <Badge className="schema-badge"><Braces size={12} /> type: financial-comparison-chart</Badge>
          </div>
          <div className="preview-chart-heading"><span>Gross margin</span><span className="mono">5Y <i /> 2Y PROJECTION</span></div>
          <div className="preview-chart">
            <ResponsiveContainer width="100%" height="100%">
              <LineChart data={marginData} margin={{ top: 7, right: 10, bottom: 0, left: -17 }}>
                <CartesianGrid stroke="#e5e7eb" vertical={false} />
                <XAxis dataKey="year" tick={{ fill: "#737373", fontSize: 12 }} axisLine={false} tickLine={false} />
                <YAxis domain={[35, 75]} ticks={[40, 50, 60, 70]} tickFormatter={(value: number) => `${value}%`} tick={{ fill: "#737373", fontSize: 11 }} axisLine={false} tickLine={false} />
                <Tooltip contentStyle={{ background: "#ffffff", border: "1px solid #d4d4d8", borderRadius: 7, color: "#171717", fontSize: 11 }} formatter={(value) => [`${Number(value).toFixed(1)}%`, ""]} labelStyle={{ color: "#737373" }} />
                <Line type="monotone" dataKey="aapl" name="AAPL" stroke="#4f6bed" strokeWidth={1.7} dot={false} activeDot={{ r: 3 }} isAnimationActive={false} />
                <Line type="monotone" dataKey="msft" name="MSFT" stroke="#168c80" strokeWidth={1.7} dot={false} activeDot={{ r: 3 }} isAnimationActive={false} />
                <Line type="monotone" dataKey="aaplEstimate" name="AAPL projection" stroke="#4f6bed" strokeWidth={1.5} dot={false} strokeDasharray="3 4" connectNulls isAnimationActive={false} />
                <Line type="monotone" dataKey="msftEstimate" name="MSFT projection" stroke="#168c80" strokeWidth={1.5} dot={false} strokeDasharray="3 4" connectNulls isAnimationActive={false} />
              </LineChart>
            </ResponsiveContainer>
          </div>
          <div className="preview-legend"><span><i className="legend-aapl" /> AAPL</span><span><i className="legend-msft" /> MSFT</span><span><i className="legend-projection" /> Projection</span></div>
          <div className="preview-table-wrap">
            <Table aria-label="Market comparison preview">
              <TableHead><TableRow><TableCell as="th">SYMBOL</TableCell><TableCell as="th">LAST PRICE</TableCell><TableCell as="th">GROSS MARGIN</TableCell><TableCell as="th">DAY</TableCell></TableRow></TableHead>
              <TableBody>{tickerRows.map((row) => <TableRow key={row.ticker}>
                <TableCell as="th"><span className="table-ticker">{row.ticker}</span></TableCell>
                <TableCell>{row.price}</TableCell><TableCell>{row.margin}</TableCell>
                <TableCell className={row.positive ? "positive" : "negative"}>{row.change}</TableCell>
              </TableRow>)}</TableBody>
            </Table>
          </div>
        </div>
      </div>
      <div className="preview-json-footer"><span><i /> response payload</span><code>{'{ "type": "financial-comparison-chart", "series": 2 }'}</code><span>RENDERED IN 4 BLOCKS <ChevronDown size={12} /></span></div>
    </Card>

    <div className="feature-grid">
      <Card className="feature-card declarative-card">
        <div className="feature-card-heading"><span className="feature-icon"><Braces size={16} /></span><Badge>01 · SCHEMA</Badge></div>
        <h3>Declarative by design</h3><p>Typed response payloads map to reusable, native interface blocks.</p>
        <pre className="schema-code"><code><span className="code-muted">{`{`}</span>{"\n  "}<span className="code-key">"type"</span>: <span className="code-string">"StockChart"</span>,{"\n  "}<span className="code-key">"data"</span>: <span className="code-string">"market_series"</span>,{"\n  "}<span className="code-key">"config"</span>: <span className="code-muted">{`{`}</span>{"\n    "}<span className="code-key">"compare"</span>: <span className="code-bool">true</span>{"\n  "}<span className="code-muted">{`}`}</span>{"\n"}<span className="code-muted">{`}`}</span></code></pre>
        <div className="feature-card-meta"><span>SCHEMA VALIDATED</span><Check size={13} /></div>
      </Card>

      <Card className="feature-card stream-card">
        <div className="feature-card-heading"><span className="feature-icon"><ActivityIcon /></span><Badge>02 · STREAM</Badge></div>
        <h3>Responses arrive in pieces</h3><p>Progressive research states keep the conversation responsive.</p>
        <div className="stream-list">
          <div className="stream-row"><span className="stream-dot active" /><span className="mono">AAPL</span><span className="stream-state">market snapshot</span><time>120ms</time></div>
          <div className="stream-row"><span className="stream-dot active" /><span className="mono">MSFT</span><span className="stream-state">market snapshot</span><time>184ms</time></div>
          <div className="stream-row"><span className="stream-dot muted" /><span className="mono">WEB</span><span className="stream-state">news context</span><time>streaming</time></div>
        </div>
        <div className="feature-card-meta"><span>PLANNING → RETRIEVAL → UI</span><span className="stream-pulse" /></div>
      </Card>

      <Card className="feature-card ticket-card">
        <div className="feature-card-heading"><span className="feature-icon"><ArrowUpRight size={16} /></span><Badge>03 · PRIMITIVES</Badge></div>
        <h3>Interfaces inside the answer</h3><p>Structured blocks can contain controls, tables, and compact data entry.</p>
        <div className="order-ticket">
          <div className="ticket-top"><span className="mono">ORDER TICKET</span><Badge>NVDA</Badge></div>
          <div className="ticket-tabs" role="tablist" aria-label="Order side">
            <button role="tab" aria-selected={side === "buy"} className={side === "buy" ? "selected" : ""} onClick={() => setSide("buy")}>Buy</button>
            <button role="tab" aria-selected={side === "sell"} className={side === "sell" ? "selected" : ""} onClick={() => setSide("sell")}>Sell</button>
          </div>
          <div className="ticket-fields"><label>SHARES<Input value="10" readOnly aria-label="Shares" /></label><label>ORDER TYPE<button className="ticket-select" type="button">Limit <ChevronDown size={13} /></button></label></div>
          <div className="ticket-price"><span>LIMIT PRICE</span><strong>$142.50</strong><small>EST. TOTAL <b>$1,425.00</b></small></div>
          <button type="button" className="ticket-review" disabled><LockKeyhole size={13} /> Review {side} order</button>
        </div>
        <div className="feature-card-meta"><span>INLINE INTERACTIVE BLOCK</span><ArrowDownRight size={13} /></div>
      </Card>
    </div>
  </div>;
}

function ActivityIcon() {
  return <span className="activity-icon-bars"><i /><i /><i /><i /></span>;
}
