// Display names for domestic leagues (Transfermarkt ids). Source names are URL slugs.
export const LEAGUES: Record<string, { name: string; country: string; big5?: boolean }> = {
  GB1: { name: "Premier League", country: "England", big5: true },
  ES1: { name: "LaLiga", country: "Spain", big5: true },
  L1: { name: "Bundesliga", country: "Germany", big5: true },
  IT1: { name: "Serie A", country: "Italy", big5: true },
  FR1: { name: "Ligue 1", country: "France", big5: true },
  NL1: { name: "Eredivisie", country: "Netherlands" },
  PO1: { name: "Liga Portugal", country: "Portugal" },
  BE1: { name: "Belgian Pro League", country: "Belgium" },
  TR1: { name: "Süper Lig", country: "Türkiye" },
  RU1: { name: "Russian Premier League", country: "Russia" },
  SC1: { name: "Scottish Premiership", country: "Scotland" },
  GR1: { name: "Greek Super League", country: "Greece" },
  DK1: { name: "Danish Superliga", country: "Denmark" },
  UKR1: { name: "Ukrainian Premier League", country: "Ukraine" },
  A1: { name: "Austrian Bundesliga", country: "Austria" },
  C1: { name: "Swiss Super League", country: "Switzerland" },
  KR1: { name: "Croatian HNL", country: "Croatia" },
  TS1: { name: "Czech First League", country: "Czech Republic" },
  PL1: { name: "Ekstraklasa", country: "Poland" },
  RO1: { name: "Romanian Superliga", country: "Romania" },
  SER1: { name: "Serbian SuperLiga", country: "Serbia" },
  NO1: { name: "Eliteserien", country: "Norway" },
  SE1: { name: "Allsvenskan", country: "Sweden" },
  SA1: { name: "Saudi Pro League", country: "Saudi Arabia" },
  MLS1: { name: "MLS", country: "United States" },
  BRA1: { name: "Brasileirão", country: "Brazil" },
  ARG1: { name: "Argentine Primera", country: "Argentina" },
  MEX1: { name: "Liga MX", country: "Mexico" },
  JAP1: { name: "J1 League", country: "Japan" },
  RSK1: { name: "K League 1", country: "South Korea" },
  AUS1: { name: "A-League", country: "Australia" },
};

/** The 14 leagues with full history (model coverage), in display order. */
export const MODEL_LEAGUES = ["GB1", "ES1", "L1", "IT1", "FR1", "NL1", "PO1", "BE1", "TR1", "RU1", "SC1", "GR1", "DK1", "UKR1"];

export function leagueName(id: string | null | undefined): string {
  if (!id) return "Outside covered leagues";
  return LEAGUES[id]?.name ?? id;
}

/** Seasons with published data, newest first (start years: 2025 = 2025/26). */
export const SEASONS = Array.from({ length: 12 }, (_, i) => 2025 - i);
