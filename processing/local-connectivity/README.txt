Run aggregate.py with Python 3 and Shapely 2.x:
python aggregate.py INPUT_DIRECTORY OUTPUT_DIRECTORY

The input directory must contain the published asset JSONs named
<cluster>_connectivity.json, <cluster>_admin.json and <cluster>_core.json.
Cluster codes: mandera_triangle, moyale_borana, karamoja, dikhil.
Source snapshot: aaad6e20adc215e2c84d06114f866fe6a065f92d in this repository.
The public boot.json manifest exposes the asset descriptors and public key.
Input SHA-256 values are recorded in data/local-connectivity/validation.json.

This aggregation preserves the original path calculations and raw junction IDs.
District assignment uses original admin 2 polygons, repaired in derived memory
with Shapely make_valid where needed. Geometries are clipped to the cluster and
simplified by 0.00015 degrees only for map display. No input file is overwritten.
Duplicate IDs, unreconciled totals or invalid shares stop the script.
Boundary assignment issues, if any, stay unassigned and are recorded in validation.
The web release was checked with zero such assignment issues for every cluster.
