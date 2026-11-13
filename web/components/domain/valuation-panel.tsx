import { EstimateRange } from "@/components/domain/estimate-range";
import { GapLabel, ReliabilityBadge } from "@/components/domain/labels";
import { DataTierPill, InsufficientData } from "@/components/domain/profile";
import type { VPlayerSeason } from "@/lib/db/types";
import { formatEur, seasonLabel } from "@/lib/format";
import { leagueName } from "@/lib/leagues";
import { GAP_LABELS, UNOBSERVED_VALUE_FACTORS } from "@/lib/vocabulary";

/** Market value vs performance-implied range for one player-season, or an honest "insufficient" state. */
export function ValuationPanel({ row, compact = false }: { row: VPlayerSeason; compact?: boolean }) {
  const ok = row.reliability !== "Insufficient" && row.peer_estimate_eur && row.peer_lo80_eur && row.peer_hi80_eur;
  if (!ok) {
    return (
      <InsufficientData
        reason={row.reliability_reason ?? (row.eligible ? "No model estimate for this season." : "Fewer than 900 league minutes this season.")}
        fix={row.position_group === "GK" ? "goalkeeping metrics (not available in free data)" : "more league minutes, or xG-level data for this league-season"}
      />
    );
  }
  const tone = GAP_LABELS[row.gap_label ?? ""]?.tone ?? "within";
  return (
    <div className="space-y-4">
      <div className="flex flex-wrap items-center gap-2">
        <GapLabel label={row.gap_label} />
        <ReliabilityBadge level={row.reliability} reason={row.reliability_reason} />
        <DataTierPill tier={row.data_tier} />
      </div>
      <EstimateRange
        estimate={row.peer_estimate_eur!} lo80={row.peer_lo80_eur!} hi80={row.peer_hi80_eur!}
        lo95={row.peer_lo95_eur} hi95={row.peer_hi95_eur} actual={row.market_value_eur}
        actualLabel="Market value" estimateLabel="Performance-implied value" tone={tone}
      />
      {!compact && (
        <div className="space-y-2 text-xs text-muted-foreground">
          <p>
            Compared with {leagueName(row.competition_id)} players with similar profiles in summer{" "}
            {(row.season ?? 0) + 1}. Whole-market estimate: {formatEur(row.estimate_eur)}. Estimated by a model trained
            on seasons up to {seasonLabel(row.train_through)} only.
          </p>
          <p>Not observed by the model: {UNOBSERVED_VALUE_FACTORS.join(" · ")}.</p>
        </div>
      )}
    </div>
  );
}
