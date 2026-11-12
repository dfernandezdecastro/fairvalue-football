import type { Metadata } from "next";

import { InProgress } from "@/components/shell/in-progress";

export const metadata: Metadata = { title: "Hidden Gems" };

export default function Page() {
  return <InProgress title="Hidden Gems" description="Players whose market value sits below the range their measurable profile usually commands." />;
}
