# Rural road access

Each cluster map has **Travel time / access → Rural road access**. It displays the SEDAC source admin 2 polygons using five common percentage bands. Select a source unit on the map or in the dropdown to see its rate and modelled rural population. The selection can be cleared with × or a blank map click; switching views clears the layer.

All 58 supplied units are included: 15 Mandera Triangle, 5 Moyale/Borana, 27 Karamoja, and 11 Dikhil. There are 57 valid rates. West Pokot's `unknown 8` has a zero rural denominator and SEDAC code `-9998`, so it appears as no data. The other unknown labels are retained as they appear in the source.

Rates stay with their original GADM v3.6 source polygons. These differ from the OCHA administrative references used elsewhere in the maps. A displayed rate describes the whole source unit, including its area outside a focal cluster. No district rates have been copied by name or apportioned through polygon area.

The indicator is the percentage of modelled rural population within 2 km of roads classified as likely all-season. It uses WorldPop 2020, GHSL 2015 settlement classification and OSM roads downloaded on 31 March 2022. All-season status is inferred from OSM tags. **2023 is the release label**, and the 2 km measure expresses geographic proximity.

Source: CIESIN, Columbia University (2023), *SDG Indicator 9.1.1 Rural Access Index (RAI), 2023 Release*, NASA SEDAC. [DOI and documentation](https://doi.org/10.7927/fcre-m572).

The source-unit geometry and raw attributes were verified against the returned GeoPackage and setup report. GeoJSON encoding preserves every source geometry's exact WKB on roundtrip. Rural-access assets load only when requested. The existing travel view remains the initial access choice.

The junction method now describes its **10 km grid as a chosen starting scale for exploratory comparison**, rather than an operational catchment standard. The grid size, local-path search distances and junctions per 10 km of road remain separate quantities.

The data export and packaging commands are in `build_live_assets.py`. The deterministic page patch accepts `--source DECRYPTED_PAGE_DIRECTORY --output WORKING_DIRECTORY`. Validation files record the returned-data checks, export checks, page tests and encrypted packaging checks. The map update uses the existing vault and access configuration.
