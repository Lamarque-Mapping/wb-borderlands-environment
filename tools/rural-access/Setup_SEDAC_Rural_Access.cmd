@echo off
setlocal DisableDelayedExpansion
title SEDAC Rural Access - QGIS review setup
set "WB_SEDAC_SELF=%~f0"
set "WB_SEDAC_INPUT=%~1"
echo Preparing rural access layers and a separate QGIS review copy...
echo Your downloaded archive and QGIS project will not be changed.
powershell.exe -NoProfile -Command "$ErrorActionPreference='Stop'; $tmp=$null; $code=1; try { $text=[IO.File]::ReadAllText($env:WB_SEDAC_SELF); $m=[regex]::Match($text,'(?m)^#WB_RAI_SETUP_PYTHON\r?$'); if(-not $m.Success){throw 'The embedded setup script is missing.'}; $tmp=Join-Path $env:TEMP ('wb_sedac_'+[guid]::NewGuid().ToString('N')+'.py'); [IO.File]::WriteAllText($tmp,$text.Substring($m.Index+$m.Length),[Text.UTF8Encoding]::new($false)); $roots=@($env:OSGEO4W_ROOT,'C:\OSGeo4W','C:\OSGeo4W64'); foreach($pf in @($env:ProgramFiles,${env:ProgramFiles(x86)})){if($pf -and (Test-Path -LiteralPath $pf)){ $roots+=@(Get-ChildItem -LiteralPath $pf -Directory -Filter 'QGIS*' -ErrorAction SilentlyContinue | Sort-Object @{Expression={ $v=[regex]::Match($_.Name,'\d+(?:\.\d+){1,3}'); if($v.Success){[version]$v.Value}else{[version]'0.0'} }} -Descending | ForEach-Object {$_.FullName}) }}; foreach($key in @('HKLM:\SOFTWARE\Microsoft\Windows\CurrentVersion\Uninstall\*','HKLM:\SOFTWARE\WOW6432Node\Microsoft\Windows\CurrentVersion\Uninstall\*','HKCU:\SOFTWARE\Microsoft\Windows\CurrentVersion\Uninstall\*')){ $roots+=@(Get-ItemProperty -Path $key -ErrorAction SilentlyContinue | Where-Object {$_.DisplayName -like 'QGIS*' -and $_.InstallLocation} | ForEach-Object {$_.InstallLocation}) }; $runner=$null; foreach($root in @($roots | Where-Object {$_} | Select-Object -Unique)){foreach($name in @('python-qgis.bat','python-qgis-ltr.bat')){ $candidate=Join-Path $root ('bin\'+$name); if(Test-Path -LiteralPath $candidate -PathType Leaf){$runner=$candidate;break} };if($runner){break}}; if(-not $runner){throw 'QGIS Python was not found in the usual installation locations. Send the text in this window to Codex.'}; $env:WB_SEDAC_QGIS_BIN=Split-Path -Parent $runner; Write-Host ('Using: '+$runner); if($env:WB_SEDAC_INPUT){ & $runner $tmp --input $env:WB_SEDAC_INPUT }else{ & $runner $tmp }; $code=$LASTEXITCODE; if($null -eq $code){$code=1} }catch{Write-Host ('Could not run the setup: '+$_.Exception.Message);$code=1}finally{if($tmp -and (Test-Path -LiteralPath $tmp)){Remove-Item -LiteralPath $tmp -Force -ErrorAction SilentlyContinue}}; exit $code"
set "WB_SEDAC_EXIT=%ERRORLEVEL%"
echo.
if not "%WB_SEDAC_EXIT%"=="0" echo If needed, drag the smaller SEDAC_RAI_for_Codex ZIP onto this launcher and try again.
pause
exit /b %WB_SEDAC_EXIT%
#WB_RAI_SETUP_PYTHON
"""Prepare audited SEDAC source-boundary layers and a separate QGIS review copy.

The embedded audited records are populated when this launcher is built. No
external downloads, current-boundary joins, clipping, or reweighting are used.
"""
import argparse
import collections
import datetime
import hashlib
import json
import math
import os
from pathlib import Path, PurePosixPath
import shutil
import subprocess
import sys
import traceback
import zipfile

