@echo off
setlocal DisableDelayedExpansion
title SEDAC Rural Access - small review extract
set "WB_SEDAC_SELF=%~f0"
set "WB_SEDAC_INPUT=%~1"
echo Preparing a small SEDAC extract using your installed QGIS Python...
echo Your downloaded archive and QGIS project will not be changed.
powershell.exe -NoProfile -Command "$ErrorActionPreference='Stop'; $tmp=$null; $code=1; try { $text=[IO.File]::ReadAllText($env:WB_SEDAC_SELF); $m=[regex]::Match($text,'(?m)^#WB_SEDAC_PYTHON\r?$'); if(-not $m.Success){throw 'The embedded extractor is missing.'}; $tmp=Join-Path $env:TEMP ('wb_sedac_'+[guid]::NewGuid().ToString('N')+'.py'); [IO.File]::WriteAllText($tmp,$text.Substring($m.Index+$m.Length),[Text.UTF8Encoding]::new($false)); $roots=@($env:OSGEO4W_ROOT,'C:\OSGeo4W','C:\OSGeo4W64'); foreach($pf in @($env:ProgramFiles,${env:ProgramFiles(x86)})){if($pf -and (Test-Path -LiteralPath $pf)){ $roots+=@(Get-ChildItem -LiteralPath $pf -Directory -Filter 'QGIS*' -ErrorAction SilentlyContinue | Sort-Object @{Expression={ $v=[regex]::Match($_.Name,'\d+(?:\.\d+){1,3}'); if($v.Success){[version]$v.Value}else{[version]'0.0'} }} -Descending | ForEach-Object {$_.FullName}) }}; foreach($key in @('HKLM:\SOFTWARE\Microsoft\Windows\CurrentVersion\Uninstall\*','HKLM:\SOFTWARE\WOW6432Node\Microsoft\Windows\CurrentVersion\Uninstall\*','HKCU:\SOFTWARE\Microsoft\Windows\CurrentVersion\Uninstall\*')){ $roots+=@(Get-ItemProperty -Path $key -ErrorAction SilentlyContinue | Where-Object {$_.DisplayName -like 'QGIS*' -and $_.InstallLocation} | ForEach-Object {$_.InstallLocation}) }; $runner=$null; foreach($root in @($roots | Where-Object {$_} | Select-Object -Unique)){foreach($name in @('python-qgis.bat','python-qgis-ltr.bat')){ $candidate=Join-Path $root ('bin\'+$name); if(Test-Path -LiteralPath $candidate -PathType Leaf){$runner=$candidate;break} };if($runner){break}}; if(-not $runner){throw 'QGIS Python was not found in the usual installation locations. Send the text in this window to Codex.'}; Write-Host ('Using: '+$runner); if($env:WB_SEDAC_INPUT){ & $runner $tmp --input $env:WB_SEDAC_INPUT }else{ & $runner $tmp }; $code=$LASTEXITCODE; if($null -eq $code){$code=1} }catch{Write-Host ('Could not run the extractor: '+$_.Exception.Message);$code=1}finally{if($tmp -and (Test-Path -LiteralPath $tmp)){Remove-Item -LiteralPath $tmp -Force -ErrorAction SilentlyContinue}}; exit $code"
set "WB_SEDAC_EXIT=%ERRORLEVEL%"
echo.
if not "%WB_SEDAC_EXIT%"=="0" echo If needed, drag the SEDAC ZIP onto this launcher and try again.
pause
exit /b %WB_SEDAC_EXIT%
#WB_SEDAC_PYTHON
"""Read-only SEDAC extraction for boundary and field review.

Runs with the GDAL supplied with QGIS. No network requests, installations,
geometry simplification, population aggregation, map joins or project changes.
"""
import argparse
import collections
import datetime
import hashlib
import json
import os
from pathlib import Path, PurePosixPath
import re
import sys
import unicodedata
import zipfile

