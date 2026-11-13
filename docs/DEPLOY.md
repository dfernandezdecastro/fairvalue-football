# Deploying the web app (Vercel, ~10 minutes)

The site only needs two **public, read-only** values. The database password never leaves your machine, and the pipeline isn't deployed (it runs locally and publishes to Supabase).

## Steps

1. Go to https://vercel.com and sign up or log in **with GitHub** (Hobby plan, free).
2. **Add New… → Project**, then import `dfernandezdecastro/fairvalue-football`. If it isn't listed, click *Adjust GitHub App Permissions* and give Vercel access to that private repository.
3. On the configuration screen:
   - **Root Directory:** `web` (click *Edit* and select the `web` folder). This is the important one.
   - **Framework Preset:** Next.js (detected automatically). Leave the build and install commands at their defaults.
   - **Environment Variables:** add both, for all environments:
     - `SUPABASE_URL`: `https://<your-project-ref>.supabase.co` (no `/rest/v1` at the end)
     - `SUPABASE_ANON_KEY`: your **publishable** key (starts with `sb_publishable_`)
4. Click **Deploy** and wait about two minutes.
5. Open the `…vercel.app` URL it gives you and send it to me; I'll check every page on the live site.

After this, every push to `main` redeploys automatically.

## What NOT to put in Vercel
- The database password or `SUPABASE_DB_URL`. The web app never writes.
- The Supabase *secret* or *service-role* key.

## Things to know
- **Supabase free projects pause after about a week without traffic.** If the live site shows "Something went wrong", open the Supabase dashboard and click *Restore project*. Upgrading or a scheduled ping avoids this.
- `/design` (the internal component page) is deployed but excluded from search engines via `robots.ts`.
- Data refreshes require running the pipeline locally and `fairvalue db-load`; the site picks up new data within 24 hours (the fetch cache's revalidation window) or on the next deployment.
