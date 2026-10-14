"""Reproducible synthetic tests of the Python embedded in the CMD launcher.

Run using a Python interpreter providing osgeo:
  /usr/bin/python3 tools/rural-access/test_extractor.py

All GIS fixtures and extraction outputs use automatically removed temporary
directories. The launcher is read but never changed by these tests.
"""
import argparse
import hashlib
import json
from pathlib import Path
import re
import sys
import tempfile
import types
import zipfile

from osgeo import gdal, ogr, osr


def sha256(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def load_embedded(launcher):
    text = launcher.read_text(encoding='utf-8')
    marker = re.search(r'(?m)^#WB_SEDAC_PYTHON\r?$', text)
    assert marker is not None, 'Missing whole-line embedded-Python marker.'
    payload = text[marker.end():]
    module = types.ModuleType('wb_embedded_extractor_test')
    module.__file__ = str(launcher)
    exec(compile(payload, str(launcher) + ' [embedded Python]', 'exec'), module.__dict__)
    return module, hashlib.sha256(payload.encode('utf-8')).hexdigest()


def srs(epsg):
    if epsg is None:
        return None
    result = osr.SpatialReference()
    result.ImportFromEPSG(epsg)
    result.SetAxisMappingStrategy(osr.OAMS_TRADITIONAL_GIS_ORDER)
    return result


def polygon(west, south, east, north, epsg=4326):
    result = ogr.CreateGeometryFromWkt(
        'POLYGON (({w} {s},{e} {s},{e} {n},{w} {n},{w} {s}))'.format(
            w=west, s=south, e=east, n=north))
    if epsg != 4326:
        result.Transform(osr.CoordinateTransformation(srs(4326), srs(epsg)))
    return result


def fixture(root, label, fields, records, epsg=4326):
    directory = root / label / 'nested space' / 'Éthiopie'
    directory.mkdir(parents=True)
    dataset = ogr.GetDriverByName('ESRI Shapefile').CreateDataSource(str(directory / 'source admin 2.shp'))
    layer = dataset.CreateLayer('source admin 2', srs=srs(epsg), geom_type=ogr.wkbPolygon,
                                options=['ENCODING=UTF-8'])
    for name, kind in fields:
        field = ogr.FieldDefn(name, kind)
        if kind == ogr.OFTString:
            field.SetWidth(100)
        elif kind == ogr.OFTInteger64:
            field.SetWidth(18)
        elif kind == ogr.OFTReal:
            field.SetWidth(20)
            field.SetPrecision(6)
        assert layer.CreateField(field) == 0
    for values, geometry in records:
        feature = ogr.Feature(layer.GetLayerDefn())
        for name, value in values.items():
            if value is None:
                feature.SetFieldNull(name)
            else:
                feature.SetField(name, value)
        if geometry is not None:
            feature.SetGeometry(geometry)
        assert layer.CreateFeature(feature) == 0
        feature = None
    layer = None
    dataset = None
    (directory / 'README.txt').write_text('Synthetic fixture only.\n', encoding='utf-8')
    archive = root / (label + ' – données with spaces.zip')
    with zipfile.ZipFile(archive, 'w', zipfile.ZIP_DEFLATED) as zipped:
        for path in sorted((root / label).rglob('*')):
            if path.is_file():
                zipped.write(path, path.relative_to(root / label).as_posix())
    return archive, 'nested space/Éthiopie/source admin 2.shp'


def rows(layer, field_names, fid_field=None):
    result = {}
    for feature in layer:
        geometry = feature.GetGeometryRef()
        identity = feature.GetField(fid_field) if fid_field else feature.GetFID()
        result[identity] = {'attributes': {name: feature.GetField(name) for name in field_names},
                            'wkb': bytes(geometry.ExportToWkb()) if geometry is not None else None,
                            'envelope': geometry.GetEnvelope() if geometry is not None else None}
    return result


def original(archive, member):
    dataset = ogr.Open('/vsizip/' + archive.as_posix() + '/' + member, 0)
    assert dataset is not None
    layer = dataset.GetLayer(0)
    definition = layer.GetLayerDefn()
    fields = [(definition.GetFieldDefn(i).GetName(), definition.GetFieldDefn(i).GetType())
              for i in range(definition.GetFieldCount())]
    result = rows(layer, [name for name, kind in fields])
    layer = None
    dataset = None
    return fields, result


def preserved(package, item, fields, expected, epsg=None):
    gpkg = package.with_suffix('') / 'SEDAC_RAI_source_subset.gpkg'
    dataset = ogr.Open(str(gpkg), 0)
    assert dataset is not None
    layer = dataset.GetLayerByName(item['output_layer'])
    definition = layer.GetLayerDefn()
    for name, kind in fields:
        index = definition.GetFieldIndex(name)
        assert index >= 0, 'Source field lost: ' + name
        assert definition.GetFieldDefn(index).GetType() == kind, 'Source field type changed: ' + name
    assert rows(layer, [name for name, kind in fields], item['source_fid_field']) == expected, \
        'Source attributes, FIDs or full geometry changed.'
    if epsg:
        assert layer.GetSpatialRef().GetAuthorityCode(None) == str(epsg)
    layer = None
    dataset = None
    return gpkg


def package_valid(package, report):
    assert package.is_file()
    with zipfile.ZipFile(package) as zipped:
        assert zipped.testzip() is None
        names = zipped.namelist()
        assert 'extraction_report.json' in names and 'READ_ME.txt' in names
        assert json.loads(zipped.read('extraction_report.json')) == report
        assert not any(name.endswith('.shp') for name in names)
    return names


def country_test(extractor, root):
    fields = [('NAME_0', ogr.OFTString), ('NAME_2', ogr.OFTString), ('fid', ogr.OFTInteger64),
              ('zero', ogr.OFTReal), ('rural_pop', ogr.OFTInteger64), ('missing', ogr.OFTReal),
              ('custom', ogr.OFTString), ('__wb_rowid', ogr.OFTInteger)]
    records = []
    for index, country in enumerate(list(extractor.COUNTRIES) + ['Sudan']):
        values = {'NAME_0': country, 'NAME_2': 'unknown 1' if country == 'Kenya' else country + ' district',
                  'fid': 1234567890123 + index, 'zero': 0.0, 'rural_pop': 8765432101234 + index,
                  'missing': None, 'custom': 'Unrecognised source value – café', '__wb_rowid': 100 + index}
        geometry = None if country == 'Uganda' else polygon(35 + index / 10, 2, 35.05 + index / 10, 2.05)
        records.append((values, geometry))
    archive, member = fixture(root, 'country fixture', fields, records)
    before = sha256(archive)
    source_fields, source_rows = original(archive, member)
    expected = {fid: row for fid, row in source_rows.items() if row['attributes']['NAME_0'] in extractor.COUNTRIES}
    package, report = extractor.run_extraction(archive, root / 'outputs', open_folder=False)
    assert report['status'] == 'subset_ready_for_review', report['errors']
    assert report['exported_features_total'] == 6 and not report['errors']
    assert report['countries_not_confirmed_by_attributes'] == []
    item = report['layers'][0]
    assert item['selection_method'] == 'Exact country names/codes in source attributes'
    assert item['countries'] == dict.fromkeys(extractor.COUNTRIES, 1)
    assert item['null_geometries'] == 1
    gpkg = preserved(package, item, source_fields, expected)
    assert report['subset_sha256'] == sha256(gpkg)
    assert sha256(archive) == before
    names = package_valid(package, report)
    assert any(name.endswith('.prj') for name in names)
    assert any(name.endswith('.cpg') for name in names)
    assert any(name.endswith('README.txt') for name in names)
    return {'pass': True, 'selected_features': 6, 'excluded_non_target': 'Sudan inside regional envelope',
            'checks': ['nested ZIP paths and spaces/Unicode', 'all six target countries',
                       'original fid and output-row-id collision', 'NULL geometry',
                       'NULL versus zero, integer64, unknown names and Unicode custom values',
                       'source field names/types/values', 'byte-identical geometry WKB',
                       'source ZIP unchanged', 'output hash and ZIP contents']}


def fallback_test(extractor, root):
    archive, member = fixture(root, 'projected fixture', [('unit', ogr.OFTString), ('value', ogr.OFTReal)],
        [({'unit': 'extends beyond filter', 'value': 0.0}, polygon(23, -6, 51, 19, 3857)),
         ({'unit': 'outside envelope', 'value': 52.0}, polygon(60, 1, 61, 2, 3857))], epsg=3857)
    before = sha256(archive)
    fields, source_rows = original(archive, member)
    package, report = extractor.run_extraction(archive, root / 'outputs', open_folder=False)
    assert report['exported_features_total'] == 1 and report['status'] == 'subset_ready_for_review'
    item = report['layers'][0]
    assert item['country_field'] is None
    assert item['selection_method'] == 'Conservative regional envelope; full intersecting features retained'
    preserved(package, item, fields, {0: source_rows[0]}, epsg=3857)
    assert sha256(archive) == before
    package_valid(package, report)
    return {'pass': True, 'selected_features': 1,
            'checks': ['EPSG:3857 filter transformation', 'outside feature excluded',
                       'full polygon beyond envelope preserved without clipping',
                       'source CRS/WKB/attributes retained', 'source ZIP unchanged']}


def no_shapefile_test(extractor, root):
    archive = root / 'no shapefile.zip'
    with zipfile.ZipFile(archive, 'w') as zipped:
        zipped.writestr('README.txt', 'Synthetic archive without geometry.')
    before = sha256(archive)
    package, report = extractor.run_extraction(archive, root / 'outputs', open_folder=False)
    assert report['status'] == 'inspection_required' and report['exported_features_total'] == 0
    assert any('No shapefiles' in item['error'] for item in report['errors'])
    assert sha256(archive) == before
    package_valid(package, report)
    return {'pass': True, 'checks': ['report-only ZIP produced', 'absent shapefiles identified', 'source unchanged']}


def missing_crs_test(extractor, root):
    archive, member = fixture(root, 'no CRS fixture', [('unit', ogr.OFTString)],
                              [({'unit': 'unknown 8'}, polygon(40, 1, 41, 2))], epsg=None)
    before = sha256(archive)
    package, report = extractor.run_extraction(archive, root / 'outputs', open_folder=False)
    assert report['status'] == 'inspection_required' and report['exported_features_total'] == 0
    assert report['layers'][0]['source_crs'] is None
    assert any('coordinate reference system' in item['error'] for item in report['errors'])
    assert sha256(archive) == before
    package_valid(package, report)
    return {'pass': True, 'checks': ['missing CRS and country field reported', 'no inferred geography',
                                   'report-only review package produced', 'source unchanged']}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--launcher', type=Path, default=Path(__file__).with_name('Extract_SEDAC_RAI.cmd'))
    parser.add_argument('--validation', type=Path, default=Path(__file__).with_name('validation.json'))
    args = parser.parse_args()
    ogr.UseExceptions()
    osr.UseExceptions()
    extractor, embedded_sha = load_embedded(args.launcher)
    tests = {}
    with tempfile.TemporaryDirectory(prefix='wb_sedac_tests_') as temporary:
        root = Path(temporary) / 'synthetic space é'
        root.mkdir()
        for name, test in [('country_subset_and_preservation', country_test),
                           ('projected_geographic_fallback', fallback_test),
                           ('no_shapefile_report', no_shapefile_test), ('missing_crs_report', missing_crs_test)]:
            try:
                tests[name] = test(extractor, root)
            except Exception as error:
                tests[name] = {'pass': False, 'error': repr(error)}
    result = {'status': 'passed' if all(item['pass'] for item in tests.values()) else 'failed',
              'interpreter': sys.executable, 'gdal_version': gdal.VersionInfo('RELEASE_NAME'),
              'launcher_sha256': sha256(args.launcher), 'embedded_python_sha256': embedded_sha,
              'synthetic_tests': tests,
              'limitations': ['Windows CMD/PowerShell bootstrap and installed QGIS runner were not executed.',
                              'The original 600 MB SEDAC archive was not available and was not tested.',
                              'Synthetic tests do not verify source-year interpretation, admin-level alignment or map joins.',
                              'Output size for the original archive remains unknown.']}
    args.validation.parent.mkdir(parents=True, exist_ok=True)
    args.validation.write_text(json.dumps(result, indent=2, ensure_ascii=False) + '\n', encoding='utf-8')
    print(json.dumps(result, indent=2, ensure_ascii=False))
    return 0 if result['status'] == 'passed' else 1


if __name__ == '__main__':
    sys.exit(main())