COUNTRIES = ('Djibouti', 'Ethiopia', 'Kenya', 'Somalia', 'South Sudan', 'Uganda')
COUNTRY_VALUES = {
    'djibouti': 'Djibouti', 'dji': 'Djibouti', 'dj': 'Djibouti',
    'ethiopia': 'Ethiopia', 'eth': 'Ethiopia', 'et': 'Ethiopia',
    'kenya': 'Kenya', 'ken': 'Kenya', 'ke': 'Kenya',
    'somalia': 'Somalia', 'som': 'Somalia', 'so': 'Somalia',
    'somaliland': 'Somalia',
    'southsudan': 'South Sudan', 'ssd': 'South Sudan', 'ss': 'South Sudan',
    'uganda': 'Uganda', 'uga': 'Uganda', 'ug': 'Uganda',
}
COUNTRY_FIELDS = ('NAME_0', 'NAME0', 'ADM0_NAME', 'ADM0_EN', 'COUNTRY',
                  'COUNTRY_NA', 'CNTRY_NAME', 'COUNTRYNAM', 'ADMIN0',
                  'GID_0', 'GID0', 'ISO3', 'ISO_A3', 'ADM0_A3', 'ISO',
                  'ISO2', 'ISO_A2')
# A conservative review envelope, used only when country fields are unrecognised.
# Features are selected by intersection and retain their FULL source geometry.
REGIONAL_ENVELOPE = (24.0, -5.5, 50.0, 18.5)


def log(text):
    print(text, flush=True)


def normalized(value):
    text = unicodedata.normalize('NFKD', str(value or '')).encode('ascii', 'ignore').decode().lower()
    return re.sub(r'[^a-z0-9]', '', text)


def country_for(value):
    text = str(value or '').strip()
    return COUNTRY_VALUES.get(normalized(text)) or COUNTRY_VALUES.get(normalized(text.split('.')[0]))


def download_folders():
    folders = []
    if os.name == 'nt':
        try:
            import winreg
            with winreg.OpenKey(winreg.HKEY_CURRENT_USER,
                               r'Software\Microsoft\Windows\CurrentVersion\Explorer\User Shell Folders') as key:
                value, unused_type = winreg.QueryValueEx(key, '{374DE290-123F-4565-9164-39C4925E467B}')
            folders.append(Path(os.path.expandvars(value)))
        except OSError:
            pass
    folders.append(Path.home() / 'Downloads')
    if os.environ.get('OneDrive'):
        folders.append(Path(os.environ['OneDrive']) / 'Downloads')
    return list(dict.fromkeys(folders))


def find_archive(explicit=None):
    if explicit:
        path = Path(explicit).expanduser().resolve()
        if not path.is_file() or not zipfile.is_zipfile(path):
            raise ValueError('The supplied path is not a readable ZIP archive: ' + str(path))
        return path
    matches = []
    for folder in download_folders():
        if folder.is_dir():
            for path in folder.glob('*.zip'):
                if normalized(path.stem).startswith('sdgi911rai2023shp'):
                    matches.append(path)
    if not matches:
        raise FileNotFoundError('The SEDAC 2023 shapefile ZIP was not found in Downloads. '
                                'Drag that ZIP onto Extract_SEDAC_RAI.cmd to select it.')
    path = max(matches, key=lambda p: p.stat().st_mtime)
    if not zipfile.is_zipfile(path):
        raise ValueError('The archive is not a complete, readable ZIP. Check that its download has finished.')
    return path


def unique_folder(parent):
    stamp = datetime.datetime.now().strftime('%Y%m%d_%H%M%S')
    base = parent / ('SEDAC_RAI_for_Codex_' + stamp)
    path = base
    suffix = 1
    while path.exists() or path.with_suffix('.zip').exists():
        path = Path(str(base) + '_' + str(suffix))
        suffix += 1
    path.mkdir(parents=True)
    return path


def schema(layer, ogr):
    definition = layer.GetLayerDefn()
    return [{'name': definition.GetFieldDefn(i).GetName(),
             'type': ogr.GetFieldTypeName(definition.GetFieldDefn(i).GetType()),
             'width': definition.GetFieldDefn(i).GetWidth(),
             'precision': definition.GetFieldDefn(i).GetPrecision()}
            for i in range(definition.GetFieldCount())]


