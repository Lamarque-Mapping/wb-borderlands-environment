import json,urllib.request,rasterio,numpy as np
from pathlib import Path
r=next(r for r in json.loads(Path('work/hdx_search.json').read_text())['result']['results'][0]['resources'] if r['name']=='Global Drought SPEI 2.0+ Return Period 25 Years.tif')
print('Source: '+r['name'],flush=True)
u=r['url']
try:
 req=urllib.request.Request(u,headers={'Range':'bytes=0-16383'})
 with urllib.request.urlopen(req,timeout=30) as res:
  u=res.url;print('Public download supports byte ranges:',res.status,flush=True)
 with rasterio.Env(GDAL_DISABLE_READDIR_ON_OPEN='EMPTY_DIR',CPL_VSIL_CURL_USE_HEAD='NO',CPL_VSIL_CURL_ALLOWED_EXTENSIONS='.tif',GDAL_HTTP_TIMEOUT='30',GDAL_HTTP_MAX_RETRY='1'):
  with rasterio.open(u) as src:
   print('raster',src.profile,src.tags(),src.tags(1),flush=True)
   win=rasterio.windows.from_bounds(30,-1,45,14,src.transform).round_offsets().round_lengths()
   a=src.read(1,window=win)
   prof=src.profile;prof.update(width=a.shape[1],height=a.shape[0],transform=src.window_transform(win),compress='deflate')
   with rasterio.open('work/drought_source_window.tif','w',**prof) as dst:dst.write(a,1)
   print('saved',a.shape,'min',np.nanmin(a),'max',np.nanmax(a),'nodata',src.nodata,flush=True)
except Exception as e:print(type(e).__name__,str(e),flush=True)
