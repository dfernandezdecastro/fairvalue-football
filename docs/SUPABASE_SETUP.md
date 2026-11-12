# Supabase setup (one-off, ~10 minutes)

The database holds only derived outputs (decision D15) and is **public read-only**: anonymous visitors can read, nobody can write except the pipeline from your machine.

## 1. Create the project
1. https://supabase.com → **New project**
2. Name `fairvalue-football`, region **EU** (Frankfurt or Paris), free plan
3. Generate a strong database password and store it in your password manager. You'll need it once, in step 2.

## 2. Fill in `.env` (repository root, git-ignored)
Copy the template:

```bash
cp .env.example .env
```

Then fill in three values. Open `.env` in your editor; **don't paste them into chats, issues or screenshots**.

| Variable | Where to find it in the Supabase dashboard |
|---|---|
| `SUPABASE_DB_URL` | **Connect** (top bar) → *Connection string* → **Session pooler** → copy the URI and replace `[YOUR-PASSWORD]` with your database password |
| `SUPABASE_URL` | **Project Settings → Data API** → Project URL |
| `SUPABASE_ANON_KEY` | **Project Settings → API Keys** → the *publishable* key (or the legacy *anon public* key) |

Why the session pooler: Supabase's direct connection is IPv6-only on the free plan; the pooler works on any network.

Also create `web/.env.local` from `web/.env.example` with the same `SUPABASE_URL` and `SUPABASE_ANON_KEY` (server-only, so they never reach the browser bundle).

## 3. Load and verify

```bash
.venv/Scripts/fairvalue db-load     # migrations + all tables in one transaction
.venv/Scripts/fairvalue db-check    # anonymous read works, anonymous insert/delete refused
.venv/Scripts/fairvalue gen-types   # web/lib/db/types.ts from the live schema
```

## Security model
- The **database password** (`SUPABASE_DB_URL`) can write everything. It lives only in `.env` on your machine.
- The **anon/publishable key** is public by design. Row-level security allows `SELECT` only, which `db-check` verifies on every run.
- The service-role key isn't needed anywhere in this project. Don't copy it.
- If a secret ever leaks: reset the database password (Project Settings → Database) and rotate API keys.
