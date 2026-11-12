import type { Metadata } from "next";

import { InProgress } from "@/components/shell/in-progress";

export const metadata: Metadata = { title: "Transfer Intelligence" };

export default function Page() {
  return <InProgress title="Transfer Intelligence" description="Fees compared with an expected fee from information public at the time of the transfer." />;
}
