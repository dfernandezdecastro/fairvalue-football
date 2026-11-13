import type { Metadata } from "next";
import Link from "next/link";
import { notFound } from "next/navigation";
import { Suspense } from "react";

import { FeeScatter, type FeePoint } from "@/components/charts/fee-scatter";
import { Table, Td, Th } from "@/components/data/table";
import { GapLabel } from "@/components/domain/labels";
import { InsufficientData, Stat } from "@/components/domain/profile";
import { RatioRange } from "@/components/domain/ratio-range";
import { PageSkeleton } from "@/components/shell/page-skeleton";
import { Card, Section } from "@/components/shell/site-chrome";
import { select, selectOne } from "@/lib/db/server";
import type { Clubs, VClubAudit, VTransfers } from "@/lib/db/types";
import { formatEur, formatPctChange, seasonLabel } from "@/lib/format";
import { leagueName } from "@/lib/leagues";
import { FEE_LABELS, POSITION_GROUPS } from "@/lib/vocabulary";

async function getClub(slug: string) {
  return selectOne<Clubs>("clubs", { slug: `eq.${slug}`, select: "id,name,slug" });
}

export async function generateMetadata(props: PageProps<"/clubs/[slug]">): Promise<Metadata> {
  const c = await getClub((await props.params).slug);
  return { title: c ? c.name : "Club not found" };
}

export default function ClubPage(props: PageProps<"/clubs/[slug]">) {
  return (
    <Suspense fallback={<PageSkeleton />}>
      <ClubBody {...props} />
    </Suspense>
  );
}

function distribution<T>(items: T[], key: (t: T) => string): { label: string; n: number }[] {
  const counts = new Map<string, number>();
  for (const it of items) counts.set(key(it), (counts.get(key(it)) ?? 0) + 1);
  return [...counts.entries()].map(([label, n]) => ({ label, n })).sort((a, b) => b.n - a.n);
}

function Bars({ title, data, total }: { title: string; data: { label: string; n: number }[]; total: number }) {
  return (
    <div className="space-y-2">
      <p className="text-xs font-medium text-muted-foreground">{title}</p>
      {data.slice(0, 6).map((d) => (
        <div key={d.label} className="grid grid-cols-[minmax(0,9rem)_1fr_2.5rem] items-center gap-2 text-sm">
          <span className="truncate text-muted-foreground">{d.label}</span>
          <span className="h-2 rounded-full bg-range"><span className="block h-2 rounded-full bg-brand" style={{ width: `${(d.n / total) * 100}%` }} /></span>
          <span className="text-right tabular">{d.n}</span>
        </div>
      ))}
    </div>
  );
}

