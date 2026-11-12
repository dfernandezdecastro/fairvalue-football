import type { Metadata } from "next";
import { Suspense } from "react";

import { DriversList, parseDrivers } from "@/components/domain/drivers";
import { EstimateRange } from "@/components/domain/estimate-range";
import { GapLabel, ReliabilityBadge } from "@/components/domain/labels";
import { DataTierPill, InsufficientData, PercentileBar, SourceFootnote, Stat } from "@/components/domain/profile";
import { Card, PageHeader, Section } from "@/components/shell/site-chrome";
import { Skeleton } from "@/components/ui/skeleton";
import { select, selectOne } from "@/lib/db/server";
import type { VPlayerSeason, VTransfers } from "@/lib/db/types";
import { formatEur, seasonLabel } from "@/lib/format";
import { FEE_LABELS, GAP_LABELS, METRICS, RELIABILITY, type Reliability } from "@/lib/vocabulary";

export const metadata: Metadata = { title: "Design system", robots: { index: false } };

const PCT_METRICS = ["npxg_p90", "xa_p90", "shots_p90", "key_passes_p90", "xg_chain_p90", "xg_buildup_p90", "minutes_share"];
const SWATCHES = ["brand", "discount", "premium", "within", "range-strong", "range", "surface", "muted"];

function toneOf(label: string | null, kind: "gap" | "fee" = "gap") {
  return ((kind === "gap" ? GAP_LABELS : FEE_LABELS)[label ?? ""]?.tone ?? "within");
}

// Component review page (Step 7): every domain component with real database rows.
// Convention for data pages: the header renders at once, data sections stream in behind <Suspense>.
export default function DesignPage() {
  return (
    <div className="space-y-12">
      <PageHeader
        eyebrow="Internal · component review"
        title="Design system"
        description="Every domain component rendered with real rows from the database. Wording comes only from lib/vocabulary.ts; ranges are always drawn with estimates."
      />
      <Suspense fallback={<div className="space-y-6"><Skeleton className="h-24" /><Skeleton className="h-80" /></div>}>
        <DesignContent />
      </Suspense>
    </div>
  );
}

