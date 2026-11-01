"use client";

import { useCallback, useEffect, useMemo, useRef, useState, type FormEvent } from "react";
import { DefaultChatTransport } from "ai";
import { useChat } from "@ai-sdk/react";
import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";
import { Activity, ArrowUp, CircleHelp, Command, MessageSquareText, Plus, ShieldCheck, Sparkles, Square, Trash2, PencilLine } from "lucide-react";
import { ResearchResponseView } from "@/components/chat/ResearchResponseView";
import type { CompanyIdentity, ResearchChatMessage, ResearchResponse, ResearchTool, SavedConversation } from "@/types/research";

const API_BASE = process.env.NEXT_PUBLIC_API_BASE_URL ?? "http://localhost:8000";
const STORAGE_KEY = "finsight-v2-conversations";
const TOOL_LABELS: Record<ResearchTool, string> = { market_data: "Market data", news_search: "News search", web_search: "Web search" };
const SUGGESTIONS = [
  { title: "Compare two companies", detail: "Recent performance, catalysts, and key differences", prompt: "Compare AMD and Alphabet using their recent market performance and news." },
  { title: "Understand a market move", detail: "Use recent coverage to explain what may be driving it", prompt: "What recent news and market factors may explain the move in Tesla shares?" },
  { title: "Research an industry", detail: "Find current developments and company implications", prompt: "What are the most important recent developments in the semiconductor industry?" },
  { title: "Ask a finance question", detail: "Get a plain language explanation", prompt: "Explain the difference between free cash flow and operating cash flow." },
];

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