AUDITED_RECORDS = [{'fid': 21022, 'cluster': 'Mandera Triangle', 'country_side': 'Kenya', 'key': ['Kenya', 'Mandera', 'Banissa'], 'raw': {'ISO3': 'KEN', 'Pop_A2': 347121.246544, 'Pop_A2_R': 336703.025398, 'Pop_A2_R2K': 155861.137324, 'SDG911pct': 46.2903881366, 'Pct_Error': 0.0950997811971}, 'coverage': 'Partial', 'status': 'valid'}, {'fid': 21023, 'cluster': 'Mandera Triangle', 'country_side': 'Kenya', 'key': ['Kenya', 'Mandera', 'Lafey'], 'raw': {'ISO3': 'KEN', 'Pop_A2': 324789.431418, 'Pop_A2_R': 322722.61489, 'Pop_A2_R2K': 75558.4588015, 'SDG911pct': 23.412818103, 'Pct_Error': 0.0950997811971}, 'coverage': 'Partial', 'status': 'valid'}, {'fid': 21024, 'cluster': 'Mandera Triangle', 'country_side': 'Kenya', 'key': ['Kenya', 'Mandera', 'Mandera East'], 'raw': {'ISO3': 'KEN', 'Pop_A2': 404767.333024, 'Pop_A2_R': 232027.326795, 'Pop_A2_R2K': 116448.73744, 'SDG911pct': 50.1875098286, 'Pct_Error': 0.0950997811971}, 'coverage': 'Partial', 'status': 'valid'}, {'fid': 21025, 'cluster': 'Mandera Triangle', 'country_side': 'Kenya', 'key': ['Kenya', 'Mandera', 'Mandera North'], 'raw': {'ISO3': 'KEN', 'Pop_A2': 418882.943247, 'Pop_A2_R': 391368.847465, 'Pop_A2_R2K': 176340.787905, 'SDG911pct': 45.0574410935, 'Pct_Error': 0.0950997811971}, 'coverage': 'Partial', 'status': 'valid'}, {'fid': 21026, 'cluster': 'Mandera Triangle', 'country_side': 'Kenya', 'key': ['Kenya', 'Mandera', 'Mandera South'], 'raw': {'ISO3': 'KEN', 'Pop_A2': 559327.438553, 'Pop_A2_R': 470616.700349, 'Pop_A2_R2K': 226713.799878, 'SDG911pct': 48.1737685275, 'Pct_Error': 0.0950997811971}, 'coverage': 'Partial', 'status': 'valid'}, {'fid': 21027, 'cluster': 'Mandera Triangle', 'country_side': 'Kenya', 'key': ['Kenya', 'Mandera', 'Mandera West'], 'raw': {'ISO3': 'KEN', 'Pop_A2': 446728.511547, 'Pop_A2_R': 407008.32012, 'Pop_A2_R2K': 209411.192339, 'SDG911pct': 51.4513296134, 'Pct_Error': 0.0950997811971}, 'coverage': 'Partial', 'status': 'valid'}, {'fid': 21028, 'cluster': 'Mandera Triangle', 'country_side': 'Kenya', 'key': ['Kenya', 'Mandera', 'unknown 1'], 'raw': {'ISO3': 'KEN', 'Pop_A2': 98012.7380582, 'Pop_A2_R': 97920.4589369, 'Pop_A2_R2K': 28860.5060051, 'SDG911pct': 29.4734178316, 'Pct_Error': 0.0950997811971}, 'coverage': 'Partial', 'status': 'valid'}, {'fid': 37056, 'cluster': 'Mandera Triangle', 'country_side': 'Somalia', 'key': ['Somalia', 'Gedo', 'Baar-Dheere'], 'raw': {'ISO3': 'SOM', 'Pop_A2': 224910.56232, 'Pop_A2_R': 217239.465632, 'Pop_A2_R2K': 7470.67341717, 'SDG911pct': 3.43891170761, 'Pct_Error': 0.460143539398}, 'coverage': 'Exact', 'status': 'valid'}, {'fid': 37057, 'cluster': 'Mandera Triangle', 'country_side': 'Somalia', 'key': ['Somalia', 'Gedo', 'Beled Xaawo'], 'raw': {'ISO3': 'SOM', 'Pop_A2': 118602.83667, 'Pop_A2_R': 118503.449092, 'Pop_A2_R2K': 1842.35859003, 'SDG911pct': 1.55468773622, 'Pct_Error': 0.460143539398}, 'coverage': 'Exact', 'status': 'valid'}, {'fid': 37058, 'cluster': 'Mandera Triangle', 'country_side': 'Somalia', 'key': ['Somalia', 'Gedo', 'Ceel Waaq'], 'raw': {'ISO3': 'SOM', 'Pop_A2': 42358.3710217, 'Pop_A2_R': 42272.1924867, 'Pop_A2_R2K': 1135.09206612, 'SDG911pct': 2.68519799743, 'Pct_Error': 0.460143539398}, 'coverage': 'Exact', 'status': 'valid'}, {'fid': 37059, 'cluster': 'Mandera Triangle', 'country_side': 'Somalia', 'key': ['Somalia', 'Gedo', 'Dolow'], 'raw': {'ISO3': 'SOM', 'Pop_A2': 46780.8169021, 'Pop_A2_R': 46430.6782166, 'Pop_A2_R2K': 6115.66995364, 'SDG911pct': 13.1716145198, 'Pct_Error': 0.460143539398}, 'coverage': 'Exact', 'status': 'valid'}, {'fid': 37060, 'cluster': 'Mandera Triangle', 'country_side': 'Somalia', 'key': ['Somalia', 'Gedo', 'Garbahaaray'], 'raw': {'ISO3': 'SOM', 'Pop_A2': 120796.342282, 'Pop_A2_R': 116597.254858, 'Pop_A2_R2K': 9059.78018711, 'SDG911pct': 7.77014878963, 'Pct_Error': 0.460143539398}, 'coverage': 'Exact', 'status': 'valid'}, {'fid': 37061, 'cluster': 'Mandera Triangle', 'country_side': 'Somalia', 'key': ['Somalia', 'Gedo', 'Luuk'], 'raw': {'ISO3': 'SOM', 'Pop_A2': 131516.902403, 'Pop_A2_R': 126310.439513, 'Pop_A2_R2K': 13396.6486522, 'SDG911pct': 10.6061293935, 'Pct_Error': 0.460143539398}, 'coverage': 'Exact', 'status': 'valid'}, {'fid': 14551, 'cluster': 'Mandera Triangle', 'country_side': 'Ethiopia', 'key': ['Ethiopia', 'Somali', 'Afder'], 'raw': {'ISO3': 'ETH', 'Pop_A2': 890356.052203, 'Pop_A2_R': 882335.452543, 'Pop_A2_R2K': 171996.602612, 'SDG911pct': 19.4933346627, 'Pct_Error': 0.184314156967}, 'coverage': 'Partial', 'status': 'valid'}, {'fid': 14556, 'cluster': 'Mandera Triangle', 'country_side': 'Ethiopia', 'key': ['Ethiopia', 'Somali', 'Liben'], 'raw': {'ISO3': 'ETH', 'Pop_A2': 744879.418048, 'Pop_A2_R': 736612.949857, 'Pop_A2_R2K': 145322.744108, 'SDG911pct': 19.728507914, 'Pct_Error': 0.184314156967}, 'coverage': 'Partial', 'status': 'valid'}, {'fid': 21029, 'cluster': 'Moyale/Borana', 'country_side': 'Kenya', 'key': ['Kenya', 'Marsabit', 'Laisamis'], 'raw': {'ISO3': 'KEN', 'Pop_A2': 79932.0243153, 'Pop_A2_R': 79878.32423, 'Pop_A2_R2K': 12387.6747585, 'SDG911pct': 15.5081805708, 'Pct_Error': 0.0950997811971}, 'coverage': 'Exact', 'status': 'valid'}, {'fid': 21030, 'cluster': 'Moyale/Borana', 'country_side': 'Kenya', 'key': ['Kenya', 'Marsabit', 'Moyale'], 'raw': {'ISO3': 'KEN', 'Pop_A2': 126346.426155, 'Pop_A2_R': 99446.8086521, 'Pop_A2_R2K': 65259.8512135, 'SDG911pct': 65.6228712595, 'Pct_Error': 0.0950997811971}, 'coverage': 'Exact', 'status': 'valid'}, {'fid': 21031, 'cluster': 'Moyale/Borana', 'country_side': 'Kenya', 'key': ['Kenya', 'Marsabit', 'North Horr'], 'raw': {'ISO3': 'KEN', 'Pop_A2': 90450.9493507, 'Pop_A2_R': 90439.8135689, 'Pop_A2_R2K': 14779.8908445, 'SDG911pct': 16.3422393979, 'Pct_Error': 0.0950997811971}, 'coverage': 'Exact', 'status': 'valid'}, {'fid': 21032, 'cluster': 'Moyale/Borana', 'country_side': 'Kenya', 'key': ['Kenya', 'Marsabit', 'Saku'], 'raw': {'ISO3': 'KEN', 'Pop_A2': 56240.6091622, 'Pop_A2_R': 45035.3610625, 'Pop_A2_R2K': 34312.6693486, 'SDG911pct': 76.1905057248, 'Pct_Error': 0.0950997811971}, 'coverage': 'Exact', 'status': 'valid'}, {'fid': 14536, 'cluster': 'Moyale/Borana', 'country_side': 'Ethiopia', 'key': ['Ethiopia', 'Oromia', 'Borena'], 'raw': {'ISO3': 'ETH', 'Pop_A2': 1581120.3733, 'Pop_A2_R': 1502923.94501, 'Pop_A2_R2K': 896350.36536, 'SDG911pct': 59.6404341243, 'Pct_Error': 0.184314156967}, 'coverage': 'Partial', 'status': 'valid'}, {'fid': 21145, 'cluster': 'Karamoja', 'country_side': 'Kenya', 'key': ['Kenya', 'Turkana', 'Loima'], 'raw': {'ISO3': 'KEN', 'Pop_A2': 190645.859771, 'Pop_A2_R': 190645.859771, 'Pop_A2_R2K': 64303.2351317, 'SDG911pct': 33.7291537351, 'Pct_Error': 0.0950997811971}, 'coverage': 'Exact', 'status': 'valid'}, {'fid': 21146, 'cluster': 'Karamoja', 'country_side': 'Kenya', 'key': ['Kenya', 'Turkana', 'Turkana Central'], 'raw': {'ISO3': 'KEN', 'Pop_A2': 183324.267407, 'Pop_A2_R': 180147.513834, 'Pop_A2_R2K': 90919.5388885, 'SDG911pct': 50.4694941126, 'Pct_Error': 0.0950997811971}, 'coverage': 'Exact', 'status': 'valid'}, {'fid': 21147, 'cluster': 'Karamoja', 'country_side': 'Kenya', 'key': ['Kenya', 'Turkana', 'Turkana East'], 'raw': {'ISO3': 'KEN', 'Pop_A2': 75006.6915034, 'Pop_A2_R': 75006.6915034, 'Pop_A2_R2K': 4773.50676412, 'SDG911pct': 6.3641078795, 'Pct_Error': 0.0950997811971}, 'coverage': 'Exact', 'status': 'valid'}, {'fid': 21148, 'cluster': 'Karamoja', 'country_side': 'Kenya', 'key': ['Kenya', 'Turkana', 'Turkana North'], 'raw': {'ISO3': 'KEN', 'Pop_A2': 165701.058827, 'Pop_A2_R': 165701.058827, 'Pop_A2_R2K': 53652.0581311, 'SDG911pct': 32.3788263701, 'Pct_Error': 0.0950997811971}, 'coverage': 'Exact', 'status': 'valid'}, {'fid': 21149, 'cluster': 'Karamoja', 'country_side': 'Kenya', 'key': ['Kenya', 'Turkana', 'Turkana South'], 'raw': {'ISO3': 'KEN', 'Pop_A2': 191611.901566, 'Pop_A2_R': 189113.025322, 'Pop_A2_R2K': 87288.4099702, 'SDG911pct': 46.156741357, 'Pct_Error': 0.0950997811971}, 'coverage': 'Exact', 'status': 'valid'}, {'fid': 21150, 'cluster': 'Karamoja', 'country_side': 'Kenya', 'key': ['Kenya', 'Turkana', 'Turkana West'], 'raw': {'ISO3': 'KEN', 'Pop_A2': 322832.44006, 'Pop_A2_R': 301614.191279, 'Pop_A2_R2K': 115739.576373, 'SDG911pct': 38.3733855102, 'Pct_Error': 0.0950997811971}, 'coverage': 'Exact', 'status': 'valid'}, {'fid': 21151, 'cluster': 'Karamoja', 'country_side': 'Kenya', 'key': ['Kenya', 'Turkana', 'unknown 2'], 'raw': {'ISO3': 'KEN', 'Pop_A2': 57361.5839918, 'Pop_A2_R': 57361.5839918, 'Pop_A2_R2K': 9820.32352322, 'SDG911pct': 17.1200354659, 'Pct_Error': 0.0950997811971}, 'coverage': 'Exact', 'status': 'valid'}, {'fid': 21169, 'cluster': 'Karamoja', 'country_side': 'Kenya', 'key': ['Kenya', 'West Pokot', 'Kacheliba'], 'raw': {'ISO3': 'KEN', 'Pop_A2': 226604.146819, 'Pop_A2_R': 226408.258604, 'Pop_A2_R2K': 143721.323832, 'SDG911pct': 63.4788345258, 'Pct_Error': 0.0950997811971}, 'coverage': 'Exact', 'status': 'valid'}, {'fid': 21170, 'cluster': 'Karamoja', 'country_side': 'Kenya', 'key': ['Kenya', 'West Pokot', 'Kapenguria'], 'raw': {'ISO3': 'KEN', 'Pop_A2': 184992.168525, 'Pop_A2_R': 168991.796708, 'Pop_A2_R2K': 130454.140582, 'SDG911pct': 77.1955462476, 'Pct_Error': 0.0950997811971}, 'coverage': 'Exact', 'status': 'valid'}, {'fid': 21171, 'cluster': 'Karamoja', 'country_side': 'Kenya', 'key': ['Kenya', 'West Pokot', 'Pokot South'], 'raw': {'ISO3': 'KEN', 'Pop_A2': 216269.39717, 'Pop_A2_R': 214278.443194, 'Pop_A2_R2K': 156430.7633, 'SDG911pct': 73.0035000106, 'Pct_Error': 0.0950997811971}, 'coverage': 'Exact', 'status': 'valid'}, {'fid': 21172, 'cluster': 'Karamoja', 'country_side': 'Kenya', 'key': ['Kenya', 'West Pokot', 'Sigor'], 'raw': {'ISO3': 'KEN', 'Pop_A2': 125644.432711, 'Pop_A2_R': 124967.952955, 'Pop_A2_R2K': 80983.2006794, 'SDG911pct': 64.8031745453, 'Pct_Error': 0.0950997811971}, 'coverage': 'Exact', 'status': 'valid'}, {'fid': 21173, 'cluster': 'Karamoja', 'country_side': 'Kenya', 'key': ['Kenya', 'West Pokot', 'unknown 3'], 'raw': {'ISO3': 'KEN', 'Pop_A2': 12071.9153495, 'Pop_A2_R': 12071.9153495, 'Pop_A2_R2K': 2548.73918585, 'SDG911pct': 21.1129643646, 'Pct_Error': 0.0950997811971}, 'coverage': 'Exact', 'status': 'valid'}, {'fid': 21174, 'cluster': 'Karamoja', 'country_side': 'Kenya', 'key': ['Kenya', 'West Pokot', 'unknown 8'], 'raw': {'ISO3': 'KEN', 'Pop_A2': 0.0, 'Pop_A2_R': 0.0, 'Pop_A2_R2K': 0.0, 'SDG911pct': -9998.0, 'Pct_Error': 0.0950997811971}, 'coverage': 'Exact', 'status': 'no_data_zero_denominator'}, {'fid': 40708, 'cluster': 'Karamoja', 'country_side': 'Uganda', 'key': ['Uganda', 'Kotido', 'Dodoth'], 'raw': {'ISO3': 'UGA', 'Pop_A2': 165875.638336, 'Pop_A2_R': 161849.736686, 'Pop_A2_R2K': 107120.331538, 'SDG911pct': 66.1850514748, 'Pct_Error': 0.067839693798}, 'coverage': 'Proxy', 'status': 'valid'}, {'fid': 40709, 'cluster': 'Karamoja', 'country_side': 'Uganda', 'key': ['Uganda', 'Kotido', 'Jie'], 'raw': {'ISO3': 'UGA', 'Pop_A2': 235735.355087, 'Pop_A2_R': 229652.458031, 'Pop_A2_R2K': 133942.636741, 'SDG911pct': 58.3240597074, 'Pct_Error': 0.067839693798}, 'coverage': 'Proxy', 'status': 'valid'}, {'fid': 40710, 'cluster': 'Karamoja', 'country_side': 'Uganda', 'key': ['Uganda', 'Kotido', 'Labwor'], 'raw': {'ISO3': 'UGA', 'Pop_A2': 160823.284985, 'Pop_A2_R': 156090.982032, 'Pop_A2_R2K': 105921.814921, 'SDG911pct': 67.8590226945, 'Pct_Error': 0.067839693798}, 'coverage': 'Proxy', 'status': 'valid'}, {'fid': 40746, 'cluster': 'Karamoja', 'country_side': 'Uganda', 'key': ['Uganda', 'Moroto', 'Bokora'], 'raw': {'ISO3': 'UGA', 'Pop_A2': 191891.309913, 'Pop_A2_R': 191530.148966, 'Pop_A2_R2K': 94090.6538808, 'SDG911pct': 49.125766564, 'Pct_Error': 0.067839693798}, 'coverage': 'Proxy', 'status': 'valid'}, {'fid': 40747, 'cluster': 'Karamoja', 'country_side': 'Uganda', 'key': ['Uganda', 'Moroto', 'Matheniko'], 'raw': {'ISO3': 'UGA', 'Pop_A2': 116860.289903, 'Pop_A2_R': 115758.852326, 'Pop_A2_R2K': 58623.3019944, 'SDG911pct': 50.6426081601, 'Pct_Error': 0.067839693798}, 'coverage': 'Proxy', 'status': 'valid'}, {'fid': 40748, 'cluster': 'Karamoja', 'country_side': 'Uganda', 'key': ['Uganda', 'Moroto', 'Moroto'], 'raw': {'ISO3': 'UGA', 'Pop_A2': 13486.4444447, 'Pop_A2_R': 9705.23642397, 'Pop_A2_R2K': 9705.23642397, 'SDG911pct': 100.0, 'Pct_Error': 0.067839693798}, 'coverage': 'Proxy', 'status': 'valid'}, {'fid': 40762, 'cluster': 'Karamoja', 'country_side': 'Uganda', 'key': ['Uganda', 'Nakapiripirit', 'Chekwii'], 'raw': {'ISO3': 'UGA', 'Pop_A2': 161538.390386, 'Pop_A2_R': 160820.843081, 'Pop_A2_R2K': 41520.5600892, 'SDG911pct': 25.817897291, 'Pct_Error': 0.067839693798}, 'coverage': 'Proxy', 'status': 'valid'}, {'fid': 40763, 'cluster': 'Karamoja', 'country_side': 'Uganda', 'key': ['Uganda', 'Nakapiripirit', 'Pian'], 'raw': {'ISO3': 'UGA', 'Pop_A2': 81063.0790943, 'Pop_A2_R': 80446.3649659, 'Pop_A2_R2K': 48523.4067663, 'SDG911pct': 60.3177120394, 'Pct_Error': 0.067839693798}, 'coverage': 'Proxy', 'status': 'valid'}, {'fid': 40764, 'cluster': 'Karamoja', 'country_side': 'Uganda', 'key': ['Uganda', 'Nakapiripirit', 'Pokot'], 'raw': {'ISO3': 'UGA', 'Pop_A2': 155798.5436, 'Pop_A2_R': 152421.473953, 'Pop_A2_R2K': 78756.1387175, 'SDG911pct': 51.6699758078, 'Pct_Error': 0.067839693798}, 'coverage': 'Proxy', 'status': 'valid'}, {'fid': 37273, 'cluster': 'Karamoja', 'country_side': 'South Sudan', 'key': ['South Sudan', 'Eastern Equatoria', 'Kapoeta'], 'raw': {'ISO3': 'SSD', 'Pop_A2': 1294749.45021, 'Pop_A2_R': 1294070.02901, 'Pop_A2_R2K': 296781.030937, 'SDG911pct': 22.9339235347, 'Pct_Error': 0.157587041172}, 'coverage': 'Partial', 'status': 'valid'}, {'fid': 37274, 'cluster': 'Karamoja', 'country_side': 'South Sudan', 'key': ['South Sudan', 'Eastern Equatoria', 'Magwi'], 'raw': {'ISO3': 'SSD', 'Pop_A2': 714467.015061, 'Pop_A2_R': 710660.164086, 'Pop_A2_R2K': 278709.532956, 'SDG911pct': 39.2183981938, 'Pct_Error': 0.157587041172}, 'coverage': 'Partial', 'status': 'valid'}, {'fid': 37275, 'cluster': 'Karamoja', 'country_side': 'South Sudan', 'key': ['South Sudan', 'Eastern Equatoria', 'Shokodom'], 'raw': {'ISO3': 'SSD', 'Pop_A2': 793502.819679, 'Pop_A2_R': 793433.592314, 'Pop_A2_R2K': 101091.156846, 'SDG911pct': 12.7409726315, 'Pct_Error': 0.157587041172}, 'coverage': 'Partial', 'status': 'valid'}, {'fid': 14564, 'cluster': 'Karamoja', 'country_side': 'Ethiopia', 'key': ['Ethiopia', 'Southern Nations, Nationalities and Peoples', 'Bench Maji'], 'raw': {'ISO3': 'ETH', 'Pop_A2': 1046456.36695, 'Pop_A2_R': 967541.613217, 'Pop_A2_R2K': 729868.447309, 'SDG911pct': 75.4353546491, 'Pct_Error': 0.184314156967}, 'coverage': 'Proxy', 'status': 'valid'}, {'fid': 14567, 'cluster': 'Karamoja', 'country_side': 'Ethiopia', 'key': ['Ethiopia', 'Southern Nations, Nationalities and Peoples', 'Debub Omo'], 'raw': {'ISO3': 'ETH', 'Pop_A2': 919585.216375, 'Pop_A2_R': 899912.730018, 'Pop_A2_R2K': 515826.444689, 'SDG911pct': 57.3196075001, 'Pct_Error': 0.184314156967}, 'coverage': 'Proxy', 'status': 'valid'}, {'fid': 11837, 'cluster': 'Dikhil', 'country_side': 'Djibouti', 'key': ['Djibouti', 'Dikhil', 'As Eyla'], 'raw': {'ISO3': 'DJI', 'Pop_A2': 30760.5269507, 'Pop_A2_R': 30438.9859949, 'Pop_A2_R2K': 8294.94165113, 'SDG911pct': 27.2510446062, 'Pct_Error': 1.86154856202}, 'coverage': 'Exact', 'status': 'valid'}, {'fid': 11838, 'cluster': 'Dikhil', 'country_side': 'Djibouti', 'key': ['Djibouti', 'Dikhil', 'Dikhil'], 'raw': {'ISO3': 'DJI', 'Pop_A2': 41226.3504606, 'Pop_A2_R': 40009.6956583, 'Pop_A2_R2K': 22623.0948225, 'SDG911pct': 56.5440312662, 'Pct_Error': 1.86154856202}, 'coverage': 'Exact', 'status': 'valid'}, {'fid': 11839, 'cluster': 'Dikhil', 'country_side': 'Djibouti', 'key': ['Djibouti', 'Dikhil', 'Yoboki'], 'raw': {'ISO3': 'DJI', 'Pop_A2': 43788.2212919, 'Pop_A2_R': 43788.2212919, 'Pop_A2_R2K': 12379.7555247, 'SDG911pct': 28.271884903, 'Pct_Error': 1.86154856202}, 'coverage': 'Exact', 'status': 'valid'}, {'fid': 11843, 'cluster': 'Dikhil', 'country_side': 'Djibouti', 'key': ['Djibouti', 'Tadjourah', 'Balha'], 'raw': {'ISO3': 'DJI', 'Pop_A2': 27732.4345488, 'Pop_A2_R': 27732.4345488, 'Pop_A2_R2K': 6177.94573365, 'SDG911pct': 22.2769685899, 'Pct_Error': 1.86154856202}, 'coverage': 'Exact', 'status': 'valid'}, {'fid': 11844, 'cluster': 'Dikhil', 'country_side': 'Djibouti', 'key': ['Djibouti', 'Tadjourah', 'Dorra'], 'raw': {'ISO3': 'DJI', 'Pop_A2': 24159.2052377, 'Pop_A2_R': 24116.518813, 'Pop_A2_R2K': 4042.14199671, 'SDG911pct': 16.7608850517, 'Pct_Error': 1.86154856202}, 'coverage': 'Exact', 'status': 'valid'}, {'fid': 11845, 'cluster': 'Dikhil', 'country_side': 'Djibouti', 'key': ['Djibouti', 'Tadjourah', 'Randa'], 'raw': {'ISO3': 'DJI', 'Pop_A2': 39655.1871101, 'Pop_A2_R': 39345.0669905, 'Pop_A2_R2K': 8553.05680043, 'SDG911pct': 21.7385747557, 'Pct_Error': 1.86154856202}, 'coverage': 'Exact', 'status': 'valid'}, {'fid': 11846, 'cluster': 'Dikhil', 'country_side': 'Djibouti', 'key': ['Djibouti', 'Tadjourah', 'Tadjourah'], 'raw': {'ISO3': 'DJI', 'Pop_A2': 49969.0995188, 'Pop_A2_R': 46515.1345709, 'Pop_A2_R2K': 26974.1518687, 'SDG911pct': 57.9900544576, 'Pct_Error': 1.86154856202}, 'coverage': 'Exact', 'status': 'valid'}, {'fid': 37032, 'cluster': 'Dikhil', 'country_side': 'Somaliland', 'key': ['Somalia', 'Awdal', 'Boorama'], 'raw': {'ISO3': 'SOM', 'Pop_A2': 446554.888521, 'Pop_A2_R': 442064.5295, 'Pop_A2_R2K': 299035.35652, 'SDG911pct': 67.6451822222, 'Pct_Error': 0.460143539398}, 'coverage': 'Exact', 'status': 'valid'}, {'fid': 37034, 'cluster': 'Dikhil', 'country_side': 'Somaliland', 'key': ['Somalia', 'Awdal', 'Zeylac'], 'raw': {'ISO3': 'SOM', 'Pop_A2': 59234.3349764, 'Pop_A2_R': 59155.5546385, 'Pop_A2_R2K': 11931.3559355, 'SDG911pct': 20.1694600084, 'Pct_Error': 0.460143539398}, 'coverage': 'Exact', 'status': 'valid'}, {'fid': 14509, 'cluster': 'Dikhil', 'country_side': 'Ethiopia', 'key': ['Ethiopia', 'Afar', 'Afar Zone 1'], 'raw': {'ISO3': 'ETH', 'Pop_A2': 604585.237073, 'Pop_A2_R': 598966.235046, 'Pop_A2_R2K': 197322.628673, 'SDG911pct': 32.9438651341, 'Pct_Error': 0.184314156967}, 'coverage': 'Proxy', 'status': 'valid'}, {'fid': 14559, 'cluster': 'Dikhil', 'country_side': 'Ethiopia', 'key': ['Ethiopia', 'Somali', 'Siti'], 'raw': {'ISO3': 'ETH', 'Pop_A2': 853487.743329, 'Pop_A2_R': 847832.319856, 'Pop_A2_R2K': 216476.031823, 'SDG911pct': 25.5328827119, 'Pct_Error': 0.184314156967}, 'coverage': 'Proxy', 'status': 'valid'}]
SOURCE_LAYER = 'source_2_sdgi_9_1_1_rai_2023_subnational'
SOURCE_FID = '__wb_source_fid'
DEFAULT_PROJECT = Path(r'C:\Users\hughl\OneDrive\Desktop\Public Maps\Public Experiment.qgz')
CLUSTERS = (
    ('Mandera Triangle', 'rai_mandera_triangle'),
    ('Moyale/Borana', 'rai_moyale_borana'),
    ('Karamoja', 'rai_karamoja'),
    ('Dikhil', 'rai_dikhil'),
)
SOURCE_DESCRIPTION = (
    'NASA SEDAC SDG 9.1.1 Rural Access Index, 2023 release; GADM v3.6 source '
    'admin2 boundaries; WorldPop 2020 population; GHSL 2015 settlement '
    'classification; OpenStreetMap roads downloaded 31 March 2022. All-season '
    'condition is inferred from OSM tags. Values measure proximity within 2 km, '
    'not journey time. No current-admin boundary assignment has been made.'
)


