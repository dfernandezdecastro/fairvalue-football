import { cn } from "@/lib/utils";
import { formatPctChange } from "@/lib/format";

export interface Driver {
  driver: string;
  log: number;
  pct: number;
}

export function parseDrivers(raw: unknown): Driver[] {
  if (!raw) return [];
  try {
    const data = typeof raw === "string" ? JSON.parse(raw) : raw;
    return Array.isArray(data) ? (data as Driver[]) : [];
  } catch {
    return [];
  }
}

/**
 * What pushed the estimate up or down versus an average profile (model contributions, log scale,
 * shown as approximate % effects). Bars use neutral colours: a driver isn't good or bad.
 */
export function DriversList({ drivers, max = 6 }: { drivers: Driver[]; max?: number }) {
  const shown = drivers.slice(0, max);
  if (!shown.length) return <p className="text-sm text-muted-foreground">No explanation available.</p>;
  const scale = Math.max(...shown.map((d) => Math.abs(d.log)), 0.01);
  return (
    <ul className="space-y-2" aria-label="Drivers of the estimate">
      {shown.map((d) => {
        const w = (Math.abs(d.log) / scale) * 50;
        const up = d.log >= 0;
        return (
          <li key={d.driver} className="grid grid-cols-[6.5rem_1fr_3.25rem] items-center gap-2 text-sm sm:grid-cols-[minmax(0,10rem)_1fr_3.5rem] sm:gap-3">
            <span className="truncate text-muted-foreground">{d.driver}</span>
            <span className="relative h-2" aria-hidden>
              <span className="absolute inset-y-[-3px] left-1/2 w-px bg-border" />
              <span
                className={cn("absolute inset-y-0 rounded-sm", up ? "bg-foreground/70" : "bg-muted-foreground/40")}
                style={up ? { left: "50%", width: `${w}%` } : { right: "50%", width: `${w}%` }}
              />
            </span>
            <span className="text-right tabular">{formatPctChange(d.pct / 100)}</span>
          </li>
        );
      })}
    </ul>
  );
}
