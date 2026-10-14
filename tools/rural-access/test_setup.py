"""Verify the launcher's embedded data-processing code against the SEDAC subset.

Run with Python having GDAL bindings:
  python test_setup.py /path/to/SEDAC_RAI_for_Codex_YYYYMMDD_HHMMSS.zip
Windows PowerShell and QGIS project creation are explicitly outside this test.
"""
import argparse
import collections
import hashlib
import json
from pathlib import Path
import re
import shutil
import tempfile
import types
import zipfile

from osgeo import gdal, ogr


def digest(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def load_embedded(command):
    content = command.read_bytes()
    assert content.count(b'\n') == content.count(b'\r\n'), 'Launcher must use CRLF throughout.'
    assert not content.startswith(b'\xef\xbb\xbf'), 'Launcher must not have a BOM.'
    text = content.decode('utf-8')
    matches = list(re.finditer(r'(?m)^#WB_RAI_SETUP_PYTHON\r?$', text))
    assert len(matches) == 1
    body = text[matches[0].end():]
    scope = {'__name__': 'test_embedded_setup'}
    exec(compile(body, command.name, 'exec'), scope)
    assert len(scope['AUDITED_RECORDS']) == 58
    bootstrap = text[:matches[0].start()]
    assert 'DisableDelayedExpansion' in bootstrap
    assert '[version]$v.Value' in bootstrap
    assert 'python-qgis.bat' in bootstrap and 'python-qgis-ltr.bat' in bootstrap
    assert '$env:WB_SEDAC_QGIS_BIN=Split-Path -Parent $runner' in bootstrap
    assert max(map(len, bootstrap.splitlines())) < 8191
    return types.SimpleNamespace(**scope)


def mutate_copy(source, destination, field, value, fid=21022):
    shutil.copyfile(source, destination)
    dataset = ogr.Open(str(destination), 1)
    layer = dataset.GetLayerByName('source_2_sdgi_9_1_1_rai_2023_subnational')
    layer.SetAttributeFilter('__wb_source_fid = ' + str(fid))
    feature = layer.GetNextFeature()
    assert feature is not None
    feature.SetField(field, value)
    assert layer.SetFeature(feature) == 0
    feature = layer = dataset = None


def expect_rejection(module, source, output, expected_fragment):
    try:
        module.process_source(source, output)
    except (ValueError, FileExistsError) as error:
        assert expected_fragment in str(error), str(error)
    else:
        raise AssertionError('Altered input was not rejected.')
    assert not output.exists(), 'Rejected inputs must not produce mapping output.'


def run(command, archive):
    gdal.UseExceptions()
    ogr.UseExceptions()
    module = load_embedded(command)
    original_archive_hash = digest(archive)
    with tempfile.TemporaryDirectory(prefix='wb_rai_setup_') as temporary:
        temporary = Path(temporary)
        fixture_folder = temporary / 'subset with spaces and \u00e9'
        fixture_folder.mkdir()
        fixture = fixture_folder / archive.name
        shutil.copyfile(archive, fixture)
        folder, report = module.run_setup(fixture, open_gui=False, data_only=True)
        assert report['status'] == 'data_prepared'
        data = report['processed_data']
        assert (data['records'], data['valid_values'], data['no_data']) == (58, 57, 1)
        assert all(data['checks'].values())
        assert [item['records'] for item in data['layers']] == [15, 5, 27, 11]
        output = folder / 'Rural_Access_SEDAC_source_units.gpkg'
        dataset = ogr.Open(str(output), 0)
        observed = {}
        band_counts = collections.Counter()
        for cluster, layer_name in module.CLUSTERS:
            layer = dataset.GetLayerByName(layer_name)
            observed[cluster] = layer.GetFeatureCount()
            for feature in layer:
                percent = feature.GetField('rai_pct')
                if percent is None:
                    band_counts['no_data'] += 1
                    assert feature.GetField('__wb_source_fid') == 21174
                    assert feature.GetField('NAME_2') == 'unknown 8'
                    assert feature.GetField('SDG911pct') == -9998
                    assert feature.GetField('rai_share') is None
                    assert feature.GetField('beyond_pct') is None
                else:
                    band = min(int(percent // 20), 4)
                    band_counts[str(band)] += 1
                    assert 0 <= percent <= 100
                    assert abs(feature.GetField('rai_share') - percent / 100) < 1e-12
                    assert abs(feature.GetField('beyond_pct') - (100 - percent)) < 1e-12
            feature = layer = None
        dataset = None
        assert band_counts['no_data'] == 1
        package = folder / 'RAI_SETUP_REPORT.zip'
        assert package.stat().st_size < 50_000
        with zipfile.ZipFile(package) as zipped:
            assert zipped.namelist() == ['RAI_SETUP_REPORT.json']
            payload = zipped.read('RAI_SETUP_REPORT.json')
            upload_report = json.loads(payload)
            assert str(temporary).encode() not in payload
            assert b'/workspace/' not in payload
            assert 'output_folder' not in upload_report
            assert upload_report['qgis_review']['review_project_created'] is False
        source = folder / 'SEDAC_RAI_source_subset.gpkg'
        source_before = digest(source)
        changed_population = temporary / 'changed_population.gpkg'
        mutate_copy(source, changed_population, 'Pop_A2_R', 336704.025398)
        expect_rejection(module, changed_population, temporary / 'bad_population.gpkg', 'Unexpected value')
        changed_identity = temporary / 'changed_identity.gpkg'
        mutate_copy(source, changed_identity, '__wb_source_fid', 999901)
        expect_rejection(module, changed_identity, temporary / 'bad_identity.gpkg', 'Audited source IDs')
        changed_no_data = temporary / 'changed_no_data.gpkg'
        mutate_copy(source, changed_no_data, 'SDG911pct', 0, fid=21174)
        expect_rejection(module, changed_no_data, temporary / 'bad_no_data.gpkg', 'Unexpected value')
        changed_name = temporary / 'changed_name.gpkg'
        mutate_copy(source, changed_name, 'NAME_2', 'Guessed Banissa')
        expect_rejection(module, changed_name, temporary / 'bad_name.gpkg', 'ID/name mismatch')
        duplicate_package = temporary / 'duplicate.zip'
        with zipfile.ZipFile(duplicate_package, 'w') as zipped:
            zipped.writestr('a/SEDAC_RAI_source_subset.gpkg', b'a')
            zipped.writestr('b/SEDAC_RAI_source_subset.gpkg', b'b')
        try:
            module.extract_source(duplicate_package, temporary)
        except ValueError as error:
            assert 'exactly one' in str(error)
        else:
            raise AssertionError('Ambiguous source GeoPackage was accepted.')
        assert digest(source) == source_before
        assert digest(archive) == original_archive_hash
        return {
            'status': 'passed', 'command_filename': command.name,
            'command_sha256': digest(command), 'gdal_version': gdal.VersionInfo('--version'),
            'tested_input_archive': archive.name, 'input_archive_sha256': original_archive_hash,
            'actual_subset_processing': data,
            'independent_cluster_counts': observed, 'five_band_counts': dict(sorted(band_counts.items())),
            'additional_checks': {'spaces_and_unicode_paths': True, 'altered_population_rejected': True,
                                  'missing_source_id_rejected': True, 'no_data_as_zero_rejected': True,
                                  'changed_source_name_rejected': True, 'ambiguous_zip_rejected': True,
                                  'source_and_archive_unchanged': True, 'report_zip_contains_no_data_files': True,
                                  'report_zip_excludes_local_paths': True, 'crlf_bootstrap_static_checks': True},
            'not_executed_here': ['Windows CMD/PowerShell bootstrap', 'QGIS project read/write on Windows',
                                  'Automatic QGIS GUI opening', 'Original Windows project contents'],
        }


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('archive', type=Path)
    parser.add_argument('--command', type=Path,
                        default=Path(__file__).with_name('Setup_SEDAC_Rural_Access.cmd'))
    parser.add_argument('--validation', type=Path)
    args = parser.parse_args()
    result = run(args.command.resolve(), args.archive.resolve())
    text = json.dumps(result, indent=2)
    if args.validation:
        args.validation.write_text(text + '\n', encoding='utf-8')
    print(text)