async function DesignContent() {
  const [yamal, gem, mitro, unscored] = await Promise.all([
    selectOne<VPlayerSeason>("v_player_season", { player_name: "eq.Lamine Yamal", season: "eq.2024", select: "*" }),
    selectOne<VPlayerSeason>("v_player_season", {
      season: "eq.2024", gap_label: "eq.Strong signal of potential undervaluation", reliability: "eq.High",
      model_tier: "eq.full", order: "gap_log.asc", select: "*",
    }),
    selectOne<VTransfers>("v_transfers", {
      player_name: "eq.Aleksandar Mitrović", label: "not.is.null", order: "premium_eur.desc", select: "*",
    }),
    selectOne<VTransfers>("v_transfers", { reliability: "eq.Insufficient", season: "eq.2024", order: "fee_eur.desc", select: "*" }),
  ]);
  const counts = await select<{ gap_label: string }>("piv_estimates", { select: "gap_label", season: "eq.2024", model_tier: "eq.full", limit: 2000 });

  return (
    <div className="space-y-12">
      <Section title="Colour tokens" description="Blue = discount, amber = premium, neutral = within range. Never red/green: a gap is a signal, not a verdict.">
        <div className="flex flex-wrap gap-3">
          {SWATCHES.map((s) => (
            <div key={s} className="space-y-1.5 text-xs">
              <div className="size-14 rounded-md border" style={{ background: `var(--${s})` }} />
              <p className="text-muted-foreground">{s}</p>
            </div>
          ))}
        </div>
      </Section>

      <Section title="Stat tiles">
        <div className="grid gap-6 sm:grid-cols-4">
          <Stat label="Transfers covered" value="15,416" sub="paid, 2015/16 to 2025/26" />
          <Stat label="Player-seasons valued" value="47,331" sub="walk-forward estimates" />
          <Stat label="Labelled 2024/25 (xG tier)" value={counts.filter((c) => c.gap_label && c.gap_label !== "Within expected range").length.toLocaleString("en-GB")} sub="outside the 80% range" />
          <Stat label="Hidden Gems backtest" value="+7.9%" sub="vs peers over 12 months (80% CI 6.5–11.1%)" />
        </div>
      </Section>

      {yamal && yamal.peer_estimate_eur && yamal.peer_lo80_eur && yamal.peer_hi80_eur && (
        <Section title="Estimate with range: a player within the expected range" description={`${yamal.player_name}, ${yamal.club_name}, ${seasonLabel(yamal.season)}`}>
          <Card className="space-y-5">
            <div className="flex flex-wrap items-center gap-3">
              <GapLabel label={yamal.gap_label} />
              <ReliabilityBadge level={yamal.reliability ?? "Insufficient"} reason={yamal.reliability_reason} />
              <DataTierPill tier={yamal.data_tier} />
            </div>
            <EstimateRange
              estimate={yamal.peer_estimate_eur} lo80={yamal.peer_lo80_eur} hi80={yamal.peer_hi80_eur}
              lo95={yamal.peer_lo95_eur} hi95={yamal.peer_hi95_eur} actual={yamal.market_value_eur}
              actualLabel="Market value" estimateLabel="Performance-implied value" tone={toneOf(yamal.gap_label)}
            />
            <div className="grid gap-8 md:grid-cols-2">
              <div className="space-y-2">
                <p className="text-xs font-medium text-muted-foreground">Profile vs {yamal.peer_n} peers (percentiles)</p>
                {PCT_METRICS.map((m) => (
                  <PercentileBar key={m} label={METRICS[m].short} source={METRICS[m].source}
                                 percentile={yamal[`${m}_pct` as keyof VPlayerSeason] as number | null} />
                ))}
              </div>
              <div className="space-y-2">
                <p className="text-xs font-medium text-muted-foreground">Why this estimate</p>
                <DriversList drivers={parseDrivers(yamal.drivers)} />
              </div>
            </div>
            <SourceFootnote sources={["Transfermarkt (market value, minutes)", "Understat (xG metrics)", "FairValue model"]} />
          </Card>
        </Section>
      )}

      {gem && gem.peer_estimate_eur && gem.peer_lo80_eur && gem.peer_hi80_eur && (
        <Section title="Estimate with range: a strong undervaluation signal" description={`${gem.player_name}, ${gem.club_name}, ${seasonLabel(gem.season)}. Market value below the 95% range.`}>
          <Card className="space-y-4">
            <div className="flex flex-wrap items-center gap-3">
              <GapLabel label={gem.gap_label} />
              <ReliabilityBadge level={gem.reliability ?? "Insufficient"} reason={gem.reliability_reason} />
            </div>
            <EstimateRange
              estimate={gem.peer_estimate_eur} lo80={gem.peer_lo80_eur} hi80={gem.peer_hi80_eur}
              lo95={gem.peer_lo95_eur} hi95={gem.peer_hi95_eur} actual={gem.market_value_eur}
              actualLabel="Market value" estimateLabel="Performance-implied value" tone={toneOf(gem.gap_label)}
            />
          </Card>
        </Section>
      )}

      {mitro && mitro.expected_fee_eur && mitro.lo80_eur && mitro.hi80_eur && (
        <Section title="Transfer fee vs expected fee" description={`${mitro.player_name}: ${mitro.from_club_name} → ${mitro.to_club_name}, ${mitro.date}`}>
          <Card className="space-y-4">
            <div className="flex flex-wrap items-center gap-3">
              <GapLabel label={mitro.label} kind="fee" />
              <ReliabilityBadge level={mitro.reliability} reason={mitro.reliability_reason} />
            </div>
            <EstimateRange
              estimate={mitro.expected_fee_eur} lo80={mitro.lo80_eur} hi80={mitro.hi80_eur} lo95={mitro.lo95_eur}
              hi95={mitro.hi95_eur} actual={mitro.fee_eur} actualLabel="Fee paid" estimateLabel="Expected fee"
              tone={toneOf(mitro.label, "fee")}
            />
            <p className="text-xs text-muted-foreground">
              Compact table variant:
            </p>
            <div className="w-64">
              <EstimateRange size="sm" estimate={mitro.expected_fee_eur} lo80={mitro.lo80_eur} hi80={mitro.hi80_eur}
                             actual={mitro.fee_eur} tone={toneOf(mitro.label, "fee")} />
            </div>
          </Card>
        </Section>
      )}

      <Section title="Insufficient data" description="Replaces an estimate whenever the reliability rules fail (rule R3).">
        <InsufficientData
          reason={unscored ? `${unscored.player_name} → ${unscored.to_club_name} (${formatEur(unscored.fee_eur)}): ${unscored.reliability_reason}.` : "No market value within 365 days before the transfer."}
          fix="a recent market value, or more recent playing time in a covered league"
        />
      </Section>

      <Section title="Labels and reliability" description="All variants, wording from lib/vocabulary.ts. Hover for the explanation.">
        <div className="space-y-3">
          <div className="flex flex-wrap gap-2">{Object.keys(GAP_LABELS).map((l) => <GapLabel key={l} label={l} />)}</div>
          <div className="flex flex-wrap gap-2">{Object.keys(FEE_LABELS).map((l) => <GapLabel key={l} label={l} kind="fee" />)}</div>
          <div className="flex flex-wrap gap-4">
            {(Object.keys(RELIABILITY) as Reliability[]).map((r) => <ReliabilityBadge key={r} level={r} />)}
          </div>
          <div className="flex gap-2"><DataTierPill tier="full" /><DataTierPill tier="basic" /></div>
        </div>
      </Section>
    </div>
  );
}
