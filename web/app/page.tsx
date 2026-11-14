import { ArrowRight, BarChart3, Building2, Gem, Repeat2, type LucideIcon } from "lucide-react";
import Link from "next/link";
import { Suspense } from "react";

import { CaseStudyCards } from "@/components/case-study/cards";
import { Skeleton } from "@/components/ui/skeleton";
import { buttonVariants } from "@/components/ui/button";
import { Card } from "@/components/shell/site-chrome";
import { select, selectOne, selectPage } from "@/lib/db/server";
import type { VClubAudit, VPlayerSeason, VTransfers } from "@/lib/db/types";
import { formatEur, formatPctChange } from "@/lib/format";
import { leagueName } from "@/lib/leagues";
import { cn } from "@/lib/utils";
import { POSITION_GROUPS } from "@/lib/vocabulary";

const UNDER = 'in.("Potential undervaluation","Strong signal of potential undervaluation")';
const PREMIUM = 'in.("Notable transfer premium","Unusual transfer premium")';

const CAPABILITIES: { href: string; icon: LucideIcon; title: string; body: string }[] = [
  { href: "/players", icon: BarChart3, title: "Player valuations",
    body: "Percentile profiles against positional peers, and a performance-implied value with an 80% range, for every season since 2012/13." },
  { href: "/transfers", icon: Repeat2, title: "Transfer analysis",
    body: "Each fee compared with what comparable deals cost at that date, with the factors behind the expected fee and what happened next." },
  { href: "/hidden-gems", icon: Gem, title: "Hidden Gems",
    body: "Players whose market value sits below the range of same-league peers, with the reliability of each signal and a published backtest." },
  { href: "/clubs", icon: Building2, title: "Club recruitment",
    body: "How each club's fees compare with expected fees over time, and how its signings' values developed afterwards." },
];

