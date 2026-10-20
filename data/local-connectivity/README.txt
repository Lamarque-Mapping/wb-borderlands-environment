Local road connectivity: district and country summaries
21 October 2026

Source: the published junction dataset in hughlamarque-dev/wb-borderlands-environment,
commit aaad6e20adc215e2c84d06114f866fe6a065f92d. Road and settlement source:
OpenStreetMap contributors / Geofabrik extracts dated 8 October 2026; ODbL 1.0.
Attribution and licence: https://www.openstreetmap.org/copyright
Boundaries: existing OCHA COD-AB admin 2 polygons published in the same map.

The CSV contains cluster, country-portion and admin 2 rows. These are overlapping
summaries, not additive observations. Clusters also overlap. Do not sum all rows.
Shares are fractions from 0 to 1. A blank share is undefined, not zero.
Each share divides the number of qualifying reachable junctions by the number
of mapped qualifying junctions in that same area. Zero-junction units have no share.
Cities/towns and cities/towns/villages are separate destination definitions.

The junction GeoJSON contains the original source coordinates and OSM node IDs,
10 km reach flags, path lengths where available, destination node IDs and district
IDs. A missing path length means no qualifying route was found within 10 km.
The district GeoJSON contains cluster-clipped outlines simplified for display.
Original source administrative polygons, not simplified outlines, assign nodes.

Major roads are motorway, trunk, primary and links. Qualifying junctions are
shared major/local OSM nodes with at least three statically accessible neighbours.
Nodes are not merged functional interchanges. Directed local motor-access paths
exclude major roads and include a settlement snap of at most 250 m. A 15 km halo
supports the 10 km path search. Conditional access is excluded. Turn restrictions,
live closures and all-season passability are not modelled. The path limit and
10 km grid are chosen analytical scales, not standard project catchments.

District and country membership refers to the junction's location within the
cluster. Paths can leave that district or country. Hexagon values are unchanged
full-cell measures and should not be averaged to produce district shares.
All published junctions have a unique admin 2 assignment in this release.
Tiny boundary fragments under 0.1% of the original polygon's planar area in
source longitude/latitude coordinates, with no junctions, are flagged in the
CSV and retained in the data. They are omitted from the main web comparison.

OSM completeness has not been independently assessed. No mapped junctions, no
mapped major road, or no qualifying route does not establish absence on the ground.
Missing settlement nodes and settlement classifications can also affect results.
Independent imagery or a separate-provenance road inventory is needed to assess
mapping gaps. These figures measure mapped connectivity, not population access,
traffic, feeder-road use, economic effects or project beneficiaries.

validation.json records input hashes, assignment checks and conserved totals.
The live map and Analysis page offer CSV and image exports:
https://hughlamarque-dev.github.io/wb-borderlands-environment/
