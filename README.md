# HMRC spending disclosure EDA (2023–2025)

An exploratory analysis of HMRC monthly spending disclosures covering January 2023 to December 2025. The project examines payment trends, supplier concentration, expense categories, credits, repeated rows, and month-to-month patterns.

## Highlights

- 36,061 populated payment lines; £7.19bn net reported spend across the three years.
- Net spend fell 8.3% in 2024, then rose 6.5% in 2025; 2025 remained 2.4% below 2023.
- The 12 largest analytical supplier groups account for 58.4% of positive payment-line amounts.
- Exact repeated rows were retained. A sensitivity check shows their potential effect is small relative to annual net spend.
- Atos and Eviden are shown as separate analytical groups; supplier roll-ups are documented and should not be read as verified legal-entity relationships.

## Project files

- [Stakeholder report](reports/eda_report.md) — findings, methods, limitations, and all ten core charts.
- `reports/figures/` — chart images packaged with the report.
- `analysis/run_eda.py` — Python script used to generate the analysis figures.
- `analysis/supplier_name_mapping.csv` — auditable source-label to analytical-group mapping.

The public [HMRC spending over £25,000 collection](https://www.gov.uk/government/collections/hmrc-spending-over-25000) is the data source. The raw monthly CSVs and cleaned working dataset are not included in this report package.

## Interpretation

This is descriptive exploratory analysis, not a financial audit. Published line amounts are VAT-inclusive and use payment dates; the disclosure does not represent all HMRC spending. Supplier grouping and duplicate sensitivity are analytical aids, not corrections to HMRC's published records.
