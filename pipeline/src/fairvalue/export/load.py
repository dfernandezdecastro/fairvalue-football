"""Load published tables into Supabase Postgres: `fairvalue db-load`, `db-check`, `gen-types`.

Secrets come from the repository's git-ignored `.env` (see `.env.example`):
  SUPABASE_DB_URL    Postgres connection string (session pooler), includes the DB password: SECRET
  SUPABASE_URL       https://<project>.supabase.co                                      (public)
  SUPABASE_ANON_KEY  anon key, read-only through row-level security                      (public)

Writes use the database owner's connection from this machine only. The web app
only ever gets the anon key, which RLS restricts to SELECT.
"""

from __future__ import annotations

import io
import os
from pathlib import Path

import pandas as pd

from fairvalue.config import REPO_ROOT
from fairvalue.export.contracts import LOAD_ORDER, PUBLISH

MIGRATIONS = REPO_ROOT / "supabase" / "migrations"
TYPES_OUT = REPO_ROOT / "web" / "lib" / "db" / "types.ts"


def load_env(path: Path = REPO_ROOT / ".env") -> None:
    """Minimal .env reader (KEY=VALUE lines); existing environment variables win."""
    if not path.exists():
        return
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if line and not line.startswith("#") and "=" in line:
            k, v = line.split("=", 1)
            os.environ.setdefault(k.strip(), v.strip().strip('"').strip("'"))


def require(name: str) -> str:
    load_env()
    value = os.environ.get(name, "")
    if not value or "YOUR" in value.upper():
        raise SystemExit(f"{name} is not set. Copy .env.example to .env and fill it in (see docs/SUPABASE_SETUP.md).")
    return value


def connect():
    import psycopg

    return psycopg.connect(require("SUPABASE_DB_URL"), autocommit=False)


def migrate(conn, log=print) -> list[str]:
    with conn.cursor() as cur:
        cur.execute("create table if not exists _fairvalue_migrations (name text primary key, applied_at timestamptz "
                    "not null default now())")  # fmt: skip
        cur.execute("select name from _fairvalue_migrations")
        done = {r[0] for r in cur.fetchall()}
        applied = []
        for f in sorted(MIGRATIONS.glob("*.sql")):
            if f.name in done:
                continue
            log(f"  applying {f.name}")
            cur.execute(f.read_text(encoding="utf-8"))
            cur.execute("insert into _fairvalue_migrations (name) values (%s)", (f.name,))
            applied.append(f.name)
    conn.commit()
    return applied


def _csv(df: pd.DataFrame) -> str:
    buf = io.StringIO()
    df.to_csv(buf, index=False, header=False, date_format="%Y-%m-%d")
    return buf.getvalue()


def load(tables: dict[str, pd.DataFrame], conn, log=print) -> dict[str, int]:
    """Replace all data in one transaction: a failure leaves the previous data untouched."""
    counts = {}
    with conn.cursor() as cur:
        cur.execute("truncate " + ", ".join(reversed(LOAD_ORDER)) + " cascade")
        for name in LOAD_ORDER:
            cols = list(PUBLISH[name])
            col_sql = ", ".join(f'"{c}"' for c in cols)
            with cur.copy(f"copy {name} ({col_sql}) from stdin with (format csv)") as cp:
                cp.write(_csv(tables[name][cols]))
            counts[name] = len(tables[name])
            log(f"  {name:<16} {counts[name]:>8,} rows")
        for name in LOAD_ORDER:
            cur.execute(f"select count(*) from {name}")
            n = cur.fetchone()[0]
            if n != counts[name]:
                raise RuntimeError(f"{name}: loaded {n} rows, expected {counts[name]}")
        cur.execute("analyze")
    conn.commit()
    return counts