def log(message):
    print(message, flush=True)


def sha256_file(path):
    value = hashlib.sha256()
    with Path(path).open('rb') as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b''):
            value.update(chunk)
    return value.hexdigest()


def downloads_folders():
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
        archive = Path(explicit).expanduser().resolve()
        if not archive.is_file() or not zipfile.is_zipfile(archive):
            raise ValueError('The supplied path is not a readable ZIP: ' + str(archive))
        return archive
    found = []
    for folder in downloads_folders():
        if folder.is_dir():
            found.extend(path for path in folder.glob('SEDAC_RAI_for_Codex_*.zip') if path.is_file())
    if not found:
        raise FileNotFoundError('Could not find SEDAC_RAI_for_Codex_*.zip in Downloads. '
                                'Drag that smaller ZIP onto this launcher and try again.')
    return max(found, key=lambda path: (path.stat().st_mtime_ns, path.name)).resolve()


def unique_output(archive):
    stamp = datetime.datetime.now().strftime('%Y%m%d_%H%M%S')
    base = archive.parent / ('SEDAC_Rural_Access_Review_' + stamp)
    for suffix in range(1000):
        folder = base if suffix == 0 else base.with_name(base.name + '_' + str(suffix))
        try:
            folder.mkdir()
            return folder
        except FileExistsError:
            continue
    raise RuntimeError('Could not reserve a new review folder.')


