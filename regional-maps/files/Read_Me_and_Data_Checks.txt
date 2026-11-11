WORLD BANK BORDERLANDS — FOUR-CLUSTER PRESENTATION MAPS
Prepared 11 November 2026

CONTENTS
01_Four_Priority_Clusters.png — locator map with all four clusters named and shaded distinctly; shared Moyale–Borana/Mandera footprint is hatched.
02_ACLED_Event_Concentrations.png — regional concentration of recorded events.
03_Drought_and_Flood_Hazards.png — paired drought and river-flood overview.
04_Drought_Hazard.png and 05_River_Flood_Hazard.png — full-size individual panels.

All PNGs are 3840 × 2160 pixels (16:9). Insert at full slide width, preserving the aspect ratio. The individual hazard panels provide more detail if the paired figure is too small for the presentation room.

VERSION AND GEOGRAPHY
Figures use the data in the published wb-borderlands-environment repository at commit 26c41bc, checked on 11 November 2026. The source cluster data carry build ID 20260911_142548. The website interface had subsequent updates through 29 October 2026.

The four existing programme footprints are retained: Karamoja, Moyale–Borana, Mandera Triangle and Dikhil. Moyale–Borana and Mandera overlap; they are not mutually exclusive geographic units. Invalid polygon artefacts were repaired for drawing, without replacing the programme boundaries. Existing OCHA COD-AB border lines are overlaid inside the clusters; Natural Earth supplies regional context. All figures use the same regional extent and a Lambert azimuthal equal-area projection centred on 38°E, 6.8°N.

ACLED
The source period is 1 August 2020–1 August 2025. All event types retained in the published maps are included: battles, explosions/remote violence, violence against civilians, riots and protests. Each event has equal weight; this is not a fatalities map or a population-adjusted rate.

The four exports contain 2,683 records. Five repeated copies across cluster exports were removed, leaving 2,678 distinct exported records. The public map payloads omit ACLED event IDs, so matching uses each complete exported record, including geometry, date, actors and narrative notes. Identical records occurring more than once within an individual export retain their maximum within-export multiplicity.

The heat surface uses a 25 km Gaussian bandwidth, a 2 km calculation grid and one common legend, expressed as smoothed events per 1,000 km² over the full period. Only events present in the four cluster exports contribute. The surface is masked to their combined footprint; concentrations close to the outer boundary omit any events outside it. Reporting and location precision vary. Low density is not proof of safety or an absence of violence.

DROUGHT AND FLOOD
Drought source: Weller, Daniel & Mann, Holger (2022), Global Drought Hazard. Produced by the Institute for International Law of Peace and Armed Conflict (IFHV), Ruhr University Bochum; distributed through the Humanitarian Data Exchange (HDX). Its climate inputs come from CSIC’s Global SPEI Database. The World Bank Data Catalog is a catalogue listing, not the original producer.

Drought values represent modelled months at SPEI ≤ −2.0 for a 25-year return period. The source climate series covers 1902–2018. River-flood values represent modelled inundation depth in metres for the historical 25-year-return-period scenario. These are hazard surfaces, not forecasts, climate-change projections or estimates of the people exposed.

The drought resource explicitly describes its units as the number of months at SPEI −2.0 or lower for a 25-year return period. This is a statistical model output, not an observed spell length or a prediction of consecutive dry months. The available metadata does not justify interpreting a value as a single continuous event. Fractional values reflect the modelled/interpolated surface and spatial averaging. The underlying SPEI uses a six-month accumulation window; that is distinct from the output unit.

The source climate grid is approximately 0.5 degrees; interpolation to a finer published raster and presentation in 10 km hexagons do not create local climate information. Treat the drought panel as an illustration of this global product, not a basis for local targeting or a reliable ranking of the clusters.

The figures retain the published 10 km hexagon means. In overlapping programme footprints, valid estimates are averaged for the overview display; a missing estimate never overwrites a valid one. Both panels use common absolute classes across all four clusters. Flood depth is a mean over a hexagon, not the maximum depth along a river. No arbitrary combined drought/flood score is calculated.

GREY MANDERA HEXAGONS
Grey means no valid exported numeric value. It does not mean zero. The current Mandera export has 671 missing drought cells out of 2,638 (25.4%). River flooding has seven missing cells and 2,048 recorded zero values. Walking and motorised healthcare access each have seven missing cells.

A direct native-pixel check against the publisher's matching global SPEI-2.0, 25-year raster found:
• 661 of Mandera's 671 missing cells contain source pixels but none with valid values.
• Eight contain no source pixel centres, owing to small clipped cell footprints.
• Two contain only one valid source pixel each, among 80 and 75 source pixels respectively. Those sparse edge observations have not been used to fill the published gaps.

The publisher's raster defines a NoData value near −3.4 × 10^38. This check used the matching public global product, rather than the original local Africa crop. It establishes that the overwhelming majority of the Mandera gaps already exist in the underlying product. Complete coverage in another dataset would not imply complete drought coverage.

The same check was run across all four clusters. Full counts are in Map_Data_Audit.json and Source_Drought_Coverage_Check.json. No missing hazard observations have been imputed or converted to zero.

SOURCE LINKS
Current maps: https://lamarque-mapping.github.io/wb-borderlands-environment/
Repository: https://github.com/Lamarque-Mapping/wb-borderlands-environment
ACLED: https://acleddata.com/
Drought dataset: https://data.humdata.org/dataset/global-drought-hazard
Drought resource ID: 3d067bc4-e6bd-413e-a490-2010aa842a63
World Bank metadata: https://datacatalog.worldbank.org/search/dataset/0067121/global-drought-hazard-based-on-spei
Flood dataset: https://datasets.wri.org/datasets/aqueduct-floods-hazard-maps
Basemap: https://www.naturalearthdata.com/