export default function Home() {
  return (
    <div className="space-y-20 pb-10">
      <section className="space-y-8 border-b pt-4 pb-14 sm:pt-10">
        <div className="max-w-3xl space-y-5">
          <p className="text-xs font-medium tracking-widest text-brand uppercase">Football transfer intelligence</p>
          <h1 className="text-4xl leading-[1.1] font-semibold tracking-tight text-balance sm:text-5xl">
            Where the transfer market&apos;s prices and the evidence disagree
          </h1>
          <p className="text-base text-muted-foreground sm:text-lg">
            FairValue compares market values and transfer fees with what measurable performance and context usually command in
            the same market, and shows how certain each comparison is. Built on fourteen seasons of historical data, validated
            on seasons the models never saw.
          </p>
          <p className="text-sm text-muted-foreground">
            By <span className="font-medium text-foreground">Diego Fernandez de Castro</span>
          </p>
        </div>
        <div className="flex flex-wrap gap-3">
          <Link href="/players" className={cn(buttonVariants({ size: "lg" }), "h-10 px-4")}>
            Explore player valuations <ArrowRight data-icon="inline-end" />
          </Link>
          <Link href="/hidden-gems" className={cn(buttonVariants({ variant: "outline", size: "lg" }), "h-10 px-4")}>
            Discover Hidden Gems
          </Link>
        </div>
        <Suspense fallback={<Skeleton className="h-14 w-full max-w-3xl" />}>
          <CoverageStrip />
        </Suspense>
      </section>

      <HomeSection eyebrow="The platform" title="Four ways into the market">
        <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
          {CAPABILITIES.map((c) => (
            <Link key={c.href} href={c.href} className="group space-y-3 rounded-lg border bg-card p-5 transition-colors hover:border-foreground/30">
              <c.icon className="size-5 text-brand" aria-hidden />
              <p className="font-medium">{c.title}</p>
              <p className="text-sm text-muted-foreground">{c.body}</p>
            </Link>
          ))}
        </div>
      </HomeSection>

      <HomeSection eyebrow="Featured insights" title="What the data shows right now"
                   description="Live from the database. Labels mark where a value or fee falls relative to its range; they are signals to investigate, not verdicts.">
        <Suspense fallback={<div className="grid gap-6 lg:grid-cols-3">{[0, 1, 2].map((i) => <Skeleton key={i} className="h-80" />)}</div>}>
          <Insights />
        </Suspense>
      </HomeSection>

      <HomeSection eyebrow="Case studies" title="Three questions, answered with the data"
                   description="Long-form reports on a player valuation, a transfer and a club's recruitment, with what was known at the time kept apart from what happened afterwards.">
        <CaseStudyCards />
      </HomeSection>

      <HomeSection eyebrow="Methodology" title="Why the numbers can be trusted, and where they can't">
        <div className="grid gap-x-10 gap-y-6 md:grid-cols-2 lg:grid-cols-3">
          {[
            ["Historical data", "Transfermarkt values and fees across 14 leagues since 2012/13, and Understat xG for the big five to 2024/25. Raw data stays out of the repository."],
            ["Statistical modelling", "Gradient boosting and Ridge regression, chosen per model on out-of-sample error. No black-box score: every output is a value in euros."],
            ["Walk-forward validation", "Every season is scored by a model trained only on earlier seasons. Nothing dated after a valuation or transfer is used to make it."],
            ["Explainability", "Each estimate lists the factors that moved it, such as age, league, playing time or who was buying, and by how much."],
            ["Uncertainty", "Ranges are calibrated on the models' real past errors. Labels appear only outside the range, and thin data means no estimate."],
          ].map(([t, d]) => (
            <div key={t} className="space-y-1.5 border-t pt-4">
              <p className="text-sm font-medium">{t}</p>
              <p className="text-sm text-muted-foreground">{d}</p>
            </div>
          ))}
          <div className="space-y-1.5 border-t pt-4">
            <p className="text-sm font-medium">Tested in public</p>
            <Suspense fallback={<Skeleton className="h-10" />}><BacktestLine /></Suspense>
          </div>
        </div>
        <Link href="/methodology" className="inline-flex items-center gap-1.5 text-sm font-medium hover:underline">
          Full methodology, model accuracy and limitations <ArrowRight className="size-3.5" aria-hidden />
        </Link>
      </HomeSection>

      <section className="flex flex-col items-start justify-between gap-6 rounded-lg border bg-surface p-8 md:flex-row md:items-center">
        <div className="max-w-2xl space-y-2">
          <h2 className="text-xl font-semibold tracking-tight">Start with a player you know</h2>
          <p className="text-sm text-muted-foreground">
            Search any player in the 14 covered leagues to see their profile, their valuation history and every transfer, each with its range.
          </p>
        </div>
        <div className="flex flex-wrap gap-3">
          <Link href="/players" className={cn(buttonVariants({ size: "lg" }), "h-10 px-4")}>Explore player valuations</Link>
          <Link href="/case-studies" className={cn(buttonVariants({ variant: "outline", size: "lg" }), "h-10 px-4")}>Read the case studies</Link>
        </div>
      </section>
    </div>
  );
}

function HomeSection({ eyebrow, title, description, children }: {
  eyebrow: string; title: string; description?: string; children: React.ReactNode;
}) {
  return (
    <section className="space-y-6">
      <div className="max-w-3xl space-y-2">
        <p className="text-xs font-medium tracking-widest text-brand uppercase">{eyebrow}</p>
        <h2 className="text-2xl font-semibold tracking-tight">{title}</h2>
        {description && <p className="text-sm text-muted-foreground sm:text-base">{description}</p>}
      </div>
      {children}
    </section>
  );
}

async function CoverageStrip() {
  const [transfers, valued, players] = await Promise.all([
    selectPage<{ id: number }>("transfers", { select: "id", limit: 1 }),
    selectPage<{ player_id: number }>("piv_estimates", { select: "player_id", reliability: "neq.Insufficient", limit: 1 }),
    selectPage<{ id: number }>("players", { select: "id", limit: 1 }),
  ]);
  const items = [
    [players.total, "players"],
    [valued.total, "player-season valuations with ranges"],
    [transfers.total, "paid transfers since 2015/16"],
  ] as const;
  return (
    <ul className="flex flex-wrap gap-x-10 gap-y-3">
      {items.map(([n, label]) => (
        <li key={label} className="text-sm text-muted-foreground">
          <span className="text-xl font-semibold text-foreground tabular">{n.toLocaleString("en-GB")}</span> {label}
        </li>
      ))}
    </ul>
  );
}

