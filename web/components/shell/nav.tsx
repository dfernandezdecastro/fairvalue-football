"use client";

import { Moon, Sun } from "lucide-react";
import Link from "next/link";
import { usePathname } from "next/navigation";

import { cn } from "@/lib/utils";

export const NAV = [
  { href: "/players", label: "Players" },
  { href: "/transfers", label: "Transfers" },
  { href: "/hidden-gems", label: "Hidden Gems" },
  { href: "/clubs", label: "Clubs" },
  { href: "/methodology", label: "Methodology" },
];

export function NavLinks({ className }: { className?: string }) {
  return <NavLinksInner className={className} path={usePathname()} />;
}

/** Shown while the active-path version streams in (usePathname needs a Suspense boundary). */
export function NavLinksStatic({ className }: { className?: string }) {
  return <NavLinksInner className={className} path="" />;
}

function NavLinksInner({ className, path }: { className?: string; path: string }) {
  return (
    <nav className={cn("flex items-center gap-1", className)} aria-label="Main">
      {NAV.map((item) => {
        const active = path === item.href || path.startsWith(`${item.href}/`);
        return (
          <Link
            key={item.href}
            href={item.href}
            aria-current={active ? "page" : undefined}
            className={cn(
              "rounded-md px-2.5 py-1.5 text-sm whitespace-nowrap transition-colors",
              active ? "bg-accent text-foreground" : "text-muted-foreground hover:text-foreground",
            )}
          >
            {item.label}
          </Link>
        );
      })}
    </nav>
  );
}

/** Light/dark toggle. The initial class is set before paint by the inline script in layout.tsx. */
export function ThemeToggle() {
  const toggle = () => {
    const dark = !document.documentElement.classList.contains("dark");
    document.documentElement.classList.toggle("dark", dark);
    try {
      localStorage.setItem("theme", dark ? "dark" : "light");
    } catch {
      /* storage unavailable: theme still switches for this visit */
    }
  };
  return (
    <button
      type="button"
      onClick={toggle}
      className="inline-flex size-8 items-center justify-center rounded-md text-muted-foreground transition-colors hover:text-foreground"
      aria-label="Toggle light and dark theme"
    >
      <Sun className="hidden size-4 dark:block" aria-hidden />
      <Moon className="size-4 dark:hidden" aria-hidden />
    </button>
  );
}