def extract_source(archive, folder):
    # One known basename only: do not extract paths or executables supplied by ZIP.
    with zipfile.ZipFile(archive, 'r') as package:
        matches = [info for info in package.infolist()
                   if not info.is_dir() and PurePosixPath(info.filename).name == 'SEDAC_RAI_source_subset.gpkg']
        if len(matches) != 1:
            raise ValueError('The ZIP must contain exactly one SEDAC_RAI_source_subset.gpkg.')
        item = matches[0]
        if item.file_size > 1024 * 1024 * 1024:
            raise ValueError('The subset GeoPackage is unexpectedly larger than 1 GB.')
        target = folder / 'SEDAC_RAI_source_subset.gpkg'
        with package.open(item, 'r') as source, target.open('xb') as output:
            shutil.copyfileobj(source, output, length=1024 * 1024)
    return target


def same_raw_value(actual, expected):
    if isinstance(expected, (int, float)) and not isinstance(expected, bool):
        return actual is not None and math.isfinite(float(actual)) and math.isclose(
            float(actual), float(expected), rel_tol=1e-12, abs_tol=1e-8)
    return actual == expected


def validate_source(source_path):
    from osgeo import ogr
    dataset = ogr.Open(str(source_path), 0)
    if dataset is None:
        raise ValueError('Could not open the source GeoPackage.')
    layer = dataset.GetLayerByName(SOURCE_LAYER)
    if layer is None:
        raise ValueError('Expected subnational source layer is missing: ' + SOURCE_LAYER)
    required = {'NAME_0', 'NAME_1', 'NAME_2', SOURCE_FID}
    for record in AUDITED_RECORDS:
        required.update(record['raw'])
    available = {field.GetName() for field in layer.schema}
    if not required <= available:
        raise ValueError('Missing source fields: ' + ', '.join(sorted(required - available)))
    records_by_fid = {record['fid']: record for record in AUDITED_RECORDS}
    if len(records_by_fid) != 58 or len(AUDITED_RECORDS) != 58:
        raise ValueError('The embedded audit does not contain 58 distinct source records.')
    features = {}
    for feature in layer:
        fid = feature.GetField(SOURCE_FID)
        if fid not in records_by_fid:
            continue
        if fid in features:
            raise ValueError('Duplicate original source FID: ' + str(fid))
        record = records_by_fid[fid]
        actual_key = tuple(feature.GetField(field) for field in ('NAME_0', 'NAME_1', 'NAME_2'))
        if actual_key != tuple(record['key']):
            raise ValueError('Source ID/name mismatch for FID ' + str(fid))
        for field, expected in record['raw'].items():
            actual = feature.GetField(field)
            if not same_raw_value(actual, expected):
                raise ValueError('Unexpected value for FID ' + str(fid) + ', field ' + field)
        numerator = feature.GetField('Pop_A2_R2K')
        denominator = feature.GetField('Pop_A2_R')
        percent = feature.GetField('SDG911pct')
        if record['status'] == 'no_data_zero_denominator':
            if denominator != 0 or numerator != 0 or percent != -9998:
                raise ValueError('The audited no-data record no longer has its expected source values.')
        else:
            if denominator is None or denominator <= 0 or numerator is None or numerator < 0:
                raise ValueError('Invalid rural population quantities for FID ' + str(fid))
            if percent is None or not math.isfinite(percent) or not 0 <= percent <= 100:
                raise ValueError('Invalid percentage for FID ' + str(fid))
            if abs(100 * numerator / denominator - percent) > 1e-5:
                raise ValueError('Population ratio does not reproduce the source percentage for FID ' + str(fid))
        geometry = feature.GetGeometryRef()
        if geometry is None or geometry.IsEmpty():
            raise ValueError('Missing source geometry for FID ' + str(fid))
        features[fid] = feature.Clone()
    missing = set(records_by_fid) - set(features)
    if missing:
        raise ValueError('Audited source IDs were not found: ' + ', '.join(str(fid) for fid in sorted(missing)))
    if layer.GetSpatialRef() is None:
        raise ValueError('The source layer has no coordinate reference system.')
    return dataset, layer, features


