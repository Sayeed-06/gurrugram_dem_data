const order = ["srtm", "alos", "copernicus"];
let meta, current = "srtm", baseline = "srtm", scale = 1, pan = {x:0,y:0}, drag, marker;
const layer = document.querySelector("#demLayer"), viewport = document.querySelector("#mapViewport"), canvas = document.querySelector("#mapCanvas");
const title = document.querySelector("#mapTitle"), period = document.querySelector("#mapPeriod"), slider = document.querySelector("#timeSlider");
const baselineSelect = document.querySelector("#baselineSelect"), differenceLayer = document.querySelector("#differenceLayer");

meta = window.DEM_EXPLORER_METADATA;
let embeddedValues;
function unpackElevations() {
  if (embeddedValues) return embeddedValues;
  const raw = atob(window.DEM_EMBEDDED_ELEVATIONS.data_base64);
  const bytes = new Uint8Array(raw.length);
  for (let i = 0; i < raw.length; i += 1) bytes[i] = raw.charCodeAt(i);
  embeddedValues = new Int16Array(bytes.buffer);
  return embeddedValues;
}
selectDem(current);
function product(key) { return meta.products[key]; }
function selectDem(key) {
  layer.hidden=false;baselineSelect.disabled=false;
  document.querySelector('#pointTitle').textContent='Choose a location';document.querySelector('#pointIntro').hidden=false;
  document.querySelector('#pointIntro').textContent='Click within the municipal area to compare elevation values through time.';
  document.querySelector('#pointData').hidden=true;marker?.remove();marker=null;
  current = key; const p=product(key); layer.src=`static/layers/${key}.png`; title.textContent=p.label; period.textContent=p.period;
  document.querySelector("#periodOutput").textContent=p.period; slider.value=order.indexOf(key);
  document.querySelectorAll(".choice").forEach(b=>b.classList.toggle("active",b.dataset.dem===key));
  if (current === "srtm") baseline = "srtm";
  if (current === "alos" && baseline !== "srtm") baseline = "srtm";
  if (current === "copernicus" && baseline === "copernicus") baseline = "alos";
  updateDifference();
}
document.querySelectorAll(".choice").forEach(b=>b.addEventListener("click",()=>selectDem(b.dataset.dem)));
slider.addEventListener("input",e=>selectDem(order[+e.target.value]));
document.querySelector("#opacitySlider").addEventListener("input",e=>{layer.style.opacity=e.target.value/100; document.querySelector("#opacityOutput").textContent=e.target.value+"%";});
baselineSelect.addEventListener("change", e => { baseline=e.target.value; updateDifference(); });
function updateDifference() {
  const labels = {srtm:"SRTM · 2000", alos:"ALOS · 2006–11", copernicus:"Copernicus · 2011–14"};
  [...baselineSelect.options].forEach(option => option.disabled = option.value === current);
  baselineSelect.value = baseline;
  const formula = document.querySelector("#differenceFormula"), empty = document.querySelector("#differenceEmpty");
  const mapLabel = document.querySelector("#differenceMapLabel"), elevationLabel = document.querySelector("#elevationMapLabel");
  elevationLabel.textContent = `${product(current).label} · ${product(current).period}`;
  if (current === "srtm") {
    differenceLayer.style.display="none"; empty.style.display="grid";
    formula.textContent="Select ALOS or Copernicus to view a difference map.";
    mapLabel.textContent="Choose a later DEM";
    return;
  }
  const key=`${current}_minus_${baseline}`;
  if (!meta.differences[key]) return;
  differenceLayer.src=`static/layers/${key}.png`;
  differenceLayer.style.display="block"; empty.style.display="none";
  formula.textContent=`Map formula: ${labels[current]} − ${labels[baseline]}.`;
  mapLabel.textContent=`${labels[current]} − ${labels[baseline]}`;
}
function refreshTransform(){canvas.style.transform=`translate(calc(-50% + ${pan.x}px), calc(-50% + ${pan.y}px)) scale(${scale})`;}
function zoom(amount){scale=Math.max(.7,Math.min(5,scale*amount));refreshTransform();}
document.querySelector("#zoomIn").onclick=()=>zoom(1.25);document.querySelector("#zoomOut").onclick=()=>zoom(.8);document.querySelector("#resetView").onclick=()=>{scale=1;pan={x:0,y:0};refreshTransform();};
viewport.addEventListener("wheel",e=>{e.preventDefault();zoom(e.deltaY<0?1.12:.89);},{passive:false});
viewport.addEventListener("pointerdown",e=>{drag={x:e.clientX,y:e.clientY,pan:{...pan},moved:false};viewport.setPointerCapture(e.pointerId);});
viewport.addEventListener("pointermove",e=>{if(!drag)return;const dx=e.clientX-drag.x,dy=e.clientY-drag.y;drag.moved ||= Math.hypot(dx,dy)>4;pan={x:drag.pan.x+dx,y:drag.pan.y+dy};refreshTransform();});
viewport.addEventListener("pointerup",e=>{if(!drag)return;const moved=drag.moved;drag=null;if(!moved)inspect(e);});
function mapPosition(e){const r=viewport.getBoundingClientRect();const x=(e.clientX-r.left-r.width/2-pan.x)/(r.width*scale)+.5;const y=(e.clientY-r.top-r.height/2-pan.y)/(r.height*scale)+.5;return {x,y,screenX:e.clientX-r.left,screenY:e.clientY-r.top};}
async function inspect(e){if(!meta)return;const p=mapPosition(e);if(p.x<0||p.x>1||p.y<0||p.y>1)return;const [left,bottom,right,top]=product(current).bounds_utm43n;const east=left+p.x*(right-left),north=top-p.y*(top-bottom);let d;
  if(['localhost','127.0.0.1','[::1]'].includes(location.hostname)) {
    try { const res=await fetch(`/api/elevation?easting=${east}&northing=${north}`); if(res.ok) d=await res.json(); } catch (_) { /* fall back to the bundled lookup */ }
  }
  if (!d) d=embeddedSample(p.x,p.y,east,north);
  if(!Object.values(order).some(k=>d[k]!==null))return;drawMarker(p.screenX,p.screenY);renderInspector(d);}
