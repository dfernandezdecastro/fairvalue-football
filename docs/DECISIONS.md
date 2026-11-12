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
