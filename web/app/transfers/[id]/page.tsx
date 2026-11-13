import type { Metadata } from "next";
import Link from "next/link";
import { notFound } from "next/navigation";
import { Suspense } from "react";

import { DriversList, parseDrivers } from "@/components/domain/drivers";
import { EstimateRange } from "@/components/domain/estimate-range";
import { GapLabel, ReliabilityBadge } from "@/components/domain/labels";
import { InsufficientData, Stat } from "@/components/domain/profile";
import { ValuationPanel } from "@/components/domain/valuation-panel";
import { PageSkeleton } from "@/components/shell/page-skeleton";
import { Card, Section } from "@/components/shell/site-chrome";
import { select, selectOne } from "@/lib/db/server";
import type { VPlayerSeason, VTransfers } from "@/lib/db/types";
import { formatEur, formatPctChange, seasonLabel } from "@/lib/format";
import { leagueName } from "@/lib/leagues";
import { FEE_LABELS, POSITION_GROUPS, UNOBSERVED_FEE_FACTORS } from "@/lib/vocabulary";

async function getTransfer(id: string) {
  if (!/^\d+$/.test(id)) return null;
  return selectOne<VTransfers>("v_transfers", { id: `eq.${id}`, select: "*" });
}

export async function generateMetadata(props: PageProps<"/transfers/[id]">): Promise<Metadata> {
  const t = await getTransfer((await props.params).id);
  return { title: t ? `${t.player_name}: ${t.from_club_name} → ${t.to_club_name}` : "Transfer not found" };
}

export default function TransferPage(props: PageProps<"/transfers/[id]">) {
  return (
    <Suspense fallback={<PageSkeleton />}>
      <TransferBody {...props} />
    </Suspense>
  );
}

async function TransferBody(props: PageProps<"/transfers/[id]">) {
  const t = await getTransfer((await props.params).id);
  if (!t) notFound();
  const assessed = t.expected_fee_eur && t.lo80_eur && t.hi80_eur;
  return (
    <div className="space-y-10">
      <div className="space-y-2">
        <p className="text-xs font-medium tracking-widest text-muted-foreground uppercase">
          Transfer · {t.date} · {seasonLabel(t.season)} {t.transfer_window} window
        </p>
        <h1 className="text-3xl font-semibold tracking-tight">
          <Link href={`/players/${t.player_slug}`} className="hover:underline">{t.player_name}</Link>
        </h1>
        <p className="text-sm text-muted-foreground">
          <Link href={`/clubs/${t.from_club_slug}`} className="text-foreground hover:underline">{t.from_club_name}</Link>{" "}
          ({leagueName(t.from_competition_id)}) →{" "}
          <Link href={`/clubs/${t.to_club_slug}`} className="text-foreground hover:underline">{t.to_club_name}</Link>{" "}
          ({leagueName(t.to_competition_id)})
          {t.age != null && <> · age {Math.floor(t.age)}</>} · {POSITION_GROUPS[t.position_group ?? ""] ?? "position unknown"}
        </p>
      </div>

      <div className="grid gap-6 sm:grid-cols-3">
        <Stat label="Fee" value={formatEur(t.fee_eur)} sub="as reported by Transfermarkt" />
        <Stat label="Market value before" value={formatEur(t.mv_before_eur)} sub={t.mv_before_date ? `valued ${t.mv_before_date}` : "no recent value"} />
        <Stat label="Expected fee" value={assessed ? formatEur(t.expected_fee_eur) : "–"}
              sub={assessed ? `${formatPctChange(t.premium_pct)} vs expected` : "not assessed"} />
      </div>

      {assessed ? (
        <div className="grid gap-6 lg:grid-cols-[1.4fr_1fr]">
          <Card className="space-y-4">
            <div className="flex flex-wrap items-center gap-2">
              <GapLabel label={t.label} kind="fee" />
              <ReliabilityBadge level={t.reliability} reason={t.reliability_reason} />
            </div>
            <EstimateRange estimate={t.expected_fee_eur!} lo80={t.lo80_eur!} hi80={t.hi80_eur!} lo95={t.lo95_eur} hi95={t.hi95_eur}
                           actual={t.fee_eur} actualLabel="Fee paid" estimateLabel="Expected fee"
                           tone={FEE_LABELS[t.label ?? ""]?.tone ?? "within"} />
            <div className="space-y-1 text-xs text-muted-foreground">
              <p>The fee can sit outside the range for reasons the data can&apos;t see:</p>
              <ul className="list-disc pl-4">{UNOBSERVED_FEE_FACTORS.map((f) => <li key={f}>{f}</li>)}</ul>
            </div>
          </Card>
          <Card className="space-y-4">
            <h2 className="text-sm font-semibold">What drove the expected fee</h2>
            <DriversList drivers={parseDrivers(t.drivers)} />
            <p className="text-xs text-muted-foreground">Effects relative to an average transfer, using only information public before {t.date}.</p>
          </Card>
        </div>
      ) : (
        <InsufficientData reason={t.reliability_reason ?? "This transfer is outside the model's coverage."}
                          fix="a market value from the year before the transfer" />
      )}

      <Suspense fallback={<div className="h-40" />}>
        <BeforeAndAfter t={t} />
      </Suspense>
    </div>
  );
}

/** The last season finished before the move (what the model could know) and the first season after (outcome). */
async function BeforeAndAfter({ t }: { t: VTransfers }) {
  const rows = await select<VPlayerSeason>("v_player_season", {
    player_id: `eq.${t.player_id}`, season: `in.(${t.season! - 1},${t.season})`, select: "*", order: "minutes.desc",
  });
  const before = rows.find((r) => r.season === t.season! - 1);
  const after = rows.find((r) => r.season === t.season);
  const change = after?.market_value_eur && t.mv_before_eur ? after.market_value_eur / t.mv_before_eur - 1 : null;
  return (
    <div className="grid gap-6 lg:grid-cols-2">
      <Section title={`Before the move: ${seasonLabel(t.season! - 1)}`} description="The last season that had finished before the transfer.">
        <Card>
          {before ? <ValuationPanel row={before} compact /> : <p className="text-sm text-muted-foreground">No league season in the covered data before this move.</p>}
        </Card>
      </Section>
      <Section title={`Outcome: after ${seasonLabel(t.season)}`} description="Observed after the transfer. Not used by any model.">
        <Card className="space-y-2 text-sm">
          {after?.market_value_eur ? (
            <>
              <p className="text-2xl font-semibold tabular">{formatEur(after.market_value_eur)}</p>
              <p className="text-muted-foreground">
                Market value at the end of the first season at {after.club_name} ({leagueName(after.competition_id)}),{" "}
                {change != null ? `${formatPctChange(change)} vs the value before the move` : ""}. {after.minutes?.toLocaleString("en-GB")} league minutes.
              </p>
              <p className="text-xs text-muted-foreground">A rise or fall reflects how the market&apos;s view changed, not whether the fee was justified.</p>
            </>
          ) : (
            <p className="text-muted-foreground">No covered league season after the move yet (or under 900 minutes).</p>
          )}
        </Card>
      </Section>
    </div>
  );
}
