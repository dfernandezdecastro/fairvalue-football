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
