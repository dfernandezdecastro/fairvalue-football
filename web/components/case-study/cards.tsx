import { ArrowRight } from "lucide-react";
import Link from "next/link";

import { CASE_STUDIES } from "@/lib/case-studies";

const ORDER = [CASE_STUDIES.player, CASE_STUDIES.transfer, CASE_STUDIES.club];

/** The three case studies as editorial cards (case-studies index and homepage). */
export function CaseStudyCards() {
  return (
    <div className="grid gap-4 md:grid-cols-3">
      {ORDER.map((c, i) => (
        <Link key={c.href} href={c.href}
              className="group flex flex-col justify-between gap-6 rounded-lg border bg-card p-5 transition-colors hover:border-foreground/30">
          <div className="space-y-2">
            <p className="text-xs font-medium tracking-widest text-brand uppercase">
              <span className="font-mono">{String(i + 1).padStart(2, "0")}</span> · {c.kind}
            </p>
            <h3 className="text-lg leading-snug font-semibold tracking-tight text-balance">{c.title}</h3>
            <p className="text-sm text-muted-foreground">{c.question}</p>
          </div>
          <span className="inline-flex items-center gap-1.5 text-sm font-medium">
            Read the report <ArrowRight className="size-3.5 transition-transform group-hover:translate-x-0.5" aria-hidden />
          </span>
        </Link>
      ))}
    </div>
  );
}
