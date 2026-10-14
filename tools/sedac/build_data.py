"""Audit returned SEDAC subsets and export web data without changing source values."""
import base64
import hashlib
import json
import math
from pathlib import Path
import re
import sys
import zipfile
import numpy as np
from osgeo import gdal, ogr, osr

ROOT = Path(__file__).resolve().parent
INPUT = ROOT / 'input'
OUT = ROOT / 'data'
OUT.mkdir(exist_ok=True)
gdal.UseExceptions()
ogr.UseExceptions()
osr.UseExceptions()
REPORT = json.loads((INPUT / 'setup_report.json').read_text())
CODES = ['mandera_triangle', 'moyale_borana', 'karamoja', 'dikhil']
LABELS = ['Mandera Triangle', 'Moyale / Borana', 'Karamoja', 'Dikhil']
GRDI = [(50, '0–50', '#f1eef6'), (75, '>50–75', '#bdc9e1'), (90, '>75–90', '#74a9cf'),
        (95, '>90–95', '#2b8cbe'), (100, '>95–100', '#045a8d')]
HEAT = [(0, '0', '#fff7d9'), (7, '>0–7', '#fee391'), (30, '>7–30', '#fec44f'),
        (90, '>30–90', '#fe9929'), (180, '>90–180', '#ec7014'), (366, '>180', '#993404')]


def write(path, document):
    path.write_text(json.dumps(document, ensure_ascii=False, separators=(',', ':'), allow_nan=False))


def valid(ds):
    b = ds.GetRasterBand(1)
    a = b.ReadAsArray()
    no = b.GetNoDataValue()
    return a, np.isfinite(a) & (a != no)


def cutmask(outline, ds):
    shape = ogr.CreateGeometryFromJson(json.dumps(outline['features'][0]['geometry']))
    s = osr.SpatialReference(); s.ImportFromEPSG(4326); shape.AssignSpatialReference(s)
    v = ogr.GetDriverByName('Memory').CreateDataSource('')
    l = v.CreateLayer('mask', s, ogr.wkbUnknown)
    f = ogr.Feature(l.GetLayerDefn()); f.SetGeometry(shape); l.CreateFeature(f)
    m = gdal.GetDriverByName('MEM').Create('', ds.RasterXSize, ds.RasterYSize, 1, gdal.GDT_Byte)
    m.SetProjection(ds.GetProjection()); m.SetGeoTransform(ds.GetGeoTransform())
    gdal.RasterizeLayer(m, [1], l, burn_values=[1])
    return m.ReadAsArray().astype(bool)


def weights(ds):
    gt = ds.GetGeoTransform()
    top = gt[3] + np.arange(ds.RasterYSize) * gt[5]
    bottom = top + gt[5]
    row = 6371.0088**2 * math.radians(gt[1]) * (np.sin(np.radians(top)) - np.sin(np.radians(bottom)))
    return np.repeat(row[:, None], ds.RasterXSize, axis=1)


def image_raster(ds, bands):
    warped = gdal.Warp('', ds, format='MEM', dstSRS='EPSG:3857', resampleAlg='near',
                       width=ds.RasterXSize, height=ds.RasterYSize)
    a, v = valid(warped)
    classes = np.digitize(a, [x[0] for x in bands], right=True)
    rgba = np.zeros((4, *a.shape), dtype='uint8')
    for i, (_, _, colour) in enumerate(bands):
        match = v & (classes == i)
        for channel in range(3): rgba[channel][match] = int(colour[1 + channel*2:3 + channel*2], 16)
        rgba[3][match] = 235
    mem = gdal.GetDriverByName('MEM').Create('', a.shape[1], a.shape[0], 4, gdal.GDT_Byte)
    for i in range(4):
        mem.GetRasterBand(i+1).WriteArray(rgba[i])
        mem.GetRasterBand(i+1).SetColorInterpretation([gdal.GCI_RedBand,gdal.GCI_GreenBand,gdal.GCI_BlueBand,gdal.GCI_AlphaBand][i])
    png = gdal.GetDriverByName('PNG').CreateCopy('/vsimem/sedac_preview.png', mem)
    png = None
    h = gdal.VSIFOpenL('/vsimem/sedac_preview.png', 'rb'); gdal.VSIFSeekL(h, 0, 2); n = gdal.VSIFTellL(h); gdal.VSIFSeekL(h, 0, 0)
    raw = bytes(gdal.VSIFReadL(1, n, h)); gdal.VSIFCloseL(h); gdal.Unlink('/vsimem/sedac_preview.png')
    gt = warped.GetGeoTransform()
    a_srs = osr.SpatialReference(); a_srs.ImportFromEPSG(3857)
    b_srs = osr.SpatialReference(); b_srs.ImportFromEPSG(4326); b_srs.SetAxisMappingStrategy(osr.OAMS_TRADITIONAL_GIS_ORDER)
    tx = osr.CoordinateTransformation(a_srs, b_srs)
    west, north, _ = tx.TransformPoint(gt[0], gt[3])
    east, south, _ = tx.TransformPoint(gt[0]+warped.RasterXSize*gt[1], gt[3]+warped.RasterYSize*gt[5])
    return 'data:image/png;base64,' + base64.b64encode(raw).decode(), [[south, west], [north, east]]


