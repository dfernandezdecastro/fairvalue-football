import type { Metadata } from "next";
import Link from "next/link";
import { notFound } from "next/navigation";
import { Suspense } from "react";

import { ValueHistoryChart, type HistoryPoint } from "@/components/charts/value-history";
import { Table, Td, Th } from "@/components/data/table";
import { DriversList, parseDrivers } from "@/components/domain/drivers";
import { EstimateRange } from "@/components/domain/estimate-range";
import { GapLabel } from "@/components/domain/labels";
import { PercentileBar, SourceFootnote } from "@/components/domain/profile";
import { ValuationPanel } from "@/components/domain/valuation-panel";
import { PageSkeleton } from "@/components/shell/page-skeleton";
import { Card, Section } from "@/components/shell/site-chrome";
import { Skeleton } from "@/components/ui/skeleton";
import { select, selectOne } from "@/lib/db/server";
import type { Players, SimilarPlayers, VPlayerSeason, VTransfers } from "@/lib/db/types";
import { formatEur, formatNumber, seasonLabel } from "@/lib/format";
import { leagueName } from "@/lib/leagues";
import { str, type SearchParams } from "@/lib/params";
import { cn } from "@/lib/utils";
import { FEE_LABELS, METRICS, NOT_MEASURED, POSITION_GROUPS } from "@/lib/vocabulary";

const FULL_METRICS = ["npxg_p90", "xa_p90", "shots_p90", "key_passes_p90", "xg_chain_p90", "xg_buildup_p90", "goals_p90", "assists_p90", "minutes_share", "starts_share"];
const BASIC_METRICS = ["goals_p90", "assists_p90", "minutes_share", "starts_share"];

async function getPlayer(slug: string) {
  return selectOne<Players>("players", { slug: `eq.${slug}`, select: "*" });
}

export async function generateMetadata(props: PageProps<"/players/[slug]">): Promise<Metadata> {
  const { slug } = await props.params;
  const p = await getPlayer(slug);
  return { title: p ? p.name : "Player not found" };
}

export default function PlayerPage(props: PageProps<"/players/[slug]">) {
  return (
    <Suspense fallback={<PageSkeleton />}>
      <PlayerBody {...props} />
    </Suspense>
  );
}

