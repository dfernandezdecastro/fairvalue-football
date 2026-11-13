import { cn } from "@/lib/utils";

/**
 * A price ratio (fees / expected fees) with its 80% range on a log scale centred on 1.0.
 * Left of the centre line: paid less than comparable deals; right: paid premiums.
 */
export function RatioRange({ ratio, lo, hi, className }: { ratio: number; lo?: number | null; hi?: number | null; className?: string }) {
  const MIN = 0.25;
  const MAX = 4;
  const x = (v: number) => `${((Math.log(Math.min(Math.max(v, MIN), MAX)) - Math.log(MIN)) / (Math.log(MAX) - Math.log(MIN))) * 100}%`;
  const tone = hi != null && hi < 1 ? "bg-discount" : lo != null && lo > 1 ? "bg-premium" : "bg-within";
  return (
    <div className={cn("relative h-4 w-full", className)} aria-label={`Price ratio ${ratio.toFixed(2)}${lo != null && hi != null ? `, 80% range ${lo.toFixed(2)} to ${hi.toFixed(2)}` : ""}`}>
      <span className="absolute inset-x-0 top-1/2 h-px -translate-y-1/2 bg-border" aria-hidden />
      <span className="absolute top-0 h-4 w-px bg-muted-foreground/60" style={{ left: x(1) }} aria-hidden />
      {lo != null && hi != null && (
        <span className="absolute top-1/2 h-1.5 -translate-y-1/2 rounded-full bg-range-strong"
              style={{ left: x(lo), width: `calc(${x(hi)} - ${x(lo)})` }} aria-hidden />
      )}
      <span className={cn("absolute top-1/2 size-2.5 -translate-x-1/2 -translate-y-1/2 rounded-full ring-2 ring-background", tone)}
            style={{ left: x(ratio) }} aria-hidden />
    </div>
  );
}