def run_load(log=print) -> dict[str, int]:
    from fairvalue.export.publish import build_tables

    log("building published tables...")
    tables = build_tables()
    with connect() as conn:
        log("migrations:")
        applied = migrate(conn, log)
        if not applied:
            log("  up to date")
        log("loading (single transaction):")
        counts = load(tables, conn, log)
        with conn.cursor() as cur:
            cur.execute("select pg_size_pretty(pg_database_size(current_database()))")
            log(f"database size: {cur.fetchone()[0]}")
    return counts


def check_public_access(log=print) -> bool:
    """As an anonymous visitor (anon key): reads must work, writes must be refused."""
    import requests

    url, key = require("SUPABASE_URL").rstrip("/"), require("SUPABASE_ANON_KEY")
    # Legacy anon keys are JWTs (also sent as Bearer); new publishable keys (sb_publishable_...) go in apikey only.
    h = {"apikey": key} if key.startswith("sb_publishable_") else {"apikey": key, "Authorization": f"Bearer {key}"}
    ok = True
    read = requests.get(f"{url}/rest/v1/competitions?select=id&limit=1", headers=h, timeout=30)
    log(f"  anonymous read competitions: HTTP {read.status_code} {'OK' if read.ok and read.json() else 'FAIL'}")
    ok &= read.ok and bool(read.json())
    view = requests.get(f"{url}/rest/v1/v_player_season?select=player_name,season&limit=1", headers=h, timeout=30)
    log(f"  anonymous read v_player_season: HTTP {view.status_code} {'OK' if view.ok else 'FAIL'}")
    ok &= view.ok
    write = requests.post(f"{url}/rest/v1/app_meta", headers=h | {"Content-Type": "application/json"},
                          json={"key": "intrusion-test", "value": {}}, timeout=30)  # fmt: skip
    refused = write.status_code in (401, 403)
    log(f"  anonymous insert app_meta: HTTP {write.status_code} {'refused (good)' if refused else 'NOT REFUSED'}")
    ok &= refused
    prefer = h | {"Prefer": "return=representation"}
    delete = requests.delete(f"{url}/rest/v1/app_meta?key=eq.data_vintage", headers=prefer, timeout=30)
    deleted = delete.ok and delete.json() not in ([], None)
    verdict = "DELETED ROWS" if deleted else "nothing deleted (good)"
    log(f"  anonymous delete app_meta: HTTP {delete.status_code} {verdict}")
    ok &= not deleted
    return ok


TS_TYPES = {
    "integer": "number", "bigint": "number", "real": "number", "double precision": "number", "numeric": "number",
    "boolean": "boolean", "jsonb": "unknown", "json": "unknown", "date": "string",
    "timestamp with time zone": "string", "text": "string",
}  # fmt: skip


def gen_types(log=print) -> str:
    """Write web/lib/db/types.ts from the live schema (tables and views in `public`)."""
    with connect() as conn, conn.cursor() as cur:
        cur.execute("""
            select c.table_name, c.column_name, c.data_type, c.is_nullable, t.table_type
            from information_schema.columns c
            join information_schema.tables t on t.table_name = c.table_name and t.table_schema = c.table_schema
            where c.table_schema = 'public' and c.table_name not like '\\_%'
            order by c.table_name, c.ordinal_position""")
        rows = cur.fetchall()
    out = ["// Generated by `fairvalue gen-types` from the live database schema. Do not edit by hand.", ""]
    current = None
    for table, col, dtype, nullable, ttype in rows:
        if table != current:
            if current:
                out.append("}\n")
            name = "".join(p.capitalize() for p in table.split("_"))
            kind = "view" if ttype == "VIEW" else "table"
            out.append(f"/** `{table}` ({kind}) */\nexport interface {name} {{")
            current = table
        ts = TS_TYPES.get(dtype, "unknown")
        out.append(f"  {col}: {ts}{' | null' if nullable == 'YES' else ''};")
    out.append("}\n")
    TYPES_OUT.parent.mkdir(parents=True, exist_ok=True)
    TYPES_OUT.write_text("\n".join(out), encoding="utf-8")
    log(f"wrote {TYPES_OUT}")
    return str(TYPES_OUT)
