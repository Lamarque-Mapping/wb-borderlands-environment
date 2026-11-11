# Four-cluster presentation figures

These scripts document the 11 November 2026 figure build from the published map payloads. Work from a staging directory containing `live_repo/` (a checkout) and `work/`. Copy these scripts to `work/`, then run `python work/unpack_live.py`. Download Natural Earth's `ne_50m_admin_0_countries.geojson` to `work/`. Run `python work/build_maps.py` (rename `render_maps.py` to `build_maps.py` when staging). Outputs are written to `deliverables/`.

Dependencies: Python, numpy, scipy, matplotlib, shapely, pyproj, rasterio, cryptography. Use the source commit in `audit.json` to reproduce the original inputs. `check_drought_source.py` expects the HDX CKAN package-search response in `work/hdx_search.json`; it downloads a regional window of the matching source raster. `audit_source.py` checks native pixel-centre coverage in the exported hexagons.

The figures use the existing footprints and 10 km hazard summaries. The 25 km ACLED kernel has a shared regional scale. Cross-cluster record copies are deduplicated by complete exported feature because the public export omits event IDs. Missing climate cells remain missing. The audit establishes source gaps for 661 of Mandera's 671 missing drought cells; eight contain no native pixel centres and two have only one valid pixel each.
