import { PageHeader } from "@/components/shell/site-chrome";
import { InsufficientData } from "@/components/domain/profile";

/** Temporary page body for routes built in Step 8 (states clearly that the page isn't built yet). */
export function InProgress({ title, description }: { title: string; description: string }) {
  return (
    <>
      <PageHeader eyebrow="Coming in the next build step" title={title} description={description} />
      <InsufficientData
        title="This page is being built"
        reason="The data and models behind it are ready; the page itself is the next development step."
      />
    </>
  );
}
