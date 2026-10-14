const fs=require('fs'),vm=require('vm'),assert=require('node:assert/strict');
const html=fs.readFileSync('source_balance/working/page_map_karamoja.html','utf8');
const fn=html.slice(html.indexOf('async function setPreset('),html.indexOf('\nasync function syncRoadDetail()'));
const log=[],pending=new Map(),box={style:{}},menu={inert:false};
const noop=()=>{};const c={setTimeout,clearTimeout,console:{error:noop},presetSerial:0,currentPreset:'clean',requestedPreset:'clean',viewReady:true,currentContext:new Set(),PRESET_GROUPS:{},CONTEXT_GROUPS:{},themeState:{acled:'points'},resolvePreset:x=>x,prepareTheme:noop,document:{getElementById:id=>id==='viewLoading'?box:menu,querySelectorAll:()=>[]},thematicGroups:name=>[name],map:{getZoom:()=>7,stop:noop},ensureGroup:name=>new Promise((resolve,reject)=>pending.set(name,{resolve,reject})),clearRuralAccessSelection:()=>log.push('clear'),corridors:{prepare:()=>log.push('corridors.clear'),ready:noop},sedac:{prepare:()=>log.push('sedac.clear')},closeMapOverlays:noop,hideProjectLayer:noop,closeProjectDetails:noop,setProjectPanelVisible:noop,setEventPanelVisible:noop,pEl:()=>({checked:false}),applyPresetNow:name=>{c.currentPreset=name;log.push(name)},renderEventResults:noop,renderProjectMap:noop};
vm.createContext(c);vm.runInContext(fn,c);
(async()=>{
 const a=c.setPreset('a');assert.equal(log.length,0,'Old view must remain visible while loading');
 const b=c.setPreset('b');pending.get('b').resolve();await b;assert.equal(c.currentPreset,'b');
 const completed=[...log];pending.get('a').resolve();await a;assert.deepEqual(log,completed,'Stale request must never replace the newer view');
 const failure=c.setPreset('failed');pending.get('failed').reject(new Error('offline'));await failure;assert.deepEqual(log,completed,'Load failure must retain the previous view');assert.equal(menu.inert,false);assert.equal(box.style.display,'block');
 const retry=c.setPreset('failed');pending.get('failed').resolve();await retry;assert.equal(c.currentPreset,'failed');assert.equal(box.style.display,'none');
 console.log('Passed: retain old view during load, latest selection wins, failed load preserves map, retry succeeds.');
})();
