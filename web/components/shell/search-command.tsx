"use client";

import { Search, Shield, User } from "lucide-react";
import { useRouter } from "next/navigation";
import { useEffect, useState } from "react";

import {
  Command, CommandDialog, CommandEmpty, CommandGroup, CommandInput, CommandItem, CommandList,
} from "@/components/ui/command";

interface Results {
  players: { name: string; slug: string; sub_position: string | null; birth_year: number | null }[];
  clubs: { name: string; slug: string }[];
  error?: string;
}

const EMPTY: Results = { players: [], clubs: [] };

/** ⌘K / Ctrl+K palette searching players and clubs (accent-insensitive, server-side). */
export function SearchCommand() {
  const router = useRouter();
  const [open, setOpen] = useState(false);
  const [query, setQuery] = useState("");
  const [results, setResults] = useState<Results>(EMPTY);
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    const onKey = (e: KeyboardEvent) => {
      if (e.key.toLowerCase() === "k" && (e.metaKey || e.ctrlKey)) {
        e.preventDefault();
        setOpen((o) => !o);
      }
    };
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, []);

  useEffect(() => {
    if (query.trim().length < 2) return;
    const controller = new AbortController();
    const t = setTimeout(async () => {
      setLoading(true);
      try {
        const res = await fetch(`/api/search?q=${encodeURIComponent(query)}`, { signal: controller.signal });
        setResults((await res.json()) as Results);
      } catch {
        /* aborted or offline: keep previous results */
      } finally {
        setLoading(false);
      }
    }, 180); // debounce
    return () => {
      clearTimeout(t);
      controller.abort();
    };
  }, [query]);

  const go = (href: string) => {
    setOpen(false);
    setQuery("");
    router.push(href);
  };
  const shown = query.trim().length < 2 ? EMPTY : results;

  return (
    <>
      <button
        type="button"
        onClick={() => setOpen(true)}
        className="inline-flex h-8 items-center gap-2 rounded-md border bg-surface px-2.5 text-sm whitespace-nowrap text-muted-foreground transition-colors hover:text-foreground lg:w-60"
        aria-label="Search players or clubs"
      >
        <Search className="size-3.5" aria-hidden />
        <span className="hidden lg:inline">Search players or clubs</span>
        <kbd className="ml-auto hidden rounded border bg-background px-1 font-mono text-[10px] whitespace-nowrap lg:inline">Ctrl K</kbd>
      </button>
      <CommandDialog open={open} onOpenChange={setOpen} title="Search" description="Search players or clubs">
        <Command shouldFilter={false}>
          <CommandInput placeholder="Type a player or club…" value={query} onValueChange={setQuery} />
          <CommandList>
            {query.trim().length >= 2 && !loading && (
              <CommandEmpty>{shown.error ?? "No players or clubs found."}</CommandEmpty>
            )}
            {shown.players.length > 0 && (
              <CommandGroup heading="Players">
                {shown.players.map((p) => (
                  <CommandItem key={p.slug} value={`player-${p.slug}`} onSelect={() => go(`/players/${p.slug}`)}>
                    <User className="size-3.5 text-muted-foreground" aria-hidden />
                    <span>{p.name}</span>
                    <span className="ml-auto text-xs text-muted-foreground">
                      {[p.sub_position, p.birth_year && `b. ${p.birth_year}`].filter(Boolean).join(" · ")}
                    </span>
                  </CommandItem>
                ))}
              </CommandGroup>
            )}
            {shown.clubs.length > 0 && (
              <CommandGroup heading="Clubs">
                {shown.clubs.map((c) => (
                  <CommandItem key={c.slug} value={`club-${c.slug}`} onSelect={() => go(`/clubs/${c.slug}`)}>
                    <Shield className="size-3.5 text-muted-foreground" aria-hidden />
                    {c.name}
                  </CommandItem>
                ))}
              </CommandGroup>
            )}
          </CommandList>
        </Command>
      </CommandDialog>
    </>
  );
}