function embeddedSample(x,y,easting,northing) {
  const lookup=window.DEM_EMBEDDED_ELEVATIONS, values=unpackElevations();
  const col=Math.min(lookup.width-1,Math.max(0,Math.floor(x*lookup.width)));
  const row=Math.min(lookup.height-1,Math.max(0,Math.floor(y*lookup.height)));
  const index=row*lookup.width+col, cells=lookup.width*lookup.height;
  const result={easting_m:easting,northing_m:northing,longitude:null,latitude:null};
  lookup.band_order.forEach((key,band)=>{const value=values[band*cells+index];result[key]=value===lookup.nodata_decimetres?null:value/10;});
  return result;
}
function drawMarker(x,y){marker?.remove();marker=document.createElement("i");marker.className="marker";marker.style.left=x+"px";marker.style.top=y+"px";viewport.append(marker);}
function renderInspector(d){document.querySelector("#pointTitle").textContent="Elevation at selected point";document.querySelector("#pointIntro").hidden=true;document.querySelector("#pointData").hidden=false;document.querySelector("#coordinates").textContent=d.latitude===null?`${d.easting_m.toFixed(0)} E, ${d.northing_m.toFixed(0)} N · UTM Zone 43N`:`${d.latitude.toFixed(5)}° N, ${d.longitude.toFixed(5)}° E  ·  ${d.easting_m.toFixed(0)} E, ${d.northing_m.toFixed(0)} N`;
 const labels={srtm:"SRTM · 2000",alos:"ALOS · 2006–11",copernicus:"Copernicus · 2011–14"};document.querySelector("#values").innerHTML=order.map(k=>`<div class="value-row"><span>${labels[k]}</span><b>${d[k]===null?"No data":d[k].toFixed(1)+" m"}</b></div>`).join("");drawChart(d,labels);}
function drawChart(d,labels){const svg=document.querySelector("#seriesChart"),v=order.map(k=>d[k]).filter(v=>v!==null);const min=Math.floor((Math.min(...v)-4)/5)*5,max=Math.ceil((Math.max(...v)+4)/5)*5;const xs=[44,160,276],sy=x=>155-(x-min)/(max-min)*118;let out=`<line x1="44" y1="155" x2="292" y2="155" stroke="#bdc9c3"/><line x1="44" y1="32" x2="44" y2="155" stroke="#bdc9c3"/><text x="7" y="36" fill="#63736d" font-size="10">${max} m</text><text x="7" y="157" fill="#63736d" font-size="10">${min} m</text>`;let pts=[];order.forEach((k,i)=>{if(d[k]!==null){const y=sy(d[k]);pts.push(`${xs[i]},${y}`);out+=`<circle cx="${xs[i]}" cy="${y}" r="5" fill="#197d63"/><text x="${xs[i]}" y="174" text-anchor="middle" fill="#52655c" font-size="10">${labels[k].split(" · ")[1]}</text><text x="${xs[i]}" y="${y-10}" text-anchor="middle" fill="#13251f" font-size="10" font-weight="700">${d[k].toFixed(1)}</text>`;}});out+=`<polyline points="${pts.join(" ")}" fill="none" stroke="#197d63" stroke-width="2"/>`;svg.innerHTML=out;}