async function PlayerBody(props: PageProps<"/players/[slug]">) {
  const { slug } = await props.params;
  const sp = (await props.searchParams) as SearchParams;
  const player = await getPlayer(slug);
  if (!player) notFound();
  const seasons = await select<VPlayerSeason>("v_player_season", {
    player_id: `eq.${player.id}`, select: "*", order: "season.desc,minutes.desc",
  });
  if (!seasons.length) notFound();

  // Selected season: ?season=2024&league=ES1, else the latest season with an estimate, else the latest season.
  const wanted = seasons.find((s) => String(s.season) === str(sp, "season") && (!str(sp, "league") || s.competition_id === str(sp, "league")));
  const row = wanted ?? seasons.find((s) => s.reliability && s.reliability !== "Insufficient") ?? seasons[0];

  return (
    <div className="space-y-10">
      <PlayerHeader player={player} row={row} seasons={seasons} />

      <div className="grid gap-6 lg:grid-cols-[1.4fr_1fr]">
        <Card className="space-y-4">
          <h2 className="text-sm font-semibold">Valuation, {seasonLabel(row.season)}</h2>
          <ValuationPanel row={row} />
        </Card>
        <Card className="space-y-4">
          <h2 className="text-sm font-semibold">Why this estimate</h2>
          {row.reliability !== "Insufficient" && row.drivers ? (
            <>
              <DriversList drivers={parseDrivers(row.drivers)} />
              <p className="text-xs text-muted-foreground">
                Approximate effect of each factor versus an average profile, from the model&apos;s explanation (SHAP).
              </p>
            </>
          ) : (
            <p className="text-sm text-muted-foreground">No estimate, so no explanation.</p>
          )}
        </Card>
      </div>

      <Section
        title={`Performance profile vs ${POSITION_GROUPS[row.position_group ?? ""]?.toLowerCase() ?? "peers"}, ${row.peer_scope === "big5" ? "big five" : leagueName(row.competition_id)}, ${seasonLabel(row.season)}`}
        description={row.eligible ? `Percentiles among ${formatNumber(row.peer_n)} players with 900+ league minutes. Per-90 rates are adjusted for sample size before ranking.` : "Fewer than 900 league minutes: too few to rank against peers."}
      >
        <Card className="grid gap-8 md:grid-cols-2">
          <div className="space-y-2.5">
            {(row.data_tier === "full" ? FULL_METRICS : BASIC_METRICS).map((m) => (
              <PercentileBar key={m} label={METRICS[m].short} source={METRICS[m].source}
                             percentile={row.eligible ? (row[`${m}_pct` as keyof VPlayerSeason] as number | null) : null} />
            ))}
          </div>
          <div className="space-y-3 text-sm">
            <dl className="grid grid-cols-2 gap-x-4 gap-y-2 tabular">
              <dt className="text-muted-foreground">League minutes</dt><dd>{formatNumber(row.minutes)} ({Math.round((row.minutes_share ?? 0) * 100)}% of the season)</dd>
              <dt className="text-muted-foreground">Starts / games</dt><dd>{row.starts} / {row.games}</dd>
              <dt className="text-muted-foreground">Goals / assists</dt><dd>{row.goals} / {row.assists}</dd>
              {row.data_tier === "full" && (<>
                <dt className="text-muted-foreground">npxG / xA</dt><dd>{formatNumber(row.npxg, 1)} / {formatNumber(row.xa, 1)}</dd>
              </>)}
              <dt className="text-muted-foreground">Team points per game</dt><dd>{formatNumber(row.team_ppg, 2)}</dd>
            </dl>
            <p className="text-xs text-muted-foreground">
              Not measured in the available data: {NOT_MEASURED.join(", ").toLowerCase()}.
              {row.position_group === "CB" || row.position_group === "FB" ? " Defenders are therefore judged mostly on playing time, team strength and age." : ""}
            </p>
          </div>
        </Card>
      </Section>

      <Section title="Valuation history" description="Market value after each season (line) against the performance-implied 80% range (band). Each season's range comes from a model trained only on earlier seasons.">
        <Card><ValueHistoryChart data={historyPoints(seasons)} /></Card>
      </Section>

      <Suspense fallback={<Skeleton className="h-48" />}>
        <TransferHistory playerId={player.id} />
      </Suspense>

      {row.eligible && row.position_group !== "GK" && (
        <Suspense fallback={<Skeleton className="h-40" />}>
          <SimilarProfiles row={row} />
        </Suspense>
      )}

      <Section title="Data & coverage">
        <Card className="space-y-2 text-xs text-muted-foreground">
          <p>
            Data tier: {row.data_tier === "full" ? "xG-level (Understat + Transfermarkt)" : "basic (Transfermarkt match data only)"}.
            Position group: {POSITION_GROUPS[row.position_group ?? ""] ?? "unknown"}
            {row.position_source === "understat_season" ? " (from this season's usage)" : row.position_source === "tm_current_confirmed" ? " (current label, confirmed by this season's usage)" : " (current Transfermarkt label)"}.
          </p>
          <SourceFootnote sources={["Transfermarkt via transfermarkt-datasets (market values, minutes, transfers)", "Understat (xG metrics)", "FairValue models"]} />
        </Card>
      </Section>
    </div>
  );
}

function PlayerHeader({ player, row, seasons }: { player: Players; row: VPlayerSeason; seasons: VPlayerSeason[] }) {
  const options = seasons.filter((s, i, a) => a.findIndex((x) => x.season === s.season && x.competition_id === s.competition_id) === i);
  return (
    <div className="space-y-4">
      <div className="space-y-2">
        <p className="text-xs font-medium tracking-widest text-muted-foreground uppercase">
          {POSITION_GROUPS[row.position_group ?? ""] ?? "Player"} · {player.sub_position ?? "position unknown"}
        </p>
        <h1 className="text-3xl font-semibold tracking-tight">{player.name}</h1>
        <p className="text-sm text-muted-foreground">
          {row.club_slug ? <Link href={`/clubs/${row.club_slug}`} className="text-foreground hover:underline">{row.club_name}</Link> : row.club_name}
          {" · "}{leagueName(row.competition_id)}
          {row.age != null && <> · age {Math.floor(row.age)} at the end of {seasonLabel(row.season)}</>}
          {player.citizenship && <> · {player.citizenship}</>}
          {player.foot && <> · {player.foot} foot</>}
        </p>
      </div>
      <nav className="flex flex-wrap gap-1.5" aria-label="Seasons">
        {options.slice(0, 12).map((s) => {
          const active = s.season === row.season && s.competition_id === row.competition_id;
          return (
            <Link key={`${s.season}-${s.competition_id}`} scroll={false}
                  href={`/players/${player.slug}?season=${s.season}&league=${s.competition_id}`}
                  className={cn("rounded-md border px-2 py-0.5 text-xs tabular",
                                active ? "border-foreground/40 bg-accent text-foreground" : "text-muted-foreground hover:text-foreground")}>
              {seasonLabel(s.season)}{options.filter((o) => o.season === s.season).length > 1 ? ` ${leagueName(s.competition_id)}` : ""}
            </Link>
          );
        })}
      </nav>
    </div>
  );
}

