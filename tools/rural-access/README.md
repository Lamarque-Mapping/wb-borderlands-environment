The extractor produces a small source-data ZIP from the downloaded SEDAC 2023 shapefile archive. It selects Djibouti, Ethiopia, Kenya, Somalia, South Sudan and Uganda, retaining full source polygons and fields so names, IDs, missing values and historical boundaries can be checked before a map join.

Download `Extract_SEDAC_RAI.cmd` and double-click it. It looks for the SEDAC archive in Downloads and uses an installed QGIS Python launcher. If the archive is elsewhere, drag the ZIP onto the launcher. The resulting `SEDAC_RAI_for_Codex_*.zip` appears beside the original archive; the containing folder opens when processing finishes.

The script opens the source read-only. It makes no network requests, installs no packages, starts no QGIS GUI, and does not modify the archive or QGIS project. Output is a GeoPackage plus a report and small source documentation files. Source FIDs are added in a separate column; input attributes are preserved. It does not interpret the supplied spreadsheet's Exact/Partial/Proxy flags or resolve any unnamed district.

Country selection uses recognised country-name/code fields. If none can be recognised, a conservative East Africa spatial envelope is used and recorded, while retaining the full intersecting polygons. Unsupported CRS/schema problems produce a small inspection report rather than guessed joins. If the new ZIP remains too large to attach, upload only `extraction_report.json` from the new output folder for a narrower follow-up selection.

The embedded Python is tested with synthetic shapefiles for source-field, missing-value and geometry preservation. The Windows bootstrap and the user's actual global archive require validation on the user's computer.
