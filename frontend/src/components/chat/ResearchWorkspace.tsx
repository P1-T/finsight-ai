"use client";

import { useCallback, useEffect, useMemo, useRef, useState, type FormEvent } from "react";
import { DefaultChatTransport } from "ai";
import { useChat } from "@ai-sdk/react";
import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";
import { ArrowUp, ChartCandlestick, CircleHelp, Command, MessageSquareText, PanelLeftClose, PanelLeftOpen, Plus, ReceiptText, Scale, ShieldCheck, Sparkles, Square, Trash2, PencilLine } from "lucide-react";
import { ResearchResponseView } from "@/components/chat/ResearchResponseView";
import type { CompanyIdentity, ResearchChatMessage, ResearchLayout, ResearchResponse, ResearchTool, SavedConversation } from "@/types/research";

const API_BASE = process.env.NEXT_PUBLIC_API_BASE_URL ?? "http://localhost:8000";
const STORAGE_KEY = "finsight-v2-conversations";
const TOOL_LABELS: Record<ResearchTool, string> = { market_data: "Market data", news_search: "News search", web_search: "Web search" };
const COMPONENT_LABELS: Record<string, string> = {
  company_header: "Company overview", metric_grid: "Market snapshot", price_chart: "Price chart",
  fundamental_cards: "Fundamentals", scenario_cards: "Scenarios", news_timeline: "Recent coverage",
  comparison_table: "Comparison", fact_grid: "Reported results", data_chart: "Chart", answer_card: "Answer",
  takeaways: "Takeaways",
};
const QUICK_PROMPTS = [
  { label: "Apple margin trends", prompt: "How have Apple's gross margins changed over the last five years?", icon: SquareLetterAIcon },
  { label: "Microsoft quarterly results", prompt: "Summarize Microsoft's latest quarterly results and the main drivers.", icon: ChartCandlestick },
  { label: "NVIDIA market context", prompt: "What market factors and recent news may explain NVIDIA's share move?", icon: ReceiptText },
  { label: "Compare two companies", prompt: "Compare the recent performance and business outlook for AMD and Intel.", icon: Scale },
];

function SquareLetterAIcon({ size = 24, strokeWidth = 2 }: { size?: number; strokeWidth?: number }) {
  return <svg width={size} height={size} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth={strokeWidth} strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">
    <rect x="3" y="3" width="18" height="18" rx="2" />
    <path d="m8 16 4-9 4 9M9.5 13h5" />
  </svg>;
}

function messageText(message: ResearchChatMessage): string {
  return message.parts.filter((part) => part.type === "text").map((part) => part.text).join("");
}

function parseConversations(value: unknown): SavedConversation[] {
  if (!Array.isArray(value)) return [];
  return value.filter((item): item is SavedConversation => {
    if (typeof item !== "object" || item === null) return false;
    const row = item as Record<string, unknown>;
    return typeof row.id === "string" && typeof row.title === "string" &&
      typeof row.updatedAt === "string" && Array.isArray(row.messages);
  }).slice(0, 20);
}

function titleFromMessages(messages: ResearchChatMessage[]): string {
  const firstPrompt = messages.find((message) => message.role === "user");
  const title = firstPrompt ? messageText(firstPrompt).trim() : "New research chat";
  return title.length > 48 ? `${title.slice(0, 45)}…` : title || "New research chat";
}

function toolStatuses(message: ResearchChatMessage): Array<{ tool: ResearchTool; status: string }> {
  const latest = new Map<ResearchTool, string>();
  for (const part of message.parts) {
    if (part.type === "data-tool-status") latest.set(part.data.tool, part.data.status);
  }
  return [...latest].filter(([, status]) => status === "running").map(([tool, status]) => ({ tool, status }));
}

function latestStage(message: ResearchChatMessage): string | null {
  const part = message.parts.filter((item) => item.type === "data-research-stage").at(-1);
  return part?.type === "data-research-stage" ? part.data.label : null;
}

function researchResponse(message: ResearchChatMessage): ResearchResponse | null {
  const part = message.parts.filter((item) => item.type === "data-research-response").at(-1);
  return part?.type === "data-research-response" ? part.data : null;
}

function researchLayout(message: ResearchChatMessage): ResearchLayout | null {
  const part = message.parts.filter((item) => item.type === "data-research-layout").at(-1);
  return part?.type === "data-research-layout" ? part.data : null;
}

