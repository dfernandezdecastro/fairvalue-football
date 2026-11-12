import type { Metadata } from "next";

import { InProgress } from "@/components/shell/in-progress";

export const metadata: Metadata = { title: "Players" };

export default function Page() {
  return <InProgress title="Players" description="Explore player-seasons with performance profiles and performance-implied values." />;
}