def discover_country_field(layer, ogr):
    names = [f['name'] for f in schema(layer, ogr)]
    by_normal = {normalized(name): name for name in names}
    candidates = list(dict.fromkeys(by_normal[normalized(name)] for name in COUNTRY_FIELDS
                                   if normalized(name) in by_normal))
    counts = {name: collections.Counter() for name in candidates}
    values = {name: set() for name in candidates}
    samples = []
    if not candidates:
        return None, counts, values, samples
    try:
        layer.SetIgnoredFields(['OGR_GEOMETRY'])
        layer.ResetReading()
        for i, feature in enumerate(layer):
            if len(samples) < 3:
                samples.append({'source_fid': feature.GetFID(),
                                'country_fields': {name: feature.GetField(name) for name in candidates}})
            for name in candidates:
                value = feature.GetField(name)
                country = country_for(value)
                if country:
                    counts[name][country] += 1
                    values[name].add(str(value))
            if i and i % 10000 == 0:
                log('  Checked ' + str(i) + ' source attribute records...')
    finally:
        layer.SetIgnoredFields([])
        layer.ResetReading()
    best = max(candidates, key=lambda name: sum(counts[name].values()))
    return (best if counts[best] else None), counts, values, samples


def set_regional_filter(layer, osr):
    source = layer.GetSpatialRef()
    if source is None:
        raise ValueError('No recognisable country field or coordinate reference system; '
                         'the inspection report is needed before selecting geometry.')
    source = source.Clone()
    target = osr.SpatialReference()
    target.ImportFromEPSG(4326)
    if hasattr(osr, 'OAMS_TRADITIONAL_GIS_ORDER'):
        source.SetAxisMappingStrategy(osr.OAMS_TRADITIONAL_GIS_ORDER)
        target.SetAxisMappingStrategy(osr.OAMS_TRADITIONAL_GIS_ORDER)
    transform = osr.CoordinateTransformation(target, source)
    west, south, east, north = REGIONAL_ENVELOPE
    points = []
    for i in range(21):
        t = i / 20
        for x, y in ((west + t * (east-west), south), (west + t * (east-west), north),
                     (west, south + t * (north-south)), (east, south + t * (north-south))):
            points.append(transform.TransformPoint(x, y))
    xs, ys = [p[0] for p in points], [p[1] for p in points]
    layer.SetSpatialFilterRect(min(xs), min(ys), max(xs), max(ys))


def new_field_name(base, existing):
    name = base
    while name.lower() in existing:
        name += '_'
    existing.add(name.lower())
    return name


def export_layer(source, destination, layer_name, field_name, ogr):
    source_definition = source.GetLayerDefn()
    existing = {source_definition.GetFieldDefn(i).GetName().lower()
                for i in range(source_definition.GetFieldCount())}
    row_id = new_field_name('__wb_rowid', existing)
    geometry_name = new_field_name('__wb_geometry', existing)
    output = destination.CreateLayer(layer_name, srs=source.GetSpatialRef(), geom_type=ogr.wkbUnknown,
                                     options=['FID=' + row_id, 'GEOMETRY_NAME=' + geometry_name])
    if output is None:
        raise RuntimeError('Could not create the output layer ' + layer_name)
    for i in range(source_definition.GetFieldCount()):
        if output.CreateField(source_definition.GetFieldDefn(i)) != 0:
            raise RuntimeError('Could not preserve field ' + source_definition.GetFieldDefn(i).GetName())
    id_name = new_field_name('__wb_source_fid', existing)
    if output.CreateField(ogr.FieldDefn(id_name, ogr.OFTInteger64)) != 0:
        raise RuntimeError('Could not create the source identifier field.')
    output_definition = output.GetLayerDefn()
    count = 0
    countries = collections.Counter()
    null_geometries = 0
    output.StartTransaction()
    try:
        source.ResetReading()
        for feature in source:
            target = ogr.Feature(output_definition)
            for i in range(source_definition.GetFieldCount()):
                if feature.IsFieldSetAndNotNull(i):
                    target.SetField(i, feature.GetField(i))
            target.SetField(id_name, feature.GetFID())
            geometry = feature.GetGeometryRef()
            if geometry is not None:
                target.SetGeometry(geometry)
            else:
                null_geometries += 1
            if output.CreateFeature(target) != 0:
                raise RuntimeError('Could not preserve source feature ' + str(feature.GetFID()))
            target = None
            count += 1
            if field_name:
                countries[country_for(feature.GetField(field_name)) or 'Unrecognised'] += 1
            if count % 500 == 0:
                log('  Saved ' + str(count) + ' selected features...')
        if output.CommitTransaction() != 0:
            raise RuntimeError('The output layer could not be committed.')
    except Exception:
        output.RollbackTransaction()
        raise
    return {'output_layer': layer_name, 'exported_features': count,
            'countries': dict(countries), 'null_geometries': null_geometries,
            'source_fid_field': id_name}


