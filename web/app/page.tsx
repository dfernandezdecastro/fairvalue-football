const DATA_VINTAGE = "Transfermarkt data to 6 Jul 2026 · Understat to 2024/25";

const MODULES = [
  {
    name: "Player Intelligence",
    text: "Performance profiles, percentiles against position peers, and a performance-implied value with its uncertainty range.",
  },
  {
    name: "Transfer Intelligence",
    text: "Fees compared with an expected fee from information public at the time. Notable premiums are flagged only outside the 80% range.",
  },
  {
    name: "Hidden Gems",
    text: "Players whose market value sits below the range their measurable profile usually commands, with a historical backtest.",
  },
  {
    name: "Club Transfer Audit",
    text: "Price efficiency of each club's recruitment, kept separate from sporting outcomes.",
  },
];

export default function Home() {
  return (
    <div className="flex flex-1 flex-col">
      <header className="border-b border-border">
        <div className="mx-auto flex h-14 w-full max-w-6xl items-center justify-between px-4 sm:px-6">
          <span className="text-sm font-semibold tracking-tight">FairValue Football</span>
          <span className="rounded-full border border-border px-2.5 py-0.5 text-xs text-muted-foreground">
            {DATA_VINTAGE}
          </span>
        </div>
      </header>

      <main className="mx-auto w-full max-w-6xl flex-1 px-4 py-16 sm:px-6">
        <p className="text-xs font-medium uppercase tracking-widest text-muted-foreground">
          In development
        </p>
        <h1 className="mt-3 max-w-2xl text-3xl font-semibold tracking-tight sm:text-4xl">
          Where does the market&apos;s price disagree with the evidence, and how sure can we be?
        </h1>
        <p className="mt-4 max-w-2xl text-muted-foreground">
          FairValue compares market valuations and transfer fees with what measurable performance and
          context usually command. Every estimate comes with a range, and we say so when the data is
          too thin to judge.
        </p>

        <ul className="mt-12 grid gap-px overflow-hidden rounded-lg border border-border bg-border sm:grid-cols-2">
          {MODULES.map((m) => (
            <li key={m.name} className="bg-background p-6">
              <h2 className="text-sm font-medium">{m.name}</h2>
              <p className="mt-2 text-sm text-muted-foreground">{m.text}</p>
            </li>
          ))}
        </ul>
      </main>

      <footer className="border-t border-border">
        <div className="mx-auto w-full max-w-6xl px-4 py-6 text-xs text-muted-foreground sm:px-6">
          Non-commercial research project. Transfer and market-value data: Transfermarkt, via the
          community transfermarkt-datasets project. xG data: Understat. Not affiliated with any club or
          data provider.
        </div>
      </footer>
    </div>
  );
}
