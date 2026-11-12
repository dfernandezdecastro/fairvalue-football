import { NextResponse, type NextRequest } from "next/server";

import { DbNotConfiguredError, ilikeContains, select } from "@/lib/db/server";

interface PlayerHit {
  name: string;
  slug: string;
  sub_position: string | null;
  birth_year: number | null;
}
interface ClubHit {
  name: string;
  slug: string;
}

// GET /api/search?q=saka -> { players: [...], clubs: [...] } for the ⌘K palette.
export async function GET(request: NextRequest) {
  // Same normalisation as the pipeline's search_name: lower-case, accents stripped ("Mbappé" -> "mbappe").
  const q = (request.nextUrl.searchParams.get("q") ?? "")
    .normalize("NFKD")
    .replace(/[̀-ͯ]/g, "") // combining accent marks
    .toLowerCase()
    .trim()
    .slice(0, 60);
  if (q.length < 2) return NextResponse.json({ players: [], clubs: [] });
  try {
    const [players, clubs] = await Promise.all([
      select<PlayerHit>("players", { select: "name,slug,sub_position,birth_year", search_name: ilikeContains(q), limit: 8, order: "name" }),
      select<ClubHit>("clubs", { select: "name,slug", search_name: ilikeContains(q), limit: 5, order: "name" }),
    ]);
    return NextResponse.json({ players, clubs });
  } catch (e) {
    const status = e instanceof DbNotConfiguredError ? 503 : 502;
    return NextResponse.json({ error: "Search is temporarily unavailable", players: [], clubs: [] }, { status });
  }
}
