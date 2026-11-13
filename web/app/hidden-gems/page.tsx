import type { Metadata } from "next";
import Link from "next/link";
import { Suspense } from "react";

import { FilterForm, NumberField, SelectField } from "@/components/data/filters";
import { Pagination } from "@/components/data/table";
import { EstimateRange } from "@/components/domain/estimate-range";
import { GapLabel, ReliabilityBadge } from "@/components/domain/labels";
import { DataTierPill, InsufficientData } from "@/components/domain/profile";
import { PageSkeleton } from "@/components/shell/page-skeleton";
import { PageHeader } from "@/components/shell/site-chrome";
import { select, selectOne, selectPage, type Params } from "@/lib/db/server";
import type { Players, SimilarPlayers, VPlayerSeason } from "@/lib/db/types";
import { formatEur, formatEurRange, ordinal, seasonLabel } from "@/lib/format";
import { leagueName, MODEL_LEAGUES } from "@/lib/leagues";
import { int, PAGE_SIZE, str, type SearchParams } from "@/lib/params";
import { GAP_LABELS, METRICS, POSITION_GROUPS } from "@/lib/vocabulary";

export const metadata: Metadata = { title: "Hidden Gems" };

const BIG5 = ["GB1", "ES1", "L1", "IT1", "FR1"];
const UNDER = ["Potential undervaluation", "Strong signal of potential undervaluation"];
const FULL_METRICS = ["npxg_p90", "xa_p90", "shots_p90", "key_passes_p90", "xg_chain_p90", "xg_buildup_p90", "goals_p90", "assists_p90", "minutes_share"];
const BASIC_METRICS = ["goals_p90", "assists_p90", "minutes_share", "starts_share"];
const quote = (xs: string[]) => `in.(${xs.map((x) => `"${x}"`).join(",")})`;

interface Backtest {
  pooled: { under: { n: number; median_excess_pct: number; ci80_pct: [number, number]; share_beating_peers: number } };
  strong_signal_only: { n: number; median_excess_pct: number; ci80_pct: [number, number] };
  by_season: Record<string, unknown>;
}

export default function HiddenGemsPage(props: PageProps<"/hidden-gems">) {
  return (
    <>
      <PageHeader
        eyebrow="Hidden Gems Finder"
        title="Potential undervaluation"
        description="Players whose market value sits below the range their measurable profile usually commands among same-league peers that summer. A starting point for scouting, not a verdict: contracts, injuries and club conventions are invisible to the model."
      />
      <Suspense fallback={<PageSkeleton />}>
        <GemsBody searchParams={props.searchParams} />
      </Suspense>
    </>
  );
}

async function GemsBody({ searchParams }: { searchParams: Promise<SearchParams> }) {
  const sp = await searchParams;
  const season = int(sp, "season", 2024)!;
  const full = season <= 2024;
  const metrics = full ? FULL_METRICS : BASIC_METRICS;
  const league = str(sp, "league", "big5");
  const like = str(sp, "like");
  const m1 = metrics.includes(str(sp, "m1")) ? str(sp, "m1") : "";
  const m2 = metrics.includes(str(sp, "m2")) ? str(sp, "m2") : "";
  const page = Math.max(1, int(sp, "page", 1)!);

  const backtest = await selectOne<{ gems_backtest: Backtest }>("model_runs", {
    model: "eq.expected_fee", is_current: "eq.true", select: "gems_backtest:summary->gems_backtest",
  });

  return (
    <div className="space-y-6">
      {backtest && <BacktestBanner b={backtest.gems_backtest} />}

      <FilterForm action="/hidden-gems">
        <SelectField label="Season" name="season" value={String(season)} options={[
          { value: "2024", label: "2024/25 (xG-level data)" }, { value: "2025", label: "2025/26 (basic data)" },
          { value: "2023", label: "2023/24 (xG-level)" }, { value: "2022", label: "2022/23 (xG-level)" },
        ]} />
        <SelectField label="League" name="league" value={league}
                     options={[{ value: "big5", label: "Big five" }, ...(full ? [] : [{ value: "all", label: "All 14 leagues" }]),
                               ...(full ? BIG5 : MODEL_LEAGUES).map((l) => ({ value: l, label: leagueName(l) }))]} />
        <SelectField label="Position" name="position" value={str(sp, "position")}
                     options={[{ value: "", label: "All outfield" }, ...Object.entries(POSITION_GROUPS).filter(([k]) => k !== "GK").map(([value, label]) => ({ value, label }))]} />
        <NumberField label="Max. age" name="age_max" value={int(sp, "age_max", 23)} min={16} max={40} />
        <NumberField label="Max. market value (€M)" name="max_mv" value={int(sp, "max_mv", 20)} min={1} />
        <NumberField label="Min. minutes" name="min_minutes" value={int(sp, "min_minutes", 1200)} min={900} step={100} />
        <SelectField label="Signal strength" name="strength" value={str(sp, "strength")}
                     options={[{ value: "", label: "Potential or strong" }, { value: "strong", label: "Strong signal only" }]} />
        <SelectField label="Metric" name="m1" value={m1} options={[{ value: "", label: "Any metric" }, ...metrics.map((m) => ({ value: m, label: METRICS[m].short }))]} />
        <NumberField label="Min. percentile" name="p1" value={int(sp, "p1")} min={0} max={100} step={5} placeholder="70" />
        <SelectField label="and metric" name="m2" value={m2} options={[{ value: "", label: "Any metric" }, ...metrics.map((m) => ({ value: m, label: METRICS[m].short }))]} />
        <NumberField label="Min. percentile" name="p2" value={int(sp, "p2")} min={0} max={100} step={5} placeholder="70" />
      </FilterForm>

      {like ? <Alternatives slug={like} sp={sp} season={season} /> : <Results sp={sp} season={season} league={league} m1={m1} m2={m2} page={page} metrics={metrics} />}
    </div>
  );
}

