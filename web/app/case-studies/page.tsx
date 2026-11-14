import type { Metadata } from "next";
import Link from "next/link";

import { CaseStudyCards } from "@/components/case-study/cards";
import { PageHeader } from "@/components/shell/site-chrome";

export const metadata: Metadata = {
  title: "Case studies",
  description: "Three worked examples of FairValue in use: a player valuation, a transfer evaluation and a club recruitment screen.",
};

export default function CaseStudiesPage() {
  return (
    <div className="space-y-10 pb-10">
      <PageHeader
        eyebrow="Case studies"
        title="Three questions, answered with the data"
        description="Each report follows one real case from the database: what was known at the time, what FairValue estimated and why, how uncertain that was, and (kept separate) what happened afterwards. Every figure is read live, and each report re-checks the facts its narrative relies on."
      />
      <CaseStudyCards />
      <div className="max-w-3xl space-y-2 border-t pt-8 text-sm text-muted-foreground">
        <p className="font-medium text-foreground">How the subjects were chosen</p>
        <p>
          Cases were picked from the data for what they teach, not for flattering outcomes: each has a clear, high- or
          moderate-reliability estimate made strictly before the event, enough later data to show what happened, and at least one
          honest complication. Outcomes are shown for context; a single case can&apos;t validate a model, which is what the{" "}
          <Link href="/methodology#backtest" className="underline underline-offset-2">backtest</Link> is for.
        </p>
      </div>
    </div>
  );
}
