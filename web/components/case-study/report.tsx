import { AlertTriangle, History } from "lucide-react";
import Link from "next/link";

import { cn } from "@/lib/utils";

/** Editorial building blocks for the case-study reports (consistent across all three). */

export function ReportHeader({
  kind, title, standfirst, meta,
}: { kind: string; title: string; standfirst: string; meta: { label: string; value: React.ReactNode }[] }) {
  return (
    <header className="space-y-6 border-b pb-10">
      <div className="space-y-3">
        <p className="text-xs font-medium tracking-widest text-brand uppercase">
          <Link href="/case-studies" className="hover:underline">Case study</Link> · {kind}
        </p>
        <h1 className="max-w-4xl text-3xl font-semibold tracking-tight text-balance sm:text-4xl">{title}</h1>
        <p className="max-w-3xl text-base text-muted-foreground sm:text-lg">{standfirst}</p>
      </div>
      <dl className="grid gap-x-8 gap-y-3 text-sm sm:grid-cols-2 lg:grid-cols-4">
        {meta.map((m) => (
          <div key={m.label} className="space-y-0.5">
            <dt className="text-xs text-muted-foreground">{m.label}</dt>
            <dd className="font-medium tabular">{m.value}</dd>
          </div>
        ))}
      </dl>
    </header>
  );
}

/** A lettered report section (A, B, C…) with a narrow prose column and an optional wide figure area. */
export function ReportSection({
  letter, title, children, className,
}: { letter: string; title: string; children: React.ReactNode; className?: string }) {
  return (
    <section className={cn("grid gap-6 border-b py-10 lg:grid-cols-[12rem_1fr]", className)}>
      <div className="flex items-baseline gap-3 lg:block lg:space-y-1">
        <span className="font-mono text-xs text-brand">{letter}</span>
        <h2 className="text-lg font-semibold tracking-tight">{title}</h2>
      </div>
      <div className="min-w-0 space-y-5">{children}</div>
    </section>
  );
}

export function Prose({ children }: { children: React.ReactNode }) {
  return <div className="max-w-3xl space-y-3 text-[15px] leading-relaxed text-foreground/90">{children}</div>;
}

/** The key takeaway of a section, visually distinct. */
export function Finding({ title = "Finding", children }: { title?: string; children: React.ReactNode }) {
  return (
    <div className="max-w-3xl rounded-lg border-l-2 border-brand bg-surface px-5 py-4">
      <p className="text-xs font-medium tracking-wide text-brand uppercase">{title}</p>
      <div className="mt-1 text-[15px] leading-relaxed">{children}</div>
    </div>
  );
}

/** Information observed AFTER the reference date: never used by the model, always visibly separated. */
export function Hindsight({ title, children }: { title: string; children: React.ReactNode }) {
  return (
    <div className="space-y-3 rounded-lg border border-dashed p-5">
      <p className="inline-flex items-center gap-2 text-xs font-medium tracking-wide text-muted-foreground uppercase">
        <History className="size-3.5" aria-hidden /> Hindsight · observed afterwards, not used by the model
      </p>
      <p className="font-medium">{title}</p>
      <div className="space-y-2 text-sm text-muted-foreground">{children}</div>
    </div>
  );
}

export function Limitations({ items }: { items: string[] }) {
  return (
    <ul className="max-w-3xl space-y-2 text-[15px] text-foreground/90">
      {items.map((i) => (
        <li key={i} className="flex gap-3">
          <span aria-hidden className="mt-2 size-1.5 shrink-0 rounded-full bg-muted-foreground" />
          <span>{i}</span>
        </li>
      ))}
    </ul>
  );
}

/**
 * Data-integrity guard: the narrative was written against specific facts. Each fact is re-checked against the
 * live database on every render; if any no longer holds, the page says so instead of silently drifting.
 */
export function IntegrityNotice({ checks }: { checks: { claim: string; ok: boolean }[] }) {
  const failed = checks.filter((c) => !c.ok);
  if (!failed.length) {
    return (
      <p className="text-xs text-muted-foreground">
        All {checks.length} facts this report relies on were re-checked against the database when this page loaded.
      </p>
    );
  }
  return (
    <div className="flex gap-3 rounded-lg border border-premium/40 bg-premium-soft p-4 text-sm" role="alert">
      <AlertTriangle className="mt-0.5 size-4 shrink-0 text-premium" aria-hidden />
      <div>
        <p className="font-medium">The data has changed since this case study was written</p>
        <p className="text-muted-foreground">No longer true: {failed.map((f) => f.claim).join("; ")}. Figures shown are live; the narrative may be out of date.</p>
      </div>
    </div>
  );
}

export function ReportFooter({ next }: { next?: { href: string; label: string } }) {
  return (
    <div className="flex flex-wrap items-center justify-between gap-4 py-10 text-sm">
      <Link href="/case-studies" className="text-muted-foreground hover:text-foreground">← All case studies</Link>
      {next && <Link href={next.href} className="font-medium hover:underline">Next: {next.label} →</Link>}
    </div>
  );
}
