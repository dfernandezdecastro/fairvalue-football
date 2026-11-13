import type { Metadata } from "next";
import Link from "next/link";
import { Suspense } from "react";

import { FilterForm, NumberField, SelectField } from "@/components/data/filters";
import { EmptyRow, Pagination, Table, Td, Th } from "@/components/data/table";
import { EstimateRange } from "@/components/domain/estimate-range";
import { GapLabel, ReliabilityBadge } from "@/components/domain/labels";
import { DataTierPill } from "@/components/domain/profile";
import { PageSkeleton } from "@/components/shell/page-skeleton";
import { PageHeader } from "@/components/shell/site-chrome";
import { selectPage, type Params } from "@/lib/db/server";
import type { VPlayerSeason } from "@/lib/db/types";
import { formatEur, formatNumber, seasonLabel } from "@/lib/format";
import { leagueName, MODEL_LEAGUES, SEASONS } from "@/lib/leagues";
import { int, PAGE_SIZE, str, type SearchParams } from "@/lib/params";
import { GAP_LABELS, POSITION_GROUPS } from "@/lib/vocabulary";

export const metadata: Metadata = { title: "Players" };


const BIG5 = ["GB1", "ES1", "L1", "IT1", "FR1"];
const SORTS: Record<string, { label: string; order: string }> = {
  value: { label: "Market value (high to low)", order: "market_value_eur.desc.nullslast" },
  gap: { label: "Largest potential undervaluation first", order: "gap_log.asc.nullslast" },
  implied: { label: "Performance-implied value", order: "peer_estimate_eur.desc.nullslast" },
  minutes: { label: "Minutes", order: "minutes.desc" },
  age: { label: "Youngest first", order: "age.asc" },
};
const LABEL_GROUPS: Record<string, string[]> = {
  under: ["Potential undervaluation", "Strong signal of potential undervaluation"],
  premium: ["Market premium", "Unusual market premium"],
  within: ["Within expected range"],
};
const quote = (xs: string[]) => `in.(${xs.map((x) => `"${x}"`).join(",")})`;

export default function PlayersPage(props: PageProps<"/players">) {
  return (
    <>
      <PageHeader
        eyebrow="Player Intelligence"
        title="Players"
        description="Every player-season with 900+ league minutes in the 14 covered leagues: market value against the range comparable profiles carry in the same league and summer."
      />
      <Suspense fallback={<PageSkeleton />}>
        <PlayersBody searchParams={props.searchParams} />
      </Suspense>
    </>
  );
}