def run_extraction(archive, output_parent=None, open_folder=True):
    from osgeo import ogr, osr, gdal
    ogr.UseExceptions()
    if hasattr(osr, 'UseExceptions'):
        osr.UseExceptions()
    archive = Path(archive).resolve()
    folder = unique_folder(Path(output_parent) if output_parent else archive.parent)
    report = {'extractor_version': 1, 'source_archive': archive.name,
              'source_archive_bytes': archive.stat().st_size,
              'target_countries': list(COUNTRIES), 'layers': [], 'errors': [],
              'geometry_policy': 'Full source geometry retained; no clipping, reprojection or simplification.',
              'value_policy': 'Source attributes copied without aggregation, imputation or map joining.',
              'purpose': 'Source boundary/identifier review for the four borderland maps.',
              'gdal_version': gdal.VersionInfo('RELEASE_NAME')}
    destination = None
    gpkg = folder / 'SEDAC_RAI_source_subset.gpkg'
    try:
        with zipfile.ZipFile(archive) as zipped:
            members = [info for info in zipped.infolist() if info.filename.lower().endswith('.shp')
                       and not info.filename.startswith('__MACOSX/')]
            if not members:
                raise ValueError('No shapefiles were found inside the archive.')
            report['archive_shapefiles'] = [info.filename for info in members]
            # Retain small supplied documentation and projection/encoding sidecars.
            docs = folder / 'source_documentation'
            for i, info in enumerate(zipped.infolist()):
                name = info.filename.lower()
                if info.file_size <= 5*1024*1024 and not info.is_dir() and (
                    name.endswith(('.prj', '.cpg', '.shp.xml', '.pdf')) or
                    (name.endswith('.txt') and any(word in name for word in ('readme','license','documentation')))):
                    docs.mkdir(exist_ok=True)
                    safe = re.sub(r'[^A-Za-z0-9_.-]', '_', PurePosixPath(info.filename).name)
                    (docs / (str(i) + '_' + safe)).write_bytes(zipped.read(info))
            destination = ogr.GetDriverByName('GPKG').CreateDataSource(str(gpkg))
            if destination is None:
                raise RuntimeError('The installed GDAL could not create a GeoPackage.')
            for ordinal, info in enumerate(members):
                log('Reading ' + PurePosixPath(info.filename).name + '...')
                item = {'source_member': info.filename, 'source_member_crc32': format(info.CRC, '08x'),
                        'source_member_bytes': info.file_size}
                report['layers'].append(item)
                datasource = None
                try:
                    uri = '/vsizip/' + archive.as_posix() + '/' + info.filename
                    datasource = ogr.Open(uri, 0)
                    if datasource is None:
                        raise ValueError('GDAL could not open this archived shapefile.')
                    source = datasource.GetLayer(0)
                    item['schema'] = schema(source, ogr)
                    srs = source.GetSpatialRef()
                    item['source_crs'] = srs.ExportToWkt() if srs else None
                    field, counts, values, samples = discover_country_field(source, ogr)
                    item['country_field_candidates'] = {name: dict(count) for name, count in counts.items()}
                    item['sample_country_attributes'] = samples
                    item['country_field'] = field
                    if field:
                        # Quote literal source values; source files are always opened read-only.
                        literals = ','.join("'" + value.replace("'", "''") + "'" for value in sorted(values[field]))
                        expression = '"' + field.replace('"','""') + '" IN (' + literals + ')'
                        source.SetAttributeFilter(expression)
                        item['selection_method'] = 'Exact country names/codes in source attributes'
                    else:
                        set_regional_filter(source, osr)
                        item['selection_method'] = 'Conservative regional envelope; full intersecting features retained'
                        item['envelope_wgs84'] = list(REGIONAL_ENVELOPE)
                    name = re.sub(r'[^A-Za-z0-9_]', '_', PurePosixPath(info.filename).stem)
                    output_name = 'source_' + str(ordinal + 1) + '_' + name[:50]
                    item.update(export_layer(source, destination, output_name, field, ogr))
                    log('  Selected ' + str(item['exported_features']) + ' features.')
                except Exception as error:
                    item['error'] = str(error)
                    report['errors'].append({'source_member': info.filename, 'error': str(error)})
                    log('  Inspection issue: ' + str(error))
                finally:
                    source = None
                    datasource = None
    except Exception as error:
        report['errors'].append({'error': str(error)})
        log('Extraction issue: ' + str(error))
    finally:
        destination = None
    exported = sum(item.get('exported_features', 0) for item in report['layers'])
    report['exported_features_total'] = exported
    represented = {country for item in report['layers'] for country in item.get('countries', {})}
    report['countries_not_confirmed_by_attributes'] = [country for country in COUNTRIES if country not in represented]
    report['status'] = 'subset_ready_for_review' if exported and not report['errors'] else 'inspection_required'
    # Close all GIS handles before hashing or compressing the output.
    if gpkg.exists():
        with gpkg.open('rb') as handle:
            report['subset_sha256'] = hashlib.file_digest(handle, 'sha256').hexdigest() if hasattr(hashlib,'file_digest') else hash_file(gpkg)
    (folder / 'extraction_report.json').write_text(json.dumps(report, indent=2, ensure_ascii=False)+'\n', encoding='utf-8')
    (folder / 'READ_ME.txt').write_text(
        'This package contains source data for review, not a completed map join.\n'
        'Original polygons and attribute values have been retained.\n'
        'The added source-FID column ties each record to its original shapefile member.\n'
        'Check extraction_report.json for field names, countries, selection method and any errors.\n'
        'Unnamed records and blank population values remain unchanged.\n'
        'The original downloaded archive and the QGIS project were not modified.\n', encoding='utf-8')
    package = folder.with_suffix('.zip')
    with zipfile.ZipFile(package, 'w', zipfile.ZIP_DEFLATED, compresslevel=9) as zipped:
        for path in sorted(folder.rglob('*')):
            if path.is_file():
                zipped.write(path, path.relative_to(folder).as_posix())
    megabytes = package.stat().st_size / (1024*1024)
    log('\nCreated: ' + str(package))
    log('ZIP size: ' + format(megabytes, '.1f') + ' MB')
    if report['status'] == 'inspection_required':
        log('Some source details need inspection. Upload this ZIP so Codex can check the report.')
    else:
        log('Upload this smaller ZIP to the chat. Do not upload the original 600 MB archive.')
    if megabytes > 40:
        log('If this ZIP is still too large, upload extraction_report.json first; a tighter selection can be made.')
    if os.name == 'nt' and open_folder:
        os.startfile(str(package.parent))
    return package, report


def hash_file(path):
    digest = hashlib.sha256()
    with Path(path).open('rb') as handle:
        for chunk in iter(lambda: handle.read(1024*1024), b''):
            digest.update(chunk)
    return digest.hexdigest()


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--input', default=None)
    parser.add_argument('--output-parent', default=None)
    parser.add_argument('--no-open', action='store_true')
    args = parser.parse_args()
    try:
        archive = find_archive(args.input)
        log('Source: ' + str(archive))
        log('Reading the archive may take a few minutes. Leave this window open.\n')
        package, report = run_extraction(archive, args.output_parent, not args.no_open)
        return 0 if report['exported_features_total'] else 2
    except Exception as error:
        log('\nCould not complete the extraction: ' + str(error))
        log('The original archive and QGIS project have not been changed.')
        return 1


if __name__ == '__main__':
    sys.exit(main())
