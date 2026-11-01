import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";
import Home from "./page";

const mocks = vi.hoisted(() => ({ sendMessage: vi.fn(), stop: vi.fn(), regenerate: vi.fn(), status: vi.fn() }));

vi.mock("@ai-sdk/react", () => ({
  useChat: () => {
    let messages: Array<Record<string, unknown>> = [];
    try {
      const saved = JSON.parse(window.localStorage.getItem("finsight-v2-conversations") ?? "[]") as Array<{ messages?: Array<Record<string, unknown>> }>;
      messages = saved[0]?.messages ?? [];
    } catch { /* The workspace handles invalid saved chats. */ }
    return { messages, setMessages: vi.fn(), sendMessage: mocks.sendMessage, status: mocks.status(), error: undefined, stop: mocks.stop, clearError: vi.fn(), regenerate: mocks.regenerate };
  },
}));

describe("FinSight V2 text research chat", () => {
  beforeEach(() => {
    window.localStorage.clear();
    mocks.sendMessage.mockClear();
    mocks.stop.mockClear();
    mocks.status.mockReturnValue("ready");
  });

  it("opens on an open-ended research screen without a company selector", async () => {
    render(<Home />);
    expect(await screen.findByRole("heading", { name: /Ask a question/ })).toBeInTheDocument();
    expect(screen.getByRole("textbox", { name: "Ask a research question" })).toBeInTheDocument();
    expect(screen.queryByRole("textbox", { name: /ticker|company/i })).not.toBeInTheDocument();
  });

  it("submits a natural-language prompt without ticker metadata", async () => {
    render(<Home />);
    const composer = screen.getByRole("textbox", { name: "Ask a research question" });
    fireEvent.change(composer, { target: { value: "Compare several semiconductor companies" } });
    fireEvent.click(screen.getByRole("button", { name: "Send message" }));
    await waitFor(() => expect(mocks.sendMessage).toHaveBeenCalledWith({ text: "Compare several semiconductor companies" }));
  });

  it("renders Claude's response as readable Markdown text", async () => {
    window.localStorage.setItem("finsight-v2-conversations", JSON.stringify([{
      id: "chat-1", title: "Research question", updatedAt: "2026-10-30T10:00:00Z",
      messages: [
        { id: "user-1", role: "user", parts: [{ type: "text", text: "Explain the metric" }] },
        { id: "assistant-1", role: "assistant", parts: [{ type: "text", text: "## Summary\n\nThe metric is **not a forecast**." }] },
      ],
    }]));
    render(<Home />);
    expect(await screen.findByRole("heading", { name: "Summary" })).toBeInTheDocument();
    expect(screen.getByText("not a forecast")).toBeInTheDocument();
  });

  it("renders a typed company-analysis template from response data", async () => {
    window.localStorage.setItem("finsight-v2-conversations", JSON.stringify([{
      id: "typed-1", title: "Analyze a company", updatedAt: "2026-10-30T10:00:00Z",
      messages: [
        { id: "user-1", role: "user", parts: [{ type: "text", text: "Analyze Example Corp" }] },
        { id: "assistant-1", role: "assistant", parts: [
          { type: "text", text: "Legacy fallback text should not be shown." },
          { type: "data-research-response", data: {
            schema_version: 1,
            template: "company_analysis",
            title: "Company analysis · Example Corp (EXM)",
            companies: [{ ticker: "EXM", name: "Example Corp", exchange: "Nasdaq" }],
            company: { ticker: "EXM", name: "Example Corp", exchange: "Nasdaq" },
            market_snapshot: { ticker: "EXM", as_of_date: "2026-10-30", period: "6mo", source_id: "MKT-EXM", metrics: [
              { key: "latest_close", value: 125.5, unit: "usd" },
              { key: "return_5d", value: 2.5, unit: "percent" },
            ] },
            news_articles: [], news_coverage: [], sources: [], limitations: [],
            narrative: { summary: "A sourced summary.", source_ids: [], positive_drivers: [], risks: [] },
          } },
        ] },
      ],
    }]));
    render(<Home />);
    expect(await screen.findByText("Company analysis · Example Corp (EXM)")).toBeInTheDocument();
    expect(screen.getByText("$125.50")).toBeInTheDocument();
    expect(screen.getByText("+2.50%")).toBeInTheDocument();
    expect(screen.queryByText("Legacy fallback text should not be shown.")).not.toBeInTheDocument();
  });

  it("shows only currently running research tools", async () => {
    mocks.status.mockReturnValue("streaming");
    window.localStorage.setItem("finsight-v2-conversations", JSON.stringify([{
      id: "active-1", title: "Research chat", updatedAt: "2026-10-30T10:00:00Z",
      messages: [
        { id: "user-1", role: "user", parts: [{ type: "text", text: "Recent company news" }] },
        { id: "assistant-1", role: "assistant", parts: [
          { type: "data-tool-status", data: { tool: "news_search", status: "running" } },
          { type: "data-tool-status", data: { tool: "market_data", status: "succeeded" } },
        ] },
      ],
    }]));
    render(<Home />);
    expect(await screen.findByText("News search · running")).toBeInTheDocument();
    expect(screen.queryByText(/Market data · succeeded/)).not.toBeInTheDocument();
  });
});
