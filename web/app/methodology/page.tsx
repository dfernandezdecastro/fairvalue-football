import type { Metadata } from "next";

import { InProgress } from "@/components/shell/in-progress";

export const metadata: Metadata = { title: "Methodology" };

export default function Page() {
  return <InProgress title="Methodology" description="Data, models, uncertainty and limitations, explained." />;
}
