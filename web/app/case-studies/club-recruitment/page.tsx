import type { Metadata } from "next";
import Link from "next/link";
import { notFound } from "next/navigation";
import { Suspense } from "react";

import { Finding, Hindsight, IntegrityNotice, Limitations, Prose, ReportFooter, ReportHeader, ReportSection } from "@/components/case-study/report";
import { Table, Td, Th } from "@/components/data/table";
import { parseDrivers } from "@/components/domain/drivers";
import { GapLabel, ReliabilityBadge } from "@/components/domain/labels";
import { Stat } from "@/components/domain/profile";
import { RatioRange } from "@/components/domain/ratio-range";
import { PageSkeleton } from "@/components/shell/page-skeleton";
import { Card } from "@/components/shell/site-chrome";
import { CASE_STUDIES } from "@/lib/case-studies";
import { select } from "@/lib/db/server";
import type { VClubAudit, VPlayerSeason, VTransfers } from "@/lib/db/types";
import { formatEur, formatEurRange, formatPctChange, ordinal, seasonLabel } from "@/lib/format";
import { leagueName } from "@/lib/leagues";
import { METRICS, POSITION_GROUPS } from "@/lib/vocabulary";

const CS = CASE_STUDIES.club;
export const metadata: Metadata = { title: `Case study: ${CS.kind}`, description: CS.question };

/** The shortlist is built as of the summer after this season; nothing dated later feeds the profile or the screen. */
const CUTOFF = `${CS.shortlistSeason + 1}-07-01`;
const UNDERVALUATION = ["Potential undervaluation", "Strong signal of potential undervaluation"];
const BIG5 = ["GB1", "ES1", "IT1", "L1", "FR1"];
const POS_SHORT: Record<string, string> = { CB: "Centre-back", FB: "Full-back", CM: "Midfielder", AM_W: "Att. mid / winger", ST: "Striker" };
const STAT_KEYS = ["npxg_p90", "xa_p90", "shots_p90", "key_passes_p90", "xg_chain_p90", "xg_buildup_p90"] as const;

export default function ClubCaseStudy() {
  return (
    <Suspense fallback={<PageSkeleton />}>
      <Report />
    </Suspense>
  );
}

