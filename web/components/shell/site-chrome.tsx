import Link from "next/link";
import { Suspense } from "react";

import { NavLinks, NavLinksStatic, ThemeToggle } from "@/components/shell/nav";
import { SearchCommand } from "@/components/shell/search-command";

export const DATA_VINTAGE = "Data to 6 Jul 2026 · xG to 2024/25";

export function SiteHeader() {
  return (
    <header className="sticky top-0 z-40 border-b bg-background/85 backdrop-blur supports-[backdrop-filter]:bg-background/70">
      <div className="mx-auto flex h-14 w-full max-w-7xl items-center gap-4 px-4 sm:px-6">
        <Link href="/" className="flex items-center gap-2 text-sm font-semibold tracking-tight whitespace-nowrap">
          <span aria-hidden className="grid size-5 place-items-center rounded bg-brand text-[10px] font-bold text-background">
            FV
          </span>
          FairValue
        </Link>
        <Suspense fallback={<NavLinksStatic className="hidden md:flex" />}>
          <NavLinks className="hidden md:flex" />
        </Suspense>
        <div className="ml-auto flex items-center gap-2">
          <Link
            href="/methodology#data"
            className="hidden rounded-full border px-2.5 py-0.5 text-xs text-muted-foreground hover:text-foreground lg:inline"
            title="Frozen snapshot: see Methodology for coverage and sources"
          >
            {DATA_VINTAGE}
          </Link>
          <SearchCommand />
          <ThemeToggle />
        </div>
      </div>
      <Suspense fallback={<NavLinksStatic className="overflow-x-auto px-3 pb-2 [scrollbar-width:none] md:hidden [&::-webkit-scrollbar]:hidden" />}>
        <NavLinks className="overflow-x-auto px-3 pb-2 [scrollbar-width:none] md:hidden [&::-webkit-scrollbar]:hidden" />
      </Suspense>
    </header>
  );
}

export function SiteFooter() {
  return (
    <footer className="mt-16 border-t">
      <div className="mx-auto grid w-full max-w-7xl gap-2 px-4 py-6 text-xs text-muted-foreground sm:px-6">
        <p>
          Non-commercial research project. Transfer and market-value data: Transfermarkt, via the community
          transfermarkt-datasets project. xG data: Understat. Not affiliated with any club or data provider.
        </p>
        <p>
          Estimates are statistical signals with uncertainty ranges, not verdicts on players, clubs or transfers.{" "}
          <Link href="/methodology" className="underline underline-offset-2 hover:text-foreground">
            How it works
          </Link>
        </p>
      </div>
    </footer>
  );
}

/** Consistent page header used by every page. */
export function PageHeader({ eyebrow, title, description, children }: {
  eyebrow?: string; title: string; description?: React.ReactNode; children?: React.ReactNode;
}) {
  return (
    <div className="flex flex-wrap items-end justify-between gap-4 pb-8">
      <div className="max-w-3xl space-y-2">
        {eyebrow && <p className="text-xs font-medium tracking-widest text-muted-foreground uppercase">{eyebrow}</p>}
        <h1 className="text-2xl font-semibold tracking-tight sm:text-3xl">{title}</h1>
        {description && <p className="text-sm text-muted-foreground sm:text-base">{description}</p>}
      </div>
      {children}
    </div>
  );
}

export function Section({ title, description, children, className }: {
  title?: string; description?: React.ReactNode; children: React.ReactNode; className?: string;
}) {
  return (
    <section className={className ? `space-y-4 ${className}` : "space-y-4"}>
      {(title || description) && (
        <div className="space-y-1">
          {title && <h2 className="text-sm font-semibold">{title}</h2>}
          {description && <p className="text-sm text-muted-foreground">{description}</p>}
        </div>
      )}
      {children}
    </section>
  );
}

export function Card({ children, className }: { children: React.ReactNode; className?: string }) {
  return <div className={`rounded-lg border bg-card p-5 ${className ?? ""}`}>{children}</div>;
}
