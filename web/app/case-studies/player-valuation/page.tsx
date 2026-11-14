import type { Metadata } from "next";
import Link from "next/link";
import { notFound } from "next/navigation";
import { Suspense } from "react";

import { ValueHistoryChart, type HistoryPoint } from "@/components/charts/value-history";
import { Finding, Hindsight, IntegrityNotice, Limitations, Prose, ReportFooter, ReportHeader, ReportSection } from "@/components/case-study/report";
import { Table, Td, Th } from "@/components/data/table";
import { DriversList, parseDrivers } from "@/components/domain/drivers";
import { EstimateRange } from "@/components/domain/estimate-range";
import { GapLabel, ReliabilityBadge } from "@/components/domain/labels";
import { PercentileBar, Stat } from "@/components/domain/profile";
import { PageSkeleton } from "@/components/shell/page-skeleton";
import { Card } from "@/components/shell/site-chrome";
import { CASE_STUDIES } from "@/lib/case-studies";
import { select, selectOne } from "@/lib/db/server";
import type { Players, VPlayerSeason, VTransfers } from "@/lib/db/types";
import { formatEur, formatEurRange, formatNumber, formatPctChange, ordinal, seasonLabel } from "@/lib/format";
import { leagueName } from "@/lib/leagues";
import { FEE_LABELS, METRICS } from "@/lib/vocabulary";

const CS = CASE_STUDIES.player;
export const metadata: Metadata = { title: `Case study: ${CS.kind}`, description: CS.question };

const METRIC_KEYS = ["npxg_p90", "xa_p90", "shots_p90", "key_passes_p90", "xg_chain_p90", "xg_buildup_p90", "goals_p90", "assists_p90", "minutes_share", "starts_share"];

export default function PlayerCaseStudy() {
  return (
    <Suspense fallback={<PageSkeleton />}>
      <Report />
    </Suspense>
  );
}

