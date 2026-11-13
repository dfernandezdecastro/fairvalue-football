import Link from "next/link";
import { Suspense } from "react";

import { MarketCycleChart, type CyclePoint } from "@/components/charts/market-cycle";
import { Stat } from "@/components/domain/profile";
import { PageSkeleton } from "@/components/shell/page-skeleton";
import { Card, PageHeader, Section } from "@/components/shell/site-chrome";
import { select, selectOne, selectPage } from "@/lib/db/server";
import type { VClubAudit, VPlayerSeason, VTransfers } from "@/lib/db/types";
import { formatEur, formatPctChange, seasonLabel } from "@/lib/format";
import { leagueName } from "@/lib/leagues";
import { POSITION_GROUPS } from "@/lib/vocabulary";

const UNDER = 'in.("Potential undervaluation","Strong signal of potential undervaluation")';
const PREMIUM = 'in.("Notable transfer premium","Unusual transfer premium")';

export default function Home() {
  return (
    <>
      <PageHeader
        eyebrow="Market overview"
        title="Where does the market's price disagree with the evidence, and how sure can we be?"
        description="FairValue compares market values and transfer fees with what measurable performance and context usually command in the same market. Every estimate comes with a range, and it says so when the data is too thin to judge."
      />
      <Suspense fallback={<PageSkeleton />}>
        <Overview />
      </Suspense>
    </>
  );
}

