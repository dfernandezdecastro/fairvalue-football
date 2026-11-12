# Decision log

Short records of non-obvious technical decisions: context, decision, consequence. Newest last.

## D1. Staging files are compressed CSV with schema-on-read, not Parquet (Step 2)
- **Context:** Parquet (via pyarrow) is the usual choice for typed tables, but Windows Smart App Control blocks pyarrow's native DLL on the development machine.
- **Decision:** write `*.csv.gz` and re-apply each table's data contract on every read (`fairvalue.io`).
- **Consequence:** types survive the round trip and a format drift fails loudly. Reads are slower (seconds, not milliseconds), which is irrelevant for a batch pipeline. Revisit if the data grows by 10× or the machine policy changes.

## D2. Snapshot-only fields are excluded at ingest (Step 2)
- **Context:** the Transfermarkt snapshot includes fields describing *today* (international caps, contract expiry, current club, latest market value, agent). Using them for a 2018 prediction leaks the future.
- **Decision:** they aren't part of any data contract, so they never reach staging. A test asserts it.
- **Consequence:** contract length, the strongest known fee driver, is unavailable historically; this is documented as a model limitation.

## D3. Loan detection ignores same-day reverse moves (Step 2)
- **Context:** "buy and loan back" deals record a paid A→B move and a B→A loan on the same date. The original rule ("the next move reverses this one") depended on arbitrary same-day row order.
- **Decision:** a move is a probable loan only if it's reversed on a *later* date, within 400 days.
- **Consequence:** 11 permanent transfers restored (e.g. Bastoni, Atalanta → Inter, 2017). Erratum in the feasibility report.

## D4. Season-level features use the last season finished before the transfer (Step 3)
- **Context:** COVID-delayed 2019/20 seasons ended as late as 2 Aug 2020. Summer-2020 transfers dated in July would otherwise see matches played after the transfer.
- **Decision:** use the most recent season whose league had finished before the transfer date (normally s−1, otherwise s−2).
- **Consequence:** 140 transfers fall back a season. Usable full-tier set 1,792 → 1,794 (+6/−5 from this rule, +1 from D3).

## D5. Position groups start from the current label, corrected by season usage (Step 3)
- **Context:** Transfermarkt's position is a current snapshot. Understat lists every line used in a season but no primary position.
- **Decision:** six peer groups (GK, CB, FB, CM, AM_W, ST) from the Transfermarkt label, overridden only when that season's Understat record shows a single, incompatible line.
- **Consequence:** 217 player-seasons overridden; 21,070 confirmed; 71,671 rely on the current label (flagged `position_source`).

## D6. Empirical-Bayes shrinkage, with xG metrics borrowing their noise level (Step 3)
- **Context:** per-90 rates from few minutes are noisy. A Gamma-Poisson method-of-moments estimate of the prior strength k works for counts, but treats xG-type metrics (sums of probabilities, much less noisy) as mostly noise. First run: Haaland 2023/24 npxG 0.89 → 0.61 per 90.
- **Decision:** estimate k directly for counts (goals, assists, shots, key passes). npxG borrows k from shots; xA, xGChain and xGBuildup borrow it from key passes, since their noise comes mainly from how many chances occur. k is clamped to 90–3,600 minutes.
- **Consequence:** Haaland 0.89 → 0.81. Big-five median prior strength ≈ 750 minutes for chance metrics, 2,450 for goals, at the 3,600 cap for assists (assist counts are mostly noise at season scale).

## D7. PIV is a same-market (cross-sectional) valuation, not a forecast (Step 4)
- **Context:** the target (market value after the season) must be comparable across years despite heavy market inflation.
- **Decision:** model log market value relative to that summer's market index (median value of eligible big-five outfield players). The estimate is converted back to euros with the same summer's index.
- **Consequence:** the PIV answers "what does this market typically pay for this profile?", which is what the valuation gap needs. Using the same-summer index isn't leakage, because PIV is compared with market values from that same summer. Features only use data up to season end.

## D8. Same-market re-centring of predictions (Step 4)
- **Context:** the first walk-forward run over-predicted (bias −0.11 log in the full tier). The median relative value is 0 every season by construction, but the mean fell from +0.16 (2012) to −0.10 (2024): the market became more unequal, so models trained on earlier seasons over-value the typical player.
- **Decision:** each season, shift predictions so the median prediction over big-five rows is 0, the known median of the target by definition. It uses only that season's predictions (features), never its targets, and is applied identically during hyperparameter selection.
- **Consequence:** full-tier bias −0.11 → +0.01 and MAE 0.422 → 0.408. Tested with a synthetic "market gets more unequal" scenario.

## D9. Point-in-time league market level feature (Step 4)
- **Context:** after D8, the basic tier still over-predicted non-big-five leagues by ~30% (median log residual −0.36). Leagues drift strongly against the big five (Portugal −0.66 → −2.24 from 2013 to 2019; Russia fell after 2022), so league coefficients learned from earlier seasons go stale.
- **Decision:** add `league_mv_level`: the league's median market value dated strictly before season end, relative to the big five. It's an aggregate over hundreds of players, so it isn't circular for an individual.
- **Consequence:** basic-tier MAE 0.485 → 0.419, median error 41% → 34%, bias −0.20 → −0.04; non-big-five bias −0.36 → −0.07.

