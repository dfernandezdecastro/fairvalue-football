import { Skeleton } from "@/components/ui/skeleton";

/** Placeholder shaped like a page header plus content blocks (used by loading.tsx and Suspense fallbacks). */
export function PageSkeleton() {
  return (
    <div className="space-y-8" aria-busy="true" aria-label="Loading">
      <div className="space-y-3">
        <Skeleton className="h-3 w-24" />
        <Skeleton className="h-8 w-80 max-w-full" />
        <Skeleton className="h-4 w-[32rem] max-w-full" />
      </div>
      <div className="grid gap-4 md:grid-cols-3">
        <Skeleton className="h-28" />
        <Skeleton className="h-28" />
        <Skeleton className="h-28" />
      </div>
      <Skeleton className="h-64" />
    </div>
  );
}
