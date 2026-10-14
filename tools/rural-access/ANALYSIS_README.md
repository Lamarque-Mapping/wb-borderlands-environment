# Rural access on the analysis page

The analysis section uses the 58 audited SEDAC source units already mapped. It starts with four population-weighted summaries of the **supplied whole-source-unit selections**, then shows ranked source-unit percentages on a fixed 0–100% scale. Rural population denominators are visible beside every row. The section has its own cluster and country/side controls because its geography differs from the clipped study areas elsewhere on the page.

The four summaries are 56.284139362984774% (Moyale–Borana), 29.606867675637574% (Mandera Triangle), 45.223804910940565% (Karamoja) and 36.99197821186931% (Dikhil). These must not be described as access estimates for the clipped cluster boundaries. Each is `100 * sum(Pop_A2_R2K) / sum(Pop_A2_R)` over valid selected units. No selection-tag or area-overlap weights are used. No values were transferred to current OCHA districts.

All 58 records remain in the comparison and CSV export. West Pokot `unknown 8` (source ID `sedac2023:21174`) has an undefined percentage and zero rural denominator. It is displayed as unavailable and excluded from summaries. No unknown names were replaced. Exact original values are exported; displayed rates use one decimal place and modelled population counts are rounded to whole people.

Each source-unit name links to its own rural-access map with the source ID selected and its polygon framed. All four map source tables explain the aggregation and geography. The analysis page includes the same source table.

## Rebuild

`build_analysis.py` expects the decrypted baseline at commit `927b510566dfa32c24452b20a77970b1b0865568`: `analysis.html`, four `page_map_CODE.html` files, `boot.json` and `manifest.json`. The `--data` directory must contain the four audited `CODE_ruralAccess.json` exports from the Stage 2 package. Source geometry assets are reused unchanged.

```sh
python tools/rural-access/build_analysis.py --input BASELINE_CACHE --data AUDITED_EXPORTS --output RELEASE_DIRECTORY
```

The script writes a sibling `working` directory and `changes.json`. Only paths in that changes list belong in the release. The build does not publish. The editable section template is beside the script; browser code and styles are in `analysis/rural-access-v1.js` and `.css`.

Validation checks preserve the 58 unique source IDs and source fields, recompute each rate from the source population counts, preserve all unrelated manifest entries, and round-trip encrypted assets. Separate numerical tests check unequal population weights, the missing denominator, sorting and CSV quoting. Live UI verification is required after deployment.