async function BacktestLine() {
  const backtest = await selectOne<{ under: { median_excess_pct: number; ci80_pct: [number, number] } }>("model_runs", {
    model: "eq.expected_fee", is_current: "eq.true", select: "under:summary->gems_backtest->pooled->under",
  });
  if (!backtest) return <p className="text-sm text-muted-foreground">Backtest results unavailable.</p>;
  return (
    <p className="text-sm text-muted-foreground">
      Players flagged in past seasons gained a median {backtest.under.median_excess_pct}% more market value over 12 months than
      comparable peers (80% CI {backtest.under.ci80_pct[0]}–{backtest.under.ci80_pct[1]}%). An association, published whatever it showed.
    </p>
  );
}

async function Insights() {
  const [gems, premiums, clubs] = await Promise.all([
    select<VPlayerSeason>("v_player_season", {
      select: "*", season: "eq.2024", model_tier: "eq.full", reliability: "in.(High,Moderate)", gap_label: UNDER, order: "gap_log.asc", limit: 5,
    }),
    select<VTransfers>("v_transfers", { select: "*", season: "eq.2025", label: PREMIUM, reliability: "in.(High,Moderate)", order: "premium_eur.desc", limit: 5 }),
    select<VClubAudit>("v_club_audit", { select: "*", period: "eq.last3", ranked: "eq.true", order: "price_ratio_hi80.asc", limit: 5 }),
  ]);
  return (
    <div className="grid gap-6 lg:grid-cols-3">
      <InsightCard title="Strongest undervaluation signals" href="/hidden-gems"
                   note="2024/25 season (values of summer 2025), big five, xG-level data, high or moderate reliability.">
        {gems.map((r) => (
          <li key={`${r.player_id}-${r.competition_id}`} className="py-2.5">
            <Link href={`/players/${r.player_slug}?season=${r.season}&league=${r.competition_id}`} className="text-sm font-medium hover:underline">{r.player_name}</Link>
            <p className="text-xs text-muted-foreground tabular">
              {POSITION_GROUPS[r.position_group ?? ""]} · {leagueName(r.competition_id)} · market value {formatEur(r.market_value_eur)} vs implied {formatEur(r.peer_estimate_eur)}
            </p>
          </li>
        ))}
      </InsightCard>
      <InsightCard title="Largest transfer premiums, 2025/26" href="/transfers?view=premiums"
                   note="Fees above the 80% range of comparable deals at the transfer date.">
        {premiums.map((t) => (
          <li key={t.id} className="py-2.5">
            <Link href={`/transfers/${t.id}`} className="text-sm font-medium hover:underline">{t.player_name}</Link>
            <p className="text-xs text-muted-foreground tabular">
              {t.to_club_name} · fee {formatEur(t.fee_eur)} vs expected {formatEur(t.expected_fee_eur)} ({formatPctChange(t.premium_pct)})
            </p>
          </li>
        ))}
      </InsightCard>
      <InsightCard title="Most price-efficient clubs" href="/clubs?period=last3"
                   note="Last three seasons: fees ÷ expected fees, ranked by the cautious end of the 80% range.">
        {clubs.map((c) => (
          <li key={c.club_id} className="flex items-baseline justify-between gap-3 py-2.5">
            <Link href={`/clubs/${c.club_slug}`} className="truncate text-sm font-medium hover:underline">{c.club_name}</Link>
            <span className="text-xs whitespace-nowrap text-muted-foreground tabular">
              {c.price_ratio?.toFixed(2)}× ({c.price_ratio_lo80?.toFixed(2)}–{c.price_ratio_hi80?.toFixed(2)})
            </span>
          </li>
        ))}
      </InsightCard>
    </div>
  );
}

function InsightCard({ title, href, note, children }: { title: string; href: string; note: string; children: React.ReactNode }) {
  return (
    <Card className="flex flex-col gap-3">
      <div className="flex items-baseline justify-between gap-2">
        <h3 className="text-sm font-semibold">{title}</h3>
        <Link href={href} className="text-xs whitespace-nowrap text-muted-foreground hover:text-foreground">View all →</Link>
      </div>
      <p className="text-xs text-muted-foreground">{note}</p>
      <ul className="divide-y">{children}</ul>
    </Card>
  );
}
