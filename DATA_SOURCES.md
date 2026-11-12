# Data Sources and Licensing Report

*FairValue Football, data feasibility study, 12 November 2026.*
*This is a practical risk assessment, not legal advice.*

## Summary

| Source | Used for | Status (Nov 2026) | Legal position | Verdict |
|---|---|---|---|---|
| **transfermarkt-datasets** (dcaribou) | Transfers & fees, market valuations, players, clubs, per-match appearances | Frozen: data current to **6 Jul 2026**, updates "paused indefinitely" | Repo is CC0 but the **underlying data is Transfermarkt's**; CC0 cannot license rights the maintainer does not hold | Use for **non-commercial portfolio/research only**, with attribution, no raw redistribution |
| **Understat** (via Internet Archive) | xG, npxG, xA, shots, key passes, xGChain, xGBuildup (season level) | Site **offline since ~2 Nov 2026**; 45 of 55 big-five league-seasons 2014/15–2024/25 recovered from Wayback snapshots; 2025/26 unrecoverable | No published licence or terms found → default "all rights reserved". Archive copies do not transfer any rights | Same posture as Transfermarkt: non-commercial, attributed, derived data only |
| **StatsBomb Open Data** | Not used in model; optional showcase | Available | Explicit user agreement: **no redistribution, no commercial exploitation "of the data or any analysis derived"**, logo attribution required | Optional deep-dive pages only; would block any commercial use of those pages |
| **FBref** | Not used | Advanced (Opta) stats **removed Jan 2026** | Sports Reference data-use policy restricts scraping and bulk reuse | Excluded |
| Kaggle dumps of pre-2026 FBref/Opta data | Not used | Available | Redistributed third-party (Opta) data without evident rights | **Excluded deliberately** |

## 1. transfermarkt-datasets

- **What it is:** a community project that scrapes transfermarkt.co.uk and publishes 12 joinable tables (repo `dcaribou/transfermarkt-datasets`, mirrored on Kaggle as `davidcariboo/player-scores`). We downloaded `transfermarkt-datasets.zip` (241 MB, last modified 5 Sep 2026) from the project's public R2 bucket on 12 Nov 2026.
- **Licence:** the repository declares **CC0-1.0**. CC0 waives the *maintainer's* rights (code, curation). It **does not and cannot** grant rights over Transfermarkt's content. The README doesn't mention Transfermarkt's terms.
- **Transfermarkt's position:** we couldn't retrieve Transfermarkt's terms of use directly (automated access to transfermarkt.com was blocked from this environment). Secondary sources report Transfermarkt stating that its data is protected under German law and not licensed for reuse. In the EU, Transfermarkt's database very likely qualifies for the **sui generis database right** (Directive 96/9/EC), which protects against extracting or re-using a *substantial part* of the database without consent. Courts have also upheld website terms restricting scraping (CJEU *Ryanair v PR Aviation*, 2015).
- **Mitigating factors (not guarantees):** individual facts (a fee, a date of birth) aren't copyrightable; the EU text-and-data-mining exceptions (DSM Directive 2019/790, Art. 3 for scientific research by research organisations, Art. 4 general TDM unless the rights holder opts out) may cover analysis, but not public republication of the database.
- **Practical rules for FairValue:**
  1. Non-commercial portfolio/research positioning, stated on the site.
  2. Attribute: "Transfer and market-value data: Transfermarkt, via the community transfermarkt-datasets project."
  3. **Never commit or publish raw tables.** `data/raw/` stays out of Git. Publish only derived outputs (model estimates, aggregates, and the individual fields needed for an analysis page).
  4. Don't hotlink or copy Transfermarkt **player photos** (`image_url`): copyright plus image rights.
  5. Any commercial step requires written permission from Transfermarkt or a licensed provider.
- **Freshness risk:** the maintainer reports the collection pipeline "stopped completing successfully in mid-July 2026", with no restart date. **Treat the data as a frozen snapshot to 6 Jul 2026.**

## 2. Understat

- **What it is:** a free xG site covering the big five leagues and the Russian Premier League from 2014/15. There's no official API. Data was embedded as JSON in league pages until early 2026.
- **Status:** understat.com has served a "We will come back soon" page since about 2 Nov 2026 (verified 12 Nov 2026). The cause is unconfirmed; social media reports of a hosting-provider cyberattack are unverified. Archived pages from about Feb 2026 onward load data client-side and contain no data.
- **How we obtained data:** we read archived league pages from the Internet Archive's Wayback Machine (CDX API, one request at a time, 1.5 s pauses, cached locally). Recovered: **45 of 55** league-seasons 2014/15–2024/25 (one, La Liga 2024/25, from a capture dated 25 May 2025, a few days before the final round: "near-final"). Missing: La Liga 2023/24; Serie A 2014/15, 2016/17, 2018/19, 2022/23; Ligue 1 2014/15, 2015/16, 2016/17, 2020/21, 2024/25. **2025/26 is missing for all leagues.**
- **Licence:** no terms of use or licence found. Default copyright and database-right rules apply, and the Internet Archive grants no rights in archived content. Same practical rules as Transfermarkt: non-commercial, attributed ("xG data: Understat"), derived outputs only.
- **Risk:** the source may never return. Our cached copies are the only reproducible input, and the recovery script is in `scripts/feasibility/fetch_understat_wayback.py`.

## 3. StatsBomb Open Data

- **Terms** (StatsBomb Public Data User Agreement, last updated 8 Sep 2023): users may not "distribute, reproduce, sell or in any way provide the data" to third parties (1.2.1), or "commercially exploit the data or any analysis derived" from it (1.2.2). Publications must carry the StatsBomb logo (1.4). Governed by English law.
- **Coverage:** selected competitions and seasons only (it isn't league-wide season coverage), so it can't feed a transfer model.
- **Use:** optional event-level showcase pages (for example a player shot map) with logo attribution. These pages would need removing in any commercial version.

## 4. FBref

- On 20 Jan 2026 Sports Reference removed FBref's advanced stats (xG, progressive actions, shot-creating actions) after Opta ended its data agreement. The remaining basic stats duplicate Transfermarkt appearances. **Excluded.**

## 5. What would make this commercial

A commercial version would need licensed event data (Opta/Stats Perform, Hudl StatsBomb, Wyscout) and a licensed transfer/contract feed. The pipeline is designed so the source layer can be swapped without touching the model or the app.

## 6. Personal data note

Player names, dates of birth and nationalities are personal data under GDPR. Publishing football statistics about professional players is common under legitimate-interest and journalistic grounds, but we minimise fields (no agent names, no birthplaces) and keep nationality out of the model.

## Sources consulted

- transfermarkt-datasets README and status discussion #383: github.com/dcaribou/transfermarkt-datasets
- StatsBomb Open Data README and `LICENSE.pdf`: github.com/statsbomb/open-data
- FBref advanced-stats removal: Awful Announcing; The IX
- Understat outage: xG Stat "Understat alternative" page; public developer PRs referencing the maintenance page; direct check of understat.com on 12 Nov 2026
- Transfermarkt rights position (secondary): R-pkg-devel mailing list, 2018 thread
