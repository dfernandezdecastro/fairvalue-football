import type { Metadata } from "next";
import Link from "next/link";
import { Suspense } from "react";

import { FilterForm, SelectField } from "@/components/data/filters";
import { EmptyRow, Pagination, Table, Td, Th, ViewTabs } from "@/components/data/table";
import { RatioRange } from "@/components/domain/ratio-range";
import { PageSkeleton } from "@/components/shell/page-skeleton";
import { PageHeader } from "@/components/shell/site-chrome";
import { selectPage, type Params } from "@/lib/db/server";
import type { VClubAudit } from "@/lib/db/types";
import { formatEur, formatPctChange, seasonLabel } from "@/lib/format";
import { int, PAGE_SIZE, str, type SearchParams } from "@/lib/params";

export const metadata: Metadata = { title: "Club Transfer Audit" };

const VIEWS: Record<string, { label: string; order: string }> = {
  lowest: { label: "Lowest price ratio", order: "price_ratio_hi80.asc" },
  highest: { label: "Highest price ratio", order: "price_ratio_lo80.desc" },
  spend: { label: "Biggest spenders", order: "total_fee_eur.desc" },
};

export default function ClubsPage(props: PageProps<"/clubs">) {
  return (
    <>
      <PageHeader
        eyebrow="Club Transfer Audit"
        title="Price efficiency by club"
        description="Total fees paid divided by total expected fees for each club's assessed purchases, with an 80% range. Below 1: paid less than comparable deals commanded. This measures price, not sporting success."
      />
      <Suspense fallback={<PageSkeleton />}>
        <ClubsBody searchParams={props.searchParams} />
      </Suspense>
    </>
  );
}

async function ClubsBody({ searchParams }: { searchParams: Promise<SearchParams> }) {
  const sp = await searchParams;
  const view = VIEWS[str(sp, "view")] ? str(sp, "view") : "lowest";
  const period = str(sp, "period") === "last3" ? "last3" : "all";
  const page = Math.max(1, int(sp, "page", 1)!);
  const params: Params = {
    select: "*", period: `eq.${period}`, ranked: "eq.true", order: VIEWS[view].order,
    limit: PAGE_SIZE, offset: (page - 1) * PAGE_SIZE,
  };
  const { rows, total } = await selectPage<VClubAudit>("v_club_audit", params);
  const range = rows[0] ? `${seasonLabel(rows[0].season_from)} to ${seasonLabel(rows[0].season_to)}` : "";

  return (
    <div className="space-y-4">
      <div className="flex flex-wrap items-end justify-between gap-3">
        <ViewTabs path="/clubs" sp={sp} param="view" value={view} tabs={Object.entries(VIEWS).map(([value, v]) => ({ value, label: v.label }))} />
        <FilterForm action="/clubs" className="p-2">
          <input type="hidden" name="view" value={view} />
          <SelectField label="Period" name="period" value={period}
                       options={[{ value: "all", label: "All seasons" }, { value: "last3", label: "Last three seasons" }]} />
        </FilterForm>
      </div>
      <p className="text-xs text-muted-foreground">
        {range && `${range}. `}Clubs with at least 8 assessed purchases. Rankings use the cautious end of the range, so a few lucky deals
        can&apos;t top the table. The range reflects how much the ratio depends on individual deals; each fee&apos;s own model uncertainty
        isn&apos;t included, so the true uncertainty is wider.
      </p>
      <Table>
        <thead>
          <tr>
            <Th>Club</Th><Th align="right">Purchases</Th><Th align="right">Fees paid</Th><Th align="right">Expected fees</Th>
            <Th align="right">Price ratio</Th><Th className="w-48">80% range (log scale, 1.0 = expected)</Th>
            <Th align="right">Notable premiums</Th><Th align="right">Notable discounts</Th><Th align="right">Value change after 12m*</Th>
          </tr>
        </thead>
        <tbody>
          {rows.length === 0 && <EmptyRow colSpan={9}>No clubs to show.</EmptyRow>}
          {rows.map((c) => (
            <tr key={c.club_id} className="hover:bg-surface">
              <Td className="min-w-40"><Link href={`/clubs/${c.club_slug}`} className="font-medium hover:underline">{c.club_name}</Link></Td>
              <Td align="right">{c.n_assessed}</Td>
              <Td align="right">{formatEur(c.total_fee_eur)}</Td>
              <Td align="right" className="text-muted-foreground">{formatEur(c.total_expected_eur)}</Td>
              <Td align="right" className="font-medium">{c.price_ratio?.toFixed(2)}</Td>
              <Td className="w-48"><RatioRange ratio={c.price_ratio ?? 1} lo={c.price_ratio_lo80} hi={c.price_ratio_hi80} /></Td>
              <Td align="right">{Math.round((c.share_notable_premium ?? 0) * 100)}%</Td>
              <Td align="right">{Math.round((c.share_notable_discount ?? 0) * 100)}%</Td>
              <Td align="right" className="text-muted-foreground">{formatPctChange(c.outcome_median_mv_change_12m)}</Td>
            </tr>
          ))}
        </tbody>
      </Table>
      <p className="text-xs text-muted-foreground">
        * Outcome, observed after signing and not used by any model: median change in market value about 12 months after the move.
      </p>
      <Pagination path="/clubs" sp={sp} page={page} total={total} />
    </div>
  );
}
