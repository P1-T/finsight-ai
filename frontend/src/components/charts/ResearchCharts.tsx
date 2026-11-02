"use client";

import {
  Bar,
  BarChart,
  CartesianGrid,
  Cell,
  Line,
  LineChart,
  Pie,
  PieChart,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";
import type { DataChartBlock, PricePoint } from "@/types/research";

const COLORS = ["#4f805a", "#7fa184", "#b1c9ae", "#d2a16a", "#c77863", "#8aa7b2"];

export function HistoricalPriceChart({ points }: { points: PricePoint[] }) {
  return <div className="research-chart" role="img" aria-label={`Historical closing prices for ${points.length} trading sessions`}>
    <ResponsiveContainer width="100%" height={250}>
      <LineChart data={points} margin={{ top: 8, right: 8, bottom: 0, left: 4 }}>
        <CartesianGrid stroke="#edf0eb" vertical={false} />
        <XAxis dataKey="date" tick={{ fill: "#879188", fontSize: 11 }} tickLine={false} axisLine={false} minTickGap={32} />
        <YAxis tickFormatter={(value: number) => `$${value.toFixed(0)}`} tick={{ fill: "#879188", fontSize: 11 }} tickLine={false} axisLine={false} width={56} domain={["auto", "auto"]} />
        <Tooltip labelStyle={{ color: "#344139" }} formatter={(value) => [`$${Number(value).toFixed(2)}`, "Close"]} />
        <Line type="monotone" dataKey="close" stroke="#4f805a" strokeWidth={2.5} dot={false} activeDot={{ r: 4 }} isAnimationActive={false} />
      </LineChart>
    </ResponsiveContainer>
  </div>;
}

function valueFormatter(unit: DataChartBlock["unit"]): (value: number) => string {
  if (unit === "percent") return (value) => `${value}%`;
  if (unit.endsWith("_billions")) return (value) => `${unit.startsWith("EUR") ? "€" : "$"}${value}B`;
  if (unit.endsWith("_millions")) return (value) => `${unit.startsWith("EUR") ? "€" : "$"}${value}M`;
  if (unit === "USD") return (value) => `$${value}`;
  if (unit === "EUR") return (value) => `€${value}`;
  return (value) => value.toLocaleString();
}

export function DataChart({ block }: { block: DataChartBlock }) {
  const formatValue = valueFormatter(block.unit);
  if (block.chart_type === "donut") {
    return <div className="research-chart research-donut-layout">
      <div className="research-donut">
        <ResponsiveContainer width="100%" height={230}>
          <PieChart>
            <Pie data={block.data} dataKey="value" nameKey="label" innerRadius={58} outerRadius={88} paddingAngle={2} isAnimationActive={false}>
              {block.data.map((item, index) => <Cell key={`${item.label}-${index}`} fill={COLORS[index % COLORS.length]} />)}
            </Pie>
            <Tooltip formatter={(value) => formatValue(Number(value))} />
          </PieChart>
        </ResponsiveContainer>
      </div>
      <ul className="research-chart-legend">{block.data.map((item, index) => <li key={`${item.label}-${index}`}><i style={{ backgroundColor: COLORS[index % COLORS.length] }} /><span>{item.label}</span><strong>{formatValue(item.value)}</strong></li>)}</ul>
    </div>;
  }
  if (block.chart_type === "line") {
    return <div className="research-chart" role="img" aria-label={block.title}>
      <ResponsiveContainer width="100%" height={250}>
        <LineChart data={block.data} margin={{ top: 8, right: 8, bottom: 4, left: 4 }}>
          <CartesianGrid stroke="#edf0eb" vertical={false} />
          <XAxis dataKey="label" tick={{ fill: "#879188", fontSize: 11 }} tickLine={false} axisLine={false} />
          <YAxis tickFormatter={(value: number) => formatValue(value)} tick={{ fill: "#879188", fontSize: 11 }} tickLine={false} axisLine={false} width={64} />
          <Tooltip formatter={(value) => formatValue(Number(value))} />
          <Line type="monotone" dataKey="value" stroke="#4f805a" strokeWidth={2.5} dot={{ r: 3 }} isAnimationActive={false} />
        </LineChart>
      </ResponsiveContainer>
    </div>;
  }
  return <div className="research-chart" role="img" aria-label={block.title}>
    <ResponsiveContainer width="100%" height={260}>
      <BarChart data={block.data} margin={{ top: 8, right: 8, bottom: 24, left: 4 }}>
        <CartesianGrid stroke="#edf0eb" vertical={false} />
        <XAxis dataKey="label" tick={{ fill: "#738076", fontSize: 11 }} tickLine={false} axisLine={false} interval={0} angle={-12} textAnchor="end" height={52} />
        <YAxis tickFormatter={(value: number) => formatValue(value)} tick={{ fill: "#879188", fontSize: 11 }} tickLine={false} axisLine={false} width={64} />
        <Tooltip formatter={(value) => formatValue(Number(value))} />
        <Bar dataKey="value" fill="#5c8764" radius={[5, 5, 0, 0]} isAnimationActive={false} />
      </BarChart>
    </ResponsiveContainer>
  </div>;
}
