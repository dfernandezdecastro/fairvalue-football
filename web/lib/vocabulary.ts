// Controlled vocabulary (PRODUCT_SPEC section 2, rule R1). The ONLY place UI wording for model
// classifications is defined. Labels come from interval positions, never from a gap's sign.

export type Tone = "discount" | "premium" | "within" | "muted";

export interface LabelMeta {
  tone: Tone;
  strength: 0 | 1 | 2; // 0 within, 1 notable (outside 80% range), 2 unusual/strong (outside 95% range)
  short: string; // compact chip text
  explain: string; // one-sentence tooltip
}

/** Player market value vs the performance-implied range (same-league peers, same summer). */
export const GAP_LABELS: Record<string, LabelMeta> = {
  "Strong signal of potential undervaluation": {
    tone: "discount",
    strength: 2,
    short: "Strong undervaluation signal",
    explain: "Market value is below the 95% range for comparable profiles in the same league that summer.",
  },
  "Potential undervaluation": {
    tone: "discount",
    strength: 1,
    short: "Potential undervaluation",
    explain: "Market value is below the 80% range for comparable profiles in the same league that summer.",
  },
  "Within expected range": {
    tone: "within",
    strength: 0,
    short: "Within expected range",
    explain: "Market value sits inside the 80% range for comparable profiles.",
  },
  "Market premium": {
    tone: "premium",
    strength: 1,
    short: "Market premium",
    explain: "The market values this player above the 80% range of his measurable profile.",
  },
  "Unusual market premium": {
    tone: "premium",
    strength: 2,
    short: "Unusual market premium",
    explain: "The market values this player above the 95% range of his measurable profile.",
  },
};

/** Transfer fee vs the expected-fee range. */
export const FEE_LABELS: Record<string, LabelMeta> = {
  "Unusually low fee": {
    tone: "discount",
    strength: 2,
    short: "Unusually low fee",
    explain: "The fee is below the 95% range of fees for comparable deals at that date.",
  },
  "Notable fee discount": {
    tone: "discount",
    strength: 1,
    short: "Notable fee discount",
    explain: "The fee is below the 80% range of fees for comparable deals at that date.",
  },
  "Within expected range": {
    tone: "within",
    strength: 0,
    short: "Within expected range",
    explain: "The fee sits inside the 80% range for comparable deals.",
  },
  "Notable transfer premium": {
    tone: "premium",
    strength: 1,
    short: "Notable transfer premium",
    explain: "The fee is above the 80% range for comparable deals at that date.",
  },
  "Unusual transfer premium": {
    tone: "premium",
    strength: 2,
    short: "Unusual transfer premium",
    explain: "The fee is above the 95% range for comparable deals at that date.",
  },
};

export type Reliability = "High" | "Moderate" | "Low" | "Insufficient";

export const RELIABILITY: Record<Reliability, { level: number; explain: string }> = {
  High: { level: 3, explain: "Strong data coverage. The range is as narrow as this data allows." },
  Moderate: { level: 2, explain: "Usable estimate with some data limitations; read the range, not just the point." },
  Low: { level: 1, explain: "Thin or basic data. Treat as a rough indication only." },
  Insufficient: { level: 0, explain: "Not enough data for a reliable estimate, so none is shown." },
};

/** Always shown alongside premiums and gaps. */
export const UNOBSERVED_FEE_FACTORS = [
  "Contract length and release clauses",
  "Add-ons and payment structure",
  "Competition between buying clubs",
  "Agent fees and personal terms",
  "Injury history and medical results",
];
export const UNOBSERVED_VALUE_FACTORS = [
  "Contract length",
  "Injuries",
  "Reputation and marketability",
  "Club conventions (e.g. players rarely sold)",
];

export const POSITION_GROUPS: Record<string, string> = {
  GK: "Goalkeepers",
  CB: "Centre-backs",
  FB: "Full-backs",
  CM: "Central & defensive midfielders",
  AM_W: "Attacking midfielders & wingers",
  ST: "Strikers",
};

export const METRICS: Record<string, { label: string; short: string; source: "Understat" | "Transfermarkt" }> = {
  npxg_p90: { label: "Non-penalty xG per 90", short: "npxG/90", source: "Understat" },
  xa_p90: { label: "Expected assists per 90", short: "xA/90", source: "Understat" },
  shots_p90: { label: "Shots per 90", short: "Shots/90", source: "Understat" },
  key_passes_p90: { label: "Key passes per 90", short: "Key passes/90", source: "Understat" },
  xg_chain_p90: { label: "xGChain per 90", short: "xGChain/90", source: "Understat" },
  xg_buildup_p90: { label: "xGBuildup per 90", short: "xGBuildup/90", source: "Understat" },
  goals_p90: { label: "Goals per 90", short: "Goals/90", source: "Transfermarkt" },
  assists_p90: { label: "Assists per 90", short: "Assists/90", source: "Transfermarkt" },
  minutes_share: { label: "Share of league minutes", short: "Minutes share", source: "Transfermarkt" },
  starts_share: { label: "Share of league starts", short: "Starts share", source: "Transfermarkt" },
};

export const NOT_MEASURED = ["Dribbles", "Progressive passes and carries", "Tackles and interceptions", "Aerial duels"];
