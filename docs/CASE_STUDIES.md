# Case studies

Three real examples from the published data, chosen to show what FairValue can and can't say. All numbers are walk-forward model outputs (each from a model that never saw the season it scores) and Transfermarkt-reported fees and market values.

---

## 1. Mitrović to Al-Hilal: an unusual transfer premium, and why that isn't a verdict

**The transfer.** Aleksandar Mitrović, 28, moved from Fulham to Al-Hilal on 19 August 2023 for a reported **€52.6M**. His Transfermarkt market value just before the move was €28.0M.

**What the model expected.** Using only information public before that date (market value and its trend, age, position, both clubs' leagues and spending, recent playing time, the market cycle), comparable deals commanded about **€13.9M**, with an 80% range of €6.4–25.5M and a 95% range of €3.1–36.5M. The fee sits above the 95% range, so the label is **"Unusual transfer premium"** (High reliability).

**What drove the expectation.** Two effects pulled it *below* his market value: the size of the market value itself (−36%; fees for high-value players in the training data tend to sit below value) and his age (−25%). His position (+13%) and the buying club's profile (+7%) pushed it up.

**How to read it.** The label says the fee was far outside what comparable public information predicted. It doesn't say Al-Hilal "overpaid": the 2023 Saudi Pro League window had its own economics (state-backed budgets, the need to attract players to a new destination, competition between Saudi clubs), none of which the model can observe. The pattern is systematic: across 120 assessed transfers into the Saudi league, the median fee was **52% above** the expected fee, against **2%** for all assessed transfers, and 37 of 120 were labelled notable or unusual premiums.

**Interview takeaway.** A model residual is a question, not an answer. The product's job is to surface where price and evidence disagree, with a range, and to name the factors it can't see.

---

## 2. Athletic Club: one club convention, two signals

Athletic Club only signs players with Basque roots. This single convention shows up in **both** of FairValue's models, in opposite directions.

**As a buyer: paying premiums.** Athletic's 8 assessed purchases since 2018/19 cost **€77.8M** against **€45.9M** in expected fees: a price ratio of **1.70** (80% bootstrap range 1.50–1.95), among the highest of any big-five club. Examples: Álex Berenguer from Torino (€11.1M against €3.1M expected, unusual premium), Álvaro Djaló from Braga (€15M against €8.5M, notable premium), Jesús Areso from Osasuna (€12M against €6.7M, notable premium). With a tiny eligible pool, sellers know Athletic can't easily look elsewhere.

**As a valuation: its players look undervalued.** In 2024/25, Athletic attackers Gorka Guruzeta and Álex Berenguer were among the strongest "potential undervaluation" flags in LaLiga (Guruzeta: €9M market value against a performance-implied €30.8M). Athletic players rarely move, which plausibly keeps their market values low regardless of performance.

**How to read it.** A convention the data can't see inflates one model's residuals upwards (fees) and another's downwards (market values). The model card lists this explicitly as a limitation, and it's the clearest argument for why FairValue says "potential undervaluation" and never "undervalued".

**Interview takeaway.** When two independent models disagree with the market in a consistent direction for the same club, look for an unobserved structural cause before believing either.

---

## 3. Hidden Gems in practice: the flags that worked, and the ones that didn't

The backtest says flagged players gained **+7.9%** more market value than comparable peers over the next 12 months (80% CI 6.5–11.1%; "strong signal" +13.9%), positive in all 10 seasons tested. Individual flags are much noisier, and the product should be judged on both.

**A flag that worked: Samuel Lino, 2022/23.** At 23, after 2,899 LaLiga minutes, his market value was **€16M** against a performance-implied **€38.1M** (80% range €22.1–84.8M), a potential undervaluation with High reliability. A year later his market value was **€30M (+88%)**.

**Flags that didn't move: Pascal Groß and Granit Xhaka, 2022/23.** These were the only two High-reliability "strong signal" players that season. Both were in their thirties and central to strong teams (Xhaka: €20M against €52.9M implied). Twelve months later **neither market value had changed**. Xhaka's 2023 move to Leverkusen (€15M against an expected €10.6M, range €4.9–17.8M) was *within* the expected range: the club paid roughly what comparable deals commanded, and went on to win the Bundesliga unbeaten (a sporting outcome outside this dataset).

**What this shows.** Among all 69 flagged 2022/23 players (xG-level data, High or Moderate reliability), only 32% rose in value and the median change was 0%. The edge comes from comparing with *similar* players, not from flags rising on average. The market discounts age heavily, and performance doesn't change that quickly. Market value also isn't sporting success: Xhaka's value stood still while he won a league.

**Interview takeaway.** Report the aggregate evidence *and* show individual cases where the signal fails. Hiding the misses would make the product less credible, not more.
