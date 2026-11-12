"use client";

import { RotateCw } from "lucide-react";

// Route-level error boundary: a failed query never blanks the whole site.
export default function Error({ error, reset }: { error: Error & { digest?: string }; reset: () => void }) {
  const notConfigured = error.message.includes("not configured");
  return (
    <div className="mx-auto max-w-lg space-y-4 py-16 text-center">
      <h1 className="text-xl font-semibold">{notConfigured ? "Data source not configured" : "Something went wrong"}</h1>
      <p className="text-sm text-muted-foreground">
        {notConfigured
          ? "The database connection isn't set up in this environment. See docs/SUPABASE_SETUP.md."
          : "This page couldn't load its data. It's usually temporary."}
      </p>
      {!notConfigured && (
        <button
          type="button"
          onClick={reset}
          className="inline-flex items-center gap-2 rounded-md border px-3 py-1.5 text-sm hover:bg-accent"
        >
          <RotateCw className="size-3.5" aria-hidden /> Try again
        </button>
      )}
    </div>
  );
}
