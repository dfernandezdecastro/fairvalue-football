import type { Metadata } from "next";
import Link from "next/link";
import { Suspense } from "react";

import { FilterForm, NumberField, SelectField } from "@/components/data/filters";
import { EmptyRow, Pagination, Table, Td, Th, ViewTabs } from "@/components/data/table";
import { EstimateRange } from "@/components/domain/estimate-range";
import { GapLabel, ReliabilityBadge } from "@/components/domain/labels";
import { PageSkeleton } from "@/components/shell/page-skeleton";
import { PageHeader } from "@/components/shell/site-chrome";
import { selectPage, type Params } from "@/lib/db/server";
import type { VTransfers } from "@/lib/db/types";
import { formatEur, formatPctChange, seasonLabel } from "@/lib/format";
import { leagueName, MODEL_LEAGUES } from "@/lib/leagues";
import { int, PAGE_SIZE, str, type SearchParams } from "@/lib/params";
import { FEE_LABELS, POSITION_GROUPS } from "@/lib/vocabulary";

export const metadata: Metadata = { title: "Transfer Intelligence" };

const TRANSFER_SEASONS = Array.from({ length: 12 }, (_, i) => 2026 - i);
const BIG5 = ["GB1", "ES1", "L1", "IT1", "FR1"];
const PREMIUM = ["Notable transfer premium", "Unusual transfer premium"];
const DISCOUNT = ["Notable fee discount", "Unusually low fee"];
const quote = (xs: string[]) => `in.(${xs.map((x) => `"${x}"`).join(",")})`;
const leagueFilter = (v: string) => (v === "big5" ? `in.(${BIG5.join(",")})` : v ? `eq.${v}` : undefined);
const leagueOptions = (any: string) => [
  { value: "", label: any }, { value: "big5", label: "Big five" }, ...MODEL_LEAGUES.map((l) => ({ value: l, label: leagueName(l) })),
];

export default function TransfersPage(props: PageProps<"/transfers">) {
  return (
    <>
      <PageHeader
        eyebrow="Transfer Intelligence"
        title="Fees vs expected fees"
        description="Each fee is compared with what deals with comparable public information commanded at the time. A transfer is only labelled when its fee falls outside the 80% range; the gap can reflect contracts, clauses or competition the data can't see."
      />
      <Suspense fallback={<PageSkeleton />}>
        <TransfersBody searchParams={props.searchParams} />
      </Suspense>
    </>
  );
}

