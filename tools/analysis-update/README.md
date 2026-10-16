# Analysis order and exports — 16 October 2026

The analysis page now starts with general population and settlement context and progresses to more specialised measures:

1. Population and density
2. Urban settlements and population
3. Built-up area, 2000–2020
4. Land-cover composition
5. Relative deprivation
6. Rural road access
7. Access to healthcare
8. Recorded violence
9. Historical humid heat
10. Project coverage
11. Sources and limitations

Section links, numbering and DOM order agree. The comparison geography controls stay at the top.

Every analysis has Export data (CSV) and Export chart (PNG), in the same position below its heading. The sources table also has CSV export, including source URLs. CSV files retain original numerical precision, explicit units, source dates, geographical identity and missing values. The six original comparison charts export the same sorted/filtered rows used to render them. Project exports count distinct families by the selected grouping and include the matching family IDs. Rural access, deprivation and heat exports include their four visible overview summaries separately from the selected detail rows using `record_type`; these must not be added together. Rural source-unit boundaries and denominators remain distinct from clipped cluster geography.

Chart export snapshots the chosen section at click time, expands scrollable data, retains legends, source notes and current controls as text, and produces a white framed PNG with attribution and date. It uses the existing, locally hosted html-to-image library. Output is normally 2× CSS resolution, bounded to 16,000 pixels in height and 24 megapixels to limit memory use. It does not alter the displayed chart. Download links remain available beside the section after automatic download.

No data, calculations, map pages or source values were changed. Four existing data download controls were replaced by the common toolbar and enhanced with source context.

## Reproduction and checks

`patch.py` expects the deployed, decoded analysis page and existing module versions under `baseline/`; `boot.json` and the decoded manifest belong beside it. Recover these from the precise pre-change Git commit, using the public boot key and original asset metadata. `core-exports.js` is inserted within the existing analysis closure to reuse its source data and filters. `package.py` changes only the `page/analysis` manifest entry and preserves every data and map descriptor.

Run `python patch.py`, `python check_structure.py`, and `node check_exports.cjs` with decoded analysis summary, geography, SEDAC and rural-access JSON fixtures under `baseline/`. The functional checks exercise the actual page and module code in a lightweight DOM harness, then verify filters, source values, missing denominators, partial-month flags, overview/detail records and CSV encoding. Browser rendering and PNG generation are checked separately on the deployed page.