def process_source(source_path, output_path):
    """GDAL-only transformation, independent of QGIS imports and project access."""
    from osgeo import ogr, gdal
    gdal.UseExceptions()
    ogr.UseExceptions()
    source_path = Path(source_path)
    output_path = Path(output_path)
    if output_path.exists():
        raise FileExistsError('Refusing to overwrite processed data: ' + str(output_path))
    original_sha = sha256_file(source_path)
    dataset, source, features = validate_source(source_path)
    destination = None
    target = readback = saved = feature = None
    reports = []
    try:
        original_fields = [source.GetLayerDefn().GetFieldDefn(index)
                           for index in range(source.GetLayerDefn().GetFieldCount())]
        added_fields = [
            ('rai_pct', ogr.OFTReal), ('rai_share', ogr.OFTReal), ('beyond_pct', ogr.OFTReal),
            ('data_status', ogr.OFTString), ('cluster', ogr.OFTString),
            ('country_side', ogr.OFTString), ('supplied_coverage_label', ogr.OFTString),
            ('boundary_basis', ogr.OFTString), ('source_release', ogr.OFTString),
        ]
        source_names = {field.GetName().lower() for field in original_fields}
        if source_names & {name.lower() for name, unused in added_fields}:
            raise ValueError('A derived field name already occurs in the source; no fields will be replaced.')
        destination = ogr.GetDriverByName('GPKG').CreateDataSource(str(output_path))
        if destination is None:
            raise RuntimeError('Could not create the processed GeoPackage.')
        for cluster, layer_name in CLUSTERS:
            records = [record for record in AUDITED_RECORDS if record['cluster'] == cluster]
            if not records:
                raise ValueError('No audited records for cluster ' + cluster)
            target = destination.CreateLayer(layer_name, source.GetSpatialRef(), ogr.wkbUnknown,
                                              options=['FID=__wb_rowid', 'GEOMETRY_NAME=__wb_geometry'])
            for definition in original_fields:
                if target.CreateField(definition) != 0:
                    raise RuntimeError('Could not preserve field ' + definition.GetName())
            for name, field_type in added_fields:
                definition = ogr.FieldDefn(name, field_type)
                if target.CreateField(definition) != 0:
                    raise RuntimeError('Could not create field ' + name)
            if target.StartTransaction() != 0:
                raise RuntimeError('Could not start output transaction.')
            try:
                no_data = 0
                for record in records:
                    original = features[record['fid']]
                    feature = ogr.Feature(target.GetLayerDefn())
                    for index, definition in enumerate(original_fields):
                        if original.IsFieldSetAndNotNull(index):
                            feature.SetField(index, original.GetField(index))
                    feature.SetGeometry(original.GetGeometryRef())
                    feature.SetField('cluster', cluster)
                    feature.SetField('country_side', record['country_side'])
                    feature.SetField('supplied_coverage_label', record['coverage'])
                    feature.SetField('boundary_basis', 'GADM v3.6 source admin2')
                    feature.SetField('source_release', 'NASA SEDAC 2023 release')
                    feature.SetField('data_status', record['status'])
                    if record['status'] == 'valid':
                        percent = original.GetField('SDG911pct')
                        feature.SetField('rai_pct', percent)
                        feature.SetField('rai_share', percent / 100)
                        feature.SetField('beyond_pct', 100 - percent)
                    else:
                        no_data += 1  # Numeric derived fields remain NULL, never zero.
                    if target.CreateFeature(feature) != 0:
                        raise RuntimeError('Could not write source FID ' + str(record['fid']))
                    feature = None
                if target.CommitTransaction() != 0:
                    raise RuntimeError('Could not commit output layer ' + layer_name)
            except Exception:
                target.RollbackTransaction()
                raise
            reports.append({'cluster': cluster, 'layer': layer_name, 'records': len(records),
                            'valid_values': len(records) - no_data, 'no_data': no_data})
            target = None
        destination = None
        readback = ogr.Open(str(output_path), 0)
        if readback is None:
            raise RuntimeError('Could not verify the saved processed GeoPackage.')
        geometry_hashes = {}
        verified_ids = []
        for cluster, layer_name in CLUSTERS:
            saved = readback.GetLayerByName(layer_name)
            expected_ids = {record['fid'] for record in AUDITED_RECORDS if record['cluster'] == cluster}
            saved_ids = set()
            for feature in saved:
                fid = feature.GetField(SOURCE_FID)
                if fid in saved_ids or fid not in expected_ids:
                    raise RuntimeError('Unexpected source record ID in saved output.')
                saved_ids.add(fid)
                original = features[fid]
                for definition in original_fields:
                    name = definition.GetName()
                    if feature.GetField(name) != original.GetField(name):
                        raise RuntimeError('Saved output changed source field ' + name + ' for FID ' + str(fid))
                if feature.GetGeometryRef().ExportToWkb() != original.GetGeometryRef().ExportToWkb():
                    raise RuntimeError('Saved output changed source geometry for FID ' + str(fid))
                geometry_hashes[str(fid)] = hashlib.sha256(original.GetGeometryRef().ExportToWkb()).hexdigest()
                record = next(record for record in AUDITED_RECORDS if record['fid'] == fid)
                if record['status'] != feature.GetField('data_status'):
                    raise RuntimeError('Saved output status differs from audit.')
                if record['status'] == 'no_data_zero_denominator':
                    if any(feature.GetField(name) is not None for name in ('rai_pct', 'rai_share', 'beyond_pct')):
                        raise RuntimeError('A no-data indicator was saved as a numeric value.')
                elif feature.GetField('rai_pct') != original.GetField('SDG911pct'):
                    raise RuntimeError('Saved mapping percentage differs from the source indicator.')
            if saved_ids != expected_ids:
                raise RuntimeError('Saved source record IDs differ from the audited selection.')
            verified_ids.extend(sorted(saved_ids))
            saved = None
        feature = None
        readback = None
    except Exception:
        feature = saved = target = None
        readback = None
        destination = None
        if output_path.exists():
            try:
                output_path.unlink()  # Our new incomplete file only, never an input.
            except OSError:
                log('The incomplete output could not be removed; do not use it.')
        raise
    finally:
        features.clear()
        source = None
        dataset = None
    if sha256_file(source_path) != original_sha:
        raise RuntimeError('Unexpected source-file change detected.')
    return {'records': 58, 'valid_values': 57, 'no_data': 1,
            'source_sha256': original_sha, 'processed_sha256': sha256_file(output_path),
            'source_layer': SOURCE_LAYER, 'source_fid_field': SOURCE_FID,
            'layers': reports, 'method': SOURCE_DESCRIPTION,
            'checks': {'expected_raw_values': True, 'population_ratio': True,
                       'all_original_fields_preserved': True, 'all_source_ids_preserved': True,
                       'full_geometry_wkb_unchanged': True, 'no_data_derived_fields_null': True,
                       'source_file_sha256_unchanged': True},
            'preserved_source_ids': sorted(verified_ids), 'geometry_sha256_by_source_id': geometry_hashes,
            'coverage_label_policy': 'Supplied Exact/Partial/Proxy label retained as raw provenance only; '
                                     'no clipping, weighting, or join treatment inferred.',
            'geometry_policy': 'Full original source polygons; no simplification or reprojection.'}


