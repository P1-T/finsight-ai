"use client";

import Link from "next/link";
import { ArrowRight, Braces, ChartNoAxesCombined, Database, Network, Search, Server, Workflow } from "lucide-react";
import { GenerativePreview } from "@/components/chat/GenerativePreview";

const steps = [
  { number: "01", title: "Understand the question", description: "Claude identifies the request, relevant companies, and the evidence needed to answer it." },
  { number: "02", title: "Gather context", description: "The workflow calls market data, web search, and news tools when they fit the request." },
  { number: "03", title: "Compose the response", description: "A validated response schema maps the answer to reusable charts, metrics, tables, and other UI blocks." },
];

export function DocumentationPage() {
  return <main className="documentation-page">
    <header className="documentation-header">
      <Link href="/" className="documentation-brand"><span className="v2-brand-mark" aria-hidden="true">*</span><span>Finsight AI</span></Link>
      <Link href="/" className="documentation-back">Open research workspace <ArrowRight size={15} /></Link>
    </header>

    <div className="documentation-content">
      <section className="documentation-intro">
        <span className="documentation-eyebrow">PRODUCT DOCUMENTATION</span>
        <h1>How Finsight works</h1>
        <p>Finsight turns open-ended market research questions into grounded answers and structured visual components.</p>
      </section>

      <section className="documentation-demo" aria-labelledby="demo-heading">
        <div className="documentation-section-heading"><div><span className="documentation-eyebrow">INTERACTIVE EXAMPLE</span><h2 id="demo-heading">A response, assembled from components</h2></div><Braces size={19} /></div>
        <GenerativePreview onUsePrompt={(prompt) => { window.location.assign(`/?prompt=${encodeURIComponent(prompt)}`); }} />
      </section>

      <section className="documentation-architecture" aria-labelledby="architecture-heading">
        <div className="documentation-section-heading"><div><span className="documentation-eyebrow">HIGH-LEVEL SYSTEM DESIGN</span><h2 id="architecture-heading">How a question becomes a response</h2></div><Network size={19} /></div>

        <div className="architecture-flow" aria-label="FinSight request and response architecture">
          <article className="architecture-node"><span className="architecture-node-icon"><Braces size={17} /></span><div><small>CLIENT</small><strong>Next.js chat UI</strong><p>React, TypeScript, AI SDK streaming, and browser-local conversation history.</p></div></article>
          <ArrowRight className="architecture-arrow" size={18} />
          <article className="architecture-node"><span className="architecture-node-icon"><Server size={17} /></span><div><small>API</small><strong>FastAPI stream endpoint</strong><p><code>POST /api/chat/stream</code> validates input and streams stages and results.</p></div></article>
          <ArrowRight className="architecture-arrow" size={18} />
          <article className="architecture-node"><span className="architecture-node-icon"><Workflow size={17} /></span><div><small>ORCHESTRATION</small><strong>LangGraph workflow</strong><p>Runs a bounded plan → retrieve → synthesize graph for each turn.</p></div></article>
        </div>

        <div className="architecture-lanes">
          <div className="architecture-lane-label"><span>1</span><strong>Plan</strong><small>Claude returns a structured tool and response-template plan.</small></div>
          <div className="architecture-lane-label"><span>2</span><strong>Retrieve selected evidence</strong><small>Only requested tools run; independent calls run concurrently.</small></div>
          <div className="architecture-provider-grid">
            <article><ChartNoAxesCombined size={16} /><strong>Market data</strong><code>YFinanceMarketDataProvider</code><small>Historical OHLCV, normalized and summarized into market metrics.</small></article>
            <article><Search size={16} /><strong>Web and news search</strong><code>DDGSWebSearchProvider</code><small>DuckDuckGo text/news results, normalized, filtered, and deduplicated.</small></article>
            <article><Database size={16} /><strong>Company directory</strong><code>company_directory</code><small>Company/ticker matching and autocomplete for ambiguous names.</small></article>
          </div>
          <div className="architecture-lane-label"><span>3</span><strong>Synthesize and validate</strong><small>Claude receives the prompt and bounded evidence; Pydantic validates typed response data.</small></div>
          <div className="architecture-output-row">
            <article><Braces size={16} /><strong>Visual response schema</strong><small>Template, narrative, evidence references, and approved component blocks.</small></article>
            <ArrowRight className="architecture-arrow" size={18} />
            <article><ChartNoAxesCombined size={16} /><strong>Visual composer and renderer</strong><small>Backend composes declarative blocks; React renders cards, tables, and Recharts visualizations.</small></article>
          </div>
        </div>

        <div className="architecture-details">
          <article><h3>Frontend</h3><p><code>ResearchWorkspace.tsx</code> manages the chat, streaming state, prompt input, company resolution, and local conversation history. <code>ResearchResponseView.tsx</code> and <code>VisualBlockRenderer.tsx</code> render validated response blocks.</p></article>
          <article><h3>Backend</h3><p><code>api/routes.py</code> exposes health, company search, and streaming chat routes. <code>graph/chat_graph.py</code> orchestrates the request; provider modules isolate external data access.</p></article>
          <article><h3>Analysis and resilience</h3><p><code>technical_indicators.py</code> calculates market metrics deterministically. <code>demo_data.py</code> supplies clearly isolated demo fallbacks when live evidence is unavailable; tool failures are reported without stopping successful tools.</p></article>
        </div>
      </section>

      <section className="documentation-workflow" aria-labelledby="workflow-heading">
        <div className="documentation-section-heading"><div><span className="documentation-eyebrow">RESEARCH PIPELINE</span><h2 id="workflow-heading">From question to response</h2></div><Workflow size={19} /></div>
        <div className="documentation-steps">{steps.map((step) => <article className="documentation-step" key={step.number}>
          <span className="documentation-step-number">{step.number}</span><h3>{step.title}</h3><p>{step.description}</p>
        </article>)}</div>
      </section>

      <section className="documentation-components" aria-labelledby="components-heading">
        <div className="documentation-section-heading"><div><span className="documentation-eyebrow">REUSABLE RESPONSE UI</span><h2 id="components-heading">Visual building blocks</h2></div><ChartNoAxesCombined size={19} /></div>
        <p>Response layouts are assembled from typed components such as market snapshots, company headers, comparison tables, price history, fundamental metrics, news timelines, scenario cards, and interactive charts.</p>
      </section>
    </div>
  </main>;
}
