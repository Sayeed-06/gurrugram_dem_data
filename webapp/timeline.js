(() => {
  const history = window.DEM_ACQUISITION_TIMELINE;
  const slider = document.querySelector('#acquisitionSlider');
  const tileSelect = document.querySelector('#timelineTile');
  let source = 'alos', entries = [];
  const formatDate = date => new Date(date).toLocaleDateString('en-GB', {day:'numeric', month:'short', year:'numeric', timeZone:'UTC'});
  const filtered = () => source === 'alos'
    ? history.alos.map(entry => ({...entry, scenes:entry.scenes.filter(scene => tileSelect.value === 'all' || scene.tile === tileSelect.value)})).filter(entry => entry.scenes.length)
    : history.copernicus.filter(entry => tileSelect.value === 'all' || entry.tile === tileSelect.value);

  function render(reset = false) {
    entries = filtered();
    slider.max = Math.max(0, entries.length - 1);
    if (reset) slider.value = 0;
    slider.disabled = entries.length < 2;
    document.querySelectorAll('[data-timeline]').forEach(button => button.setAttribute('aria-pressed', button.dataset.timeline === source));
    const isAlos = source === 'alos';
    const label = isAlos ? 'Browse observation dates' : 'Browse source tile ranges';
    document.querySelector('#acquisitionSliderLabel').textContent = label;
    slider.setAttribute('aria-label', label);
    document.querySelector('#timelineSummary').textContent = isAlos
      ? `${entries.length} distinct observation dates · ${formatDate(entries[0].date)} to ${formatDate(entries.at(-1).date)}`
      : `${entries.length} tile acquisition ranges · individual acquisition dates are unavailable in the retained XML`;
    drawChart();
    const entry = entries[Number(slider.value)];
    document.querySelector('#acquisitionDate').textContent = isAlos ? formatDate(entry.date) : entry.tile;
    const detail = document.querySelector('#acquisitionDetail');
    if (isAlos) {
      detail.innerHTML = `<h3>${formatDate(entry.date)} <small>Observation ${Number(slider.value)+1} of ${entries.length}</small></h3><p class="small">${entry.scenes.length} source scene records on this date. Records may repeat across tile lists.</p><div class="scene-table"><table><thead><tr><th>Tile</th><th>Scene ID</th><th>Path / frame</th><th>Stereo mode</th></tr></thead><tbody>${entry.scenes.map(scene => `<tr><td>${scene.tile}</td><td>${scene.scene}</td><td>${scene.path} / ${scene.frame}</td><td>${scene.stereo_mode}</td></tr>`).join('')}</tbody></table></div>`;
    } else {
      detail.innerHTML = `<h3>${entry.tile}</h3><p>${formatDate(entry.start)} → ${formatDate(entry.end)}</p><p class="small">${entry.acquisitions} contributing acquisitions · source tile version ${entry.tile_version}. Only the acquisition envelope is available; no individual date-specific DEMs are included.</p>`;
    }
  }

  function drawChart() {
    const chart = document.querySelector('#acquisitionChart');
    const start = Date.parse(source === 'alos' ? '2006-01-01' : '2011-01-01');
    const end = Date.parse(source === 'alos' ? '2012-01-01' : '2015-01-01');
    const x = date => 120 + (Date.parse(date)-start)/(end-start)*750;
    let svg = '';
    const firstYear = source === 'alos' ? 2006 : 2011;
    const lastYear = source === 'alos' ? 2011 : 2014;
    for (let year=firstYear; year<=lastYear; year++) {
      const pos=x(`${year}-01-01`);
      svg+=`<line x1="${pos}" y1="15" x2="${pos}" y2="95" stroke="#dde4df"/><text x="${pos}" y="116" text-anchor="middle" font-size="12" fill="#52655c">${year}</text>`;
    }
    ['N028E076','N028E077'].forEach((tile,index) => {
      const y=35+index*45;
      svg+=`<text x="4" y="${y+4}" font-size="12" fill="#52655c">${tile}</text><line x1="120" x2="870" y1="${y}" y2="${y}" stroke="#d9ded5"/>`;
      entries.forEach((entry,position) => {
        const selected=position===Number(slider.value), color=selected?'#e66b3e':'#197d63';
        if(source==='alos' && entry.scenes.some(scene => scene.tile===tile)) {
          svg+=`<circle cx="${x(entry.date)}" cy="${y}" r="${selected?6:3}" fill="${color}"><title>${entry.date} · ${tile}</title></circle>`;
        } else if(source==='copernicus' && entry.tile===tile) {
          svg+=`<rect x="${x(entry.start)}" y="${y-7}" width="${x(entry.end)-x(entry.start)}" height="14" rx="4" fill="${color}"><title>${entry.start} to ${entry.end} · ${entry.acquisitions} acquisitions</title></rect>`;
        }
      });
    });
    chart.innerHTML=svg;
  }
  document.querySelectorAll('[data-timeline]').forEach(button => button.addEventListener('click', () => {source=button.dataset.timeline;render(true);}));
  tileSelect.addEventListener('change',()=>render(true));
  slider.addEventListener('input',()=>render());
  document.querySelector('#exportTimeline').addEventListener('click',()=>{
    const rows = source==='alos'
      ? [['observation_date_UTC','tile','scene_id','path','frame','stereo_mode'], ...entries.flatMap(entry=>entry.scenes.map(scene=>[entry.date,scene.tile,scene.scene,scene.path,scene.frame,scene.stereo_mode]))]
      : [['tile','start_UTC','end_UTC','contributing_acquisitions','tile_version'],...entries.map(entry=>[entry.tile,entry.start,entry.end,entry.acquisitions,entry.tile_version])];
    const csv=rows.map(row=>row.map(value=>'"'+String(value).replaceAll('"','""')+'"').join(',')).join('\r\n');
    const url=URL.createObjectURL(new Blob([csv],{type:'text/csv;charset=utf-8'}));
    const link=document.createElement('a');link.href=url;link.download=`${source}_acquisition_timeline_${tileSelect.value}.csv`;link.click();setTimeout(()=>URL.revokeObjectURL(url),1000);
  });
  render(true);
})();
