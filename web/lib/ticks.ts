/** "Nice" ticks for a log axis in euros: 1-2-5 steps (€1M, €2M, €5M, €10M, …) within [min, max]. */
export function logTicks(min: number, max: number): number[] {
  const ticks: number[] = [];
  for (let p = Math.floor(Math.log10(Math.max(min, 1))); p <= Math.ceil(Math.log10(max)); p++) {
    for (const m of [1, 2, 5]) {
      const v = m * 10 ** p;
      if (v >= min && v <= max) ticks.push(v);
    }
  }
  return ticks;
}
