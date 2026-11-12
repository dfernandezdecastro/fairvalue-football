// Number and label formatting used everywhere in the UI (spec section 5).

/** €12.4M, €850k, €3.2bn. Null-safe ("–"). */
export function formatEur(value: number | null | undefined, opts: { precise?: boolean } = {}): string {
  if (value === null || value === undefined || Number.isNaN(value)) return "–";
  const abs = Math.abs(value);
  const sign = value < 0 ? "−" : "";
  if (abs >= 1e9) return `${sign}€${(abs / 1e9).toFixed(1)}bn`;
  if (abs >= 1e6) {
    const m = abs / 1e6;
    const digits = opts.precise || m < 10 ? 1 : 0;
    return `${sign}€${m.toFixed(digits).replace(/\.0$/, "")}M`;
  }
  if (abs >= 1e3) return `${sign}€${Math.round(abs / 1e3)}k`;
  return `${sign}€${Math.round(abs)}`;
}

/** "€11–24M" when both ends share a unit, else "€850k–2.1M". */
export function formatEurRange(lo: number | null | undefined, hi: number | null | undefined): string {
  if (lo == null || hi == null) return "–";
  const a = formatEur(lo);
  const b = formatEur(hi);
  const unit = (s: string) => s.match(/(bn|M|k)$/)?.[1] ?? "";
  if (unit(a) && unit(a) === unit(b)) return `${a.replace(unit(a), "")}–${b.replace("€", "")}`;
  return `${a}–${b.replace("€", "")}`;
}

/** 93 -> "93rd" */
export function ordinal(n: number | null | undefined): string {
  if (n === null || n === undefined || Number.isNaN(n)) return "–";
  const r = Math.round(n);
  const suffix = r % 100 >= 11 && r % 100 <= 13 ? "th" : ({ 1: "st", 2: "nd", 3: "rd" } as Record<number, string>)[r % 10] ?? "th";
  return `${r}${suffix}`;
}

/** 0.234 -> "+23%", -0.1 -> "−10%" */
export function formatPctChange(ratio: number | null | undefined, digits = 0): string {
  if (ratio === null || ratio === undefined || Number.isNaN(ratio)) return "–";
  const v = ratio * 100;
  const s = Math.abs(v).toFixed(digits);
  return `${v > 0 ? "+" : v < 0 ? "−" : ""}${s}%`;
}

/** 2024 -> "2024/25" */
export function seasonLabel(startYear: number | null | undefined): string {
  if (startYear == null) return "–";
  return `${startYear}/${String(startYear + 1).slice(-2)}`;
}

export function formatNumber(n: number | null | undefined, digits = 0): string {
  if (n === null || n === undefined || Number.isNaN(n)) return "–";
  return n.toLocaleString("en-GB", { minimumFractionDigits: digits, maximumFractionDigits: digits });
}
