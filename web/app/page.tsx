import Link from "next/link";

import { PageHeader } from "@/components/shell/site-chrome";

const MODULES = [
  { href: "/players", name: "Player Intelligence", text: "Performance profiles against position peers, and a performance-implied value with its uncertainty range." },
  { href: "/transfers", name: "Transfer Intelligence", text: "Fees compared with an expected fee from information public at the time. Labels only outside the 80% range." },
  { href: "/hidden-gems", name: "Hidden Gems", text: "Players whose market value sits below the range their measurable profile usually commands, with a historical backtest." },
  { href: "/clubs", name: "Club Transfer Audit", text: "Price efficiency of each club's recruitment, kept separate from sporting outcomes." },
];

export default function Home() {
  return (
    <>
      <PageHeader
        eyebrow="Market overview · in development"
        title="Where does the market's price disagree with the evidence, and how sure can we be?"
        description="FairValue compares market valuations and transfer fees with what measurable performance and context usually command. Every estimate comes with a range, and we say so when the data is too thin to judge."
      />
      <ul className="grid gap-px overflow-hidden rounded-lg border bg-border sm:grid-cols-2">
        {MODULES.map((m) => (
          <li key={m.name}>
            <Link href={m.href} className="block h-full bg-background p-6 transition-colors hover:bg-surface">
              <h2 className="text-sm font-medium">{m.name}</h2>
              <p className="mt-2 text-sm text-muted-foreground">{m.text}</p>
            </Link>
          </li>
        ))}
      </ul>
    </>
  );
}
