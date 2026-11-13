import Link from "next/link";

import { hrefWith, PAGE_SIZE, type SearchParams } from "@/lib/params";
import { cn } from "@/lib/utils";

export function Table({ children, className }: { children: React.ReactNode; className?: string }) {
  return (
    <div className={cn("overflow-x-auto rounded-lg border", className)}>
      <table className="w-full min-w-[720px] border-collapse text-sm tabular">{children}</table>
    </div>
  );
}

export function Th({ children, className, align = "left" }: { children?: React.ReactNode; className?: string; align?: "left" | "right" }) {
  return (
    <th className={cn("border-b bg-surface px-3 py-2 text-xs font-medium whitespace-nowrap text-muted-foreground",
                      align === "right" ? "text-right" : "text-left", className)}>
      {children}
    </th>
  );
}

export function Td({ children, className, align = "left" }: { children?: React.ReactNode; className?: string; align?: "left" | "right" }) {
  return <td className={cn("border-b px-3 py-2 align-middle", align === "right" && "text-right", className)}>{children}</td>;
}

export function EmptyRow({ colSpan, children }: { colSpan: number; children: React.ReactNode }) {
  return (
    <tr>
      <td colSpan={colSpan} className="px-3 py-10 text-center text-sm text-muted-foreground">{children}</td>
    </tr>
  );
}

export function Pagination({ path, sp, page, total }: { path: string; sp: SearchParams; page: number; total: number }) {
  const pages = Math.max(1, Math.ceil(total / PAGE_SIZE));
  if (pages <= 1) return <p className="text-xs text-muted-foreground">{total.toLocaleString("en-GB")} results</p>;
  const link = (p: number, label: string, disabled: boolean) =>
    disabled ? (
      <span className="rounded-md border px-2.5 py-1 text-muted-foreground/50">{label}</span>
    ) : (
      <Link href={hrefWith(path, sp, { page: p === 1 ? undefined : p })} scroll={false}
            className="rounded-md border px-2.5 py-1 hover:bg-accent">{label}</Link>
    );
  return (
    <div className="flex items-center justify-between gap-3 text-xs text-muted-foreground">
      <span>
        {total.toLocaleString("en-GB")} results · page {page} of {pages}
      </span>
      <span className="flex gap-2">
        {link(page - 1, "Previous", page <= 1)}
        {link(page + 1, "Next", page >= pages)}
      </span>
    </div>
  );
}

/** Tab-like links that change one URL param. */
export function ViewTabs({ path, sp, param, value, tabs }: {
  path: string; sp: SearchParams; param: string; value: string; tabs: { value: string; label: string }[];
}) {
  return (
    <div className="inline-flex rounded-lg border bg-surface p-0.5 text-sm" role="tablist">
      {tabs.map((t) => (
        <Link key={t.value} role="tab" aria-selected={t.value === value} scroll={false}
              href={hrefWith(path, sp, { [param]: t.value, page: undefined })}
              className={cn("rounded-md px-3 py-1 whitespace-nowrap",
                            t.value === value ? "bg-background text-foreground shadow-sm" : "text-muted-foreground hover:text-foreground")}>
          {t.label}
        </Link>
      ))}
    </div>
  );
}
