import "server-only";

import { connection } from "next/server";

// Server-only access to the public, read-only Supabase REST API (PostgREST).
// - SUPABASE_URL / SUPABASE_ANON_KEY come from web/.env.local (no NEXT_PUBLIC_ prefix: never sent to browsers).
// - Row-level security makes this key read-only (verified by `fairvalue db-check`).
// - `connection()` renders DB pages per request, so builds (and CI) never need database credentials;
//   responses are still cached for a day because the data is a frozen snapshot.

const REVALIDATE_SECONDS = 60 * 60 * 24;

export class DbNotConfiguredError extends Error {
  constructor() {
    super("Database not configured: set SUPABASE_URL and SUPABASE_ANON_KEY in web/.env.local");
  }
}

export class DbQueryError extends Error {
  constructor(public status: number, message: string) {
    super(`Database query failed (${status}): ${message}`);
  }
}

function config() {
  const url = process.env.SUPABASE_URL?.replace(/\/rest\/v1\/?$/, "").replace(/\/$/, "");
  const key = process.env.SUPABASE_ANON_KEY;
  if (!url || !key || /YOUR/i.test(url + key)) throw new DbNotConfiguredError();
  return { url, key };
}

export type Params = Record<string, string | number | boolean | undefined>;

/** GET /rest/v1/{relation}?{params}. Params use PostgREST syntax, e.g. { season: "eq.2024", order: "minutes.desc" }. */
export async function select<T>(relation: string, params: Params = {}): Promise<T[]> {
  await connection();
  const { url, key } = config();
  const qs = new URLSearchParams();
  for (const [k, v] of Object.entries(params)) if (v !== undefined) qs.set(k, String(v));
  const headers: Record<string, string> = { apikey: key };
  if (!key.startsWith("sb_")) headers.Authorization = `Bearer ${key}`; // legacy JWT anon keys
  const res = await fetch(`${url}/rest/v1/${relation}?${qs}`, {
    headers,
    cache: "force-cache",
    next: { revalidate: REVALIDATE_SECONDS, tags: ["db"] },
  });
  if (!res.ok) throw new DbQueryError(res.status, await res.text());
  return (await res.json()) as T[];
}

export async function selectOne<T>(relation: string, params: Params = {}): Promise<T | null> {
  const rows = await select<T>(relation, { ...params, limit: 1 });
  return rows[0] ?? null;
}

/** PostgREST pattern for a case-insensitive "contains" filter, with the user input escaped. */
export function ilikeContains(term: string): string {
  const safe = term.replace(/[*,()\\]/g, " ").trim();
  return `ilike.*${safe}*`;
}
