import type { Metadata } from "next";
import Link from "next/link";
import { notFound } from "next/navigation";
import { Suspense } from "react";

import { FeeScatter, type FeePoint } from "@/components/charts/fee-scatter";
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
import type { VPlayerSeason, VTransfers } from "@/lib/db/types";
import { formatEur, formatEurRange, formatNumber, formatPctChange, ordinal, seasonLabel } from "@/lib/format";
import { leagueName } from "@/lib/leagues";
import { FEE_LABELS, METRICS, UNOBSERVED_FEE_FACTORS } from "@/lib/vocabulary";

const CS = CASE_STUDIES.transfer;
export const metadata: Metadata = { title: `Case study: ${CS.kind}`, description: CS.question };

const METRIC_KEYS = ["npxg_p90", "xa_p90", "shots_p90", "key_passes_p90", "xg_chain_p90", "goals_p90", "minutes_share"];

export default function TransferCaseStudy() {
  return (
    <Suspense fallback={<PageSkeleton />}>
      <Report />
    </Suspense>
  );
}

async function Report() {
  const t = await selectOne<VTransfers>("v_transfers", { id: `eq.${CS.transferId}`, select: "*" });
  if (!t || !t.fee_eur || !t.expected_fee_eur || !t.lo80_eur || !t.hi80_eur || !t.mv_before_eur || !t.date || !t.season) notFound();
  const age = t.age ?? 0;
  // Comparables: strikers of a similar age and market value, sold BEFORE this deal (only what was known on the day).
  const [comps, seasons, laterMoves] = await Promise.all([
    select<VTransfers>("v_transfers", {
      select: "*", position_group: `eq.${t.position_group}`, age: [`gte.${Math.floor(age) - 2}`, `lte.${Math.floor(age) + 2.5}`],
      mv_before_eur: [`gte.${t.mv_before_eur * (2 / 3)}`, `lte.${t.mv_before_eur * 1.5}`],
      date: ["gte.2017-07-01", `lt.${t.date}`], expected_fee_eur: "not.is.null", order: "date.desc",
    }),
    select<VPlayerSeason>("v_player_season", { player_id: `eq.${t.player_id}`, select: "*", order: "season.asc" }),
    select<VTransfers>("v_transfers", { player_id: `eq.${t.player_id}`, date: `gt.${t.date}`, fee_eur: "gt.0", select: "*", order: "date.asc" }),
  ]);
  const before = seasons.find((s) => s.season === t.season! - 1);
  const twoBefore = seasons.find((s) => s.season === t.season! - 2);
  const after = seasons.filter((s) => (s.season ?? 0) >= t.season! && s.market_value_eur);
  const drivers = parseDrivers(t.drivers);
  const d = (name: string) => drivers.find((x) => x.driver === name);
  const feeMv = t.fee_eur / t.mv_before_eur;
  const compFeeMv = comps.map((c) => (c.fee_eur ?? 0) / (c.mv_before_eur ?? 1));
  const compFeeExp = comps.map((c) => (c.fee_eur ?? 0) / (c.expected_fee_eur ?? 1));
  const maxCompFeeMv = Math.max(...compFeeMv);
  const top = comps.reduce((a, b) => ((b.fee_eur ?? 0) / (b.mv_before_eur ?? 1) > (a.fee_eur ?? 0) / (a.mv_before_eur ?? 1) ? b : a), comps[0]);
  const nWithin = comps.filter((c) => c.label === "Within expected range").length;
  const sale = laterMoves[0];
  const mvFell = (twoBefore?.market_value_eur ?? 0) > t.mv_before_eur;

  const toPoint = (c: VTransfers): FeePoint => ({
    player: c.player_name ?? "", date: c.date ?? "", expected: c.expected_fee_eur!, fee: c.fee_eur!,
    tone: (["discount", "premium"] as const).find((x) => x === FEE_LABELS[c.label ?? ""]?.tone) ?? "within",
  });
  const points = comps.filter((c) => (c.fee_eur ?? 0) > 0).map(toPoint);

  const checks = [
    { claim: "labelled a notable transfer premium", ok: t.label === "Notable transfer premium" },
    { claim: "High reliability", ok: t.reliability === "High" },
    { claim: "fee above the 80% range but inside the 95% range", ok: t.fee_eur > t.hi80_eur && (t.hi95_eur ?? Infinity) >= t.fee_eur },
    { claim: "buying club is the largest upward driver", ok: drivers[0]?.driver === "Buying club" && drivers[0].log > 0 },
    { claim: "highest fee-to-market-value ratio among the comparables", ok: feeMv > maxCompFeeMv },
    { claim: "market value fell in the year before the deal", ok: mvFell },
    { claim: "recent xG rate below the previous season's", ok: (before?.npxg_p90_pct ?? 100) < (twoBefore?.npxg_p90_pct ?? 0) },
    { claim: "at least 15 earlier comparable deals", ok: comps.length >= 15 },
    { claim: "most comparables within their expected range", ok: nWithin / comps.length > 0.5 },
    { claim: "comparables' median fee at or below their expected fee", ok: median(compFeeExp) <= 1 },
  ];

  return (
    <article className="pb-6">
      <ReportHeader
        kind={CS.kind}
        title={CS.title}
        standfirst={`On ${t.date}, ${t.to_club_name} paid ${formatEur(t.fee_eur)} for ${t.player_name}, ${feeMv.toFixed(1)} times his market value. Using only information public before that day, FairValue expected a fee of ${formatEur(t.expected_fee_eur)}. This report breaks down the difference and what it does and doesn't mean.`}
        meta={[
          { label: "Transaction", value: `${t.from_club_name} → ${t.to_club_name}` },
          { label: "Date and window", value: `${t.date} · ${seasonLabel(t.season)} ${t.transfer_window ?? ""} window` },
          { label: "Player at the time", value: `${t.player_name} · striker · ${Math.floor(age)}` },
          { label: "Estimate reliability", value: <ReliabilityBadge level={t.reliability} reason={t.reliability_reason} /> },
        ]}
      />

      <ReportSection letter="A" title="The transaction">
        <div className="grid gap-6 sm:grid-cols-2 lg:grid-cols-4">
          <Stat label="Fee paid" value={formatEur(t.fee_eur)} sub="as reported by Transfermarkt" />
          <Stat label="Market value before" value={formatEur(t.mv_before_eur)} sub={`dated ${t.mv_before_date}`} />
          <Stat label="Expected fee" value={formatEur(t.expected_fee_eur)} sub={`80% range ${formatEurRange(t.lo80_eur, t.hi80_eur)}`} />
          <Stat label="Premium vs expected" value={formatEur(t.premium_eur)} sub={`${formatPctChange(t.premium_pct)} above the expected fee`} />
        </div>
        <Prose>
          <p>
            {t.player_name} moved from {t.from_club_name} ({leagueName(t.from_competition_id)}) to {t.to_club_name} ({leagueName(t.to_competition_id)})
            {" "}in the final week of the {t.transfer_window} window, aged {Math.floor(age)}. Three numbers frame the deal, and they
            measure different things: the <strong>market value</strong> is Transfermarkt&apos;s estimate of his worth, the{" "}
            <strong>expected fee</strong> is what comparable deals actually cost relative to market value, and the{" "}
            <strong>fee</strong> is what was paid.
          </p>
        </Prose>
      </ReportSection>

      <ReportSection letter="B" title="What the club paid for">
        <div className="grid gap-6 lg:grid-cols-[1fr_1fr]">
          <Card className="space-y-3">
            <p className="text-xs font-medium text-muted-foreground">What moved the expected fee vs an average transfer (as of {t.date})</p>
            <DriversList drivers={drivers} />
          </Card>
          <Prose>
            <p>
              Before any premium, FairValue already expected a fee well above his {formatEur(t.mv_before_eur)} market value. The
              largest factor is <strong>who was buying</strong> ({formatPctChange((d("Buying club")?.pct ?? 0) / 100)}): the
              buyer&apos;s league and how much it had spent in the previous twelve months. Clubs in that position have historically
              paid more for the same player. Timing in the window ({formatPctChange((d("Timing")?.pct ?? 0) / 100)}) and the selling club&apos;s
              league and recent sales ({formatPctChange((d("Selling club")?.pct ?? 0) / 100)}) add to it.
            </p>
            <p>
              <strong>The player&apos;s output.</strong> In {seasonLabel(t.season - 1)}, the last season finished before the move,
              {" "}his numbers were good rather than exceptional: {ordinal(before?.npxg_p90_pct)} percentile for non-penalty xG per 90 among
              big-five strikers, {ordinal(before?.shots_p90_pct)} for shots and {ordinal(before?.goals_p90_pct)} for goals.
              {twoBefore?.npxg_p90_pct != null && ` The season before, his xG rate was in the ${ordinal(twoBefore.npxg_p90_pct)} percentile.`}
              {mvFell && ` His market value had fallen from ${formatEur(twoBefore?.market_value_eur)} a year earlier.`}
              {" "}A buyer paying {feeMv.toFixed(1)}× market
              value was betting on the stronger earlier season and his age, not on his most recent form.
            </p>
          </Prose>
        </div>
        {before && (
          <Card className="space-y-2.5">
            <p className="text-xs font-medium text-muted-foreground">
              {seasonLabel(before.season)} percentiles vs {formatNumber(before.peer_n)} big-five strikers ({before.club_name}, {formatNumber(before.minutes)} league minutes)
            </p>
            <div className="grid gap-x-10 gap-y-2.5 md:grid-cols-2">
              {METRIC_KEYS.map((m) => (
                <PercentileBar key={m} label={METRICS[m].short} source={METRICS[m].source} percentile={before[`${m}_pct` as keyof VPlayerSeason] as number | null} />
              ))}
            </div>
          </Card>
        )}

        <div className="space-y-3">
          <p className="text-sm font-medium">Comparable strikers sold before this deal</p>
          <p className="text-sm text-muted-foreground">
            {comps.length} transfers between July 2017 and {t.date}: strikers aged {Math.floor(age) - 2}–{Math.floor(age) + 2}, market value
            {" "}{formatEurRange(t.mv_before_eur * (2 / 3), t.mv_before_eur * 1.5)}. Median fee {median(compFeeMv).toFixed(2)}× market value;
            {" "}median fee {median(compFeeExp).toFixed(2)}× its expected fee. The highest multiple was {top.player_name}&apos;s
            {" "}{maxCompFeeMv.toFixed(2)}×; {t.player_name}&apos;s was {feeMv.toFixed(2)}×.
          </p>
          <Table>
            <thead><tr><Th>Player</Th><Th>Move</Th><Th>Date</Th><Th align="right">Age</Th><Th align="right">Market value</Th><Th align="right">Fee</Th><Th align="right">Fee ÷ MV</Th><Th>Fee vs expected</Th></tr></thead>
            <tbody>
              {comps.map((c) => (
                <tr key={c.id} className="hover:bg-surface">
                  <Td><Link href={`/transfers/${c.id}`} className="font-medium hover:underline">{c.player_name}</Link></Td>
                  <Td className="text-muted-foreground">{c.from_club_name} → {c.to_club_name}</Td>
                  <Td className="text-muted-foreground">{c.date}</Td>
                  <Td align="right">{Math.floor(c.age ?? 0)}</Td>
                  <Td align="right">{formatEur(c.mv_before_eur)}</Td>
                  <Td align="right">{formatEur(c.fee_eur)}</Td>
                  <Td align="right">{((c.fee_eur ?? 0) / (c.mv_before_eur ?? 1)).toFixed(2)}×</Td>
                  <Td><GapLabel label={c.label} kind="fee" /></Td>
                </tr>
              ))}
            </tbody>
          </Table>
        </div>
      </ReportSection>

      <ReportSection letter="C" title="Financial analysis">
        <div className="grid gap-6 lg:grid-cols-[1fr_1fr]">
          <Card className="space-y-3">
            <div className="flex flex-wrap items-center gap-2"><GapLabel label={t.label} kind="fee" /></div>
            <EstimateRange estimate={t.expected_fee_eur} lo80={t.lo80_eur} hi80={t.hi80_eur} lo95={t.lo95_eur} hi95={t.hi95_eur}
                           actual={t.fee_eur} actualLabel="Fee paid" estimateLabel="Expected fee" tone="premium" />
            <p className="text-xs text-muted-foreground">
              Dark band: 80% range ({formatEurRange(t.lo80_eur, t.hi80_eur)}). Light band: 95% range ({formatEurRange(t.lo95_eur, t.hi95_eur)}).
            </p>
          </Card>
          <Card className="space-y-2">
            <p className="text-xs font-medium text-muted-foreground">Fee vs expected fee: comparables (dots) and this deal (diamond)</p>
            <FeeScatter points={points} highlight={toPoint(t)} />
            <p className="text-xs text-muted-foreground">Dashed line: fee equal to the expected fee. Both axes are logarithmic.</p>
          </Card>
        </div>
        <Prose>
          <p>
            The fee is {formatEur(t.premium_eur)} above the expected fee: above the 80% range, so FairValue calls it a{" "}
            <em>notable transfer premium</em>, but inside the 95% range, so not an extreme outlier. Among the {comps.length} earlier
            comparables, {nWithin} sat within their expected range, and their median fee was {median(compFeeExp).toFixed(2)}× the expected
            fee. If anything, the model ran slightly high for this segment, so the premium isn&apos;t explained by the model
            systematically under-pricing young strikers.
          </p>
        </Prose>
      </ReportSection>

      <ReportSection letter="D" title="The analytical verdict">
        <Finding title="As of the transfer date">
          {t.to_club_name} paid a notable premium: {formatEur(t.premium_eur)} above what comparable deals implied, and a fee-to-market-value multiple
          higher than any of the {comps.length} earlier comparables. The data shows that the price was unusual; it can&apos;t show
          whether it was a mistake. Premiums like this often reflect factors the model can&apos;t observe: competition from other
          buyers, contract and release-clause terms, and a squad need the club judged to be urgent.
        </Finding>
        <Hindsight title="What happened afterwards">
          <ul className="space-y-1.5">
            {after.map((s) => (
              <li key={`${s.season}-${s.competition_id}`}>
                After {seasonLabel(s.season)} ({s.club_name}, {formatNumber(s.minutes)} league minutes): market value{" "}
                <strong className="text-foreground">{formatEur(s.market_value_eur)}</strong>
              </li>
            ))}
          </ul>
          {sale && (
            <p>
              On {sale.date} he joined {sale.to_club_name} for{" "}
              <Link href={`/transfers/${sale.id}`} className="text-foreground underline underline-offset-2">{formatEur(sale.fee_eur)}</Link>
              {sale.expected_fee_eur ? `; that fee was ${FEE_LABELS[sale.label ?? ""]?.short.toLowerCase() ?? "not assessed"} (expected ${formatEur(sale.expected_fee_eur)}).` : "."}
            </p>
          )}
          <p>
            In hindsight, the premium was followed by a large rise in value. That is one outcome, not evidence that paying premiums
            works: the model can&apos;t separate the player&apos;s development from luck, the club&apos;s environment or the market&apos;s
            rise over the same period, and premium deals that went badly look just as convincing in advance.
          </p>
        </Hindsight>
      </ReportSection>

      <ReportSection letter="E" title="Limitations">
        <Limitations items={[
          "The expected fee describes what comparable deals cost, not what the player was worth to this buyer.",
          ...UNOBSERVED_FEE_FACTORS.map((f) => `Not observed by the model: ${f.charAt(0).toLowerCase()}${f.slice(1)}`),
          "Reported fees exclude most add-ons and are sometimes estimates themselves.",
          "Comparables are defined by position, age and market value; they don't account for playing style or contract situation.",
          "Hindsight values are shown for context only and were never used by the model.",
        ]} />
        <IntegrityNotice checks={checks} />
      </ReportSection>

      <ReportFooter next={{ href: CASE_STUDIES.club.href, label: CASE_STUDIES.club.kind }} />
    </article>
  );
}

function median(xs: number[]): number {
  if (!xs.length) return 0;
  const s = [...xs].sort((a, b) => a - b);
  const m = Math.floor(s.length / 2);
  return s.length % 2 ? s[m] : (s[m - 1] + s[m]) / 2;
}
