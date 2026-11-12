"use client";

import { Tooltip, TooltipContent, TooltipTrigger } from "@/components/ui/tooltip";
import { cn } from "@/lib/utils";
import { FEE_LABELS, GAP_LABELS, RELIABILITY, type Reliability, type Tone } from "@/lib/vocabulary";

const TONE_CHIP: Record<Tone, string> = {
  discount: "bg-discount-soft text-discount border-discount/30",
  premium: "bg-premium-soft text-premium border-premium/30",
  within: "bg-muted text-muted-foreground border-transparent",
  muted: "bg-muted text-muted-foreground border-transparent",
};

/** Valuation-gap or fee label chip. Wording and tone come only from lib/vocabulary.ts (rule R1). */
export function GapLabel({ label, kind = "gap", className }: { label: string | null; kind?: "gap" | "fee"; className?: string }) {
  if (!label) return <span className="text-xs text-muted-foreground">No label</span>;
  const meta = (kind === "fee" ? FEE_LABELS : GAP_LABELS)[label];
  if (!meta) return <span className="text-xs text-muted-foreground">{label}</span>;
  return (
    <Tooltip>
      <TooltipTrigger
        render={
          <span
            className={cn(
              "inline-flex items-center gap-1.5 rounded-full border px-2 py-0.5 text-xs font-medium whitespace-nowrap",
              TONE_CHIP[meta.tone],
              className,
            )}
          />
        }
      >
        {meta.strength === 2 && <span aria-hidden className="size-1.5 rounded-full bg-current" />}
        {meta.short}
      </TooltipTrigger>
      <TooltipContent>{meta.explain} A signal for further analysis, not a verdict.</TooltipContent>
    </Tooltip>
  );
}

/** Three-dot reliability indicator with the rule-based reason (spec 2.3). */
export function ReliabilityBadge({
  level: rawLevel, reason, showLabel = true,
}: { level: Reliability | string | null; reason?: string | null; showLabel?: boolean }) {
  const level = rawLevel ?? "Insufficient";
  const meta = RELIABILITY[level as Reliability] ?? RELIABILITY.Insufficient;
  return (
    <Tooltip>
      <TooltipTrigger render={<span className="inline-flex items-center gap-1.5 text-xs text-muted-foreground" />}>
        <span className="inline-flex gap-0.5" aria-hidden>
          {[1, 2, 3].map((i) => (
            <span key={i} className={cn("size-1.5 rounded-full", i <= meta.level ? "bg-foreground" : "bg-range")} />
          ))}
        </span>
        {showLabel ? <span>{level} reliability</span> : <span className="sr-only">{level} reliability</span>}
      </TooltipTrigger>
      <TooltipContent>
        {meta.explain}
        {reason ? ` Why: ${reason}.` : ""}
      </TooltipContent>
    </Tooltip>
  );
}
