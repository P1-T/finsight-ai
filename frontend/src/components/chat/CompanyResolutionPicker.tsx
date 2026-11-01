"use client";

import { useEffect, useState } from "react";
import { Check, Search } from "lucide-react";
import type { CompanyIdentity, CompanySearchResponse } from "@/types/research";

const API_BASE = process.env.NEXT_PUBLIC_API_BASE_URL ?? "http://localhost:8000";

export function CompanyResolutionPicker({
  initialQuery,
  initialSuggestions = [],
  onResolve,
}: {
  initialQuery: string;
  initialSuggestions?: CompanyIdentity[];
  onResolve: (company: CompanyIdentity) => void;
}) {
  const [query, setQuery] = useState(initialQuery);
  const [suggestions, setSuggestions] = useState(initialSuggestions);
  const [selected, setSelected] = useState<CompanyIdentity | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    const normalized = query.trim();
    if (normalized.length < 2) return;
    const controller = new AbortController();
    const timer = window.setTimeout(async () => {
      setLoading(true);
      setError(null);
      try {
        const response = await fetch(`${API_BASE}/api/companies/search?q=${encodeURIComponent(normalized)}`, { signal: controller.signal });
        if (!response.ok) throw new Error("Company search is unavailable right now.");
        const result = await response.json() as CompanySearchResponse;
        setSuggestions(result.companies);
      } catch (reason) {
        if (!controller.signal.aborted) {
          setError(reason instanceof Error ? reason.message : "Company search is unavailable right now.");
          setSuggestions([]);
        }
      } finally {
        if (!controller.signal.aborted) setLoading(false);
      }
    }, 220);
    return () => {
      window.clearTimeout(timer);
      controller.abort();
    };
  }, [query]);

  return <section className="company-resolution-picker" aria-label="Resolve company name">
    <label htmlFor="company-resolution-query">Find the company by name or ticker</label>
    <div className="company-resolution-input-wrap">
      <Search size={16} aria-hidden="true" />
      <input
        id="company-resolution-query"
        value={query}
        onChange={(event) => {
          const value = event.target.value;
          setQuery(value);
          setSuggestions([]);
          setSelected(null);
          setError(null);
          setLoading(value.trim().length >= 2);
          if (value.trim().length < 2) {
            setLoading(false);
          }
        }}
        placeholder="Search company or ticker"
        autoComplete="off"
      />
      {loading ? <span className="company-resolution-loading">Searching</span> : null}
    </div>
    {suggestions.length ? <ul id="company-resolution-options" className="company-resolution-options" aria-label="Matching companies">
      {suggestions.map((company) => <li key={company.ticker}>
        <button type="button" aria-pressed={selected?.ticker === company.ticker} onClick={() => setSelected(company)}>
          <span className="company-resolution-symbol">{company.ticker}</span>
          <span className="company-resolution-name">{company.name}<small>{company.exchange}</small></span>
          {selected?.ticker === company.ticker ? <Check size={16} aria-label="Selected" /> : null}
        </button>
      </li>)}
    </ul> : null}
    {error ? <p className="company-resolution-message" role="status">{error}</p>
      : !loading && query.trim().length >= 2 && !suggestions.length ? <p className="company-resolution-message">No matching US-listed companies found. Try another spelling or ticker.</p> : null}
    {selected ? <button className="company-resolution-continue" type="button" onClick={() => onResolve(selected)}>
      Continue with {selected.ticker}
    </button> : null}
  </section>;
}