async function Results({ sp, season, league, m1, m2, page, metrics }: {
  sp: SearchParams; season: number; league: string; m1: string; m2: string; page: number; metrics: string[];
}) {
  const params: Params = {
    select: "*",
    season: `eq.${season}`,
    eligible: "eq.true",
    gap_label: str(sp, "strength") === "strong" ? 'eq."Strong signal of potential undervaluation"' : quote(UNDER),
    reliability: "in.(High,Moderate)",
    competition_id: league === "big5" ? `in.(${BIG5.join(",")})` : league === "all" ? undefined : `eq.${league}`,
    position_group: str(sp, "position") ? `eq.${str(sp, "position")}` : "neq.GK",
    age: `lt.${int(sp, "age_max", 23)! + 1}`,
    market_value_eur: `lte.${int(sp, "max_mv", 20)! * 1e6}`,
    minutes: `gte.${int(sp, "min_minutes", 1200)}`,
    order: "gap_log.asc",
    limit: PAGE_SIZE,
    offset: (page - 1) * PAGE_SIZE,
  };
  if (m1 && int(sp, "p1")) params[`${m1}_pct`] = `gte.${int(sp, "p1")}`;
  if (m2 && int(sp, "p2")) params[`${m2}_pct`] = m2 === m1 ? undefined : `gte.${int(sp, "p2")}`;
  const { rows, total } = await selectPage<VPlayerSeason>("v_player_season", params);

  if (!rows.length) {
    return <InsufficientData title="No candidates match" reason="No player flagged as potential undervaluation meets all these conditions." fix="raising the maximum age or market value, lowering the percentile thresholds, or including more leagues" />;
  }
  return (
    <div className="space-y-4">
      <div className="grid gap-4 lg:grid-cols-2">
        {rows.map((r) => <GemCard key={`${r.player_id}-${r.competition_id}`} r={r} metrics={metrics} />)}
      </div>
      <Pagination path="/hidden-gems" sp={sp} page={page} total={total} />
    </div>
  );
}

function strengths(r: VPlayerSeason, metrics: string[]) {
  return metrics
    .map((m) => ({ m, pct: r[`${m}_pct` as keyof VPlayerSeason] as number | null }))
    .filter((x): x is { m: string; pct: number } => x.pct != null)
    .sort((a, b) => b.pct - a.pct)
    .slice(0, 3);
}

/** Deterministic scouting rationale (a template, never generated text). */
function rationale(r: VPlayerSeason, metrics: string[]): string {
  const top = strengths(r, metrics);
  const group = POSITION_GROUPS[r.position_group ?? ""]?.toLowerCase() ?? "peers";
  const parts = [
    `Market value ${formatEur(r.market_value_eur)} sits below the 80% range (${formatEurRange(r.peer_lo80_eur, r.peer_hi80_eur)}) for comparable ${leagueName(r.competition_id)} profiles in summer ${(r.season ?? 0) + 1}.`,
    top.length ? `Strongest measured areas among ${group}: ${top.map((t) => `${METRICS[t.m].short} ${ordinal(t.pct)}`).join(", ")} percentile.` : "",
    `${(r.minutes ?? 0).toLocaleString("en-GB")} league minutes; ${r.reliability?.toLowerCase()} reliability.`,
  ];
  return parts.filter(Boolean).join(" ");
}

