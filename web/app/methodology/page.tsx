import type { Metadata } from "next";
import { Suspense } from "react";

import { Table, Td, Th } from "@/components/data/table";
import { PageSkeleton } from "@/components/shell/page-skeleton";
import { Card, PageHeader, Section } from "@/components/shell/site-chrome";
import { select } from "@/lib/db/server";
import { seasonLabel } from "@/lib/format";
import { leagueName, MODEL_LEAGUES } from "@/lib/leagues";
import { cn } from "@/lib/utils";
import { FEE_LABELS, GAP_LABELS, RELIABILITY, type Reliability } from "@/lib/vocabulary";

export const metadata: Metadata = { title: "Methodology" };

interface Metrics { n: number; mae_log: number; median_ape: number; within_50pct: number; r2_log?: number; r2_log_fee?: number }
interface PivTier { rows: number; chosen: "ridge" | "gbm"; baseline: Metrics; peer_coverage: { coverage80: number; coverage95: number }; ridge: { metrics: Metrics }; gbm: { metrics: Metrics; coverage: { coverage80: number } } }
interface PivSummary { tiers: { full: PivTier; basic: PivTier } }
interface FeeSummary {
  rows: number; chosen: "ridge" | "gbm"; baselines: Record<string, Metrics>;
  ridge: { metrics: Metrics; coverage: { coverage80: number; coverage95: number; median_width80_ratio: number } };
  gbm: { metrics: Metrics; coverage: { coverage80: number } };
  gems_backtest: { by_season: Record<string, { under: { n?: number; median_excess_pct?: number }; premium: { median_excess_pct?: number } }> };
}
interface Coverage { source: string; competition_id: string; season: number; status: string }

const pct = (x: number | undefined) => (x == null ? "–" : `${(x * 100).toFixed(1)}%`);

export default function MethodologyPage() {
  return (
    <>
      <PageHeader
        eyebrow="Methodology"
        title="How FairValue works, and where it stops"
        description="Three layers, each used where its data is strong: facts (performance profiles), a performance-implied value for every player-season, and an expected fee for every transfer. All model numbers below are out-of-sample."
      />
      <Suspense fallback={<PageSkeleton />}>
        <MethodologyBody />
      </Suspense>
    </>
  );
}