async function Report() {
  const [audits, buys, sales, squad] = await Promise.all([
    select<VClubAudit>("v_club_audit", { club_id: `eq.${CS.clubId}`, select: "*" }),
    select<VTransfers>("v_transfers", { to_club_id: `eq.${CS.clubId}`, fee_eur: "gt.0", date: ["gte.2017-07-01", `lt.${CUTOFF}`], select: "*", order: "fee_eur.desc" }),
    select<VTransfers>("v_transfers", { from_club_id: `eq.${CS.clubId}`, fee_eur: "gt.0", date: ["gte.2017-07-01", `lt.${CUTOFF}`], select: "*", order: "fee_eur.desc" }),
    select<VPlayerSeason>("v_player_season", { club_id: `eq.${CS.clubId}`, season: `eq.${CS.shortlistSeason}`, select: "*", order: "minutes.desc" }),
  ]);
  const club = audits[0]?.club_name ?? buys[0]?.to_club_name;
  if (!club || buys.length < 20) notFound();

  // --- Recruitment profile, computed from the club's own paid purchases before the cutoff.
  const ages = buys.map((b) => b.age).filter((a): a is number => a != null);
  const mvs = buys.map((b) => b.mv_before_eur).filter((v): v is number => !!v);
  const fees = buys.map((b) => b.fee_eur!);
  const medAge = quantile(ages, 0.5);
  const shareU23 = ages.filter((a) => a < 23).length / ages.length;
  // Selling clubs outside the covered top flights have no league id: they count as outside the big five too.
  const outsideBig5 = buys.filter((b) => !BIG5.includes(b.from_competition_id ?? "")).length / buys.length;
  // Price ratio (fees ÷ expected fees) from assessed purchases before the cutoff only; the precomputed club audit includes later deals.
  const ratio = (xs: VTransfers[]) => {
    const a = xs.filter((b) => b.expected_fee_eur);
    return { n: a.length, r: a.reduce((s, b) => s + b.fee_eur!, 0) / Math.max(1, a.reduce((s, b) => s + b.expected_fee_eur!, 0)) };
  };
  const allRatio = ratio(buys);
  const recentRatio = ratio(buys.filter((b) => (b.season ?? 0) >= CS.shortlistSeason - 2));
  const mvCap = quantile(mvs, 0.9);
  const positions = Object.entries(count(buys.map((b) => b.position_group ?? "?"))).sort((a, b) => b[1] - a[1]);
  const totalSales = sales.reduce((s, x) => s + (x.fee_eur ?? 0), 0);
  const totalBuys = fees.reduce((s, x) => s + x, 0);

  // --- The screen: undervaluation flags among young, affordable, regular big-five players in the season before the cutoff.
  const ageCap = 24;
  const shareUnderCap = ages.filter((a) => a < ageCap).length / ages.length;
  const shortlist = await select<VPlayerSeason>("v_player_season", {
    select: "*", season: `eq.${CS.shortlistSeason}`, model_tier: "eq.full", gap_label: `in.(${UNDERVALUATION.map((l) => `"${l}"`).join(",")})`,
    reliability: "in.(High,Moderate)", age: `lt.${ageCap}`, market_value_eur: `lte.${mvCap}`, minutes: "gte.1500",
    club_id: `neq.${CS.clubId}`, position_group: "neq.GK", order: "peer_estimate_eur.desc", limit: 10,
  });
  const ids = shortlist.map((s) => s.player_id).join(",");
  const [later, laterMoves] = ids
    ? await Promise.all([
        select<VPlayerSeason>("v_player_season", { player_id: `in.(${ids})`, season: `eq.${CS.shortlistSeason + 1}`, select: "*", order: "minutes.desc" }),
        select<VTransfers>("v_transfers", { player_id: `in.(${ids})`, date: `gte.${CUTOFF.slice(0, 4)}-06-01`, fee_eur: "gt.0", select: "*", order: "date.asc" }),
      ])
    : [[], []];
  const sumMv = shortlist.reduce((s, p) => s + (p.market_value_eur ?? 0), 0);
  const sumEst = shortlist.reduce((s, p) => s + (p.peer_estimate_eur ?? 0), 0);
  const tracked = shortlist.map((p) => ({ p, next: later.find((l) => l.player_id === p.player_id) }));
  const rose = tracked.filter((x) => x.next?.market_value_eur && x.next.market_value_eur > (x.p.market_value_eur ?? Infinity)).length;
  const withNext = tracked.filter((x) => x.next?.market_value_eur).length;

  const squadByPos = Object.entries(
    squad.reduce<Record<string, number[]>>((acc, s) => ((acc[s.position_group ?? "?"] ??= []).push(s.age ?? 0), acc), {}),
  ).map(([pos, a]) => ({ pos, n: a.length, age: quantile(a, 0.5) })).sort((a, b) => b.age - a.age);

  const checks = [
    { claim: `${club} paid below expected fees overall`, ok: allRatio.r < 1 },
    { claim: "recent purchases close to expected fees", ok: Math.abs(recentRatio.r - 1) < 0.2 },
    { claim: "majority of purchases signed from outside the big five", ok: outsideBig5 > 0.5 },
    { claim: "about half of purchases under 23", ok: shareU23 >= 0.45 },
    { claim: "the screen returns exactly five players", ok: shortlist.length === 5 },
    { claim: "every shortlisted market value within the club's usual spending", ok: shortlist.every((s) => (s.market_value_eur ?? Infinity) <= mvCap) },
    { claim: "sales exceeded purchases since 2017", ok: totalSales > totalBuys },
    { claim: "several sales above the largest fee the club has paid", ok: sales.filter((x) => (x.fee_eur ?? 0) > fees[0]).length >= 2 },
  ];

  return (
    <article className="pb-6">
      <ReportHeader
        kind={CS.kind}
        title={CS.title}
        standfirst={`${club} has bought ${buys.length} players for a fee since 2017, mostly young and from outside the big five, and has sold several players for far more than it has ever paid for one. This report turns that pattern into a screen, applies it to the ${seasonLabel(CS.shortlistSeason)} data as of summer ${CS.shortlistSeason + 1}, and then shows what happened next.`}
        meta={[
          { label: "Club", value: club },
          { label: "Purchase history used", value: `July 2017 – June ${CS.shortlistSeason + 1} · ${buys.length} paid transfers` },
          { label: "Shortlist reference", value: `${seasonLabel(CS.shortlistSeason)} season · values of summer ${CS.shortlistSeason + 1}` },
          { label: "What this isn't", value: "a scouting report or a transfer budget" },
        ]}
      />

      <ReportSection letter="A" title="Recruitment profile">
        <div className="grid gap-6 sm:grid-cols-2 lg:grid-cols-4">
          <Stat label="Median age at signing" value={medAge.toFixed(1)} sub={`${Math.round(shareU23 * 100)}% signed under 23`} />
          <Stat label="Signed from outside the big five" value={`${Math.round(outsideBig5 * 100)}%`} sub="of paid purchases" />
          <Stat label="Typical market value at signing" value={formatEur(quantile(mvs, 0.5))} sub={`90% of signings at or below ${formatEur(mvCap)}`} />
          <Stat label="Fees paid vs expected" value={`${allRatio.r.toFixed(2)}×`} sub={`total fees ÷ total expected fees, ${allRatio.n} assessed purchases`} />
        </div>
        <div className="grid gap-6 lg:grid-cols-[1fr_1fr]">
          <Card className="space-y-3">
            <p className="text-xs font-medium text-muted-foreground">Price ratio (fees ÷ expected fees), purchases to June {CS.shortlistSeason + 1}</p>
            <RatioRange ratio={allRatio.r} />
            <p className="text-xs text-muted-foreground">
              Left of the line: paid less than comparable deals. The <Link href={`/clubs/${CS.clubSlug}`} className="underline underline-offset-2">club page</Link> shows
              the full audit with uncertainty ranges, including later purchases.
            </p>
            <p className="pt-2 text-xs font-medium text-muted-foreground">Positions bought</p>
            <ul className="grid grid-cols-2 gap-x-6 gap-y-1 text-sm">
              {positions.map(([pos, n]) => (
                <li key={pos} className="flex justify-between gap-2"><span className="text-muted-foreground">{POSITION_GROUPS[pos] ?? pos}</span><span className="tabular">{n}</span></li>
              ))}
            </ul>
          </Card>
          <Prose>
            <p>
              <strong>A buy-young, sell-high model.</strong> {club} signs players at a median age of {medAge.toFixed(1)}, usually from
              outside the big five, and historically paid {Math.round((1 - allRatio.r) * 100)}% less than comparable deals
              implied ({allRatio.r.toFixed(2)}×). Over the same period it received {formatEur(totalSales)} from {sales.length} paid sales, against{" "}
              {formatEur(totalBuys)} spent on {buys.length} purchases.
            </p>
            <p>
              The pattern isn&apos;t constant. In the three seasons before the reference date ({seasonLabel(CS.shortlistSeason - 2)} to {seasonLabel(CS.shortlistSeason)}) it paid{" "}
              {recentRatio.r.toFixed(2)}× expected fees across {recentRatio.n} assessed purchases, close to the market rate, so the discount is a historical trait rather than a guarantee.
            </p>
          </Prose>
        </div>
        <div className="grid gap-6 lg:grid-cols-2">
          <div className="space-y-2">
            <p className="text-sm font-medium">Largest purchases</p>
            <Table>
              <thead><tr><Th>Player</Th><Th>From</Th><Th align="right">Age</Th><Th align="right">Fee</Th><Th>Fee vs expected</Th></tr></thead>
              <tbody>
                {buys.slice(0, 6).map((b) => (
                  <tr key={b.id} className="hover:bg-surface">
                    <Td><Link href={`/transfers/${b.id}`} className="font-medium hover:underline">{b.player_name}</Link></Td>
                    <Td className="text-muted-foreground">{b.from_club_name}</Td>
                    <Td align="right">{Math.floor(b.age ?? 0)}</Td>
                    <Td align="right">{formatEur(b.fee_eur)}</Td>
                    <Td>{b.label ? <GapLabel label={b.label} kind="fee" /> : <span className="text-xs text-muted-foreground">not assessed</span>}</Td>
                  </tr>
                ))}
              </tbody>
            </Table>
          </div>
          <div className="space-y-2">
            <p className="text-sm font-medium">Largest sales</p>
            <Table>
              <thead><tr><Th>Player</Th><Th>To</Th><Th>Date</Th><Th align="right">Fee</Th></tr></thead>
              <tbody>
                {sales.slice(0, 6).map((s) => (
                  <tr key={s.id} className="hover:bg-surface">
                    <Td><Link href={`/transfers/${s.id}`} className="font-medium hover:underline">{s.player_name}</Link></Td>
                    <Td className="text-muted-foreground">{s.to_club_name}</Td>
                    <Td className="text-muted-foreground">{s.date}</Td>
                    <Td align="right">{formatEur(s.fee_eur)}</Td>
                  </tr>
                ))}
              </tbody>
            </Table>
          </div>
        </div>
      </ReportSection>

      <ReportSection letter="B" title="Recruitment opportunities">
        <Prose>
          <p>
            FairValue doesn&apos;t know {club}&apos;s tactical plans or needs, so this section only describes the squad as it stood in
            {" "}{seasonLabel(CS.shortlistSeason)}: who played league minutes, by position and median age. Older groups are where
            a buy-young, sell-high club would usually plan ahead; whether it should is a coaching decision.
          </p>
        </Prose>
        <Table>
          <thead><tr><Th>Position group</Th><Th align="right">Players with league minutes</Th><Th align="right">Median age</Th></tr></thead>
          <tbody>
            {squadByPos.map((g) => (
              <tr key={g.pos}><Td>{POSITION_GROUPS[g.pos] ?? g.pos}</Td><Td align="right">{g.n}</Td><Td align="right">{g.age.toFixed(1)}</Td></tr>
            ))}
          </tbody>
        </Table>
      </ReportSection>

      <ReportSection letter="C" title="A ranked shortlist">
        <Prose>
          <p>
            The screen copies the club&apos;s own buying pattern rather than inventing a brief: outfield players in the big five in
            {" "}{seasonLabel(CS.shortlistSeason)} younger than {ageCap} ({Math.round(shareUnderCap * 100)}% of its signings were), with a market value at or below{" "}
            {formatEur(mvCap)} (90% of its signings were), 1,500+ league minutes, xG-level data, and a potential-undervaluation flag
            with High or Moderate reliability. Ranked by performance-implied value.
          </p>
        </Prose>
        <Table>
          <thead><tr><Th>#</Th><Th>Player</Th><Th>Position · age</Th><Th align="right">Market value</Th><Th align="right">Implied value (80% range)</Th><Th>Gap</Th><Th>Reliability</Th><Th>Main statistical reason</Th></tr></thead>
          <tbody>
            {shortlist.map((p, i) => {
              const top = parseDrivers(p.drivers).find((d) => d.log > 0);
              const best = STAT_KEYS.map((k) => ({ k, v: p[`${k}_pct` as keyof VPlayerSeason] as number | null })).filter((x) => x.v != null).sort((a, b) => b.v! - a.v!)[0];
              return (
                <tr key={p.player_id} className="align-top hover:bg-surface">
                  <Td className="text-muted-foreground">{i + 1}</Td>
                  <Td>
                    <Link href={`/players/${p.player_slug}?season=${CS.shortlistSeason}&league=${p.competition_id}`} className="font-medium hover:underline">{p.player_name}</Link>
                    <span className="block text-xs text-muted-foreground">{p.club_name} · {leagueName(p.competition_id)}</span>
                  </Td>
                  <Td className="text-muted-foreground">{POS_SHORT[p.position_group ?? ""] ?? p.position_group} · {Math.floor(p.age ?? 0)}</Td>
                  <Td align="right">{formatEur(p.market_value_eur)}</Td>
                  <Td align="right">{formatEur(p.peer_estimate_eur)}<span className="block text-xs text-muted-foreground">{formatEurRange(p.peer_lo80_eur, p.peer_hi80_eur)}</span></Td>
                  <Td><GapLabel label={p.gap_label} /></Td>
                  <Td><ReliabilityBadge level={p.reliability} reason={p.reliability_reason} /></Td>
                  <Td className="text-xs text-muted-foreground">
                    {best ? `${ordinal(best.v)} pct ${METRICS[best.k].short}` : "–"}
                    {top && <span className="block">largest driver: {top.driver.toLowerCase()} ({formatPctChange(top.pct / 100)})</span>}
                  </Td>
                </tr>
              );
            })}
          </tbody>
        </Table>
        <p className="text-xs text-muted-foreground">
          &ldquo;Main statistical reason&rdquo; shows the player&apos;s best output percentile among big-five players in his position and the
          largest factor pushing his estimate up. For most of the five, context (age, league, team) matters more than output.
        </p>
      </ReportSection>

      <ReportSection letter="D" title="Financial perspective">
        <div className="grid gap-6 sm:grid-cols-3">
          <Stat label="Combined market value" value={formatEur(sumMv)} sub={`summer ${CS.shortlistSeason + 1}`} />
          <Stat label="Combined implied value" value={formatEur(sumEst)} sub="sum of central estimates" />
          <Stat label="Club's largest fee paid to date" value={formatEur(fees[0])} sub={buys[0]?.player_name ?? ""} />
        </div>
        <Prose>
          <p>
            Every player on the list has a market value within the range {club} has usually paid. Market value isn&apos;t a fee:
            across all transfers, fees for players like these vary widely around market value, and the club&apos;s own fees ran at{" "}
            {allRatio.r.toFixed(2)}× the expected level historically. FairValue has no view on the club&apos;s budget,
            wages or appetite for risk, so it can&apos;t say which deals were affordable.
          </p>
        </Prose>
      </ReportSection>

      <ReportSection letter="E" title="Strategic conclusion and limitations">
        <Finding title="What this shows">
          A club&apos;s own transfer history is enough to define a data-driven screen, and the screen produces a short, explainable
          list rather than hundreds of names. It is a starting point for scouting, not a recommendation to sign anyone.
        </Finding>
        <Hindsight title={`One season later (${seasonLabel(CS.shortlistSeason + 1)})`}>
          <ul className="space-y-1.5">
            {tracked.map(({ p, next }) => {
              const move = laterMoves.find((m) => m.player_id === p.player_id);
              return (
                <li key={p.player_id}>
                  <span className="text-foreground">{p.player_name}</span>:{" "}
                  {next?.market_value_eur
                    ? <>market value {formatEur(next.market_value_eur)} ({formatPctChange(next.market_value_eur / (p.market_value_eur ?? 1) - 1)}) at {next.club_name}</>
                    : "no covered league season with enough minutes"}
                  {move && <> · permanent transfer to {move.to_club_name} for {formatEur(move.fee_eur)} ({move.date})</>}
                </li>
              );
            })}
          </ul>
          <p>
            {rose} of the {withNext} players with a later market value saw it rise. {shortlist.length} players can&apos;t test a method; the{" "}
            <Link href="/methodology#backtest" className="underline underline-offset-2">backtest</Link> covers every flag in past seasons:
            flagged players gained more value than comparable peers on average, with wide variation and many flags that never moved.
          </p>
        </Hindsight>
        <Limitations items={[
          "The screen reproduces the club's past choices; it doesn't know whether those choices fit its current strategy, coach or budget.",
          "Tactical fit, character, wage demands, contract status and willingness to move are all invisible to the model.",
          "Defensive contribution isn't measured, which understates defenders and defensive midfielders.",
          "Only big-five players with xG data are screened; much of the club's real recruitment happens in leagues this screen can't see.",
          "Hindsight values are shown for context and were never used to build the list.",
        ]} />
        <IntegrityNotice checks={checks} />
      </ReportSection>

      <ReportFooter next={{ href: CASE_STUDIES.player.href, label: CASE_STUDIES.player.kind }} />
    </article>
  );
}

function quantile(xs: number[], q: number): number {
  if (!xs.length) return 0;
  const s = [...xs].sort((a, b) => a - b);
  const pos = (s.length - 1) * q;
  const lo = Math.floor(pos);
  return s[lo] + (s[Math.min(lo + 1, s.length - 1)] - s[lo]) * (pos - lo);
}

function count(xs: string[]): Record<string, number> {
  return xs.reduce<Record<string, number>>((acc, x) => ((acc[x] = (acc[x] ?? 0) + 1), acc), {});
}