async function Report() {
  const player = await selectOne<Players>("players", { slug: `eq.${CS.playerSlug}`, select: "*" });
  if (!player) notFound();
  const [seasons, transfers, peers] = await Promise.all([
    select<VPlayerSeason>("v_player_season", { player_id: `eq.${player.id}`, select: "*", order: "season.asc" }),
    select<VTransfers>("v_transfers", { player_id: `eq.${player.id}`, select: "*", order: "date.asc" }),
    select<VPlayerSeason>("v_player_season", {
      select: "*", season: `eq.${CS.season}`, competition_id: `eq.${CS.league}`, position_group: "eq.CM", eligible: "eq.true",
      model_tier: "eq.full", age: "lt.24", minutes: "gte.1500", order: "market_value_eur.desc",
    }),
  ]);
  const row = seasons.find((s) => s.season === CS.season && s.competition_id === CS.league);
  if (!row || !row.peer_estimate_eur || !row.peer_lo80_eur || !row.peer_hi80_eur || !row.market_value_eur) notFound();
  const next = seasons.find((s) => s.season === CS.season + 1 && s.competition_id === CS.league);
  const drivers = parseDrivers(row.drivers);
  const d = (name: string) => drivers.find((x) => x.driver === name);
  const est = row.peer_estimate_eur;
  const mv = row.market_value_eur;
  const age = Math.floor(row.age ?? 0);
  const buy = transfers.find((t) => t.to_club_name === row.club_name);
  const sale = transfers.find((t) => t.from_club_name === row.club_name && (t.season ?? 0) > CS.season);
  const peerOthers = peers.filter((p) => p.player_id !== row.player_id);
  const peerMedianMv = median(peerOthers.map((p) => p.market_value_eur ?? 0).filter(Boolean));
  const npxg = row.npxg_p90_pct ?? 0;
  const mins = row.minutes_share_pct ?? 0;

  const checks = [
    { claim: "flagged as potential undervaluation", ok: !!row.gap_label?.includes("undervaluation") },
    { claim: "High reliability", ok: row.reliability === "High" },
    { claim: "market value below the 80% range", ok: mv < row.peer_lo80_eur },
    { claim: "aged 21 or under at season end", ok: age <= 21 },
    { claim: "age and league are the largest upward drivers", ok: (d("Age")?.log ?? 0) > 0 && (d("League")?.log ?? 0) > 0 },
    { claim: "team strength pulls the estimate down", ok: (d("Team strength")?.log ?? 0) < 0 },
  ];

  return (
    <article className="pb-6">
      <ReportHeader
        kind={CS.kind}
        title={CS.title}
        standfirst={`After ${seasonLabel(CS.season)}, ${player.name} was valued by the market at ${formatEur(mv)}. FairValue's performance-implied value for comparable ${leagueName(CS.league)} profiles was ${formatEur(est)}. This report explains where that gap came from, how much of it the evidence supports, and what it can't tell us.`}
        meta={[
          { label: "Player", value: `${player.name}, ${row.club_name}` },
          { label: "Season and reference date", value: `${seasonLabel(CS.season)} · market value of ${row.market_value_date}` },
          { label: "Position and age", value: `${player.sub_position ?? "Central midfield"} · ${age} at season end` },
          { label: "Estimate reliability", value: <ReliabilityBadge level={row.reliability} reason={row.reliability_reason} /> },
        ]}
      />

      <ReportSection letter="A" title="The player">
        <div className="grid gap-6 sm:grid-cols-2 lg:grid-cols-4">
          <Stat label="Market value (Transfermarkt)" value={formatEur(mv)} sub={`dated ${row.market_value_date}`} />
          <Stat label="Performance-implied value" value={formatEur(est)} sub={`80% range ${formatEurRange(row.peer_lo80_eur, row.peer_hi80_eur)}`} />
          <Stat label="Gap" value={`${formatEur(est - mv)}`} sub={`implied value is ${(est / mv).toFixed(1)}× market value`} />
          <Stat label="League minutes" value={formatNumber(row.minutes)} sub={`${Math.round((row.minutes_share ?? 0) * 100)}% of the season · ${row.starts} starts`} />
        </div>
        <Card className="space-y-3">
          <div className="flex flex-wrap items-center gap-2"><GapLabel label={row.gap_label} /></div>
          <EstimateRange estimate={est} lo80={row.peer_lo80_eur} hi80={row.peer_hi80_eur} lo95={row.peer_lo95_eur} hi95={row.peer_hi95_eur}
                         actual={mv} actualLabel="Market value" estimateLabel="Performance-implied value" tone="discount" />
        </Card>
        <Prose>
          <p>
            {player.name} joined {row.club_name} {buy ? `from ${buy.from_club_name} in ${buy.date?.slice(0, 7)} for ${formatEur(buy.fee_eur)}` : ""} and
            played {formatNumber(row.minutes)} {leagueName(CS.league)} minutes in {seasonLabel(CS.season)}, starting {row.starts} of {row.games} appearances,
            for a team that took {row.team_ppg?.toFixed(2)} points per game. His market value sits below the 80% range of what
            comparable profiles carried in the same league that summer, so FairValue labels it a <em>potential undervaluation</em>: a
            signal worth investigating, not a price.
          </p>
        </Prose>
      </ReportSection>

      <ReportSection letter="B" title="Why FairValue values him differently">
        <div className="grid gap-6 lg:grid-cols-[1fr_1fr]">
          <Card className="space-y-3">
            <p className="text-xs font-medium text-muted-foreground">Effect of each factor vs an average profile (model explanation, SHAP)</p>
            <DriversList drivers={drivers} />
          </Card>
          <Prose>
            <p>
              <strong>The estimate is driven by context more than by standout statistics.</strong> The two largest upward factors are
              playing in the {leagueName(CS.league)} ({formatPctChange((d("League")?.pct ?? 0) / 100)}) and his age
              ({formatPctChange((d("Age")?.pct ?? 0) / 100)}): the market typically pays a large premium for players this young who
              already hold a regular place in the strongest league. Playing time adds {formatPctChange((d("Playing time")?.pct ?? 0) / 100)}.
            </p>
            <p>
              <strong>One factor pulls the other way.</strong> Team strength ({formatPctChange((d("Team strength")?.pct ?? 0) / 100)})
              reflects {row.club_name}&apos;s weak season. Even after that discount, the estimate stays well above his market value.
            </p>
            <p>
              Measured output contributes little either way (chance creation {formatPctChange((d("Chance creation")?.pct ?? 0) / 100)}).
              That matters for the interpretation: the case isn&apos;t &ldquo;elite numbers being ignored&rdquo;, it&apos;s &ldquo;a
              {` ${age}`}-year-old starter in the {leagueName(CS.league)} priced like a fringe player&rdquo;.
            </p>
          </Prose>
        </div>
      </ReportSection>

      <ReportSection letter="C" title="Statistical evidence">
        <div className="grid gap-6 lg:grid-cols-[1fr_1fr]">
          <Card className="space-y-2.5">
            <p className="text-xs font-medium text-muted-foreground">
              Percentiles vs {formatNumber(row.peer_n)} big-five central and defensive midfielders with 900+ minutes, {seasonLabel(CS.season)}
            </p>
            {METRIC_KEYS.map((m) => (
              <PercentileBar key={m} label={METRICS[m].short} source={METRICS[m].source} percentile={row[`${m}_pct` as keyof VPlayerSeason] as number | null} />
            ))}
          </Card>
          <Prose>
            <p>
              Against big-five midfielders his profile is <strong>above average rather than elite</strong>: {ordinal(npxg)} percentile
              for non-penalty xG per 90 and {ordinal(row.shots_p90_pct)} for shots, around the middle for build-up involvement
              ({ordinal(row.xg_buildup_p90_pct)}). The strongest signal is availability: {ordinal(mins)} percentile for share of
              league minutes and {ordinal(row.starts_share_pct)} for starts.
            </p>
            <p>
              Per-90 rates are adjusted for sample size before ranking, and defensive actions (tackles, interceptions, duels) aren&apos;t
              in the free data, which matters for a midfielder.
            </p>
          </Prose>
        </div>

        <div className="space-y-3">
          <p className="text-sm font-medium">Young central midfielders in the {leagueName(CS.league)}, {seasonLabel(CS.season)}</p>
          <p className="text-sm text-muted-foreground">
            Under 24, 1,500+ league minutes, xG-level data. The median market value of the other {peerOthers.length} players was{" "}
            {formatEur(peerMedianMv)}.
          </p>
          <Table>
            <thead><tr><Th>Player</Th><Th>Club</Th><Th align="right">Age</Th><Th align="right">Minutes</Th><Th align="right">Market value</Th><Th align="right">Implied</Th><Th>Gap</Th></tr></thead>
            <tbody>
              {peers.map((p) => (
                <tr key={p.player_id} className={p.player_id === row.player_id ? "bg-brand/10" : "hover:bg-surface"}>
                  <Td><Link href={`/players/${p.player_slug}?season=${CS.season}&league=${CS.league}`} className="font-medium hover:underline">{p.player_name}</Link></Td>
                  <Td className="text-muted-foreground">{p.club_name}</Td>
                  <Td align="right">{Math.floor(p.age ?? 0)}</Td>
                  <Td align="right">{formatNumber(p.minutes)}</Td>
                  <Td align="right">{formatEur(p.market_value_eur)}</Td>
                  <Td align="right" className="text-muted-foreground">{p.reliability !== "Insufficient" ? formatEur(p.peer_estimate_eur) : "–"}</Td>
                  <Td>{p.reliability !== "Insufficient" && p.gap_label ? <GapLabel label={p.gap_label} /> : null}</Td>
                </tr>
              ))}
            </tbody>
          </Table>
        </div>

        <div className="space-y-3">
          <p className="text-sm font-medium">Market value against the performance-implied range, by season</p>
          <Card><ValueHistoryChart data={history(seasons.filter((s) => (s.season ?? 0) <= CS.season))} /></Card>
          <p className="text-xs text-muted-foreground">Each season&apos;s range comes from a model trained only on earlier seasons. Later seasons appear only in the hindsight note below.</p>
        </div>
      </ReportSection>

      <ReportSection letter="D" title="The valuation conclusion">
        <Finding title="What the model suggests">
          In summer {CS.season + 1}, the market valued {player.name} at {formatEur(mv)}, below the {formatEurRange(row.peer_lo80_eur, row.peer_hi80_eur)} that
          comparable {leagueName(CS.league)} profiles carried. The gap is explained mainly by age and league context, partly offset by a weak team,
          with his measured output solid rather than exceptional.
        </Finding>
        <Prose>
          <p>
            <strong>How a recruitment analyst might read it.</strong> Not as &ldquo;he is worth {formatEur(est)}&rdquo;, but as a prompt:
            the market seems to be discounting him more than his age and role would normally justify. The next questions are the ones the
            data can&apos;t answer: contract length, release clause, injury record, defensive work and how much of his playing time
            reflects his club&apos;s circumstances.
          </p>
        </Prose>
        <Hindsight title={`What happened by summer ${CS.season + 2}`}>
          {next?.market_value_eur ? (
            <p>
              His market value after {seasonLabel(CS.season + 1)} was <strong className="text-foreground">{formatEur(next.market_value_eur)}</strong>
              {" "}({formatPctChange(next.market_value_eur / mv - 1)}).
              {next.reliability !== "Insufficient" && next.peer_lo80_eur && next.peer_hi80_eur
                ? ` That season's estimate (basic data) placed him within the expected range (${formatEurRange(next.peer_lo80_eur, next.peer_hi80_eur)}): the gap had closed.`
                : ""}
            </p>
          ) : <p>No later market value is available in the data.</p>}
          {sale && (
            <p>
              <Link href={`/transfers/${sale.id}`} className="text-foreground underline underline-offset-2">{sale.to_club_name} paid {formatEur(sale.fee_eur)}</Link>
              {" "}on {sale.date}{sale.expected_fee_eur ? `, against an expected fee of ${formatEur(sale.expected_fee_eur)} (${FEE_LABELS[sale.label ?? ""]?.short.toLowerCase() ?? "not assessed"}).` : "."}
            </p>
          )}
          <p>
            One case proves nothing on its own. Across all past seasons, flagged players gained more value than comparable peers on average,
            but many flags didn&apos;t move at all (see the <Link href="/methodology#backtest" className="underline underline-offset-2">backtest</Link>).
          </p>
        </Hindsight>
      </ReportSection>

      <ReportSection letter="E" title="Limitations">
        <Limitations items={[
          "The performance-implied value isn't a price: it describes what comparable profiles typically carried in the same league that summer, with an 80% range of " + formatEurRange(row.peer_lo80_eur, row.peer_hi80_eur) + ".",
          "Contract length, release clauses, injuries, personality and agent relationships are invisible to the model and can explain any gap.",
          "Defensive contribution isn't measured in the free data, which limits any assessment of a midfielder.",
          "The target is Transfermarkt's crowd valuation, so the model reproduces how the market prices profiles, including its biases.",
          "Hindsight figures are shown for context only. They were never available to, or used by, the model.",
        ]} />
        <IntegrityNotice checks={checks} />
      </ReportSection>

      <ReportFooter next={{ href: CASE_STUDIES.transfer.href, label: CASE_STUDIES.transfer.kind }} />
    </article>
  );
}

function median(xs: number[]): number {
  if (!xs.length) return 0;
  const s = [...xs].sort((a, b) => a - b);
  const m = Math.floor(s.length / 2);
  return s.length % 2 ? s[m] : (s[m - 1] + s[m]) / 2;
}

function history(seasons: VPlayerSeason[]): HistoryPoint[] {
  const best = new Map<number, VPlayerSeason>();
  for (const s of seasons) {
    const cur = best.get(s.season!);
    if (!cur || (s.minutes ?? 0) > (cur.minutes ?? 0)) best.set(s.season!, s);
  }
  return [...best.values()].sort((a, b) => a.season! - b.season!).map((s) => {
    const ok = s.reliability && s.reliability !== "Insufficient";
    return { season: seasonLabel(s.season), marketValue: s.market_value_eur, estimate: ok ? s.peer_estimate_eur : null,
             lo80: ok ? s.peer_lo80_eur : null, hi80: ok ? s.peer_hi80_eur : null };
  });
}