async function MethodologyBody() {
  const [runs, coverage] = await Promise.all([
    select<{ model: string; created_at: string; summary: unknown }>("model_runs", { is_current: "eq.true", select: "model,created_at,summary" }),
    select<Coverage>("data_coverage", { select: "*", order: "season" }),
  ]);
  const piv = runs.find((r) => r.model === "piv")?.summary as PivSummary | undefined;
  const fee = runs.find((r) => r.model === "expected_fee")?.summary as FeeSummary | undefined;

  return (
    <div className="space-y-14">
      <Section title="1. The three layers">
        <div className="grid gap-4 md:grid-cols-3">
          <Card className="space-y-2"><p className="text-sm font-medium">Performance profiles (facts)</p>
            <p className="text-sm text-muted-foreground">Per-90 statistics, adjusted for small samples (empirical-Bayes shrinkage), ranked as percentiles against players in the same position group and season.</p></Card>
          <Card className="space-y-2"><p className="text-sm font-medium">Performance-implied value</p>
            <p className="text-sm text-muted-foreground">The market value players with a similar measurable profile typically carry in the same market that summer. Not a &ldquo;true value&rdquo;, and not a price forecast.</p></Card>{/* vocab-ok: explains what we do not claim */}
          <Card className="space-y-2"><p className="text-sm font-medium">Expected fee</p>
            <p className="text-sm text-muted-foreground">The fee deals with comparable public information commanded at the transfer date, anchored on the market value just before the move.</p></Card>
        </div>
      </Section>

      <Section title="2. Data" description="A frozen snapshot: Transfermarkt data to 6 July 2026 (via the community transfermarkt-datasets project) and Understat xG data to 2024/25 (recovered from the Internet Archive after understat.com went offline in November 2026).">
        <div id="data" className="scroll-mt-24" />
        <CoverageGrid coverage={coverage} />
        <Card className="grid gap-x-8 gap-y-1 text-sm sm:grid-cols-2">
          <p className="text-muted-foreground">Paid permanent transfers since 2015/16</p><p className="tabular">15,416</p>
          <p className="text-muted-foreground">… involving a big-five club</p><p className="tabular">5,637</p>
          <p className="text-muted-foreground">… with xG-level pre-transfer data (full tier)</p><p className="tabular">1,794</p>
          <p className="text-muted-foreground">… with basic pre-transfer data and a recent market value</p><p className="tabular">4,893</p>
          <p className="text-muted-foreground">Understat ↔ Transfermarkt player match rate</p><p className="tabular">98.1% (estimated error ≈ 0.2%)</p>
        </Card>
        <p className="text-xs text-muted-foreground">
          Not available in free data: defensive actions, progressive passes and carries, dribbles, aerial duels, goalkeeping metrics,
          and contract length at the time of a transfer.
        </p>
      </Section>

      <Section title="3. Models and accuracy" description="Every number is walk-forward: each season is scored by a model trained only on earlier seasons, with hyperparameters chosen on the season before. Gradient boosting is used only if it beats Ridge regression by at least 5% without worse calibration.">
        {piv && fee ? (
          <Table>
            <thead>
              <tr><Th>Model</Th><Th align="right">Scored</Th><Th>Chosen</Th><Th align="right">Typical error</Th><Th align="right">Within ±50%</Th><Th align="right">Naive baseline error</Th><Th align="right">80% range coverage</Th></tr>
            </thead>
            <tbody>
              {(["full", "basic"] as const).map((t) => {
                const tier = piv.tiers[t];
                const m = tier[tier.chosen].metrics;
                return (
                  <tr key={t}>
                    <Td>Performance-implied value: {t === "full" ? "big five, xG-level" : "14 leagues, basic data"}</Td>
                    <Td align="right">{m.n.toLocaleString("en-GB")}</Td>
                    <Td>{tier.chosen === "gbm" ? "Gradient boosting" : "Ridge"}</Td>
                    <Td align="right">{pct(m.median_ape)}</Td><Td align="right">{pct(m.within_50pct)}</Td>
                    <Td align="right">{pct(tier.baseline.median_ape)}</Td><Td align="right">{pct(tier.peer_coverage.coverage80)}</Td>
                  </tr>
                );
              })}
              <tr>
                <Td>Expected fee</Td>
                <Td align="right">{fee[fee.chosen].metrics.n.toLocaleString("en-GB")}</Td>
                <Td>{fee.chosen === "gbm" ? "Gradient boosting" : "Ridge"}</Td>
                <Td align="right">{pct(fee[fee.chosen].metrics.median_ape)}</Td><Td align="right">{pct(fee[fee.chosen].metrics.within_50pct)}</Td>
                <Td align="right">{pct(fee.baselines["fee = market value"]?.median_ape)} <span className="text-xs text-muted-foreground">(fee = market value)</span></Td>
                <Td align="right">{pct(fee.ridge.coverage.coverage80)}</Td>
              </tr>
            </tbody>
          </Table>
        ) : <p className="text-sm text-muted-foreground">Model summaries unavailable.</p>}
        <p className="text-xs text-muted-foreground">
          &ldquo;Typical error&rdquo; is the median absolute percentage error in euros. Two drift corrections matter: predictions are
          re-centred each season on the market&apos;s median (the market became more unequal over time), and a point-in-time league
          market level tracks leagues getting relatively richer or poorer. Full model cards are in the project repository.
        </p>
      </Section>

      <Section title="4. Uncertainty and reliability" description="Ranges come from group-wise split-conformal calibration: the model's real out-of-sample errors in the previous three seasons, per league and position line, give the 80% and 95% bands. Valuation gaps compare players with same-league peers in the same summer, so league-wide market moves aren't mistaken for individual undervaluation.">
        <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-4">
          {(Object.keys(RELIABILITY) as Reliability[]).map((r) => (
            <Card key={r} className="space-y-1"><p className="text-sm font-medium">{r}</p><p className="text-xs text-muted-foreground">{RELIABILITY[r].explain}</p></Card>
          ))}
        </div>
        <p className="text-xs text-muted-foreground">
          Rules: High needs xG-level data and 1,800+ minutes; centre-backs and full-backs drop one level because defensive work isn&apos;t
          measured; goalkeepers and players under 900 minutes get no estimate.
        </p>
      </Section>

      <Section title="5. No look-ahead" description="Every number shown for a date uses only information available at that date.">
        <ul className="list-disc space-y-1 pl-5 text-sm text-muted-foreground">
          <li>Market values are taken strictly before the transfer date; recent form uses the 365 days before it.</li>
          <li>Season statistics come only from a season that had finished before the transfer (COVID-delayed 2019/20 seasons included).</li>
          <li>Fields that only describe today (current international caps, contract expiry, current club) never enter the pipeline.</li>
          <li>Historical estimates come from &ldquo;vintage&rdquo; models trained on earlier seasons only; automated tests inject future data and check nothing changes.</li>
        </ul>
      </Section>

      <Section title="6. Does a flag mean anything? The backtest" description="Players flagged as potential undervaluation compared with players of the same season, position, age band and value tier, 12 months later. Published whatever it shows.">
        <div id="backtest" className="scroll-mt-24" />
        {fee && (
          <Table>
            <thead><tr><Th>Season</Th><Th align="right">Flagged players</Th><Th align="right">Value change vs peers</Th><Th align="right">Market premium group vs peers</Th></tr></thead>
            <tbody>
              {Object.entries(fee.gems_backtest.by_season).map(([s, v]) => (
                <tr key={s}>
                  <Td>{seasonLabel(Number(s))}</Td><Td align="right">{v.under.n ?? "–"}</Td>
                  <Td align="right">{v.under.median_excess_pct != null ? `${v.under.median_excess_pct > 0 ? "+" : ""}${v.under.median_excess_pct}%` : "–"}</Td>
                  <Td align="right">{v.premium.median_excess_pct != null ? `${v.premium.median_excess_pct > 0 ? "+" : ""}${v.premium.median_excess_pct}%` : "–"}</Td>
                </tr>
              ))}
            </tbody>
          </Table>
        )}
        <p className="text-xs text-muted-foreground">
          Caveats: market values are crowd opinion, so part of the effect is the crowd catching up with the same public statistics; values
          that were unusually low for any reason tend to drift back; only players with a later valuation are counted.
        </p>
      </Section>

      <Section title="7. Glossary" description="FairValue never calls a player or transfer &ldquo;overpaid&rdquo; or &ldquo;underpaid&rdquo;; labels mark where a value falls relative to a range."> {/* vocab-ok: explains what we do not claim */}
        <div className="grid gap-3 md:grid-cols-2">
          {Object.entries({ ...GAP_LABELS, ...FEE_LABELS }).map(([label, m]) => (
            <div key={label} className="text-sm"><span className="font-medium">{label}.</span> <span className="text-muted-foreground">{m.explain}</span></div>
          ))}
        </div>
      </Section>

      <Section title="8. Limitations, sources and licensing">
        <ul className="list-disc space-y-1 pl-5 text-sm text-muted-foreground">
          <li>The valuation target is Transfermarkt&apos;s crowd opinion, including its biases (reputation, league prestige).</li>
          <li>Club conventions are invisible: e.g. Athletic Club players rarely move, which plausibly depresses their market values.</li>
          <li>Ranges are wide (a typical 80% range spans about ×3.6 for player values and ×9 for fees): that is the honest uncertainty with public data.</li>
          <li>Scottish Premiership ranges under-cover (≈73% inside the 80% range); treat labels there with extra caution.</li>
          <li>Non-commercial research project. Data: Transfermarkt via transfermarkt-datasets; xG: Understat. Raw data isn&apos;t republished; players appear with birth year only. Not affiliated with any club or data provider.</li>
        </ul>
      </Section>
    </div>
  );
}