export function ResearchWorkspace() {
  const [input, setInput] = useState("");
  const [conversations, setConversations] = useState<SavedConversation[]>([]);
  const [activeId, setActiveId] = useState<string | null>(null);
  const [activeUpdatedAt, setActiveUpdatedAt] = useState<string | null>(null);
  const [hydrated, setHydrated] = useState(false);
  const [sidebarOpen, setSidebarOpen] = useState(false);
  const scrollRef = useRef<HTMLDivElement>(null);
  const composerRef = useRef<HTMLTextAreaElement>(null);
  const anchorNextPromptRef = useRef(false);
  const activeIdRef = useRef(activeId);
  const chatCounterRef = useRef(0);

  useEffect(() => { activeIdRef.current = activeId; }, [activeId]);

  useEffect(() => {
    if (window.matchMedia("(max-width: 540px)").matches) setSidebarOpen(false);
  }, []);

  const prepareTransportRequest = useCallback(({ messages }: { messages: ResearchChatMessage[] }) => {
    const latest = [...messages].reverse().find((message) => message.role === "user");
    const prompt = latest ? messageText(latest).slice(0, 1200) : "";
    const history = messages.slice(0, -1)
      .filter((message) => message.role === "user" || message.role === "assistant")
      .map((message) => ({ role: message.role, text: messageText(message).slice(0, 1200) }))
      .filter((turn) => turn.text).slice(-8);
    return { body: { prompt, history } };
  }, []);

  const transport = useMemo(() => new DefaultChatTransport<ResearchChatMessage>({
    api: `${API_BASE}/api/chat/stream`,
    prepareSendMessagesRequest: prepareTransportRequest,
  }), [prepareTransportRequest]);
  const { messages, sendMessage, setMessages, status, error, stop, clearError, regenerate } = useChat<ResearchChatMessage>({ transport });
  const busy = status === "submitted" || status === "streaming";
  const hasConversation = messages.length > 0;

  const visibleConversations = useMemo(() => {
    if (!activeId || messages.length === 0) return conversations;
    const existing = conversations.find((conversation) => conversation.id === activeId);
    const conversation: SavedConversation = {
      id: activeId,
      title: existing?.title ?? titleFromMessages(messages),
      updatedAt: activeUpdatedAt ?? existing?.updatedAt ?? "",
      messages,
    };
    return [conversation, ...conversations.filter((item) => item.id !== activeId)].slice(0, 20);
  }, [activeId, activeUpdatedAt, conversations, messages]);
  const activeConversation = visibleConversations.find((conversation) => conversation.id === activeId);

  useEffect(() => {
    let timer = 0;
    const transferredPrompt = new URLSearchParams(window.location.search).get("prompt");
    if (transferredPrompt) {
      setInput(transferredPrompt.slice(0, 1200));
      window.history.replaceState(null, "", "/");
      timer = window.setTimeout(() => {
        setHydrated(true);
        composerRef.current?.focus();
      }, 0);
      return () => window.clearTimeout(timer);
    }
    try {
      const saved = parseConversations(JSON.parse(window.localStorage.getItem(STORAGE_KEY) ?? "[]"));
      timer = window.setTimeout(() => {
        setConversations(saved);
        setHydrated(true);
      }, 0);
    } catch {
      window.localStorage.removeItem(STORAGE_KEY);
      timer = window.setTimeout(() => setHydrated(true), 0);
    }
    return () => window.clearTimeout(timer);
  }, [setMessages]);

  useEffect(() => {
    if (!anchorNextPromptRef.current) return;
    const latestUserMessage = [...(scrollRef.current?.querySelectorAll<HTMLElement>(".v2-message-user") ?? [])].at(-1);
    if (!latestUserMessage) return;
    latestUserMessage.scrollIntoView({ block: "start", behavior: "smooth" });
    anchorNextPromptRef.current = false;
  }, [messages]);

  useEffect(() => {
    if (!hydrated) return;
    const timer = window.setTimeout(() => {
      try { window.localStorage.setItem(STORAGE_KEY, JSON.stringify(visibleConversations)); }
      catch { /* Keep the current chat in memory if storage is full or unavailable. */ }
    }, 250);
    return () => window.clearTimeout(timer);
  }, [hydrated, visibleConversations]);

  function submitPrompt(value: string) {
    const prompt = value.trim();
    if (!prompt || busy) return;
    const id = activeIdRef.current ?? globalThis.crypto?.randomUUID?.() ?? `chat-${++chatCounterRef.current}`;
    activeIdRef.current = id;
    setActiveId(id);
    setActiveUpdatedAt(new Date().toISOString());
    anchorNextPromptRef.current = true;
    clearError();
    sendMessage({ text: prompt });
    setInput("");
  }

  function onSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    submitPrompt(input);
  }

  function renderComposer(className: string) {
    return <form className={className} onSubmit={onSubmit}>
      <textarea ref={composerRef} value={input} rows={1} maxLength={1200} aria-label="Ask a research question" placeholder="Ask about a company, the market, or a recent move…" onChange={(event) => setInput(event.target.value)} onKeyDown={(event) => { if (event.key === "Enter" && !event.shiftKey) { event.preventDefault(); submitPrompt(input); } }} disabled={busy} />
      {busy ? <button type="button" className="v2-send-button stop" onClick={stop} aria-label="Stop response"><Square size={14} fill="currentColor" /></button> : <button type="submit" className="v2-send-button" disabled={!input.trim()} aria-label="Send message"><ArrowUp size={18} /></button>}
    </form>;
  }

  function focusComposer() {
    window.requestAnimationFrame(() => composerRef.current?.focus());
  }

  const newChat = useCallback(() => {
    stop();
    activeIdRef.current = null;
    setActiveId(null);
    setActiveUpdatedAt(null);
    setMessages([]);
    clearError();
    setInput("");
  }, [clearError, setMessages, stop]);

  function openConversation(conversation: SavedConversation) {
    if (busy) stop();
    activeIdRef.current = conversation.id;
    setActiveId(conversation.id);
    setActiveUpdatedAt(conversation.updatedAt);
    setMessages(conversation.messages as ResearchChatMessage[]);
    clearError();
  }

  function renameConversation(conversation: SavedConversation) {
    const title = window.prompt("Rename this chat", conversation.title)?.trim();
    if (!title) return;
    setConversations((previous) => previous.map((item) => item.id === conversation.id ? { ...item, title: title.slice(0, 80) } : item));
  }

  function deleteConversation(conversationId: string) {
    setConversations((previous) => previous.filter((item) => item.id !== conversationId));
    if (activeId === conversationId) newChat();
  }

  useEffect(() => {
    function onShortcut(event: KeyboardEvent) {
      if ((event.metaKey || event.ctrlKey) && event.key.toLowerCase() === "k") {
        event.preventDefault();
        if (!busy) { newChat(); focusComposer(); }
      }
    }
    window.addEventListener("keydown", onShortcut);
    return () => window.removeEventListener("keydown", onShortcut);
  }, [busy, newChat]);

  return <main className={`v2-shell ${sidebarOpen ? "sidebar-visible" : "sidebar-collapsed"}`}>
    <aside className="v2-sidebar" aria-label="Chat history">
      <div className="sidebar-brand-row"><a href="/" className="v2-brand" aria-label="Finsight AI home"><span className="v2-brand-mark" aria-hidden="true">*</span><span>Finsight AI</span></a>{sidebarOpen ? <button className="sidebar-toggle" onClick={() => setSidebarOpen(false)} aria-label="Collapse sidebar" title="Collapse sidebar"><PanelLeftClose size={17} /></button> : null}</div>
      <button className="new-chat-button" onClick={newChat}><Plus size={16} /> New chat <kbd>⌘ K</kbd></button>
      <div className="history-heading"><span>RECENT CHATS</span></div>
      <nav className="conversation-list" aria-label="Recent chats">
        {visibleConversations.map((conversation) => <div className={`conversation-row ${conversation.id === activeId ? "is-active" : ""}`} key={conversation.id}>
          <button className="conversation-open" onClick={() => openConversation(conversation)}><MessageSquareText size={15} /><span>{conversation.title}</span></button>
          <div className="conversation-actions"><button onClick={() => renameConversation(conversation)} aria-label={`Rename ${conversation.title}`} title="Rename"><PencilLine size={13} /></button><button onClick={() => deleteConversation(conversation.id)} aria-label={`Delete ${conversation.title}`} title="Delete"><Trash2 size={13} /></button></div>
        </div>)}
        {visibleConversations.length === 0 ? <p className="history-empty">Your chats are saved in this browser.</p> : null}
      </nav>
      <div className="sidebar-bottom"><div className="local-history-note"><ShieldCheck size={14} /><span>Private to this browser<br />No account or server history</span></div><a className="sidebar-help" href="/documentation"><CircleHelp size={15} /> Documentation</a></div>
    </aside>
    {sidebarOpen ? <button className="sidebar-backdrop" onClick={() => setSidebarOpen(false)} aria-label="Close chat history" /> : null}

    <section className="v2-main" id="home">
      {!sidebarOpen ? <button className="sidebar-expand-floating" onClick={() => setSidebarOpen(true)} aria-label="Expand sidebar" title="Expand sidebar"><PanelLeftOpen size={18} /></button> : null}
      {hasConversation ? <header className="v2-topbar">
        <div className="v2-breadcrumb"><span>Finsight AI</span><i>/</i><strong>{activeConversation?.title ?? "Research chat"}</strong></div>
        <span className="text-only-label"><i /> COMPONENT-DRIVEN RESEARCH</span>
      </header> : null}

      <div className={`v2-conversation ${hasConversation ? "with-messages" : "welcome-state"}`} ref={scrollRef}>
        {!hasConversation ? <section className="v2-welcome">
          <div className="landing-content">
            <h1>Hi, I'm Finsight. Where should we start?</h1>
            {renderComposer("v2-composer welcome-composer")}
            <div className="welcome-suggestions" aria-label="Suggested prompts">
              {QUICK_PROMPTS.map((item) => {
                const PromptIcon = item.icon;
                return <button key={item.label} onClick={() => submitPrompt(item.prompt)} disabled={busy}>
                  <span className="suggestion-company-icon"><PromptIcon size={17} strokeWidth={1.8} /></span>
                  <span className="suggestion-label">{item.label}</span><ArrowUp className="suggestion-arrow-icon" size={13} />
                </button>;
              })}
            </div>
          </div>
        </section> : <div className="v2-message-thread">
          {messages.map((message, messageIndex) => {
            const text = messageText(message);
            const response = message.role === "assistant" ? researchResponse(message) : null;
            const latestAssistant = message.role === "assistant" && message.id === messages.at(-1)?.id;
            const statuses = message.role === "assistant" ? toolStatuses(message) : [];
            const stage = message.role === "assistant" ? latestStage(message) : null;
            const layout = message.role === "assistant" ? researchLayout(message) : null;
            return <article className={`v2-message v2-message-${message.role}`} key={message.id}>
              {message.role === "user" ? <><div className="v2-user-label">YOU</div><div className="v2-user-text"><ReactMarkdown remarkPlugins={[remarkGfm]}>{text}</ReactMarkdown></div></> : <>
                <div className="v2-answer-heading"><span className="answer-avatar"><Sparkles size={15} /></span><div><strong>Finsight</strong><small>Research assistant</small></div></div>
                {latestAssistant && busy && statuses.length ? <div className="source-status-row">{statuses.map(({ tool }) => <span className="source-status status-running" key={tool}><i />{TOOL_LABELS[tool]} · running</span>)}</div> : null}
                {latestAssistant && busy && !statuses.length && stage ? <div className="source-status-row"><span className="source-status status-running"><i />{stage}</span></div> : null}
                {latestAssistant && busy && layout ? <div className="research-layout-preview" aria-live="polite"><span>Response layout</span>{layout.components.map((component) => COMPONENT_LABELS[component] ? <i key={component}>{COMPONENT_LABELS[component]}</i> : null)}</div> : null}
                {response ? <ResearchResponseView
                  response={response}
                  copyText={text}
                  onFollowUp={submitPrompt}
                  onResolveCompany={(company: CompanyIdentity) => {
                    const originalPrompt = [...messages.slice(0, messageIndex)].reverse().find((item) => item.role === "user");
                    submitPrompt(`I meant ${company.name} (${company.ticker}). Please continue with my previous request: ${originalPrompt ? messageText(originalPrompt) : "research this company"}`);
                  }}
                /> : text ? <div className="v2-assistant-text"><ReactMarkdown remarkPlugins={[remarkGfm]}>{text}</ReactMarkdown></div> : null}
                {latestAssistant && !busy && text ? <div className="answer-actions"><button onClick={() => regenerate()} title="Regenerate answer">Regenerate</button></div> : null}
              </>}
            </article>;
          })}
          {error ? <div className="v2-stream-error" role="alert">{error.message || "The research request failed."}<button onClick={() => regenerate()}>Retry</button></div> : null}
        </div>}
      </div>

      {hasConversation ? <footer className="v2-composer-area">
        {renderComposer("v2-composer")}
        <div className="v2-composer-meta"><span><Command size={12} /> Enter to send · Shift + Enter for a new line</span><span>AI selects the response layout</span></div>
      </footer> : null}
    </section>
  </main>;
}
