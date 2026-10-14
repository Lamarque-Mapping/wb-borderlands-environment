# Rural access QGIS review setup

Download and double-click **Setup_SEDAC_Rural_Access.cmd**. Keep the smaller `SEDAC_RAI_for_Codex_*.zip` in Downloads. If it is elsewhere, drag that ZIP onto the launcher.

The launcher uses Python bundled with your installed QGIS. It needs no extra downloads or Python packages. It reads the latest matching subset ZIP, checks all 58 audited source records, creates four processed cluster layers, and saves a separate timestamped review copy beside `Public Experiment.qgz`. It opens that copy in QGIS and opens the results folder.

**Upload `RAI_SETUP_REPORT.zip` from that folder to Codex next.** This small report contains processing and project-creation checks, source IDs and geometry hashes. It contains no project, data-layer files or local folder paths. QGIS opening is recorded as requested; it is not proof that the GUI finished loading.

The existing project and source ZIP remain unchanged. The review copy has a new first group, **Rural access | SEDAC source boundaries**. Mandera is first and visible; the other three new cluster layers are initially off. The same five percentage bands apply in every cluster: 0–<20%, 20–<40%, 40–<60%, 60–<80%, and 80–100%. Grey indicates no computable value.

These are **GADM v3.6 source admin2 polygons**, retained in full. They have not been assigned to the website’s current administrative polygons. All original fields and the original shapefile record ID (`__wb_source_fid`) remain in the processed data. Supplied Exact/Partial/Proxy labels remain as raw provenance without assuming a join, clipping or weighting treatment. Unnamed source labels remain unchanged.

The audit yields 57 valid percentages and one no-data unit: Kenya / West Pokot / `unknown 8`. The source has zero rural population and indicator code `-9998` for that unit. Its derived rate, share and beyond-2-km values are NULL, not zero.

The indicator uses WorldPop 2020 population, GHSL 2015 settlement classification, and OpenStreetMap roads downloaded on 31 March 2022. All-season road condition is inferred from OSM tags. The 2023 label is the dataset release, not a common 2023 observation date. The rate measures proximity to those roads, rather than journey time.

Source: CIESIN, Columbia University (2023), *SDG Indicator 9.1.1: Rural Access Index (RAI), 2023 Release*, NASA SEDAC. [DOI: 10.7927/fcre-m572](https://doi.org/10.7927/fcre-m572).

`test_setup.py` tests the embedded processing code against the actual uploaded subset with GDAL, including field/ID/WKB preservation, ratio validation, no-data handling, altered-input rejection and report packaging. `setup_validation.json` records those results and the final launcher SHA-256. Windows CMD/PowerShell, QGIS project creation and automatic GUI opening have not been executed in this environment; the first local run checks those parts.

If setup stops, the console reports the failed check and the results folder contains `setup_report.json` plus a small `RAI_SETUP_REPORT.zip` where available. Existing unavailable project layers are listed in the report; the launcher does not guess replacement data paths.
