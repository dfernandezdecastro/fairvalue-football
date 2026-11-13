// Helpers for URL search params: every filter lives in the URL, so every view is shareable.
export type SearchParams = Record<string, string | string[] | undefined>;

export function str(sp: SearchParams, key: string, fallback = ""): string {
  const v = sp[key];
  return (Array.isArray(v) ? v[0] : v) ?? fallback;
}

export function int(sp: SearchParams, key: string, fallback?: number): number | undefined {
  const raw = str(sp, key);
  const n = Number.parseInt(raw, 10);
  return Number.isFinite(n) ? n : fallback;
}

/** Same URL with some params replaced (undefined/"" removes them). */
export function hrefWith(path: string, sp: SearchParams, changes: Record<string, string | number | undefined>): string {
  const qs = new URLSearchParams();
  for (const [k, v] of Object.entries(sp)) {
    if (v === undefined || k in changes) continue;
    for (const item of Array.isArray(v) ? v : [v]) qs.append(k, item);
  }
  for (const [k, v] of Object.entries(changes)) if (v !== undefined && v !== "") qs.set(k, String(v));
  const s = qs.toString();
  return s ? `${path}?${s}` : path;
}

export const PAGE_SIZE = 50;
