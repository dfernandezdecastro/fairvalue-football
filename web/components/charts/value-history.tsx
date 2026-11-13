"use client";

import { Area, CartesianGrid, ComposedChart, Line, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";

import { formatEur, formatEurRange } from "@/lib/format";
import { logTicks } from "@/lib/ticks";

export interface HistoryPoint {
  season: string;
  marketValue: number | null;
  estimate: number | null;
  lo80: number | null;
  hi80: number | null;
}

interface TooltipPayload {
  payload: HistoryPoint;
}

function HistoryTooltip({ active, payload }: { active?: boolean; payload?: TooltipPayload[] }) {
  if (!active || !payload?.length) return null;
  const p = payload[0].payload;
  return (
    <div className="rounded-md border bg-popover px-3 py-2 text-xs shadow-md tabular">
      <p className="mb-1 font-medium">{p.season}</p>
      <p>Market value: <span className="font-medium">{formatEur(p.marketValue)}</span></p>
      {p.estimate != null ? (
        <p className="text-muted-foreground">
          Performance-implied: {formatEur(p.estimate)} ({formatEurRange(p.lo80, p.hi80)})
        </p>
      ) : (
        <p className="text-muted-foreground">No reliable estimate this season</p>
      )}
    </div>
  );
}

/**
 * Market value (line) vs the performance-implied 80% range (band), one point per season.
 * Each season's band comes from a model trained only on earlier seasons ("vintage" estimates).
 */
export function ValueHistoryChart({ data }: { data: HistoryPoint[] }) {
  const values = data.flatMap((d) => [d.marketValue, d.lo80, d.hi80]).filter((v): v is number => v != null && v > 0);
  if (values.length < 2) return <p className="text-sm text-muted-foreground">Not enough seasons to chart.</p>;
  const domain: [number, number] = [Math.min(...values) / 1.3, Math.max(...values) * 1.3];
  const rows = data.map((d) => ({ ...d, band: d.lo80 != null && d.hi80 != null ? [d.lo80, d.hi80] : null }));
  return (
    <div className="h-64 w-full" role="img" aria-label="Market value compared with the performance-implied range by season">
      <ResponsiveContainer width="100%" height="100%">
        <ComposedChart data={rows} margin={{ top: 8, right: 8, bottom: 0, left: 8 }}>
          <CartesianGrid vertical={false} stroke="var(--border)" />
          <XAxis dataKey="season" tick={{ fontSize: 11, fill: "var(--muted-foreground)" }} tickLine={false} axisLine={false} />
          <YAxis scale="log" domain={domain} allowDataOverflow ticks={logTicks(domain[0], domain[1])} tickFormatter={(v: number) => formatEur(v)} width={56}
                 tick={{ fontSize: 11, fill: "var(--muted-foreground)" }} tickLine={false} axisLine={false} />
          <Tooltip content={<HistoryTooltip />} cursor={{ stroke: "var(--border)" }} />
          <Area dataKey="band" stroke="none" fill="var(--range-strong)" fillOpacity={0.55} isAnimationActive={false}
                connectNulls={false} />
          <Line dataKey="estimate" stroke="var(--muted-foreground)" strokeDasharray="4 3" dot={false}
                isAnimationActive={false} connectNulls={false} />
          <Line dataKey="marketValue" stroke="var(--brand)" strokeWidth={2} dot={{ r: 3, fill: "var(--brand)" }}
                isAnimationActive={false} connectNulls />
        </ComposedChart>
      </ResponsiveContainer>
    </div>
  );
}
