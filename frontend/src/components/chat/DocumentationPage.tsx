"use client";

import Link from "next/link";
import { ArrowRight, Braces, ChartNoAxesCombined, Workflow } from "lucide-react";
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