function GemCard({ r, metrics }: { r: VPlayerSeason; metrics: string[] }) {
  return (
    <article className="space-y-3 rounded-lg border bg-card p-5">
      <div className="flex flex-wrap items-start justify-between gap-2">
        <div>
          <Link href={`/players/${r.player_slug}?season=${r.season}&league=${r.competition_id}`} className="font-semibold hover:underline">
            {r.player_name}
          </Link>
          <p className="text-xs text-muted-foreground">
            {r.age != null ? `${Math.floor(r.age)} · ` : ""}{POSITION_GROUPS[r.position_group ?? ""]} · {r.club_name} · {leagueName(r.competition_id)}
          </p>
        </div>
        <div className="flex items-center gap-2">
          <ReliabilityBadge level={r.reliability} reason={r.reliability_reason} showLabel={false} />
          <DataTierPill tier={r.data_tier} />
        </div>
      </div>
      <EstimateRange estimate={r.peer_estimate_eur!} lo80={r.peer_lo80_eur!} hi80={r.peer_hi80_eur!} lo95={r.peer_lo95_eur} hi95={r.peer_hi95_eur}
                     actual={r.market_value_eur} actualLabel="Market value" estimateLabel="Implied"
                     tone={GAP_LABELS[r.gap_label ?? ""]?.tone ?? "discount"} />
      <div className="flex flex-wrap gap-2"><GapLabel label={r.gap_label} /></div>
      <p className="text-sm text-muted-foreground">{rationale(r, metrics)}</p>
      <Link href={`/hidden-gems?season=${r.season}&like=${r.player_slug}`} className="text-xs underline underline-offset-2 hover:text-foreground">
        Find similar profiles at a lower market value
      </Link>
    </article>
  );
}

async function Alternatives({ slug, sp, season }: { slug: string; sp: SearchParams; season: number }) {
  const player = await selectOne<Players>("players", { slug: `eq.${slug}`, select: "id,name,slug" });
  const base = player && await selectOne<VPlayerSeason>("v_player_season", {
    player_id: `eq.${player.id}`, season: `eq.${season}`, eligible: "eq.true", order: "minutes.desc", select: "*",
  });
  if (!player || !base) {
    return <InsufficientData reason="That player has no eligible season with a statistical profile in this season." fix="choosing another season" />;
  }
  const sims = await select<SimilarPlayers>("similar_players", {
    player_id: `eq.${player.id}`, season: `eq.${season}`, competition_id: `eq.${base.competition_id}`, order: "rank", select: "*",
  });
  const maxMv = int(sp, "max_mv") ? int(sp, "max_mv")! * 1e6 : (base.market_value_eur ?? Infinity);
  const rows = sims.length
    ? await select<VPlayerSeason>("v_player_season", { player_id: `in.(${sims.map((s) => s.neighbour_id).join(",")})`, season: `eq.${season}`, select: "*" })
    : [];
  const cheaper = sims
    .map((s) => ({ s, r: rows.find((o) => o.player_id === s.neighbour_id && o.competition_id === s.neighbour_competition_id) }))
    .filter((x): x is { s: SimilarPlayers; r: VPlayerSeason } => !!x.r && (x.r.market_value_eur ?? Infinity) <= maxMv);
  return (
    <div className="space-y-4">
      <p className="text-sm text-muted-foreground">
        Profiles most similar to <Link href={`/players/${player.slug}?season=${season}`} className="text-foreground hover:underline">{player.name}</Link>{" "}
        in {seasonLabel(season)} (market value {formatEur(base.market_value_eur)}), with a market value of at most {formatEur(maxMv)}.{" "}
        <Link href={`/hidden-gems?season=${season}`} className="underline underline-offset-2">Back to all candidates</Link>
      </p>
      {cheaper.length === 0 ? (
        <InsufficientData title="No cheaper similar profiles" reason="None of the 10 nearest profiles has a lower market value." />
      ) : (
        <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-3">
          {cheaper.map(({ s, r }) => (
            <Link key={s.rank} href={`/players/${r.player_slug}?season=${r.season}&league=${r.competition_id}`}
                  className="space-y-2 rounded-lg border bg-card p-4 transition-colors hover:bg-surface">
              <div className="flex items-baseline justify-between gap-2">
                <p className="truncate font-medium">{r.player_name}</p>
                <span className="text-xs text-muted-foreground tabular">{Math.round(s.similarity * 100)}% similar</span>
              </div>
              <p className="truncate text-xs text-muted-foreground">{r.age != null ? `${Math.floor(r.age)} · ` : ""}{r.club_name} · {leagueName(r.competition_id)}</p>
              <p className="text-sm tabular">Market value {formatEur(r.market_value_eur)}</p>
              {r.gap_label && r.reliability !== "Insufficient" && <GapLabel label={r.gap_label} />}
            </Link>
          ))}
        </div>
      )}
    </div>
  );
}

function BacktestBanner({ b }: { b: Backtest }) {
  const u = b.pooled.under;
  const s = b.strong_signal_only;
  return (
    <div className="rounded-lg border bg-surface p-4 text-sm">
      <p className="font-medium">How these flags performed historically</p>
      <p className="mt-1 text-muted-foreground">
        Across {Object.keys(b.by_season).length} past seasons, players flagged as potential undervaluation saw their market value
        change by <span className="font-medium text-foreground">+{u.median_excess_pct}%</span> more than comparable peers over the
        next 12 months (80% CI {u.ci80_pct[0]}% to {u.ci80_pct[1]}%, n = {u.n.toLocaleString("en-GB")}); strong signals{" "}
        <span className="font-medium text-foreground">+{s.median_excess_pct}%</span>. Market values are crowd opinion, so part of
        this is the crowd catching up; it measures value movement, not sporting success.{" "}
        <Link href="/methodology#backtest" className="underline underline-offset-2">Method and caveats</Link>
      </p>
    </div>
  );
}
