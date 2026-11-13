"use client";

import { CartesianGrid, Legend, Line, LineChart, ReferenceLine, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";

export interface CyclePoint {
  season: string;
  summer: number | null;
  winter: number | null;
}

/** Median fee ÷ market value by transfer window: how far fees sit above or below market values over time. */
export function MarketCycleChart({ data }: { data: CyclePoint[] }) {
  return (
    <div className="h-64 w-full" role="img" aria-label="Median fee divided by market value, by season and window">
      <ResponsiveContainer width="100%" height="100%">
        <LineChart data={data} margin={{ top: 8, right: 12, bottom: 0, left: 0 }}>
          <CartesianGrid vertical={false} stroke="var(--border)" />
          <XAxis dataKey="season" tick={{ fontSize: 11, fill: "var(--muted-foreground)" }} tickLine={false} axisLine={false} />
          <YAxis domain={[0.4, 1.6]} tickFormatter={(v: number) => `${v.toFixed(1)}×`} width={40}
                 tick={{ fontSize: 11, fill: "var(--muted-foreground)" }} tickLine={false} axisLine={false} />
          <ReferenceLine y={1} stroke="var(--muted-foreground)" strokeDasharray="4 3" />
          <Tooltip formatter={(v) => `${Number(v).toFixed(2)}× market value`}
                   contentStyle={{ background: "var(--popover)", border: "1px solid var(--border)", borderRadius: 6, fontSize: 12 }} />
          <Legend wrapperStyle={{ fontSize: 12 }} />
          <Line name="Summer window" dataKey="summer" stroke="var(--brand)" strokeWidth={2} dot={{ r: 3 }} isAnimationActive={false} connectNulls />
          <Line name="Winter window" dataKey="winter" stroke="var(--chart-2)" strokeWidth={2} dot={{ r: 3 }} isAnimationActive={false} connectNulls />
        </LineChart>
      </ResponsiveContainer>
    </div>
  );
}