async function PlayersBody({ searchParams }: { searchParams: Promise<SearchParams> }) {
  const sp = await searchParams;
  const season = int(sp, "season", 2025)!;
  const league = str(sp, "league", "big5");
  const position = str(sp, "position");
  const label = str(sp, "label");
  const reliability = str(sp, "reliability");
  const sort = SORTS[str(sp, "sort", "value")] ? str(sp, "sort", "value") : "value";
  const page = Math.max(1, int(sp, "page", 1)!);

  const params: Params = {
    select: "*",
    eligible: "eq.true",
    season: `eq.${season}`,
    competition_id: league === "big5" ? `in.(${BIG5.join(",")})` : league === "all" ? undefined : `eq.${league}`,
    position_group: position ? `eq.${position}` : "neq.GK",
    age: [int(sp, "age_min") ? `gte.${int(sp, "age_min")}` : undefined, int(sp, "age_max") ? `lt.${int(sp, "age_max")! + 1}` : undefined],
    minutes: `gte.${int(sp, "min_minutes", 900)}`,
    gap_label: LABEL_GROUPS[label] ? quote(LABEL_GROUPS[label]) : undefined,
    reliability: reliability === "high" ? "eq.High" : reliability === "moderate" ? "in.(High,Moderate)" : undefined,
    order: SORTS[sort].order,
    limit: PAGE_SIZE,
    offset: (page - 1) * PAGE_SIZE,
  };
  const { rows, total } = await selectPage<VPlayerSeason>("v_player_season", params);

  return (
    <div className="space-y-4">
      <FilterForm action="/players">
        <SelectField label="Season" name="season" value={String(season)}
                     options={SEASONS.map((s) => ({ value: String(s), label: `${seasonLabel(s)}${s === 2025 ? " (basic data)" : ""}` }))} />
        <SelectField label="League" name="league" value={league}
                     options={[{ value: "big5", label: "Big five" }, { value: "all", label: "All 14 leagues" },
                               ...MODEL_LEAGUES.map((l) => ({ value: l, label: leagueName(l) }))]} />
        <SelectField label="Position" name="position" value={position}
                     options={[{ value: "", label: "All outfield" }, ...Object.entries(POSITION_GROUPS).filter(([k]) => k !== "GK").map(([value, label]) => ({ value, label }))]} />
        <NumberField label="Age from" name="age_min" value={int(sp, "age_min")} min={15} max={40} placeholder="15" />
        <NumberField label="Age to" name="age_max" value={int(sp, "age_max")} min={15} max={40} placeholder="40" />
        <NumberField label="Min. minutes" name="min_minutes" value={int(sp, "min_minutes", 900)} min={900} step={100} />
        <SelectField label="Valuation gap" name="label" value={label}
                     options={[{ value: "", label: "Any" }, { value: "under", label: "Potential undervaluation" },
                               { value: "within", label: "Within expected range" }, { value: "premium", label: "Market premium" }]} />
        <SelectField label="Reliability" name="reliability" value={reliability}
                     options={[{ value: "", label: "Any" }, { value: "moderate", label: "Moderate or high" }, { value: "high", label: "High only" }]} />
        <SelectField label="Sort" name="sort" value={sort} options={Object.entries(SORTS).map(([value, s]) => ({ value, label: s.label }))} />
      </FilterForm>

      <Table>
        <thead>
          <tr>
            <Th>Player</Th><Th align="right">Age</Th><Th>League</Th><Th align="right">Minutes</Th>
            <Th align="right">Market value</Th><Th className="w-56">Performance-implied (80% range)</Th><Th>Gap</Th><Th>Reliability</Th>
          </tr>
        </thead>
        <tbody>
          {rows.length === 0 && <EmptyRow colSpan={8}>No player-seasons match these filters. Try widening the age range or league.</EmptyRow>}
          {rows.map((r) => {
            const ok = r.reliability !== "Insufficient" && r.peer_estimate_eur && r.peer_lo80_eur && r.peer_hi80_eur;
            return (
              <tr key={`${r.player_id}-${r.competition_id}`} className="hover:bg-surface">
                <Td className="min-w-48">
                  <Link href={`/players/${r.player_slug}?season=${r.season}&league=${r.competition_id}`} className="font-medium hover:underline">
                    {r.player_name}
                  </Link>
                  <p className="text-xs text-muted-foreground">{r.club_name} · {POSITION_GROUPS[r.position_group ?? ""]}</p>
                </Td>
                <Td align="right">{r.age != null ? Math.floor(r.age) : "–"}</Td>
                <Td className="whitespace-nowrap">{leagueName(r.competition_id)} {r.data_tier === "full" ? null : <DataTierPill tier={r.data_tier} />}</Td>
                <Td align="right">{formatNumber(r.minutes)}</Td>
                <Td align="right" className="font-medium">{formatEur(r.market_value_eur)}</Td>
                <Td className="w-56">
                  {ok ? (
                    <div className="space-y-0.5">
                      <EstimateRange size="sm" estimate={r.peer_estimate_eur!} lo80={r.peer_lo80_eur!} hi80={r.peer_hi80_eur!}
                                     actual={r.market_value_eur} tone={GAP_LABELS[r.gap_label ?? ""]?.tone ?? "within"} />
                      <p className="text-[11px] text-muted-foreground">{formatEur(r.peer_estimate_eur)} implied</p>
                    </div>
                  ) : <span className="text-xs text-muted-foreground" title={r.reliability_reason ?? undefined}>No reliable estimate</span>}
                </Td>
                <Td>{ok && r.gap_label ? <GapLabel label={r.gap_label} /> : null}</Td>
                <Td><ReliabilityBadge level={r.reliability} reason={r.reliability_reason} showLabel={false} /></Td>
              </tr>
            );
          })}
        </tbody>
      </Table>
      <Pagination path="/players" sp={sp} page={page} total={total} />
    </div>
  );
}