## D10. Gradient boosting chosen for both tiers, with SHAP explanations (Step 4)
- **Context:** the selection rule required boosting to beat Ridge by ≥ 5% walk-forward MAE without worse interval calibration.
- **Decision:** boosting passed in both tiers (full 0.404 vs 0.428; basic 0.419 vs 0.455), with calibration as good as Ridge's. Explanations use SHAP (TreeExplainer), whose contributions add up exactly to each prediction (tested). This adds the `shap` dependency.
- **Consequence:** less transparent than Ridge coefficients, mitigated by per-prediction driver groups. Ridge stays in the evaluation as the reference.

## D11. Valuation gaps are peer-relative, with league-specific interval widths (Step 4, user decision)
- **Context:** league-season market moves the model can't foresee (LaLiga 2024/25 median residual −0.21) inflated gap labels: 27% of LaLiga players were flagged "potential undervaluation" vs ~10% expected, so the Hidden Gems list leaned to whichever league dipped that year.
- **Decision (chosen by the product owner):** gap labels compare a player's market value with the range for same-league peers in the same summer. The model estimate is shifted by the league-season's median residual (leagues with < 30 valued players: no shift), and intervals are calibrated on earlier seasons' peer-centred errors. Interval widths are calibrated per league first (league × line → league → minutes band × line → minutes band → all, minimum 100 residuals), because value dispersion differs a lot between leagues.
- **Consequence:** accuracy metrics are unchanged (they use the pure model estimate). Peer-relative 80% coverage is 81.8% (full) / 80.3% (basic). Per league across all seasons, 78.6–83.4% inside, except Scotland at 72.8% (flagged in the model card). LaLiga 2024/25 undervaluation flags fell from 27% to 16–18%; single seasons still vary ±3.6 points per league, which is noise past calibration can't remove. The shift uses same-summer values of league peers. That's consistent with D7 (a same-market valuation, not a forecast), and the published output keeps both the whole-market and the peer-relative views.

## D12. Expected Fee predicts the premium over point-in-time market value; Ridge ships (Step 5)
- **Context:** market value at the transfer date is by far the strongest public signal for a fee. The fee ÷ value ratio drifts with market cycles (median log ratio +0.15 in 2016–17, −0.20 by 2022).
- **Decision:** target = log(fee ÷ market value strictly before the transfer). Features are all point-in-time: value trend; the Layer 2 *relative* performance-implied value for the last finished season (no later valuations needed); buyer's fees paid and seller's fees received in the previous 365 days; a market premium level (median ratio of the previous 12 months); deadline week; leagues, age, position, recent playing time. Same walk-forward and pre-registered selection rule as Step 4.
- **Consequence:** gradient boosting was 4.4% better, below the 5% bar, so **Ridge ships**. Typical error 44% vs 50% for "fee = market value" (R² on log fee 0.74 vs 0.66). 80% ranges cover 81.5% but span ×9: fees are noisy, and the product must show that width. The 30M+ band is over-covered (93%) because it has few calibration rows.

## D13. Club audit: bootstrap ranges, ranking by the conservative end (Step 5)
- **Context:** a price ratio from 8–40 transfers is noisy; ranking by the point estimate rewards small, lucky samples.
- **Decision:** price ratio = Σ fee ÷ Σ expected fee over assessed purchases; 80% bootstrap range over the club's transfers; clubs need ≥ 8 assessed purchases; "lowest" lists sort by the upper bound and "highest" by the lower bound. Post-transfer market-value change is shown as an outcome, never used by a model.
- **Consequence:** the bootstrap ignores each transfer's own model uncertainty, so the true uncertainty is wider (stated). The highest big-five ratios (Athletic Club 1.70, Ipswich 1.48, Newcastle 1.26) and the largest unusual premiums (2023 Saudi Pro League moves, Chris Wood to Newcastle) are well-known market stories the model was never told about.

## D14. Hidden Gems backtest against stratified peers (Step 5)
- **Context:** the spec promises to publish whether flags predict anything, whatever the answer. Young and cheap players rise more on average, which would flatter a naive comparison.
- **Decision:** outcome = 12-month market-value change after the valuation the label used; compared with the median change of "within expected range" players in the same season × position × age band × value tercile; bootstrap 80% CI.
- **Consequence:** flagged players gained **+7.9%** vs peers (80% CI 6.5–11.1%), "strong signal" **+13.9%** (11.1–20.0%), "market premium" −3.8%. Positive for undervaluation and ≤ 0 for premium in all 10 seasons. Caveats in the report: crowd opinion catching up, regression to the mean, survivors only.

## D15. What the public database contains (Step 6)
- **Context:** the web app needs a database, but the sources are non-commercial and Transfermarkt's database rights forbid re-publishing substantial parts of it (DATA_SOURCES.md). Player data is also personal data.
- **Decision:** publish only derived outputs and the individual facts each page needs: profiles (season totals, per-90s, percentiles), model estimates with ranges, paid permanent transfers since 2015/16 with expected fees, club audit, top-10 similar players since 2017/18, and one market value per player-season (the one each estimate is compared with). Not published: valuation histories, match-level appearances, loans and free transfers, contract and agent data. Players appear with **birth year only**. A licensing guard fails the build if a forbidden column reaches a published table, and a referential-integrity check runs before anything touches the database.
- **Consequence:** about 94 MB as CSV (~150–200 MB in Postgres), inside Supabase's free tier. The player page's "valuation history" shows one point per season, not Transfermarkt's full history. Access is public read-only by row-level security (SELECT policies only, verified by `fairvalue db-check`); writes happen only from the pipeline machine with the database password. The service-role key isn't used anywhere.