def review_path(original):
    stamp = datetime.datetime.now().strftime('%Y%m%d_%H%M%S')
    for suffix in range(1000):
        name = original.stem + '_SEDAC_Rural_Access_Review_' + stamp
        if suffix:
            name += '_' + str(suffix)
        path = original.with_name(name + '.qgz')
        if not path.exists():
            return path
    raise RuntimeError('Could not choose a new project filename.')


def create_review_project(original, processed_path):
    # Standalone QGIS does not execute project macros. No macros are introduced.
    original = Path(original)
    if not original.is_file():
        raise FileNotFoundError('Original project not found: ' + str(original) +
                                '. The processed GeoPackage is still available in the review folder.')
    original_sha = sha256_file(original)
    old_platform = os.environ.get('QT_QPA_PLATFORM')
    os.environ['QT_QPA_PLATFORM'] = 'offscreen'
    from qgis.core import (QgsApplication, QgsProject, QgsVectorLayer, QgsFillSymbol,
                           QgsRuleBasedRenderer, QgsCoordinateTransform,
                           QgsReferencedRectangle, Qgis)
    application = QgsApplication([], False)
    application.initQgis()
    project = QgsProject.instance()
    root = group = layer = mandera = node = renderer = rule_root = rule = fill = symbol = metadata = None
    new_layers = []
    existing = []
    try:
        log('Reading your original project and preparing a separate review copy...')
        if not project.read(str(original)):
            raise RuntimeError('QGIS could not read the original project.')
        root = project.layerTreeRoot()
        group = root.insertGroup(0, 'Rural access | SEDAC source boundaries')
        group.setExpanded(True)
        group.setItemVisibilityChecked(True)
        new_layers = []
        for cluster, layer_name in CLUSTERS:
            layer = QgsVectorLayer(str(Path(processed_path).resolve()) + '|layername=' + layer_name,
                                   cluster + ' | Rural access (%) | GADM v3.6 source units', 'ogr')
            if not layer.isValid():
                raise RuntimeError('QGIS could not read processed layer ' + layer_name)
            rule_root = QgsRuleBasedRenderer.Rule(None)
            renderer = QgsRuleBasedRenderer(rule_root)
            bands = [
                ('0 to <20%', '"rai_pct" >= 0 AND "rai_pct" < 20', '#ffffcc'),
                ('20 to <40%', '"rai_pct" >= 20 AND "rai_pct" < 40', '#c2e699'),
                ('40 to <60%', '"rai_pct" >= 40 AND "rai_pct" < 60', '#78c679'),
                ('60 to <80%', '"rai_pct" >= 60 AND "rai_pct" < 80', '#31a354'),
                ('80 to 100%', '"rai_pct" >= 80 AND "rai_pct" <= 100', '#006837'),
                ('No computable value', '"rai_pct" IS NULL', '#cbd5e1'),
            ]
            for label, expression, colour in bands:
                fill = QgsFillSymbol.createSimple({'color': colour, 'outline_color': '#64748b',
                                                   'outline_width': '0.2'})
                rule = QgsRuleBasedRenderer.Rule(fill, 0, 0, expression, label)
                rule_root.appendChild(rule)
            layer.setRenderer(renderer)
            layer.setOpacity(0.9)
            layer.setDisplayExpression('"NAME_2"')
            aliases = {'rai_pct': 'Rural population within 2 km (%)',
                       'rai_share': 'Rural population within 2 km (share)',
                       'beyond_pct': 'Rural population beyond 2 km (%)',
                       'data_status': 'Indicator status',
                       SOURCE_FID: 'Original SEDAC shapefile record ID',
                       'supplied_coverage_label': 'Supplied coverage label (uninterpreted)'}
            for field, alias in aliases.items():
                layer.setFieldAlias(layer.fields().indexFromName(field), alias)
            metadata = layer.metadata()
            metadata.setTitle(layer.name())
            metadata.setAbstract(SOURCE_DESCRIPTION + '\nSource DOI: https://doi.org/10.7927/fcre-m572\n'
                                 'Supplied coverage labels are retained without assuming their meaning. '
                                 'A source unit is not necessarily equivalent to an existing map unit.')
            layer.setMetadata(metadata)
            layer.setCustomProperty('wb_rural_access/boundary_basis', 'GADM v3.6 source admin2')
            project.addMapLayer(layer, False)
            node = group.addLayer(layer)
            node.setItemVisibilityChecked(cluster == 'Mandera Triangle')
            node.setExpanded(cluster == 'Mandera Triangle')
            new_layers.append(layer)
        # Retain any established custom order, with the new review material above it.
        if root.hasCustomLayerOrder():
            existing = [layer for layer in root.customLayerOrder() if layer not in new_layers]
            root.setCustomLayerOrder(new_layers + existing)
        project.setFilePathStorage(Qgis.FilePathType.Absolute)
        mandera = new_layers[0]
        extent = QgsCoordinateTransform(mandera.crs(), project.crs(), project).transformBoundingBox(mandera.extent())
        extent.scale(1.12)
        project.viewSettings().setDefaultViewExtent(QgsReferencedRectangle(extent, project.crs()))
        project.writeEntry('wb_rural_access', 'source_description', SOURCE_DESCRIPTION)
        project.writeEntry('wb_rural_access', 'initial_cluster', 'Mandera Triangle')
        target = review_path(original)
        if target.resolve() == original.resolve():
            raise RuntimeError('Refusing to overwrite the original project.')
        if not project.write(str(target)):
            raise RuntimeError('QGIS could not save the separate review project.')
        if sha256_file(original) != original_sha:
            raise RuntimeError('Unexpected original-project change detected.')
        invalid_existing = [layer.name() for layer in project.mapLayers().values()
                            if layer not in new_layers and not layer.isValid()]
        return {'review_project': str(target), 'original_project_sha256': original_sha,
                'original_project_preserved': True, 'new_group': group.name(),
                'initial_layer': mandera.name(), 'extent_project_crs': [extent.xMinimum(), extent.yMinimum(),
                                                                      extent.xMaximum(), extent.yMaximum()],
                'unavailable_existing_layers': invalid_existing}
    finally:
        root = group = layer = mandera = node = renderer = rule_root = rule = fill = symbol = metadata = None
        new_layers.clear()
        existing.clear()
        project.clear()
        project = None
        application.exitQgis()
        if old_platform is None:
            os.environ.pop('QT_QPA_PLATFORM', None)
        else:
            os.environ['QT_QPA_PLATFORM'] = old_platform