const STATUS_CLASS: Record<string, string> = {
  full: "bg-brand/80",
  basic: "bg-range-strong",
  recent: "bg-range",
  none: "bg-transparent border border-dashed",
};

function CoverageGrid({ coverage }: { coverage: Coverage[] }) {
  const seasons = Array.from({ length: 14 }, (_, i) => 2012 + i);
  const LEAGUE_TO_US: Record<string, string> = { GB1: "GB1", ES1: "ES1", L1: "L1", IT1: "IT1", FR1: "FR1" };
  const status = (league: string, season: number) => {
    const us = coverage.find((c) => c.source === "understat" && c.competition_id === LEAGUE_TO_US[league] && c.season === season);
    if (us && us.status !== "missing") return "full";
    const tm = coverage.find((c) => c.source === "transfermarkt" && c.competition_id === league && c.season === season);
    if (tm?.status === "full_history") return "basic";
    if (tm) return "recent";
    return "none";
  };
  return (
    <Card className="space-y-3 overflow-x-auto">
      <table className="text-[11px] tabular" aria-label="Data coverage by league and season">
        <thead>
          <tr><th className="pr-3 text-left font-normal text-muted-foreground">League</th>
            {seasons.map((s) => <th key={s} className="px-0.5 font-normal text-muted-foreground">{String(s).slice(-2)}</th>)}</tr>
        </thead>
        <tbody>
          {MODEL_LEAGUES.map((l) => (
            <tr key={l}>
              <td className="pr-3 whitespace-nowrap text-muted-foreground">{leagueName(l)}</td>
              {seasons.map((s) => {
                const st = status(l, s);
                return <td key={s} className="px-0.5 py-0.5"><div className={cn("size-4 rounded-sm", STATUS_CLASS[st])} title={`${leagueName(l)} ${seasonLabel(s)}: ${st}`} /></td>;
              })}
            </tr>
          ))}
        </tbody>
      </table>
      <div className="flex flex-wrap gap-4 text-xs text-muted-foreground">
        <span className="inline-flex items-center gap-1.5"><span className="size-3 rounded-sm bg-brand/80" /> xG-level (Understat + Transfermarkt)</span>
        <span className="inline-flex items-center gap-1.5"><span className="size-3 rounded-sm bg-range-strong" /> Basic (Transfermarkt match data)</span>
        <span className="inline-flex items-center gap-1.5"><span className="size-3 rounded-sm border border-dashed" /> Not covered</span>
        <span>Season start years (12 = 2012/13).</span>
      </div>
    </Card>
  );
}
