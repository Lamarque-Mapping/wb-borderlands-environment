"""Export audited source polygons and package a rural-access update for the vault.

Run with a Python providing GDAL and cryptography:
  python build_live_assets.py export PROCESSED.gpkg REPORT.zip DATA_DIRECTORY
  python build_live_assets.py package CACHE_DIRECTORY WORKING_PAGES SITE_OUTPUT
The package command uses data JSONs in WORKING_PAGES/data and does not publish.
"""
import argparse
import base64
import gzip
import hashlib
import json
import os
from pathlib import Path
import zipfile

CODES = ('moyale_borana', 'mandera_triangle', 'karamoja', 'dikhil')
LAYERS = {code: 'rai_' + code for code in CODES}
REVISION = '2026-10-14.rural-access.38'
PART_BYTES = 48 * 1024


def digest(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def dump(document):
    return json.dumps(document, ensure_ascii=False, separators=(',', ':'), allow_nan=False).encode('utf-8')


def export(processed, report_zip, output):
    from osgeo import ogr
    ogr.UseExceptions()
    with zipfile.ZipFile(report_zip) as zipped:
        report = json.loads(zipped.read('RAI_SETUP_REPORT.json'))
    assert report['status'] == 'complete'
    assert report['qgis_review']['review_project_created']
    assert report['qgis_review']['original_project_preserved']
    assert report['processed_data']['processed_sha256'] == digest(processed)
    assert all(report['processed_data']['checks'].values())
    output = Path(output)
    output.mkdir(parents=True, exist_ok=True)
    dataset = ogr.Open(str(processed), 0)
    assert dataset is not None
    summaries = []
    ids = set()
    for code in CODES:
        layer = dataset.GetLayerByName(LAYERS[code])
        assert layer is not None
        assert layer.GetSpatialRef().GetAuthorityCode(None) == '4326'
        features = []
        valid = missing = 0
        for row in layer:
            properties = row.items()
            fid = properties['__wb_source_fid']
            assert fid not in ids
            ids.add(fid)
            geometry = row.GetGeometryRef()
            raw_wkb = bytes(geometry.ExportToWkb())
            geometry_hash = hashlib.sha256(raw_wkb).hexdigest()
            assert geometry_hash == report['processed_data']['geometry_sha256_by_source_id'][str(fid)]
            json_geometry = json.loads(geometry.ExportToJson(['COORDINATE_PRECISION=17']))
            assert ogr.CreateGeometryFromJson(json.dumps(json_geometry)).ExportToWkb() == raw_wkb
            properties['source_record_id'] = 'sedac2023:' + str(fid)
            properties['original_wkb_sha256'] = geometry_hash
            pct = properties['rai_pct']
            if pct is None:
                missing += 1
                assert fid == 21174 and properties['SDG911pct'] == -9998
                assert properties['Pop_A2_R'] == 0
                assert properties['rai_share'] is None and properties['beyond_pct'] is None
            else:
                valid += 1
                assert pct == properties['SDG911pct'] and 0 <= pct <= 100
                assert abs(pct - 100 * properties['Pop_A2_R2K'] / properties['Pop_A2_R']) < 1e-5
            features.append({'type': 'Feature', 'id': properties['source_record_id'],
                             'properties': properties, 'geometry': json_geometry})
        source_metadata = {
            'title': 'SDG Indicator 9.1.1 Rural Access Index, 2023 Release',
            'attribution': 'CIESIN, Columbia University; NASA SEDAC',
            'doi': 'https://doi.org/10.7927/fcre-m572',
            'release': 2023, 'boundary_basis': 'GADM v3.6 source admin2',
            'population_reference': 'WorldPop 2020 UN Adjusted',
            'settlement_reference': 'GHSL GHS-SMOD R2019A, 2015',
            'road_snapshot': '2022-03-31',
            'road_condition': 'All-season classification inferred from OSM tags',
            'definition': '100 times rural population within 2 km of classified roads divided by source-unit rural population',
            'scope': 'Whole SEDAC source unit, including any area outside the focal cluster',
            'source_processed_sha256': report['processed_data']['processed_sha256'],
            'source_subset_sha256': report['processed_data']['source_sha256'],
            'source_setup_report_sha256': digest(report_zip),
            'source_record_count': len(features), 'valid_values': valid, 'no_data_values': missing,
            'coverage_tag_policy': 'Retain supplied tags as provenance without interpreting their meaning',
            'geometry_policy': 'Full source polygons; GeoJSON roundtrip verified against original WKB',
        }
        document = {'format': 'wb-rural-access-v1', 'code': code,
                    'source_metadata': source_metadata,
                    'ruralAccessUnits': {'type': 'FeatureCollection', 'features': features}}
        raw = dump(document)
        path = output / (code + '_ruralAccess.json')
        path.write_bytes(raw)
        summaries.append({'code': code, 'records': len(features), 'valid_values': valid, 'no_data': missing,
                          'json_bytes': len(raw), 'gzip_bytes': len(gzip.compress(raw, mtime=0)),
                          'sha256': hashlib.sha256(raw).hexdigest()})
    dataset = None
    assert len(ids) == 58
    assert sum(s['valid_values'] for s in summaries) == 57
    assert sum(s['no_data'] for s in summaries) == 1
    validation = {'status': 'passed', 'source_records': 58, 'valid_rates': 57, 'no_data': 1,
                  'full_geometry_json_roundtrip_wkb_identical': True, 'maps': summaries,
                  'processed_sha256': digest(processed), 'source_report_sha256': digest(report_zip)}
    (output / 'export_validation.json').write_text(json.dumps(validation, indent=2) + '\n')
    print(json.dumps(validation, indent=2))


def package(cache, working, site):
    from cryptography.hazmat.primitives.ciphers.aead import AESGCM
    cache, working, site = Path(cache), Path(working), Path(site)
    site.mkdir(parents=True, exist_ok=True)
    (site / 'assets').mkdir(exist_ok=True)
    boot = json.loads((cache / 'boot.json').read_text())
    base_manifest = json.loads((cache / 'manifest.json').read_text())
    manifest = dict(base_manifest)
    aes = AESGCM(base64.b64decode(boot['public_key']))
    asset_parts = dict(boot.get('asset_parts', {}))
    changes = []
    validations = []

    def asset(raw, mime, asset_name):
        nonce = os.urandom(12)
        # New nonce means a new path: never overwrite a previously cached asset.
        identifier = hashlib.sha256(raw + b'\0' + nonce).hexdigest()[:32]
        path = 'assets/' + identifier + '.bin'
        encrypted = aes.encrypt(nonce, gzip.compress(raw, mtime=0),
                                (boot['build'] + '|' + identifier).encode())
        assert gzip.decompress(aes.decrypt(nonce, encrypted,
                                          (boot['build'] + '|' + identifier).encode())) == raw
        parts = []
        if len(encrypted) > PART_BYTES:
            for ordinal, offset in enumerate(range(0, len(encrypted), PART_BYTES)):
                part = 'assets/' + identifier + '.part' + str(ordinal).zfill(3) + '.bin'
                (site / part).write_bytes(encrypted[offset:offset + PART_BYTES])
                parts.append(part)
                changes.append(part)
            asset_parts[path] = parts
            assert b''.join((site / part).read_bytes() for part in parts) == encrypted
        else:
            (site / path).write_bytes(encrypted)
            changes.append(path)
        validations.append({'asset': asset_name, 'clear_sha256': hashlib.sha256(raw).hexdigest(),
                            'clear_bytes': len(raw), 'encrypted_bytes': len(encrypted), 'parts': len(parts) or 1,
                            'encrypt_decrypt_roundtrip': True})
        return {'path': path, 'id': identifier, 'nonce': base64.b64encode(nonce).decode(),
                'gzip': True, 'mime': mime, 'bytes': len(encrypted)}

    for code in CODES:
        path = working / 'data' / (code + '_ruralAccess.json')
        document = json.loads(path.read_text())
        assert document['format'] == 'wb-rural-access-v1' and document['code'] == code
        name = code + '/ruralAccess'
        manifest[name] = asset(path.read_bytes(), 'application/json', name)
        page_name = 'page/map=' + code
        page = (working / ('page_map_' + code + '.html')).read_bytes()
        old_module = b'corridors/corridor-integration-v8.js?v=2026-10-11.8'
        new_module = b'corridors/corridor-integration-v9.js?v=2026-10-14.9'
        assert page.count(old_module) == 1 or page.count(new_module) == 1
        page = page.replace(old_module, new_module)
        assert b'Rural road access' in page and b'ruralAccessUnits' in page
        manifest[page_name] = asset(page, 'text/html', page_name)
    expected_changed = {'page/map=' + code for code in CODES}
    assert {key for key in base_manifest if base_manifest[key] != manifest[key]} == expected_changed
    assert set(manifest) - set(base_manifest) == {code + '/ruralAccess' for code in CODES}
    boot['asset_parts'] = asset_parts
    boot['manifest'] = asset(dump(manifest), 'application/json', 'manifest')
    boot['ui_revision'] = REVISION
    (site / 'boot.json').write_bytes(dump(boot) + b'\n')
    changes.append('boot.json')
    # The key, build ID, route and access mode are preserved from the baseline.
    old_boot = json.loads((cache / 'boot.json').read_text())
    assert {k: v for k, v in boot.items() if k not in ('asset_parts', 'manifest', 'ui_revision')} == {
        k: v for k, v in old_boot.items() if k not in ('asset_parts', 'manifest', 'ui_revision')}
    validation = {'status': 'passed', 'revision': REVISION,
                  'updated_pages': sorted(expected_changed),
                  'added_data_groups': sorted(set(manifest) - set(base_manifest)),
                  'other_manifest_entries_unchanged': True, 'assets': validations}
    folder = site / 'tools/rural-access/validation'
    folder.mkdir(parents=True, exist_ok=True)
    validation_path = folder / 'live_package_2026-10-14.json'
    validation_path.write_text(json.dumps(validation, indent=2) + '\n')
    changes.append(validation_path.relative_to(site).as_posix())
    (site / 'changes.json').write_text(json.dumps(changes, indent=2) + '\n')
    (working / 'new_manifest.json').write_text(json.dumps(manifest, indent=2) + '\n')
    print(json.dumps(validation, indent=2))


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('command', choices=['export', 'package'])
    parser.add_argument('input_1', type=Path)
    parser.add_argument('input_2', type=Path)
    parser.add_argument('output', type=Path)
    args = parser.parse_args()
    if args.command == 'export':
        export(args.input_1, args.input_2, args.output)
    else:
        package(args.input_1, args.input_2, args.output)
