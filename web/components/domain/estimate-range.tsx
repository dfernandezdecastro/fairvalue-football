import { cn } from "@/lib/utils";
import { formatEur, formatEurRange } from "@/lib/format";
import type { Tone } from "@/lib/vocabulary";

const TONE_BG: Record<Tone, string> = {
  discount: "bg-discount",
  premium: "bg-premium",
  within: "bg-within",
  muted: "bg-muted-foreground",
};

export interface EstimateRangeProps {
  estimate: number;
  lo80: number;
  hi80: number;
  lo95?: number | null;
  hi95?: number | null;
  /** Observed value to compare (market value or fee), drawn as a diamond. */
  actual?: number | null;
  actualLabel?: string;
  estimateLabel?: string;
  tone?: Tone;
  size?: "sm" | "md";
  className?: string;
}

/**
 * Dot-and-range on a log scale (rule R3: an estimate is never drawn without its range).
 * Light band = 95% range, darker band = 80% range, tick = estimate, diamond = actual value.
 */
export function EstimateRange({
  estimate, lo80, hi80, lo95, hi95, actual, actualLabel = "Actual", estimateLabel = "Estimate",
  tone = "within", size = "md", className,
}: EstimateRangeProps) {
  const values = [estimate, lo80, hi80, lo95, hi95, actual].filter((v): v is number => v != null && v > 0);
  const lmin = Math.log(Math.min(...values) / 1.2);
  const lmax = Math.log(Math.max(...values) * 1.2);
  const x = (v: number) => `${((Math.log(v) - lmin) / (lmax - lmin)) * 100}%`;
  const span = (a: number, b: number) => ({ left: x(a), width: `calc(${x(b)} - ${x(a)})` });
  const sm = size === "sm";
  const description =
    `${estimateLabel} ${formatEur(estimate)}, 80% range ${formatEurRange(lo80, hi80)}` +
    (actual != null ? `, ${actualLabel.toLowerCase()} ${formatEur(actual)}` : "");

  return (
    <figure className={cn("w-full", className)} aria-label={description}>
      <div className={cn("relative", sm ? "h-3.5" : "h-6")} aria-hidden>
        {lo95 != null && hi95 != null && (
          <span className={cn("absolute top-1/2 -translate-y-1/2 rounded-full bg-range", sm ? "h-1.5" : "h-2.5")}
                style={span(lo95, hi95)} />
        )}
        <span className={cn("absolute top-1/2 -translate-y-1/2 rounded-full bg-range-strong", sm ? "h-1.5" : "h-2.5")}
              style={span(lo80, hi80)} />
        <span className={cn("absolute top-1/2 w-0.5 -translate-x-1/2 -translate-y-1/2 rounded-full bg-foreground",
                            sm ? "h-3" : "h-5")}
              style={{ left: x(estimate) }} />
        {actual != null && actual > 0 && (
          <span className={cn("absolute top-1/2 -translate-x-1/2 -translate-y-1/2 rotate-45 ring-2 ring-background",
                              TONE_BG[tone], sm ? "size-2" : "size-2.5")}
                style={{ left: x(actual) }} />
        )}
      </div>
      {!sm && (
        <figcaption className="mt-2 flex flex-wrap items-baseline justify-between gap-x-4 gap-y-1 text-xs text-muted-foreground tabular">
          <span>
            <span className="font-medium text-foreground">{formatEur(estimate)}</span> {estimateLabel.toLowerCase()}
            {" · "}80% range {formatEurRange(lo80, hi80)}
            {lo95 != null && hi95 != null && <> · 95% {formatEurRange(lo95, hi95)}</>}
          </span>
          {actual != null && (
            <span className="inline-flex items-center gap-1.5">
              <span className={cn("inline-block size-2 rotate-45", TONE_BG[tone])} />
              {actualLabel} <span className="font-medium text-foreground">{formatEur(actual)}</span>
            </span>
          )}
        </figcaption>
      )}
    </figure>
  );
}
