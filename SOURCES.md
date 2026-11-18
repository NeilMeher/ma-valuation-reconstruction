# Data sources and dictionary

Accessed 2026-11-18 using publicly readable EDGAR HTML. Shell download in the restricted environment failed DNS resolution. Only individual factual figures needed for replication and links are included. Filings and adviser exhibits remain with their original publishers and their redistribution rights are unassessed.

| Input | Accession and locator | As-of date | Units | Cases | Status and interpretation |
|---|---|---|---|---|---|
| forecast_2025 through forecast_2029 | DEFM14A 0001193125-25-176997, pp. 50 and 51, Unlevered FCF | Management forecasts supplied April 2025; fiscal ends Dec 31 | USD millions | A/B | Reported rounded. SBC treated as cash expense. 2029 extrapolated. |
| terminal_fcf, terminal_ebitda | SC 13E-3 0001193125-25-153528, Exhibit (c)(ix), pp. 18–19, terminal columns | Dec 31 2029 normalized basis | USD millions | A/B | Reported rounded. Growth and multiple use the separate inputs shown. |
| cash, debt | Exhibit (c)(ix), pp. 18–19, EV-to-equity bridge | Dec 31 2024 | USD millions | A/B | Reported rounded. $197m/$253m March sensitivity from p. 14. |
| shares | Exhibit (c)(ix), pp. 18–19, FDSO row and footnotes | May 5 2025 | Millions of diluted shares | A/B | Reported rounded. Includes both common classes and eligible awards, with treasury stock treatment for in-the-money options. |
| wacc_lo, wacc_hi, growth_lo, growth_hi, multiple_lo, multiple_hi | Exhibit (c)(ix), pp. 18–19, sensitivity grids | Dec 31 2024 valuation | Decimal rates and EBITDA multiples | A/B | Reported. |
| discount timing | Exhibit (c)(ix), pp. 18–19, factors 0.95/0.85/0.76/0.68/0.61 at 11.5% | Dec 31 2024 valuation | Years from valuation date | A/B | Inferred from annual and terminal factor rows. |
| offer, adviser_low, adviser_high | DEFM14A, merger consideration and pp. 57–58, Evercore DCF | May 8–9 2025 | USD per share | A/B | Reported benchmarks, isolated in checks.csv. |

[Definitive proxy](https://www.sec.gov/Archives/edgar/data/1829864/000119312525176997/d111106ddefm14a.htm) · [May 8 Evercore slides](https://www.sec.gov/Archives/edgar/data/1829864/000119312525153528/d947061dex99cix.htm)

The ledger in [screening.csv](screening.csv) distinguishes eligible deals with an unfinished input audit from out-of-frame candidates. A field missing from a proxy summary can be present in an exhibit. No claim of complete disclosure coverage is made for deals awaiting an exhibit search.

The exploratory working-capital sensitivity uses terminal_revenue ($1,567m / $867m) and the 14% working-capital-to-revenue-change convention from exhibit pp. 18–19 and related forecast tables.