def launch_qgis(review):
    if os.name != 'nt':
        raise RuntimeError('Automatic QGIS opening is intended for Windows.')
    roots = []
    if os.environ.get('WB_SEDAC_QGIS_BIN'):
        roots.append(Path(os.environ['WB_SEDAC_QGIS_BIN']))
    if os.environ.get('OSGEO4W_ROOT'):
        roots.append(Path(os.environ['OSGEO4W_ROOT']) / 'bin')
    roots.append(Path(sys.executable).parent)
    executable = None
    for root in roots:
        for name in ('qgis-bin.exe', 'qgis-ltr-bin.exe'):
            candidate = root / name
            if candidate.is_file():
                executable = candidate
                break
        if executable:
            break
    if executable is None:
        raise FileNotFoundError('QGIS GUI executable was not found. Open the review .qgz shown above manually.')
    extent = ','.join(format(value, '.12g') for value in review['extent_project_crs'])
    # Argument list only: no shell interpolation, no --code and no project macro.
    child_env = os.environ.copy()
    # The GUI must never inherit our headless setup override.
    if child_env.get('QT_QPA_PLATFORM') == 'offscreen':
        child_env.pop('QT_QPA_PLATFORM', None)
    subprocess.Popen([str(executable), '--nologo', '--project', review['review_project'], '--extent', extent],
                     cwd=str(executable.parent), env=child_env, shell=False,
                     creationflags=subprocess.DETACHED_PROCESS | subprocess.CREATE_NEW_PROCESS_GROUP)
    return str(executable)