async function Overview() {
  const [transfers, valued, gems, premiums, clubs, cycle, backtest] = await Promise.all([
    selectPage<{ id: number }>("transfers", { select: "id", limit: 1 }),
    selectPage<{ player_id: number }>("piv_estimates", { select: "player_id", season: "eq.2025", reliability: "neq.Insufficient", limit: 1 }),
    select<VPlayerSeason>("v_player_season", {
      select: "*", season: "eq.2024", model_tier: "eq.full", reliability: "in.(High,Moderate)", gap_label: UNDER, order: "gap_log.asc", limit: 6,
    }),
    select<VTransfers>("v_transfers", { select: "*", season: "eq.2025", label: PREMIUM, reliability: "in.(High,Moderate)", order: "premium_eur.desc", limit: 6 }),
    select<VClubAudit>("v_club_audit", { select: "*", period: "eq.last3", ranked: "eq.true", order: "price_ratio_hi80.asc", limit: 6 }),
    selectOne<{ value: { season: number; window: string; median_ratio: number }[] }>("app_meta", { key: "eq.market_premium_by_window", select: "value" }),
    selectOne<{ under: { median_excess_pct: number; ci80_pct: [number, number] } }>("model_runs", {
      model: "eq.expected_fee", is_current: "eq.true", select: "under:summary->gems_backtest->pooled->under",
    }),
  ]);
  const series = cycle?.value ?? [];
  const seasons = [...new Set(series.map((p) => p.season))].sort();
  const points: CyclePoint[] = seasons.map((s) => ({
    season: seasonLabel(s),
    summer: series.find((p) => p.season === s && p.window === "summer")?.median_ratio ?? null,
    winter: series.find((p) => p.season === s && p.window === "winter")?.median_ratio ?? null,
  }));
  const latest = points.at(-1);

  return (
    <div className="space-y-12">
      <div className="grid gap-6 sm:grid-cols-2 lg:grid-cols-4">
        <Stat label="Paid transfers covered" value={transfers.total.toLocaleString("en-GB")} sub="permanent moves since 2015/16" />
        <Stat label="Player-seasons valued, 2025/26" value={valued.total.toLocaleString("en-GB")} sub="14 leagues, with ranges" />
        <Stat label="Typical fee vs market value" value={latest?.summer ? `${latest.summer.toFixed(2)}×` : "–"} sub={`median, ${latest?.season ?? ""} summer window`} />
        <Stat label="Flagged players vs peers" value={backtest ? `+${backtest.under.median_excess_pct}%` : "–"}
              sub={backtest ? `market-value change over 12 months (80% CI ${backtest.under.ci80_pct[0]}–${backtest.under.ci80_pct[1]}%)` : ""} />
      </div>

      <div className="grid gap-6 lg:grid-cols-3">
        <Card className="space-y-3">
          <div className="flex items-baseline justify-between gap-2">
            <h2 className="text-sm font-semibold">Strongest undervaluation signals</h2>
            <Link href="/hidden-gems" className="text-xs text-muted-foreground hover:text-foreground">All →</Link>
          </div>
          <p className="text-xs text-muted-foreground">2024/25, big five, xG-level data, high or moderate reliability.</p>
          <ul className="divide-y">
            {gems.map((r) => (
              <li key={`${r.player_id}-${r.competition_id}`} className="py-2">
                <Link href={`/players/${r.player_slug}?season=${r.season}&league=${r.competition_id}`} className="text-sm font-medium hover:underline">{r.player_name}</Link>
                <p className="text-xs text-muted-foreground tabular">
                  {POSITION_GROUPS[r.position_group ?? ""]} · {leagueName(r.competition_id)} · value {formatEur(r.market_value_eur)} vs implied {formatEur(r.peer_estimate_eur)}
                </p>
              </li>
            ))}
          </ul>
        </Card>
        <Card className="space-y-3">
          <div className="flex items-baseline justify-between gap-2">
            <h2 className="text-sm font-semibold">Largest transfer premiums, 2025/26</h2>
            <Link href="/transfers?view=premiums" className="text-xs text-muted-foreground hover:text-foreground">All →</Link>
          </div>
          <p className="text-xs text-muted-foreground">Fees above the 80% range for comparable deals.</p>
          <ul className="divide-y">
            {premiums.map((t) => (
              <li key={t.id} className="py-2">
                <Link href={`/transfers/${t.id}`} className="text-sm font-medium hover:underline">{t.player_name}</Link>
                <p className="text-xs text-muted-foreground tabular">
                  {t.to_club_name} · {formatEur(t.fee_eur)} vs expected {formatEur(t.expected_fee_eur)} ({formatPctChange(t.premium_pct)})
                </p>
              </li>
            ))}
          </ul>
        </Card>
        <Card className="space-y-3">
          <div className="flex items-baseline justify-between gap-2">
            <h2 className="text-sm font-semibold">Most price-efficient clubs</h2>
            <Link href="/clubs?period=last3" className="text-xs text-muted-foreground hover:text-foreground">All →</Link>
          </div>
          <p className="text-xs text-muted-foreground">Last three seasons, fees ÷ expected fees, ranked by the cautious end of the range.</p>
          <ul className="divide-y">
            {clubs.map((c) => (
              <li key={c.club_id} className="flex items-baseline justify-between gap-3 py-2">
                <Link href={`/clubs/${c.club_slug}`} className="truncate text-sm font-medium hover:underline">{c.club_name}</Link>
                <span className="text-xs text-muted-foreground tabular whitespace-nowrap">
                  {c.price_ratio?.toFixed(2)} ({c.price_ratio_lo80?.toFixed(2)}–{c.price_ratio_hi80?.toFixed(2)})
                </span>
              </li>
            ))}
          </ul>
        </Card>
      </div>

      <Section title="The market cycle" description="Median transfer fee as a multiple of the player's market value just before the move. Above 1×, buyers paid more than the market value; the level moves with market cycles, which is why the expected-fee model tracks it point in time.">
        <Card><MarketCycleChart data={points} /></Card>
      </Section>

      <Section title="How to read FairValue">
        <div className="grid gap-4 md:grid-cols-3">
          {[
            ["Ranges, not prices", "Every estimate is a range. A label appears only when a market value or fee falls outside it."],
            ["Signals, not verdicts", "Contracts, injuries, clauses and club conventions are invisible to the model and can explain any gap."],
            ["Honest about coverage", "xG-level data for the big five to 2024/25; basic data elsewhere. Too little data means no estimate."],
          ].map(([t, d]) => (
            <Card key={t} className="space-y-1"><p className="text-sm font-medium">{t}</p><p className="text-sm text-muted-foreground">{d}</p></Card>
          ))}
        </div>
        <p className="text-sm"><Link href="/methodology" className="underline underline-offset-2">Methodology, model cards and limitations →</Link></p>
      </Section>
    </div>
  );
}
