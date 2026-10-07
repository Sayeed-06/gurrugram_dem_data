(() => {
  const $ = id => document.getElementById(id);
  const mode=$('mapMode'), slider=$('datedSlider'), play=$('datedPlay');
  let frames=[], timer, point, source=current, maps=window.DEM_DATED_MAPS;
  const cache=new WeakMap();
  function values(frame, field='elevations_base64') {
    const saved=cache.get(frame)||{};if(saved[field]) return saved[field];
    const raw=atob(frame[field]), bytes=new Uint8Array(raw.length);
    for(let i=0;i<raw.length;i++) bytes[i]=raw.charCodeAt(i);
    const view=new DataView(bytes.buffer), data=new Float32Array(raw.length/4);
    for(let i=0;i<data.length;i++) data[i]=view.getFloat32(i*4,true);
    saved[field]=data;cache.set(frame,saved); return data;
  }
  function validate(pack) {
    if(pack.version!==1 || pack.crs!=='EPSG:32643' || pack.vertical_datum!=='EGM96' || !Array.isArray(pack.frames) || pack.frames.length>24) throw Error('Use a prepared EGM96 dated-map package (up to 24 maps).');
    const grid=meta.products.alos, seen=new Set();
    for(const f of pack.frames) {
      if(!['alos','copernicus','tandemx'].includes(f.source) || !/^\d{4}-\d{2}-\d{2}$/.test(f.date) || !Number.isFinite(Date.parse(f.date)) || new Date(f.date).toISOString().slice(0,10)!==f.date || typeof f.label!=='string' || !f.label.trim() || typeof f.provenance!=='string' || !f.provenance.trim()) throw Error('Each map needs a source, valid acquisition date, label and provenance.');
      if(f.width!==grid.shape[1] || f.height!==grid.shape[0] || JSON.stringify(f.bounds_utm43n)!==JSON.stringify(grid.bounds_utm43n)) throw Error('Maps must match the municipal grid. Prepare GeoTIFFs with import_dated_dem.py.');
      if(typeof f.elevations_base64!=='string' || atob(f.elevations_base64).length!==f.width*f.height*4) throw Error('Invalid elevation grid.');
      const key=f.source+f.date; if(seen.has(key)) throw Error('Only one map per source and date is supported.'); seen.add(key);
      const data=values(f); let valid=false;
      for(const v of data) {if(Number.isFinite(v)) {if(v < -500 || v > 9000) throw Error('Elevation values are outside the supported metre range.'); valid=true;} else if(!Number.isNaN(v)) throw Error('Invalid infinite elevation.');}
      if(!valid) throw Error('Map contains no valid municipal elevations.');
      if(f.hai_base64!==undefined) {
        if(typeof f.hai_base64!=='string' || atob(f.hai_base64).length!==f.width*f.height*4) throw Error('Invalid quality grid.');
        for(const v of values(f,'hai_base64')) if(!Number.isNaN(v) && (!Number.isFinite(v)||v<0)) throw Error('Invalid height accuracy indication.');
      }
    }
    if(pack.reference) {
      const f=pack.reference;
      if(typeof f.label!=='string' || !f.label.trim() || f.width!==grid.shape[1] || f.height!==grid.shape[0] || JSON.stringify(f.bounds_utm43n)!==JSON.stringify(grid.bounds_utm43n) || typeof f.elevations_base64!=='string' || atob(f.elevations_base64).length!==f.width*f.height*4) throw Error('Invalid EDEM reference grid.');
      for(const v of values(f)) if(!Number.isNaN(v) && (!Number.isFinite(v)||v < -500||v > 9000)) throw Error('Invalid reference elevations.');
    }
    return pack;
  }
  function stop(){clearInterval(timer);timer=null;play.textContent='Play dates';}
  function image(frame, first) {
    const canvas=document.createElement('canvas'); canvas.width=frame.width;canvas.height=frame.height;
    const ctx=canvas.getContext('2d'), pixels=ctx.createImageData(frame.width,frame.height), a=values(frame), b=first&&values(first);
    const palette=window.DEM_MAP_PALETTES[first?'difference':'elevation'];
    for(let i=0;i<a.length;i++) {
      const v=first ? a[i]-b[i] : a[i]; if(!Number.isFinite(v)) continue;
      const pos=Math.max(0,Math.min(255,Math.round((first?(v+20)/40:(v-200)/125)*255)));
      pixels.data.set([...palette[pos],255],i*4);
    }
    ctx.putImageData(pixels,0,0);return canvas.toDataURL('image/png');
  }
  function render() {
    $('datedControls').hidden=mode.value!=='dated';
    $('compositeBaseline').hidden=mode.value==='dated';
    $('qualityNote').hidden=mode.value!=='dated'||source!=='tandemx';
    if(mode.value!=='dated') return;
    frames=maps.frames.filter(f=>f.source===source).sort((a,b)=>a.date.localeCompare(b.date));
    $('datedBaseline').hidden=source!=='tandemx'||!maps.reference;
    document.querySelector('label[for="datedBaseline"]').hidden=$('datedBaseline').hidden;
    slider.max=Math.max(0,frames.length-1); slider.value=Math.min(Number(slider.value),Number(slider.max));
    slider.disabled=frames.length<2;play.disabled=frames.length<2;baselineSelect.disabled=true;
    $('pointData').hidden=true;$('pointIntro').hidden=false;$('pointIntro').textContent='Click the map to inspect the loaded dated elevations.';
    if(!frames.length) {
      layer.hidden=true;differenceLayer.style.display='none';$('differenceEmpty').style.display='grid';
      $('differenceEmpty').textContent='Load dated maps to compare against the earliest date.';
      $('datedDate').textContent='No dated maps';title.textContent=product(source).label; period.textContent='Dated maps unavailable';
      $('elevationMapLabel').textContent='No dated maps loaded';$('differenceMapLabel').textContent='No dated maps';$('differenceFormula').textContent='Dated maps compare with the earliest loaded date.';
      $('datedStatus').textContent=source==='srtm' ? 'SRTM supplies one February 2000 surface. Choose ALOS or Copernicus for dated-map imports.' : 'No genuine dated elevation maps are loaded for this source. The supplied composite is available in Product composite mode.';
      return;
    }
    const f=frames[Number(slider.value)], first=source==='tandemx'&&maps.reference&&$('datedBaseline').value==='reference'?maps.reference:frames[0];layer.hidden=false;layer.src=image(f);
    title.textContent=f.label; period.textContent=f.date;$('elevationMapLabel').textContent=f.date;
    $('datedDate').textContent=f.date;$('datedStatus').textContent=`${Number(slider.value)+1} of ${frames.length} dated maps · ${f.provenance}. Blank pixels have no retained observation for this date.`;
    differenceLayer.src=image(f,first); differenceLayer.style.display='block';$('differenceEmpty').style.display='none';
    const refLabel=first.date||first.label;
    $('differenceMapLabel').textContent=`${f.date} − ${refLabel}`;$('differenceFormula').textContent=`Surface difference: ${f.date} − ${refLabel}. Only overlapping valid pixels are compared; buildings, vegetation and residual errors may affect changes.`;
    if(point) inspect(...point);
  }
  function inspect(x,y,east,north) {
    point=[x,y,east,north]; if(!frames.length) return;
    const index=Math.min(frames[0].height-1,Math.floor(y*frames[0].height))*frames[0].width+Math.min(frames[0].width-1,Math.floor(x*frames[0].width));
    const samples=frames.map(f=>values(f)[index]);$('pointTitle').textContent='Dated elevation at selected point';$('pointIntro').hidden=true;$('pointData').hidden=false;
    $('coordinates').textContent=`${east.toFixed(0)} E, ${north.toFixed(0)} N · UTM Zone 43N`;
    $('values').replaceChildren(...frames.map((f,i)=>{const row=document.createElement('div');row.className='value-row';const label=document.createElement('span'),v=document.createElement('b');label.textContent=f.date;const hai=f.hai_base64&&values(f,'hai_base64')[index];v.textContent=Number.isFinite(samples[i])?samples[i].toFixed(1)+' m'+(Number.isFinite(hai)?` · HAI ${hai.toFixed(1)} m`:''):'No data';row.append(label,v);return row;}));
    const valid=samples.filter(Number.isFinite);if(!valid.length){$('seriesChart').innerHTML='';return;}
    const min=Math.min(...valid)-2,max=Math.max(...valid)+2,start=Date.parse(frames[0].date),end=Date.parse(frames.at(-1).date);
    let chart='';frames.forEach((f,i)=>{if(!Number.isFinite(samples[i]))return;const x=end===start?160:40+(Date.parse(f.date)-start)/(end-start)*240,y=150-(samples[i]-min)/(max-min)*115;chart+=`<circle cx="${x}" cy="${y}" r="5" fill="${i===Number(slider.value)?'#e66b3e':'#197d63'}"/><text x="${x}" y="${y-10}" text-anchor="middle" font-size="10">${samples[i].toFixed(1)} m</text>`;});
    chart+=`<text x="40" y="174" font-size="10">${frames[0].date}</text><text x="280" y="174" text-anchor="end" font-size="10">${frames.at(-1).date}</text>`;$('seriesChart').innerHTML=chart;
  }
  window.DEM_DATED_VIEW={get active(){return mode.value==='dated';},inspect,setSource(key){source=key;point=null;stop();slider.value=0;render();}};
  mode.addEventListener('change',()=>{stop();point=null;slider.value=0;if(mode.value==='composite'){layer.hidden=false;baselineSelect.disabled=false;$('differenceEmpty').textContent='Choose ALOS or Copernicus to compare against a baseline.';$('pointTitle').textContent='Choose a location';$('pointIntro').textContent='Click within the municipal area to compare elevation values through time.';$('pointIntro').hidden=false;$('pointData').hidden=true;selectDem(source);$('datedControls').hidden=true;}else render();});
  slider.addEventListener('input',()=>{stop();render();});
  $('datedBaseline').addEventListener('change',render);
  play.addEventListener('click',()=>{if(timer){stop();return;}if(frames.length<2)return;play.textContent='Pause';timer=setInterval(()=>{slider.value=(Number(slider.value)+1)%frames.length;render();},1500);});
  $('datedImport').addEventListener('change',async e=>{stop();try{const file=e.target.files[0];if(!file)return;if(file.size>150*1024*1024)throw Error('Package exceeds the 150 MB limit.');const next=validate(JSON.parse(await file.text()));maps=next;slider.value=0;point=null;render();}catch(error){$('datedStatus').textContent='Could not load maps: '+error.message;}finally{e.target.value='';}});
  try{maps=validate(maps);}catch(error){maps={frames:[]};$('datedStatus').textContent=error.message;}
})();
