from pathlib import Path
import json

ROOT = Path(__file__).resolve().parent
BASE = ROOT.parent / 'deprivation_hex'
WORK = ROOT / 'working'
SITE = ROOT / 'site'
WORK.mkdir(parents=True, exist_ok=True)
(SITE / 'sedac').mkdir(parents=True, exist_ok=True)

def replace(text, old, new, count=1):
    assert text.count(old) == count, (old[:90], text.count(old))
    return text.replace(old, new)

module = (BASE / 'site/sedac/sedac-v4.js').read_text()
module = replace(module, "pixel:null,grdiDisplay:'hex',hex:null", "pixel:null,hex:null")
module = replace(module, "populationMode()==='deprivation'", "['deprivation','deprivationHex'].includes(populationMode())")
module = replace(module, "state.grdiDisplay==='hex'", "populationMode()==='deprivationHex'")
module = replace(module, "   if(kind==='grdi')select(box,'Deprivation display','grdiDisplay',[['hex','10 km hexagons'],['grid','Source grid · approximately 1 km']],state.grdiDisplay,v=>{state.grdiDisplay=v;setPreset('population',{keepContext:true});});\n", '')
module = replace(module, "'% of cluster area mapped</strong>", "'% of cluster area has source values</strong>")
module = replace(module, "width:'+r.summary.coverage_share*100+'%", "width:'+(hexActive()?hexData.summary.mapped_area_share:r.summary.coverage_share)*100+'%")
module = replace(module, "<small>Grey = no source value. Missing data are not zero.</small>", "<small>'+(hexActive()?'Coloured hexes can contain large gaps in source coverage.':'Grey = no source value. Missing data are not zero.')+'</small>")
module = replace(module, "Hex colours average the mapped parts only. Click a hex to see its value and source coverage.", "Hex colours show averages of the available pixels, not values for the whole hex. Click a hex for its mean and source coverage.")
module = replace(module, "fillColor:b?b.colour:'#e5e7eb'", "fillColor:b?b.colour:'#d1d5db'")
module = replace(module, "   l.bindTooltip(esc(label),{sticky:true});l.on('click'", "   l.on('click'")
module = replace(module, "<p><i style=\"background:#e5e7eb\"></i>No source value</p>", "<p><i style=\"background:'+(hexActive(name)?'#d1d5db':'#e5e7eb')+'\"></i>'+(hexActive(name)?'No valid source pixels in this hex':'No source value')+'</p>")
module = replace(module, "Mean of mapped parts only. Click a hex for source coverage.", "Whole hexes are shaded, but means cover available pixels only. Click a hex to check coverage.")
(SITE / 'sedac/sedac-v5.js').write_text(module)

for code in ['mandera_triangle','moyale_borana','karamoja','dikhil']:
    page = (BASE / 'working' / f'page_map_{code}.html').read_text()
    page = replace(page, 'themeState.population!=="deprivation"', '!["deprivation","deprivationHex"].includes(themeState.population)')
    page = replace(page, "['deprivation','Relative deprivation · SEDAC']", "['deprivation','Deprivation · raster'],['deprivationHex','Deprivation · hexagons']")
    page = replace(page, "themeState.population==='deprivation'?['sedac','grdiHex']", "themeState.population==='deprivationHex'?['sedac','grdiHex']:themeState.population==='deprivation'?['sedac']")
    page = replace(page, "if(startView==='deprivation')themeState.population='deprivation';", "if(['deprivation','deprivationHex'].includes(startView))themeState.population=startView;")
    page = replace(page, "startView==='deprivation'?'population'", "['deprivation','deprivationHex'].includes(startView)?'population'")
    page = replace(page, 'sedac/sedac-v4.js?v=2026-10-15.grdi-hex.50', 'sedac/sedac-v5.js?v=2026-10-15.deprivation-tabs.51')
    page = replace(page, "  renderThemeControls(name);", "  renderThemeControls(name);\n  if(name==='population')document.querySelector('.view-options').scrollTop=0;")
    (WORK / f'page_map_{code}.html').write_text(page)

print('Prepared two Population sub-tabs in four maps; source data unchanged.')
