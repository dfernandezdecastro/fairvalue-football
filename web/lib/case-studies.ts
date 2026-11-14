// The three editorial case studies. Subjects were selected from the data (see PROGRESS.md / D18);
// every figure on the pages is read live from the database.

export const CASE_STUDIES = {
  player: {
    href: "/case-studies/player-valuation",
    kind: "Player valuation",
    title: "Mateus Fernandes: a €15M Premier League regular at 20",
    question: "Why did FairValue value a 20-year-old Premier League regular at roughly twice his market value?",
    playerSlug: "mateus-fernandes-880245",
    season: 2024,
    league: "GB1",
  },
  transfer: {
    href: "/case-studies/transfer-evaluation",
    kind: "Transfer evaluation",
    title: "Alexander Isak to Newcastle: a premium, and what it bought",
    question: "Was €77.5M a reasonable price for Isak in August 2022, judged only on what was known then?",
    transferId: 114793,
  },
  club: {
    href: "/case-studies/club-recruitment",
    kind: "Club recruitment",
    title: "Eintracht Frankfurt: a recruitment model, tested",
    question: "Can FairValue turn a club's own buying pattern into a shortlist, and how did that shortlist age?",
    clubSlug: "eintracht-frankfurt",
    clubId: 24,
    shortlistSeason: 2024,
  },
} as const;
