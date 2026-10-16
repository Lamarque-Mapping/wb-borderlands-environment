(function () {
  'use strict';
  const handlers = new Map(), urls = new Map();
  let renderer, busy = false;
  const $ = id => document.getElementById(id);
  function quote(value) {
    if (typeof value === 'number') return Number.isFinite(value) ? String(value) : '';
    let text = String(value ?? '');
    if (/^\s*[=+@\-]/.test(text) || /^[\t\r]/.test(text)) text = "'" + text;
    return '"' + text.replace(/"/g, '""') + '"';
  }
  function csv(fields, rows) {
    return '\ufeff' + [fields, ...rows].map(row => row.map(quote).join(',')).join('\r\n') + '\r\n';
  }
  function download(id, blob, filename, message) {
    const status = $(id + 'ExportStatus');
    if (urls.has(id)) URL.revokeObjectURL(urls.get(id));
    const url = URL.createObjectURL(blob); urls.set(id, url);
    const a = document.createElement('a');
    a.href = url; a.download = filename; a.textContent = 'Download again';
    status.replaceChildren(document.createTextNode(message + ' '), a);
    if (blob.type === 'image/png') {
      const preview = document.createElement('button');
      preview.type = 'button'; preview.className = 'analysis-export-preview'; preview.textContent = 'Preview chart';
      preview.onclick = () => {
        const dialog = document.createElement('dialog'); dialog.className = 'analysis-export-dialog';
        dialog.setAttribute('aria-label', 'Exported chart preview');
        const close = document.createElement('button'); close.type = 'button'; close.className = 'analysis-export'; close.textContent = 'Close preview';
        const image = document.createElement('img'); image.src = url; image.alt = text($(id).querySelector('h2')) + ' — exported chart';
        close.onclick = () => dialog.close();
        dialog.addEventListener('close', () => {dialog.remove();preview.focus();});
        dialog.append(close, image); document.body.append(dialog); dialog.showModal(); close.focus();
      };
      status.append(document.createTextNode(' · '), preview);
    }
    a.click();
  }
  function saveCSV(id, fields, rows, filename) {
    download(id, new Blob([csv(fields, rows)], {type:'text/csv;charset=utf-8'}), filename,
      rows.length.toLocaleString('en-GB') + ' rows ready.');
  }
  function register(id, callback) {
    handlers.set(id, callback);
    const button = $(id + 'ExportCSV');
    button.disabled = false;
    button.onclick = () => {
      try { callback(); } catch (error) {
        $(id + 'ExportStatus').textContent = 'Export could not be prepared. Please try again.';
        console.error(error);
      }
    };
    if ($(id + 'ExportPNG')) $(id + 'ExportPNG').disabled = false;
  }
  function loadRenderer() {
    if (window.htmlToImage) return Promise.resolve(window.htmlToImage);
    if (!renderer) renderer = new Promise((resolve, reject) => {
      const script = document.createElement('script');
      script.src = 'vendor/html-to-image.js';
      script.onload = () => window.htmlToImage ? resolve(window.htmlToImage) : reject(Error('Renderer unavailable'));
      script.onerror = () => {script.remove(); reject(Error('Renderer unavailable'));};
      document.head.append(script);
    }).catch(error => {renderer = null; throw error;});
    return renderer;
  }
  const text = node => (node?.textContent || '').replace(/\s+/g, ' ').trim();
  function context(section) {
    const local = [...section.querySelectorAll('select')].map(select =>
      text(select.closest('label')?.childNodes[0]) + ': ' + text(select.selectedOptions[0]));
    const common = ['population','settlement','landcover','healthcare'].includes(section.id);
    if (common) {
      const level = $('levelSelect');
      local.unshift('Compare: ' + text(level.selectedOptions[0]));
      if (level.value !== 'cluster') local.unshift('Borderland: ' + text($('clusterSelect').selectedOptions[0]), 'Country: ' + text($('countrySelect').selectedOptions[0]));
    }
    if (section.id === 'portfolio') local.unshift('Geography: ' + text($('portfolioScope')));
    if (section.id === 'rural-access') local.unshift('Selection: ' + text($('raiSelectionTitle')));
    for (const group of section.querySelectorAll('.button-row')) {
      const active = group.querySelector('[aria-pressed="true"]');
      if (active) local.push(text(active));
    }
    return local.join(' · ');
  }
  async function saveChart(id) {
    if (busy) return;
    busy = true;
    const section = $(id), button = $(id + 'ExportPNG'), status = $(id + 'ExportStatus');
    let sheet;
    button.disabled = true; status.textContent = 'Preparing chart…';
    try {
      // Clone before awaiting anything, so the export reflects the clicked selection.
      sheet = section.cloneNode(true);
      const description = context(section);
      sheet.querySelectorAll('.control-bar .chart-legend').forEach(node => node.closest('.control-bar').before(node));
      sheet.querySelectorAll('.analysis-exports, .control-bar, .rai-actions, .button-row, [hidden], .loading').forEach(node => node.remove());
      sheet.querySelectorAll('details').forEach(node => node.open = true);
      sheet.querySelectorAll('.chart-scroll, .rai-table-scroll, .sedac-table-wrap, .line-wrap').forEach(node => {
        node.style.maxHeight = 'none'; node.style.height = 'auto'; node.style.overflow = 'visible';
      });
      sheet.querySelectorAll('.rai-cluster-card').forEach(node => {
        const replacement = document.createElement('div');
        replacement.className = node.className;
        replacement.innerHTML = node.innerHTML;
        replacement.setAttribute('aria-pressed', node.getAttribute('aria-pressed'));
        node.replaceWith(replacement);
      });
      sheet.querySelectorAll('a').forEach(node => node.removeAttribute('href'));
      sheet.querySelectorAll('[id]').forEach(node => node.removeAttribute('id'));
      sheet.removeAttribute('id');
      sheet.classList.add('analysis-export-sheet');
      Object.assign(sheet.style, {position:'fixed',left:'-20000px',top:'0',width:Math.max(760, Math.min(1200, section.offsetWidth))+'px',margin:'0',padding:'32px',background:'#fff',border:'1px solid #ccd6df',borderRadius:'0',boxShadow:'none'});
      const info = document.createElement('p'); info.className = 'analysis-export-context'; info.textContent = description;
      sheet.querySelector('.analysis-head').after(info);
      const footer = document.createElement('p'); footer.className = 'chart-foot';
      footer.textContent = 'Borderland maps · Mapping by Hugh Lamarque · Exported ' + new Date().toISOString().slice(0,10) + ' · https://hughlamarque-dev.github.io/wb-borderlands-environment/';
      sheet.append(footer);
      // Use a reliable export font without requesting a second copy of the web font.
      [sheet, ...sheet.querySelectorAll('*')].forEach(node => node.style.fontFamily = 'Arial, Helvetica, sans-serif');
      document.body.append(sheet);
      const image = await loadRenderer();
      const width = Math.ceil(sheet.getBoundingClientRect().width), height = Math.ceil(sheet.scrollHeight);
      const ratio = Math.min(2, 16000 / height, Math.sqrt(24000000 / (width * height)));
      const blob = await image.toBlob(sheet, {width, height, pixelRatio:ratio, backgroundColor:'#fff',skipFonts:true,
        style:{position:'static',left:'auto',top:'auto',transform:'none'}});
      if (!blob || !blob.size) throw Error('Empty chart image');
      download(id, blob, 'borderland-' + id + '-' + new Date().toISOString().slice(0,10) + '.png',
        'Chart ready · ' + Math.round(width*ratio).toLocaleString('en-GB') + ' × ' + Math.round(height*ratio).toLocaleString('en-GB') + ' pixels.');
    } catch (error) {
      status.textContent = 'Chart export could not finish. Please try again; the CSV export is still available.';
      console.error(error);
    } finally {sheet?.remove(); button.disabled = false; busy = false;}
  }
  document.querySelectorAll('[data-export-chart]').forEach(button => button.onclick = () => saveChart(button.dataset.exportChart));
  window.WBAnalysisExport = {register, saveCSV, csv};
  const sources = $('data-sources');
  if (sources) register('data-sources', () => {
    const rows = [...sources.querySelectorAll('table tbody tr')].map(row => [...row.cells].map(cell => text(cell) + [...cell.querySelectorAll('a[href]')].map(a => ' [' + a.href + ']').join('')));
    saveCSV('data-sources', ['theme','source','licence_or_use_terms','notes'], rows, 'borderland-data-sources.csv');
  });
})();