def raster_doc(file, outline, bands):
    ds = gdal.Open(str(INPUT / file)); a, v = valid(ds); mask = cutmask(outline, ds)
    assert not np.any(v & ~mask), file
    w = weights(ds)
    shown_area, total_area = float(w[v].sum()), float(w[mask].sum())
    values = a[v]
    assert values.size > 0
    png, bounds = image_raster(ds, bands)
    histogram = []
    indexes = np.digitize(a, [b[0] for b in bands], right=True)
    for i, (_, label, colour) in enumerate(bands):
        histogram.append({'label':label, 'colour':colour, 'area_share':float(w[v & (indexes == i)].sum()/shown_area)})
    result = {'file':file, 'grid':list(ds.GetGeoTransform()), 'width':ds.RasterXSize, 'height':ds.RasterYSize,
              'cells':[[int(i), float(a.ravel()[i])] for i in np.flatnonzero(v)], 'image':png, 'bounds':bounds,
              'bands':[{'upper':x,'label':label,'colour':colour} for x,label,colour in bands],
              'summary':{'valid_cells':int(v.sum()), 'cluster_cells':int(mask.sum()),
                         'coverage_share':shown_area/total_area, 'min':float(values.min()), 'max':float(values.max()),
                         'area_mean':float(np.sum(values*w[v])/shown_area), 'histogram':histogram}}
    # Reconstruct every exported native pixel; verify no index/value shifts or quantisation.
    for index, value in result['cells']: assert a.ravel()[index] == value
    return result, (ds, a, v, w)


def usable(value):
    return isinstance(value, str) and value.strip() and value.strip().lower() not in ('n/a','na','null','none','unknown','-9999')


def name_of(p):
    for k in ['CIESIN_NAME_ADJ', 'JRC_NAME_MAIN', 'CIESIN_NAME_TL', 'CIESIN_NAME']:
        if usable(p.get(k)): return p[k].strip(), k
    return 'Unnamed settlement · ' + str(p['SMOD_ID']), None


def vector_records(vr):
    ds = ogr.Open(str(INPUT / vr['file'])); layer = ds.GetLayerByName(vr['layer'])
    fields = vr['source_fields']; digest = hashlib.sha256(); rows = []
    for f in layer:
        p = f.items(); g = f.GetGeometryRef()
        record = [p[vr['source_fid_field']], [p[k] for k in fields], bytes(g.ExportToWkb()).hex()]
        digest.update(json.dumps(record, sort_keys=True, default=str).encode())
        rows.append({'type':'Feature','geometry':json.loads(g.ExportToJson()),'properties':p})
    assert digest.hexdigest() == vr['content_sha256'], vr['file']
    assert len(rows) == vr['records']
    return rows


