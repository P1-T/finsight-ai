"use client";

import { useMemo, useState } from "react";
import {
  Bar, BarChart, CartesianGrid, Cell, Legend, Line, LineChart, Pie, PieChart,
  PolarAngleAxis, RadialBar, RadialBarChart, ReferenceLine, ResponsiveContainer,
  Tooltip, XAxis, YAxis,
} from "recharts";
import type { DataChartBlock, PricePoint } from "@/types/research";

const PALETTE = ["#4f6bed", "#168c80", "#8061c9", "#bd842d", "#33859b", "#bd5b8d"];
const POSITIVE = "#168c80";
const NEGATIVE = "#c05263";
const gridColor = "var(--chart-grid)";
const tick = { fill: "var(--chart-muted)", fontSize: 12 };
const tooltipStyle = { background: "var(--chart-tooltip-bg)", border: "1px solid var(--chart-tooltip-border)", borderRadius: 7, color: "var(--chart-tooltip-text)", fontSize: 12 };

export function HistoricalPriceChart({ points }: { points: PricePoint[] }) {
  return <div className="research-chart" role="img" aria-label={`Historical closing prices for ${points.length} trading sessions`}>
    <ResponsiveContainer width="100%" height={250}>
      <LineChart data={points} margin={{ top: 8, right: 8, bottom: 0, left: 4 }}>
        <CartesianGrid stroke={gridColor} vertical={false} />
        <XAxis dataKey="date" tick={tick} tickLine={false} axisLine={false} minTickGap={32} />
        <YAxis tickFormatter={(value: number) => `$${value.toFixed(0)}`} tick={tick} tickLine={false} axisLine={false} width={56} domain={["auto", "auto"]} />
        <Tooltip contentStyle={tooltipStyle} labelStyle={{ color: "var(--chart-muted)" }} formatter={(value) => [`$${Number(value).toFixed(2)}`, "Close"]} />
        <Line type="monotone" dataKey="close" stroke="#2563eb" strokeWidth={1.8} dot={false} activeDot={{ r: 3, fill: "#2563eb" }} isAnimationActive={false} />
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

function SeriesLegend({ block }: { block: DataChartBlock }) {
  if (!block.series?.length) return null;
  return <ul className="research-series-legend" aria-label="Chart series">
    {block.series.map((series, index) => <li key={series.key}><i style={{ backgroundColor: series.color ?? PALETTE[index % PALETTE.length] }} />{series.name}</li>)}
  </ul>;
}

export function DataChart({ block }: { block: DataChartBlock }) {
  const formatValue = valueFormatter(block.unit);
  const [hiddenSlices, setHiddenSlices] = useState<string[]>([]);
  const chartData = useMemo(() => block.data.map((item) => ({ ...item, ...(item.values ?? {}) })), [block.data]);
  const isDonut = ["donut", "donut_text", "pie_interactive"].includes(block.chart_type);
  const isLine = ["line", "line_multi"].includes(block.chart_type);
  const isHorizontal = block.chart_type === "bar_horizontal";
  const series = block.series?.length ? block.series : [{ key: "value", name: block.title, color: PALETTE[0] }];

  if (isDonut) {
    const visibleData = block.chart_type === "pie_interactive"
      ? block.data.filter((item) => !hiddenSlices.includes(item.label))
      : block.data;
    return <>
      <div className={`research-chart ${block.chart_type === "pie_interactive" ? "research-pie-interactive" : "research-donut-layout"}`}>
        <div className="research-donut">
          <ResponsiveContainer width="100%" height={235}>
            <PieChart>
              <Pie data={visibleData} dataKey="value" nameKey="label" innerRadius={block.chart_type === "pie_interactive" ? 0 : 62} outerRadius={88} paddingAngle={2} isAnimationActive={false}>
                {visibleData.map((item) => {
                  const originalIndex = block.data.findIndex((candidate) => candidate.label === item.label);
                  return <Cell key={item.label} fill={PALETTE[originalIndex % PALETTE.length]} />;
                })}
              </Pie>
              {block.chart_type === "donut_text" && <text x="50%" y="47%" textAnchor="middle" dominantBaseline="middle" className="research-donut-center-value">{block.center_value ?? ""}</text>}
              {block.chart_type === "donut_text" && <text x="50%" y="57%" textAnchor="middle" dominantBaseline="middle" className="research-donut-center-label">{block.center_label ?? "Total"}</text>}
              <Tooltip contentStyle={tooltipStyle} formatter={(value) => formatValue(Number(value))} />
            </PieChart>
          </ResponsiveContainer>
        </div>
        {block.chart_type === "pie_interactive" ? <div className="research-chart-legend research-chart-legend-buttons">
          {block.data.map((item, index) => {
            const hidden = hiddenSlices.includes(item.label);
            return <button type="button" key={item.label} aria-pressed={!hidden} onClick={() => setHiddenSlices((current) => hidden ? current.filter((label) => label !== item.label) : [...current, item.label])}>
              <i style={{ backgroundColor: PALETTE[index % PALETTE.length], opacity: hidden ? 0.35 : 1 }} /><span>{item.label}</span><strong>{formatValue(item.value)}</strong>
            </button>;
          })}
        </div> : <ul className="research-chart-legend">{block.data.map((item, index) => <li key={item.label}><i style={{ backgroundColor: PALETTE[index % PALETTE.length] }} /><span>{item.label}</span><strong>{formatValue(item.value)}</strong></li>)}</ul>}
      </div>
    </>;
  }

  if (block.chart_type === "radial_stacked") {
    const radialData = [{ name: block.title, ...Object.fromEntries(series.map((entry, index) => [entry.key, block.data[index]?.value ?? 0])) }];
    return <div className="research-radial-wrap">
      <ResponsiveContainer width="100%" height={250}>
        <RadialBarChart data={radialData} innerRadius="24%" outerRadius="88%" startAngle={90} endAngle={-270}>
          <PolarAngleAxis type="number" domain={[0, Math.max(100, ...block.data.map((entry) => entry.value))]} tick={false} />
          <Tooltip contentStyle={tooltipStyle} formatter={(value) => formatValue(Number(value))} />
          {series.map((entry, index) => <RadialBar key={entry.key} dataKey={entry.key} stackId="radial" cornerRadius={4} fill={entry.color ?? PALETTE[index % PALETTE.length]} isAnimationActive={false} />)}
        </RadialBarChart>
      </ResponsiveContainer>
      <SeriesLegend block={block} />
    </div>;
  }

  if (isLine) {
    return <div className="research-chart" role="img" aria-label={block.title}>
      <ResponsiveContainer width="100%" height={250}>
        <LineChart data={chartData} margin={{ top: 8, right: 8, bottom: 4, left: 4 }}>
          <CartesianGrid stroke={gridColor} vertical={false} />
          <XAxis dataKey="label" tick={tick} tickLine={false} axisLine={false} />
          <YAxis tickFormatter={(value: number) => formatValue(value)} tick={tick} tickLine={false} axisLine={false} width={64} />
          <Tooltip contentStyle={tooltipStyle} formatter={(value) => formatValue(Number(value))} />
          {series.map((entry, index) => <Line key={entry.key} type="monotone" dataKey={entry.key} name={entry.name} stroke={entry.color ?? PALETTE[index % PALETTE.length]} strokeWidth={1.8} dot={{ r: 2 }} activeDot={{ r: 3 }} isAnimationActive={false} />)}
          {series.length > 1 && <Legend />}
        </LineChart>
      </ResponsiveContainer>
    </div>;
  }

  const negative = block.chart_type === "bar_negative";
  const multiple = block.chart_type === "bar_multiple" || block.chart_type === "bar_stacked";
  return <div className="research-chart" role="img" aria-label={block.title}>
    <ResponsiveContainer width="100%" height={260}>
      <BarChart data={chartData} layout={isHorizontal ? "vertical" : "horizontal"} margin={{ top: 8, right: 8, bottom: isHorizontal ? 4 : 24, left: isHorizontal ? 18 : 4 }}>
        <CartesianGrid stroke={gridColor} vertical={!isHorizontal} horizontal={isHorizontal} />
        {isHorizontal ? <><XAxis type="number" tickFormatter={(value: number) => formatValue(value)} tick={tick} tickLine={false} axisLine={false} /><YAxis dataKey="label" type="category" tick={tick} tickLine={false} axisLine={false} width={105} /></> : <><XAxis dataKey="label" tick={tick} tickLine={false} axisLine={false} interval={0} angle={-12} textAnchor="end" height={52} /><YAxis tickFormatter={(value: number) => formatValue(value)} tick={tick} tickLine={false} axisLine={false} width={64} />{negative && <ReferenceLine y={0} stroke="#737373" />}</>}
        <Tooltip cursor={false} contentStyle={tooltipStyle} formatter={(value) => formatValue(Number(value))} />
        {multiple && <Legend />}
        {multiple ? series.map((entry, index) => <Bar key={entry.key} dataKey={entry.key} name={entry.name} fill={entry.color ?? PALETTE[index % PALETTE.length]} stackId={block.chart_type === "bar_stacked" ? "stack" : undefined} radius={block.chart_type === "bar_stacked" ? 0 : [2, 2, 0, 0]} activeBar={false} isAnimationActive={false} />) : <Bar dataKey="value" name={block.title} radius={isHorizontal ? [0, 3, 3, 0] : [2, 2, 0, 0]} activeBar={false} isAnimationActive={false}>{block.data.map((item) => <Cell key={item.label} fill={negative ? (item.value < 0 ? NEGATIVE : POSITIVE) : PALETTE[0]} />)}</Bar>}
      </BarChart>
    </ResponsiveContainer>
  </div>;
}
