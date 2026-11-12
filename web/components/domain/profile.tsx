import { CircleSlash } from "lucide-react";

import { cn } from "@/lib/utils";
import { formatNumber, ordinal } from "@/lib/format";

/** Percentile vs position peers. Null values say "Not measured" rather than disappearing. */
export function PercentileBar({
  label, percentile, value, valueDigits = 2, source,
}: { label: string; percentile: number | null; value?: number | null; valueDigits?: number; source?: string }) {
  const measured = percentile != null && !Number.isNaN(percentile);
  return (
    <div className="grid grid-cols-[6.5rem_1fr_3rem] items-center gap-2 text-sm sm:grid-cols-[minmax(0,9rem)_1fr_3rem] sm:gap-3">
      <span className="truncate text-muted-foreground" title={source ? `${label} (${source})` : label}>
        {label}
      </span>
      <div className="relative h-2 rounded-full bg-range">
        {measured && <div className="absolute inset-y-0 left-0 rounded-full bg-brand" style={{ width: `${percentile}%` }} />}
        <div className="absolute inset-y-[-3px] left-1/2 w-px bg-border" aria-hidden title="Peer median" />
      </div>
      <span className="text-right tabular">
        {measured ? (
          <>
            <span className="font-medium">{ordinal(percentile)}</span>
            {value != null && <span className="sr-only"> ({formatNumber(value, valueDigits)})</span>}
          </>
        ) : (
          <span className="text-xs text-muted-foreground">n/a</span>
        )}
      </span>
    </div>
  );
}

/** Replaces an estimate whenever the rules say the data can't support one (rule R3). */
export function InsufficientData({
  title = "Not enough data for a reliable estimate", reason, fix, className,
}: { title?: string; reason: string; fix?: string; className?: string }) {
  return (
    <div className={cn("flex gap-3 rounded-lg border border-dashed bg-surface p-4", className)} role="note">
      <CircleSlash className="mt-0.5 size-4 shrink-0 text-muted-foreground" aria-hidden />
      <div className="space-y-1 text-sm">
        <p className="font-medium">{title}</p>
        <p className="text-muted-foreground">{reason}</p>
        {fix && <p className="text-muted-foreground">What would change this: {fix}</p>}
      </div>
    </div>
  );
}

export function DataTierPill({ tier }: { tier: "full" | "basic" | string | null }) {
  const full = tier === "full";
  return (
    <span
      className={cn(
        "inline-flex items-center rounded-md border px-1.5 py-0.5 text-[11px] font-medium",
        full ? "border-brand/40 text-brand" : "border-border text-muted-foreground",
      )}
      title={full ? "Understat xG-level data plus Transfermarkt match data" : "Transfermarkt match data only (no xG)"}
    >
      {full ? "xG-level data" : "Basic data"}
    </span>
  );
}

export function Stat({ label, value, sub, className }: { label: string; value: React.ReactNode; sub?: React.ReactNode; className?: string }) {
  return (
    <div className={cn("space-y-1", className)}>
      <p className="text-xs text-muted-foreground">{label}</p>
      <p className="text-2xl font-semibold tracking-tight tabular">{value}</p>
      {sub && <p className="text-xs text-muted-foreground">{sub}</p>}
    </div>
  );
}

export function SourceFootnote({ sources }: { sources: string[] }) {
  return <p className="text-[11px] text-muted-foreground">Sources: {sources.join(" · ")}</p>;
}
