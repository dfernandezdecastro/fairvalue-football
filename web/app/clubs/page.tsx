import type { Metadata } from "next";

import { InProgress } from "@/components/shell/in-progress";

export const metadata: Metadata = { title: "Club Transfer Audit" };

export default function Page() {
  return <InProgress title="Club Transfer Audit" description="How each club's fees compare with expected fees, kept separate from sporting outcomes." />;
}