export function ResearchWorkspace() {
  const [input, setInput] = useState("");
  const [conversations, setConversations] = useState<SavedConversation[]>([]);
  const [activeId, setActiveId] = useState<string | null>(null);
  const [activeUpdatedAt, setActiveUpdatedAt] = useState<string | null>(null);
  const [hydrated, setHydrated] = useState(false);
  const [sidebarOpen, setSidebarOpen] = useState(true);
  const scrollRef = useRef<HTMLDivElement>(null);
  const activeIdRef = useRef(activeId);
  const chatCounterRef = useRef(0);

  useEffect(() => { activeIdRef.current = activeId; }, [activeId]);

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
    try {
      const saved = parseConversations(JSON.parse(window.localStorage.getItem(STORAGE_KEY) ?? "[]"));
      timer = window.setTimeout(() => {
        setConversations(saved);
        if (saved[0]) {
          activeIdRef.current = saved[0].id;
          setActiveId(saved[0].id);
          setActiveUpdatedAt(saved[0].updatedAt);
          setMessages(saved[0].messages as ResearchChatMessage[]);
        }
        setHydrated(true);
      }, 0);
    } catch {
      window.localStorage.removeItem(STORAGE_KEY);
      timer = window.setTimeout(() => setHydrated(true), 0);
    }
    return () => window.clearTimeout(timer);
  }, [setMessages]);

  useEffect(() => {
    scrollRef.current?.scrollTo({ top: scrollRef.current.scrollHeight, behavior: "smooth" });
  }, [messages, status]);

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
    clearError();
    sendMessage({ text: prompt });
    setInput("");
  }

  function onSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    submitPrompt(input);
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
        if (!busy) newChat();
      }
    }
    window.addEventListener("keydown", onShortcut);
    return () => window.removeEventListener("keydown", onShortcut);
  }, [busy, newChat]);

  return <main className={`v2-shell ${sidebarOpen ? "sidebar-visible" : "sidebar-collapsed"}`}>
    <aside className="v2-sidebar" aria-label="Chat history">
      <div className="sidebar-brand-row"><a href="#home" className="v2-brand"><span className="v2-brand-mark"><Activity size={17} /></span><span>FinSight <em>AI</em></span></a><button className="sidebar-toggle" onClick={() => setSidebarOpen(false)} aria-label="Collapse sidebar">‹</button></div>
      <button className="new-chat-button" onClick={newChat}><Plus size={16} /> New chat <kbd>⌘ K</kbd></button>
      <div className="history-heading"><span>RECENT CHATS</span></div>
      <nav className="conversation-list" aria-label="Recent chats">
        {visibleConversations.map((conversation) => <div className={`conversation-row ${conversation.id === activeId ? "is-active" : ""}`} key={conversation.id}>
          <button className="conversation-open" onClick={() => openConversation(conversation)}><MessageSquareText size={15} /><span>{conversation.title}</span></button>
          <div className="conversation-actions"><button onClick={() => renameConversation(conversation)} aria-label={`Rename ${conversation.title}`} title="Rename"><PencilLine size={13} /></button><button onClick={() => deleteConversation(conversation.id)} aria-label={`Delete ${conversation.title}`} title="Delete"><Trash2 size={13} /></button></div>
        </div>)}
        {visibleConversations.length === 0 ? <p className="history-empty">Your chats are saved in this browser.</p> : null}
      </nav>
      <div className="sidebar-bottom"><div className="local-history-note"><ShieldCheck size={14} /><span>Private to this browser<br />No account or server history</span></div><button className="sidebar-help" title="Research and educational tool"><CircleHelp size={15} /> About this workspace</button></div>
    </aside>
    {sidebarOpen ? <button className="sidebar-backdrop" onClick={() => setSidebarOpen(false)} aria-label="Close chat history" /> : null}

    <section className="v2-main" id="home">
      <header className="v2-topbar">
        {!sidebarOpen ? <button className="sidebar-toggle topbar-expand" onClick={() => setSidebarOpen(true)} aria-label="Expand sidebar">☰</button> : null}
        <div className="v2-breadcrumb"><span>FinSight AI</span><i>/</i><strong>{activeConversation?.title ?? "Research chat"}</strong></div>
        <span className="text-only-label"><Sparkles size={13} /> VISUAL RESEARCH</span>
      </header>

      <div className={`v2-conversation ${hasConversation ? "with-messages" : "welcome-state"}`} ref={scrollRef}>
        {!hasConversation ? <section className="v2-welcome">
          <div className="v2-welcome-kicker"><span /> OPEN-ENDED EQUITY RESEARCH</div>
          <h1>Ask a question.<br /><span>Get a grounded answer.</span></h1>
          <p>Claude interprets your question, selects relevant market, news, and web research, then writes a source-grounded response.</p>
          <div className="welcome-search-hint"><Command size={15} /><span>Ask about one company, compare several, or ask a general finance question.</span></div>
          <div className="v2-suggestions">
            {SUGGESTIONS.map((suggestion, index) => <button className="v2-suggestion" key={suggestion.title} onClick={() => submitPrompt(suggestion.prompt)} disabled={busy}>
              <span className="suggestion-number">0{index + 1}</span><span><strong>{suggestion.title}</strong><small>{suggestion.detail}</small></span><span className="suggestion-arrow">↗</span>
            </button>)}
          </div>
        </section> : <div className="v2-message-thread">
          {messages.map((message, messageIndex) => {
            const text = messageText(message);
            const response = message.role === "assistant" ? researchResponse(message) : null;
            const latestAssistant = message.role === "assistant" && message.id === messages.at(-1)?.id;
            const statuses = message.role === "assistant" ? toolStatuses(message) : [];
            const stage = message.role === "assistant" ? latestStage(message) : null;
            return <article className={`v2-message v2-message-${message.role}`} key={message.id}>
              {message.role === "user" ? <><div className="v2-user-label">YOU</div><div className="v2-user-text"><ReactMarkdown remarkPlugins={[remarkGfm]}>{text}</ReactMarkdown></div></> : <>
                <div className="v2-answer-heading"><span className="answer-avatar"><Sparkles size={15} /></span><div><strong>FinSight</strong><small>Research assistant</small></div></div>
                {latestAssistant && busy && statuses.length ? <div className="source-status-row">{statuses.map(({ tool }) => <span className="source-status status-running" key={tool}><i />{TOOL_LABELS[tool]} · running</span>)}</div> : null}
                {latestAssistant && busy && !statuses.length && stage ? <div className="source-status-row"><span className="source-status status-running"><i />{stage}</span></div> : null}
                {response ? <ResearchResponseView
                  response={response}
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

      <footer className="v2-composer-area">
        <form className="v2-composer" onSubmit={onSubmit}>
          <textarea value={input} rows={1} maxLength={1200} aria-label="Ask a research question" placeholder="Ask about a company, several companies, a market move, or finance…" onChange={(event) => setInput(event.target.value)} onKeyDown={(event) => { if (event.key === "Enter" && !event.shiftKey) { event.preventDefault(); submitPrompt(input); } }} disabled={busy} />
          {busy ? <button type="button" className="v2-send-button stop" onClick={stop} aria-label="Stop response"><Square size={14} fill="currentColor" /></button> : <button type="submit" className="v2-send-button" disabled={!input.trim()} aria-label="Send message"><ArrowUp size={18} /></button>}
        </form>
        <div className="v2-composer-meta"><span><Command size={12} /> Enter to send · Shift + Enter for a new line</span><span>AI selects the response layout</span></div>
        <div className="v2-disclaimer"><ShieldCheck size={13} /> Portfolio demo only. Synthetic figures are labeled; outputs are not financial advice.</div>
      </footer>
    </section>
  </main>;
}