def write_readme(folder, report):
    text = 'SEDAC RURAL ACCESS REVIEW\n\n'
    if report.get('processed_data'):
        text += ('Rural_Access_SEDAC_source_units.gpkg contains four cluster layers: '
                 '58 source units, 57 valid percentages, and one no-data unit.\n')
    else:
        text += 'No processed GeoPackage was completed. Read setup_report.json for the stopped check.\n'
    text += (
        'The percentage is the share of modelled rural population within 2 km of a '
        'road classified as likely all-season.\n\n' + SOURCE_DESCRIPTION + '\n\n'
        'Five common bands: 0-<20%, 20-<40%, 40-<60%, 60-<80%, 80-100%. '
        'Grey means no computable value. Kenya / West Pokot / unknown 8 is grey '
        'because the source has a zero rural population denominator and code -9998.\n\n'
        'All original source fields and full polygons are retained. The original '
        'source record ID is __wb_source_fid. Derived percentages are NULL for '
        'no-data. Supplied Exact/Partial/Proxy labels are retained as provenance; '
        'their meaning has not been assumed. Unknown names remain unchanged.\n\n'
        'Source attribution: CIESIN, Columbia University (2023), SDG Indicator '
        '9.1.1 Rural Access Index, 2023 Release. NASA SEDAC. '
        'https://doi.org/10.7927/fcre-m572\n\n'
    )
    if report.get('qgis_review'):
        text += ('The separate QGIS review copy preserves the original project. The new '
                 'group is first; Mandera is visible and the other three new cluster layers '
                 'are off initially. Other original project content remains in the copy.\n\n')
        text += 'Review project: ' + report['qgis_review']['review_project'] + '\n'
    if report.get('error'):
        text += '\nSetup stopped: ' + report['error'] + '\n'
    (folder / 'READ_ME.txt').write_text(text, encoding='utf-8')


def run_setup(archive, project=DEFAULT_PROJECT, open_gui=True, data_only=False):
    archive = Path(archive).resolve()
    archive_sha = sha256_file(archive)
    folder = unique_output(archive)
    report = {'input_archive': archive.name, 'input_archive_sha256': archive_sha,
              'output_folder': str(folder), 'status': 'started'}
    try:
        source = extract_source(archive, folder)
        output = folder / 'Rural_Access_SEDAC_source_units.gpkg'
        log('Validating the 58 audited source records and building the four cluster layers...')
        report['processed_data'] = process_source(source, output)
        log('Processed data: ' + str(output))
        if not data_only:
            review = create_review_project(project, output)
            report['qgis_review'] = review
            log('Separate review project: ' + review['review_project'])
            if open_gui:
                report['qgis_executable'] = launch_qgis(review)
                log('Opening the review copy in QGIS...')
        if sha256_file(archive) != archive_sha:
            raise RuntimeError('Unexpected input archive change detected.')
        report['status'] = 'data_prepared' if data_only else 'complete'
        return folder, report
    except Exception as error:
        report['status'] = 'needs_attention'
        report['error'] = str(error)
        raise
    finally:
        (folder / 'setup_report.json').write_text(json.dumps(report, indent=2, ensure_ascii=False), encoding='utf-8')
        write_readme(folder, report)
        upload_report = {key: value for key, value in report.items()
                         if key not in ('output_folder', 'qgis_review', 'qgis_executable', 'error')}
        if report.get('qgis_review'):
            upload_report['qgis_review'] = {key: value for key, value in report['qgis_review'].items()
                                          if key != 'review_project'}
            upload_report['qgis_review']['review_project_created'] = True
            upload_report['qgis_review']['review_project_filename'] = Path(report['qgis_review']['review_project']).name
        else:
            upload_report['qgis_review'] = {'review_project_created': False}
        if report.get('error'):
            upload_report['setup_error'] = report['error'].replace(str(folder), '[review folder]').replace(
                str(project), '[original project]')
        upload_report['qgis_gui_launch_requested'] = bool(report.get('qgis_executable'))
        with zipfile.ZipFile(folder / 'RAI_SETUP_REPORT.zip', 'w', compression=zipfile.ZIP_DEFLATED) as package:
            package.writestr('RAI_SETUP_REPORT.json', json.dumps(upload_report, indent=2, ensure_ascii=False))
        log('Upload this small report to Codex: ' + str(folder / 'RAI_SETUP_REPORT.zip'))
        if os.name == 'nt' and open_gui:
            os.startfile(str(folder))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--input', help='Smaller SEDAC_RAI_for_Codex ZIP (drag/drop is supported).')
    parser.add_argument('--project', default=str(DEFAULT_PROJECT), help='Original QGIS project path.')
    parser.add_argument('--data-only', action='store_true', help='Prepare and validate data without importing QGIS.')
    parser.add_argument('--no-open', action='store_true', help='Do not launch QGIS or open a folder.')
    args = parser.parse_args()
    try:
        folder, report = run_setup(find_archive(args.input), args.project,
                                   open_gui=not args.no_open, data_only=args.data_only)
        log('Done. Results are in: ' + str(folder))
        return 0
    except Exception as error:
        log('Setup stopped: ' + str(error))
        traceback.print_exc()
        log('Send the text from this window and setup_report.json to Codex if help is needed.')
        return 1


if __name__ == '__main__':
    raise SystemExit(main())
