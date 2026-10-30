export function formatCurrency(value: number | null): string {
  if (value === null || !Number.isFinite(value)) return "Unavailable";
  return new Intl.NumberFormat("en-US", { style: "currency", currency: "USD" }).format(value);
}

export function formatCompactCurrency(value: number | null): string {
  if (value === null || !Number.isFinite(value)) return "Unavailable";
  const absolute = Math.abs(value);
  const tiers = [
    { threshold: 1_000_000_000_000, suffix: "T" },
    { threshold: 1_000_000_000, suffix: "B" },
    { threshold: 1_000_000, suffix: "M" },
  ];
  const tier = tiers.find(({ threshold }) => absolute >= threshold);
  if (!tier) return formatCurrency(value);
  const sign = value < 0 ? "-" : "";
  return `${sign}$${(absolute / tier.threshold).toFixed(1)}${tier.suffix}`;
}

export function formatPercent(value: number | null): string {
  if (value === null || !Number.isFinite(value)) return "Unavailable";
  return `${value > 0 ? "+" : ""}${value.toFixed(2)}%`;
}

export function formatDate(value: string | null, includeTime = false): string {
  if (!value) return "Date unavailable";
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return "Date unavailable";
  return new Intl.DateTimeFormat("en-US", {
    dateStyle: "medium",
    ...(includeTime ? { timeStyle: "short" as const, timeZone: "UTC" } : { timeZone: "UTC" }),
  }).format(date);
}