function historyPoints(seasons: VPlayerSeason[]): HistoryPoint[] {
  const bySeason = new Map<number, VPlayerSeason>();
  for (const s of seasons) {
    const cur = bySeason.get(s.season!);
    if (!cur || (s.minutes ?? 0) > (cur.minutes ?? 0)) bySeason.set(s.season!, s);
  }
  const points = [...bySeason.values()]
    .sort((a, b) => a.season! - b.season!)
    .map((s) => {
      const ok = s.reliability && s.reliability !== "Insufficient";
      return {
        season: seasonLabel(s.season),
        marketValue: s.market_value_eur,
        estimate: ok ? s.peer_estimate_eur : null,
        lo80: ok ? s.peer_lo80_eur : null,
        hi80: ok ? s.peer_hi80_eur : null,
      };
    });
  // drop leading/trailing seasons with neither a market value nor an estimate
  const has = (p: HistoryPoint) => p.marketValue != null || p.estimate != null;
  const first = points.findIndex(has);
  const last = points.length - 1 - [...points].reverse().findIndex(has);
  return first === -1 ? [] : points.slice(first, last + 1);
}

async function TransferHistory({ playerId }: { playerId: number }) {
  const transfers = await select<VTransfers>("v_transfers", { player_id: `eq.${playerId}`, select: "*", order: "date.desc" });
  if (!transfers.length) return null;
  return (
    <Section title="Paid transfers" description="Permanent transfers with a fee since 2015/16. Loans and free transfers aren't published.">
      <Table>
        <thead>
          <tr><Th>Date</Th><Th>From → to</Th><Th align="right">Fee</Th><Th>Expected fee (80% range)</Th><Th>Classification</Th></tr>
        </thead>
        <tbody>
          {transfers.map((t) => (
            <tr key={t.id} className="hover:bg-surface">
              <Td className="whitespace-nowrap"><Link href={`/transfers/${t.id}`} className="hover:underline">{t.date}</Link></Td>
              <Td>{t.from_club_name} → {t.to_club_name}</Td>
              <Td align="right" className="font-medium">{formatEur(t.fee_eur)}</Td>
              <Td className="w-56">
                {t.expected_fee_eur && t.lo80_eur && t.hi80_eur ? (
                  <EstimateRange size="sm" estimate={t.expected_fee_eur} lo80={t.lo80_eur} hi80={t.hi80_eur} actual={t.fee_eur}
                                 tone={FEE_LABELS[t.label ?? ""]?.tone ?? "within"} />
                ) : <span className="text-xs text-muted-foreground">Not assessed</span>}
              </Td>
              <Td>{t.label ? <GapLabel label={t.label} kind="fee" /> : <span className="text-xs text-muted-foreground" title={t.reliability_reason ?? undefined}>Outside model coverage</span>}</Td>
            </tr>
          ))}
        </tbody>
      </Table>
    </Section>
  );
}

async function SimilarProfiles({ row }: { row: VPlayerSeason }) {
  const sims = await select<SimilarPlayers>("similar_players", {
    player_id: `eq.${row.player_id}`, season: `eq.${row.season}`, competition_id: `eq.${row.competition_id}`,
    order: "rank", limit: 6, select: "*",
  });
  if (!sims.length) return null;
  const others = await select<VPlayerSeason>("v_player_season", {
    player_id: `in.(${sims.map((s) => s.neighbour_id).join(",")})`, season: `eq.${row.season}`, select: "*",
  });
  const find = (s: SimilarPlayers) => others.find((o) => o.player_id === s.neighbour_id && o.competition_id === s.neighbour_competition_id);
  return (
    <Section title="Similar profiles" description={`Nearest ${POSITION_GROUPS[row.position_group ?? ""]?.toLowerCase()} by their ${seasonLabel(row.season)} statistical profile (same data tier and peer group).`}>
      <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-3">
        {sims.map((s) => {
          const o = find(s);
          if (!o) return null;
          return (
            <Link key={s.rank} href={`/players/${o.player_slug}?season=${o.season}&league=${o.competition_id}`}
                  className="space-y-2 rounded-lg border bg-card p-4 transition-colors hover:bg-surface">
              <div className="flex items-baseline justify-between gap-2">
                <p className="truncate font-medium">{o.player_name}</p>
                <span className="text-xs text-muted-foreground tabular">{Math.round(s.similarity * 100)}% similar</span>
              </div>
              <p className="truncate text-xs text-muted-foreground">{o.club_name} · {leagueName(o.competition_id)}</p>
              <p className="text-sm tabular">
                Market value {formatEur(o.market_value_eur)}
                {o.peer_estimate_eur && o.reliability !== "Insufficient" ? <span className="text-muted-foreground"> · implied {formatEur(o.peer_estimate_eur)}</span> : null}
              </p>
              {o.gap_label && o.reliability !== "Insufficient" && <GapLabel label={o.gap_label} />}
            </Link>
          );
        })}
      </div>
    </Section>
  );
}
