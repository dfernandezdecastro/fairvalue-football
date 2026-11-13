"use client";

import { useRouter } from "next/navigation";
import { useRef } from "react";

import { cn } from "@/lib/utils";

/**
 * A GET form whose fields auto-submit on change: filters live in the URL (shareable, bookmarkable)
 * and the page re-renders on the server. Works without JavaScript via the Apply button.
 */
export function FilterForm({ action, children, className }: { action: string; children: React.ReactNode; className?: string }) {
  const ref = useRef<HTMLFormElement>(null);
  const router = useRouter();
  const submit = () => {
    const form = ref.current;
    if (!form) return;
    const qs = new URLSearchParams();
    new FormData(form).forEach((v, k) => {
      if (typeof v === "string" && v !== "") qs.append(k, v);
    });
    const s = qs.toString();
    router.push(s ? `${action}?${s}` : action, { scroll: false });
  };
  return (
    <form
      ref={ref}
      action={action}
      method="get"
      onChange={submit}
      onSubmit={(e) => {
        e.preventDefault();
        submit();
      }}
      className={cn("flex flex-wrap items-end gap-3 rounded-lg border bg-surface p-3", className)}
    >
      {children}
      <noscript>
        <button type="submit" className="h-8 rounded-md border px-3 text-sm">Apply</button>
      </noscript>
    </form>
  );
}

const field = "h-8 rounded-md border bg-background px-2 text-sm text-foreground outline-none focus-visible:ring-2 focus-visible:ring-ring";

export function SelectField({
  label, name, value, options, className,
}: { label: string; name: string; value: string; options: { value: string; label: string }[]; className?: string }) {
  return (
    <label className={cn("grid gap-1 text-xs text-muted-foreground", className)}>
      {label}
      <select name={name} defaultValue={value} className={cn(field, "pr-7")}>
        {options.map((o) => (
          <option key={o.value} value={o.value}>{o.label}</option>
        ))}
      </select>
    </label>
  );
}

export function NumberField({
  label, name, value, min, max, step, placeholder, className,
}: { label: string; name: string; value?: number | string; min?: number; max?: number; step?: number; placeholder?: string; className?: string }) {
  return (
    <label className={cn("grid gap-1 text-xs text-muted-foreground", className)}>
      {label}
      <input type="number" name={name} defaultValue={value} min={min} max={max} step={step} placeholder={placeholder}
             className={cn(field, "w-24 tabular")} />
    </label>
  );
}
