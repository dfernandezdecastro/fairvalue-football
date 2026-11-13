"use client";

import { CartesianGrid, ReferenceLine, ResponsiveContainer, Scatter, ScatterChart, Tooltip, XAxis, YAxis, ZAxis } from "recharts";

import { formatEur } from "@/lib/format";
import { logTicks } from "@/lib/ticks";

export interface FeePoint {
  player: string;
  date: string;
  expected: number;
  fee: number;
  tone: "discount" | "premium" | "within";
}

const COLOR = { discount: "var(--discount)", premium: "var(--premium)", within: "var(--within)" };

function FeeTooltip({ active, payload }: { active?: boolean; payload?: { payload: FeePoint }[] }) {
  if (!active || !payload?.length) return null;
  const p = payload[0].payload;
  return (
    <div className="rounded-md border bg-popover px-3 py-2 text-xs shadow-md tabular">
      <p className="font-medium">{p.player}</p>
      <p className="text-muted-foreground">{p.date}</p>
      <p>Fee {formatEur(p.fee)} · expected {formatEur(p.expected)}</p>
    </div>
  );
}

/** Fee vs expected fee, log-log. Points on the diagonal paid exactly what comparable deals commanded. */
export function FeeScatter({ points }: { points: FeePoint[] }) {
  if (points.length < 3) return <p className="text-sm text-muted-foreground">Too few assessed purchases to chart.</p>;
  const all = points.flatMap((p) => [p.fee, p.expected]);
  const domain: [number, number] = [Math.min(...all) / 1.4, Math.max(...all) * 1.4];
  const ticks = logTicks(domain[0], domain[1]);
  const groups = (["discount", "within", "premium"] as const).map((tone) => ({ tone, data: points.filter((p) => p.tone === tone) }));
  return (
    <div className="h-72 w-full" role="img" aria-label="Scatter of fees paid against expected fees">
      <ResponsiveContainer width="100%" height="100%">
        <ScatterChart margin={{ top: 8, right: 12, bottom: 8, left: 8 }}>
          <CartesianGrid stroke="var(--border)" />
          <XAxis type="number" dataKey="expected" name="Expected fee" scale="log" domain={domain} allowDataOverflow ticks={ticks}
                 tickFormatter={(v: number) => formatEur(v)} tick={{ fontSize: 11, fill: "var(--muted-foreground)" }}
                 label={{ value: "Expected fee", position: "insideBottom", offset: -4, fontSize: 11, fill: "var(--muted-foreground)" }} />
          <YAxis type="number" dataKey="fee" name="Fee" scale="log" domain={domain} allowDataOverflow width={56} ticks={ticks}
                 tickFormatter={(v: number) => formatEur(v)} tick={{ fontSize: 11, fill: "var(--muted-foreground)" }} />
          <ZAxis range={[36, 36]} />
          <ReferenceLine segment={[{ x: domain[0], y: domain[0] }, { x: domain[1], y: domain[1] }]} stroke="var(--muted-foreground)" strokeDasharray="4 3" />
          <Tooltip content={<FeeTooltip />} />
          {groups.map((g) => (
            <Scatter key={g.tone} data={g.data} fill={COLOR[g.tone]} isAnimationActive={false} />
          ))}
        </ScatterChart>
      </ResponsiveContainer>
    </div>
  );
}