async function ClubBody(props: PageProps<"/clubs/[slug]">) {
  const club = await getClub((await props.params).slug);
  if (!club) notFound();
  const [audits, buys] = await Promise.all([
    select<VClubAudit>("v_club_audit", { club_id: `eq.${club.id}`, select: "*" }),
    select<VTransfers>("v_transfers", { to_club_id: `eq.${club.id}`, select: "*", order: "date.desc", limit: 300 }),
  ]);
  const all = audits.find((a) => a.period === "all");
  const assessed = buys.filter((t) => t.expected_fee_eur && t.reliability !== "Insufficient");
  const points: FeePoint[] = assessed.map((t) => ({
    player: t.player_name ?? "", date: t.date ?? "", expected: t.expected_fee_eur!, fee: t.fee_eur!,
    tone: FEE_LABELS[t.label ?? ""]?.tone === "discount" ? "discount" : FEE_LABELS[t.label ?? ""]?.tone === "premium" ? "premium" : "within",
  }));
  const ageBand = (a: number | null) => (a == null ? "Unknown" : a < 21 ? "Under 21" : a < 24 ? "21–23" : a < 27 ? "24–26" : a < 30 ? "27–29" : "30+");

  return (
    <div className="space-y-10">
      <div className="space-y-2">
        <p className="text-xs font-medium tracking-widest text-muted-foreground uppercase">Club Transfer Audit</p>
        <h1 className="text-3xl font-semibold tracking-tight">{club.name}</h1>
        <p className="text-sm text-muted-foreground">
          Paid permanent purchases since 2015/16. Price efficiency compares fees with expected fees; it isn&apos;t a measure of sporting success.
        </p>
      </div>

      {all ? (
        <>
          <div className="grid gap-6 sm:grid-cols-4">
            <Stat label="Assessed purchases" value={all.n_assessed} sub={`${seasonLabel(all.season_from)} to ${seasonLabel(all.season_to)}`} />
            <Stat label="Fees paid" value={formatEur(all.total_fee_eur)} sub={`expected ${formatEur(all.total_expected_eur)}`} />
            <Stat label="Price ratio" value={all.price_ratio?.toFixed(2)}
                  sub={all.price_ratio_lo80 != null ? `80% range ${all.price_ratio_lo80.toFixed(2)}–${all.price_ratio_hi80?.toFixed(2)}` : "too few purchases for a range"} />
            <Stat label="Value change after 12 months*" value={formatPctChange(all.outcome_median_mv_change_12m)} sub={`median, ${all.outcome_n} players with an outcome`} />
          </div>
          <Card className="space-y-2">
            <RatioRange ratio={all.price_ratio ?? 1} lo={all.price_ratio_lo80} hi={all.price_ratio_hi80} />
            <div className="flex justify-between text-[11px] text-muted-foreground"><span>Paid less than comparable deals</span><span>1.0 = as expected</span><span>Paid premiums</span></div>
            {!all.ranked && <p className="text-xs text-muted-foreground">Fewer than 8 assessed purchases: not ranked, treat the ratio with caution.</p>}
          </Card>
        </>
      ) : (
        <InsufficientData reason="This club has no purchases assessed by the expected-fee model (2018/19 onwards, with a recent market value)." />
      )}

      {assessed.length > 0 && (
        <div className="grid gap-6 lg:grid-cols-[1.4fr_1fr]">
          <Section title="Fees vs expected fees" description="Each dot is a purchase. Dashed line: fee equals expected fee. Blue: notable discount; amber: notable premium.">
            <Card><FeeScatter points={points} /></Card>
          </Section>
          <Section title="Recruitment patterns" description={`All ${buys.length} paid purchases since 2015/16.`}>
            <Card className="space-y-5">
              <Bars title="Age at signing" data={distribution(buys, (t) => ageBand(t.age))} total={buys.length} />
              <Bars title="Position" data={distribution(buys, (t) => POSITION_GROUPS[t.position_group ?? ""] ?? "Unknown")} total={buys.length} />
              <Bars title="Bought from" data={distribution(buys, (t) => leagueName(t.from_competition_id))} total={buys.length} />
            </Card>
          </Section>
        </div>
      )}

      <Section title="Purchases">
        <Table>
          <thead>
            <tr><Th>Date</Th><Th>Player</Th><Th>From</Th><Th align="right">Fee</Th><Th align="right">Expected</Th><Th align="right">vs expected</Th><Th>Classification</Th></tr>
          </thead>
          <tbody>
            {buys.map((t) => (
              <tr key={t.id} className="hover:bg-surface">
                <Td className="whitespace-nowrap"><Link href={`/transfers/${t.id}`} className="hover:underline">{t.date}</Link></Td>
                <Td className="min-w-40"><Link href={`/players/${t.player_slug}`} className="font-medium hover:underline">{t.player_name}</Link></Td>
                <Td className="text-muted-foreground">{t.from_club_name}</Td>
                <Td align="right" className="font-medium">{formatEur(t.fee_eur)}</Td>
                <Td align="right" className="text-muted-foreground">{formatEur(t.expected_fee_eur)}</Td>
                <Td align="right">{t.expected_fee_eur ? formatPctChange(t.premium_pct) : "–"}</Td>
                <Td>{t.label ? <GapLabel label={t.label} kind="fee" /> : <span className="text-xs text-muted-foreground" title={t.reliability_reason ?? undefined}>Not assessed</span>}</Td>
              </tr>
            ))}
          </tbody>
        </Table>
      </Section>
      <p className="text-xs text-muted-foreground">* Outcome, observed after signing and not used by any model.</p>
    </div>
  );
}