async function TransfersBody({ searchParams }: { searchParams: Promise<SearchParams> }) {
  const sp = await searchParams;
  const view = ["premiums", "discounts"].includes(str(sp, "view")) ? str(sp, "view") : "all";
  const season = str(sp, "season", "2025");
  const page = Math.max(1, int(sp, "page", 1)!);
  const cls = str(sp, "class");
  const params: Params = {
    select: "*",
    season: season === "any" ? undefined : `eq.${season}`,
    to_competition_id: leagueFilter(str(sp, "buyer")),
    from_competition_id: leagueFilter(str(sp, "seller")),
    position_group: str(sp, "position") ? `eq.${str(sp, "position")}` : undefined,
    age: int(sp, "age_max") ? `lt.${int(sp, "age_max")! + 1}` : undefined,
    fee_eur: int(sp, "min_fee") ? `gte.${int(sp, "min_fee")! * 1e6}` : undefined,
    reliability: str(sp, "reliability") === "moderate" ? "in.(High,Moderate)" : undefined,
    limit: PAGE_SIZE,
    offset: (page - 1) * PAGE_SIZE,
  };
  if (view === "premiums") Object.assign(params, { label: quote(PREMIUM), order: "premium_pct.desc" });
  else if (view === "discounts") Object.assign(params, { label: quote(DISCOUNT), order: "premium_pct.asc" });
  else {
    params.order = "fee_eur.desc";
    if (cls === "premium") params.label = quote(PREMIUM);
    else if (cls === "discount") params.label = quote(DISCOUNT);
    else if (cls === "within") params.label = "eq.Within expected range";
    else if (cls === "unassessed") params.reliability = "eq.Insufficient";
  }
  const { rows, total } = await selectPage<VTransfers>("v_transfers", params);

  return (
    <div className="space-y-4">
      <ViewTabs path="/transfers" sp={sp} param="view" value={view} tabs={[
        { value: "all", label: "All transfers" },
        { value: "premiums", label: "Largest premiums vs expectation" },
        { value: "discounts", label: "Largest discounts vs expectation" },
      ]} />
      <FilterForm action="/transfers">
        {view !== "all" && <input type="hidden" name="view" value={view} />}
        <SelectField label="Season" name="season" value={season}
                     options={[{ value: "any", label: "All seasons" }, ...TRANSFER_SEASONS.map((s) => ({ value: String(s), label: seasonLabel(s) }))]} />
        <SelectField label="Buying league" name="buyer" value={str(sp, "buyer")} options={leagueOptions("Any")} />
        <SelectField label="Selling league" name="seller" value={str(sp, "seller")} options={leagueOptions("Any")} />
        <SelectField label="Position" name="position" value={str(sp, "position")}
                     options={[{ value: "", label: "Any" }, ...Object.entries(POSITION_GROUPS).map(([value, label]) => ({ value, label }))]} />
        <NumberField label="Max. age" name="age_max" value={int(sp, "age_max")} min={15} max={40} />
        <NumberField label="Min. fee (€M)" name="min_fee" value={int(sp, "min_fee")} min={0} />
        {view === "all" && (
          <SelectField label="Classification" name="class" value={cls} options={[
            { value: "", label: "Any" }, { value: "premium", label: "Notable or unusual premium" },
            { value: "within", label: "Within expected range" }, { value: "discount", label: "Notable or unusual discount" },
            { value: "unassessed", label: "Not assessed" },
          ]} />
        )}
        <SelectField label="Reliability" name="reliability" value={str(sp, "reliability")}
                     options={[{ value: "", label: "Any" }, { value: "moderate", label: "Moderate or high" }]} />
      </FilterForm>

      <Table>
        <thead>
          <tr>
            <Th>Player</Th><Th>Date</Th><Th>From → to</Th><Th align="right">Fee</Th><Th align="right">Value before</Th>
            <Th className="w-52">Expected fee (80% range)</Th><Th align="right">vs expected</Th><Th>Classification</Th><Th>Reliability</Th>
          </tr>
        </thead>
        <tbody>
          {rows.length === 0 && <EmptyRow colSpan={9}>No transfers match these filters.</EmptyRow>}
          {rows.map((t) => {
            const assessed = t.expected_fee_eur && t.lo80_eur && t.hi80_eur;
            return (
              <tr key={t.id} className="hover:bg-surface">
                <Td className="min-w-40">
                  <Link href={`/players/${t.player_slug}`} className="font-medium hover:underline">{t.player_name}</Link>
                  <p className="text-xs text-muted-foreground">{t.age != null ? `${Math.floor(t.age)} · ` : ""}{POSITION_GROUPS[t.position_group ?? ""] ?? ""}</p>
                </Td>
                <Td className="whitespace-nowrap"><Link href={`/transfers/${t.id}`} className="hover:underline">{t.date}</Link></Td>
                <Td className="min-w-48">
                  <span className="text-muted-foreground">{t.from_club_name}</span> → <Link href={`/clubs/${t.to_club_slug}`} className="hover:underline">{t.to_club_name}</Link>
                </Td>
                <Td align="right" className="font-medium">{formatEur(t.fee_eur)}</Td>
                <Td align="right" className="text-muted-foreground">{formatEur(t.mv_before_eur)}</Td>
                <Td className="w-52">
                  {assessed ? (
                    <div className="space-y-0.5">
                      <EstimateRange size="sm" estimate={t.expected_fee_eur!} lo80={t.lo80_eur!} hi80={t.hi80_eur!} actual={t.fee_eur}
                                     tone={FEE_LABELS[t.label ?? ""]?.tone ?? "within"} />
                      <p className="text-[11px] text-muted-foreground">{formatEur(t.expected_fee_eur)} expected</p>
                    </div>
                  ) : <span className="text-xs text-muted-foreground" title={t.reliability_reason ?? undefined}>Not assessed</span>}
                </Td>
                <Td align="right">{assessed ? formatPctChange(t.premium_pct) : "–"}</Td>
                <Td>{t.label ? <GapLabel label={t.label} kind="fee" /> : null}</Td>
                <Td><ReliabilityBadge level={t.reliability} reason={t.reliability_reason} showLabel={false} /></Td>
              </tr>
            );
          })}
        </tbody>
      </Table>
      <Pagination path="/transfers" sp={sp} page={page} total={total} />
    </div>
  );
}
