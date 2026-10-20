# Primary-road proximity · 20 October 2026

The map uses every feature in each published `primaryRoads` layer. Download the source raster from the URL in `data/primary-road-population.json`, then run:

    python calculate.py --input inputs --raster /path/to/global_pop_2025_CN_1km_R2025A_UA_v1.tif --output output

Dependencies: Python, numpy, rasterio, shapely >=2, pyproj. Input SHA-256 hashes are recorded in each cluster's validation. Inputs reproduce the published layer geometry and attributes. Population TIFF windows retain original grid alignment and values without resampling.

Cluster mode uses all mapped primary roads inside the cluster. Country mode first clips the roads to a country within the cluster, buffers them by 10 km, then clips to the same country territory. Its population denominator is that territory, not the whole country. Dissolved buffers count overlap once. Cluster proximity includes cross-border effects, so national inside counts need not sum to the cluster inside count. Gaps and overlaps remain unassigned. Tiny country fragments under 1 km² without a mapped primary road are retained in CSV and totals but omitted from comparison controls.

The JSON records source provenance, limitations and numerical checks. The source count raster is a modelled 2025 estimate. 10 km is a chosen straight-line width, not observed access or a standard operational catchment. Web geometries are simplified by 20 m; calculations use the original published geometries. Roads outside the cluster are excluded. The older named Mandera pilot is retained in the repository's prior data files and version history.