def build():
    assert REPORT['status'] == 'complete' and not REPORT['warnings']
    summary = {'format':'wb-sedac-summary-v1', 'clusters':[], 'sources':REPORT['sources']}
    audit = {'status':'passed', 'input_zip_sha256':hashlib.sha256((ROOT.parent/'upload/SEDAC_ADDITIONS_FOR_CODEX.zip').read_bytes()).hexdigest(),
             'source_setup_complete':True, 'vector_hashes_verified':[], 'heat_means_verified':[], 'maps':[]}
    for code, label in zip(CODES,LABELS):
        outline = json.loads((INPUT/code/'cluster_outline.geojson').read_text())
        vectors = [r for r in REPORT['vectors'] if r['cluster'] == code]
        points = vector_records(next(r for r in vectors if r['geometry_type']=='Point'))
        polygons = vector_records(next(r for r in vectors if r['geometry_type']!='Point'))
        audit['vector_hashes_verified'].extend([r['content_sha256'] for r in vectors])
        key = lambda p: str(p['ISO']) + ':' + str(p['SMOD_ID'])
        poly_lookup = {key(f['properties']):f for f in polygons}
        selected_polys, summary_towns, ids = [], [], set()
        for f in points:
            p = f['properties']; uid = key(p); assert uid not in ids; ids.add(uid)
            poly = poly_lookup[uid]
            for field in ['GHSPOP_R23_2020','SMOD_LEVEL','ISO']: assert p[field] == poly['properties'][field]
            p['sedac_id'] = uid; p['display_name'], p['display_name_source'] = name_of(p)
            p['population_2020'] = p['GHSPOP_R23_2020'] if p['GHSPOP_R23_2020'] is not None and p['GHSPOP_R23_2020'] >= 0 else None
            p['settlement_type'] = {'30':'Urban centre','23':'Dense urban cluster','22':'Semi-dense urban cluster'}[str(p['SMOD_LEVEL'])]
            f['id'] = uid
            selected_polys.append({'type':'Feature','id':uid,'properties':{'sedac_id':uid},'geometry':poly['geometry']})
            summary_towns.append({'id':uid,'name':p['display_name'],'country':p['CNTRY_NAME'],'population_2020':p['population_2020'],
                                  'area_sqkm':p['AREA_SQKM'], 'type':p['settlement_type'], 'coordinates':f['geometry']['coordinates']})
        gr = next(r for r in REPORT['rasters'] if r['cluster']==code and r['kind']=='grdi')
        grdi, _ = raster_doc(gr['file'], outline, GRDI)
        heat = {}; yearly = {}
        for threshold in (28,30,32):
            m = next(r for r in REPORT['heat_means'] if r['cluster']==code and r['threshold_wbgt_c']==threshold)
            result, (ds,a,v,w) = raster_doc(m['file'], outline, HEAT)
            sum_values = np.zeros_like(a); valid_all = np.ones_like(v); annual = []
            source_rows = [r for r in REPORT['rasters'] if r['cluster']==code and r['kind']=='heat'+str(threshold)]
            assert len(source_rows)==34
            seen = set()
            for r in sorted(source_rows,key=lambda r:r['source_member']):
                match = re.fullmatch(r'wbgtmax'+str(threshold)+r'\.count\.(\d{4})\.tif', Path(r['source_member']).name, re.I)
                assert match, r['source_member']; year = int(match[1]); assert year not in seen; seen.add(year)
                annual_ds = gdal.Open(str(INPUT/r['file'])); values, ok = valid(annual_ds)
                assert annual_ds.GetGeoTransform() == ds.GetGeoTransform() and values.shape == a.shape
                assert np.all(values[ok] >= 0) and np.all(values[ok] <= (366 if year%4==0 else 365))
                sum_values += np.where(ok, values, 0); valid_all &= ok
                assert np.all(ok[v])
                annual.append({'year':year, 'area_mean_days':float(np.sum(values[v]*w[v])/w[v].sum())})
            assert seen == set(range(1983,2017)) and np.array_equal(valid_all,v)
            assert np.array_equal((sum_values/34)[v], a[v])
            audit['heat_means_verified'].append({'cluster':code,'threshold':threshold,'years':34,'values_exact':True})
            heat[str(threshold)] = result; yearly[str(threshold)] = sorted(annual,key=lambda x:x['year'])
        data = {'format':'wb-sedac-v1','code':code,'label':label,'sources':REPORT['sources'],
                'settlements':{'type':'FeatureCollection','features':points},
                'footprints':{'type':'FeatureCollection','features':selected_polys},
                'settlement_cohort':'Source representative points inside the cluster; whole circa-2015 footprints retained.',
                'excluded_polygon_only_records':len(polygons)-len(points),'grdi':grdi,'heat':heat}
        write(OUT/(code+'_sedac.json'), data)
        summary['clusters'].append({'code':code,'label':label,'towns':sorted(summary_towns,key=lambda x:-(x['population_2020'] or 0)),
                                    'grdi':grdi['summary'],'heat':{k:{**x['summary'],'annual':yearly[k]} for k,x in heat.items()}})
        audit['maps'].append({'code':code, 'settlements':len(points),'polygons':len(selected_polys),
                             'grdi_coverage_share':grdi['summary']['coverage_share'],
                             'heat_coverage_share':heat['28']['summary']['coverage_share'],
                             'web_json_bytes':(OUT/(code+'_sedac.json')).stat().st_size})
    write(OUT/'summary.json', summary)
    (ROOT/'audit.json').write_text(json.dumps(audit,indent=2))
    print(json.dumps(audit,indent=2))


if __name__ == '__main__': build()
