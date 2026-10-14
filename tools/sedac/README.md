# SEDAC additions: source-preserving web integration

This update adds GUPPD urban settlements, GRDI relative deprivation, and GEHE historical humid heat to the four existing borderland maps and analysis page. The Rural Access Index and earlier project, FEWS, road and environmental layers remain intact.

## Sources and interpretation

- GUPPD v1 (2024), https://doi.org/10.7927/brq1-xc29: circa-2015 settlement footprints; displayed population is the GHSL R2023 model estimate for 2020 inside the whole source footprint. It is not a current municipal census. The cohort is selected by representative points inside each cluster and paired with full footprints by ISO and SMOD_ID. Border-intersecting polygons with representative points outside the cluster are excluded. Overlapping cluster cohorts must not be summed.
- GRDI v1 (2022), https://doi.org/10.7927/3xxe-ap97: 0–100 relative deprivation, with source inputs from 2010–2020. Coverage depends on the source building-footprint mask. Missing pixels remain missing. Means and histograms describe valid mapped area, weighted by approximate grid-cell area, not population. This is not a poverty percentage or a defensible ranking of residents' poverty.
- GEHE (2023), https://doi.org/10.7927/hff0-k565: daily maximum WBGT threshold exceedance counts for 1983–2016, at 28/30/32°C WBGT. WBGT is not ordinary air temperature. Each historical mean uses all 34 annual files, with a complete-record mask. Annual area averages use fixed valid pixels. Zero and missing data remain distinct. Historical conditions do not describe current exposure or health outcomes.

All three sources are supplied under CC BY 4.0. Attribution, dates and limitations are also in every map's sources table and the analysis page. Source values are not interpolated or converted into administrative-unit estimates. Display bands are chosen for presentation, not official classification thresholds.

## Data processing and audit

`build_data.py` requires Python with GDAL and NumPy. It expects the returned regional `SEDAC_ADDITIONS_FOR_CODEX.zip` extracted into an adjacent `input` directory, including `setup_report.json`, and the original ZIP in `../upload/SEDAC_ADDITIONS_FOR_CODEX.zip`. It checks vector field/FID/geometry hashes against the preparation report, pairs source point/polygon records, independently recomputes each 34-year heat mean, checks annual count ranges, and writes native-grid values, nearest-neighbour display images and analysis summaries. See `audit.json` for the input ZIP hash and results. No user's Windows path or original QGIS project is published.

The four settlement counts are Mandera 77, Moyale/Borana 49, Karamoja 98 and Dikhil 18. GRDI covers approximately 16.2%, 10.4%, 11.7% and 13.1% of the respective cluster areas; gaps are explicitly excluded from summaries. Cell-centre boundary selection and spherical cell areas make geographic summaries approximate.

`patch_site.py` applies explicit single-occurrence changes to the prior page sources and checks JavaScript syntax. `package_site.py` preserves the existing public vault architecture, makes new assets and updates only the four map pages, analysis page and five new data groups. These scripts use the project workspace baseline directories named in the code; they are build provenance, not a standalone end-user installer. `baseline_validation.json` verifies those original pages against pinned GitHub commit `7b6f221c2960e1ad9217be8733212104bf6e1a59`. `package_validation.json` records encryption/decryption roundtrips and unchanged manifest entries.

## Website controls

- Corridors & infrastructure → Towns & transport → Town source → Urban footprints & population · SEDAC. OpenStreetMap remains the default town display. The junction metric continues to use its existing town source.
- Population → Relative deprivation · SEDAC. Click a cell for its native source value.
- Environment → Historical humid heat. Choose the WBGT threshold and click a cell for its 34-year mean.
- Analysis → SEDAC context. Settlement table, mapped-deprivation distributions, annual heat chart and CSV downloads use their own cluster selector.

Direct links use `?view=urban#map=karamoja`, `?view=deprivation#map=mandera_triangle`, or `?view=heat&heatThreshold=30#map=dikhil`. An optional `settlement=ISO:SMOD_ID` selects a source footprint. These settings do not modify the existing rural-access or corridor defaults.
