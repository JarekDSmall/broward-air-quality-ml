'use strict';
const station = document.querySelector('#station'), month = document.querySelector('#month');
const fmt = n => n.toFixed(3);
function draw(rows, monthValue) {
  const svg = document.querySelector('#chart');
  const days = new Date(2025, Number(monthValue), 0).getDate();
  const max = Math.max(5, Math.ceil(Math.max(...rows.flatMap(r => [r.observed, r.predicted, r.persistence]), 0) / 5) * 5);
  const min = Math.min(0, Math.floor(Math.min(...rows.flatMap(r => [r.observed, r.predicted, r.persistence]), 0)));
  const x = day => 65 + (day - 1) / (days - 1) * 910;
  const y = value => 280 - (value - min) / (max - min) * 250;
  let content = '';
  for (let i = 0; i <= 5; i++) {
    const value = min + (max - min) * i / 5;
    content += `<line x1="65" x2="975" y1="${y(value)}" y2="${y(value)}" stroke="#dbe5e9"/><text x="52" y="${y(value)+5}" text-anchor="end">${value.toFixed(1)}</text>`;
  }
  for (const day of [1, 7, 14, 21, days]) content += `<text x="${x(day)}" y="310" text-anchor="middle">${day}</text>`;
  for (const [key, color, dash] of [['persistence', '#9d500d', '6 5'], ['predicted', '#087d85', ''], ['observed', '#173747', '']]) {
    let last = -2, path = '';
    for (const r of rows) {
      const day = Number(r.date.slice(8));
      path += `${day === last+1 ? 'L' : 'M'}${x(day)},${y(r[key])} `; last = day;
      content += `<circle cx="${x(day)}" cy="${y(r[key])}" r="2.5" fill="${color}"/>`;
    }
    content += `<path d="${path}" fill="none" stroke="${color}" stroke-width="2.5" stroke-dasharray="${dash}"/>`;
  }
  svg.innerHTML = content;
}
function render() {
  const rows = window.HISTORY.rows.filter(r => r.station === station.value && r.date.slice(5,7) === month.value).sort((a,b) => a.date.localeCompare(b.date));
  document.querySelector('#count').textContent = rows.length;
  for (const [id,key] of [['model-mae','predicted'],['base-mae','persistence']]) document.getElementById(id).textContent = rows.length ? fmt(rows.reduce((sum,r) => sum + Math.abs(r[key]-r.observed),0)/rows.length)+' µg/m³' : '—';
  document.querySelector('#status').textContent = rows.length ? `${window.HISTORY.stations[station.value]} · ${month.selectedOptions[0].text} 2025${station.value === '120110037' ? ' · Previously unseen station' : ''}` : 'No eligible comparisons for this station and month. Choose another month.';
  const body = document.querySelector('#values'); body.replaceChildren();
  for (const row of rows) {
    const tr = document.createElement('tr');
    for (const value of [row.date, fmt(row.observed), fmt(row.predicted), fmt(row.persistence)]) {const td=document.createElement('td');td.textContent=value;tr.append(td);}
    body.append(tr);
  }
  draw(rows, month.value);
}
if (!window.HISTORY) {
  document.querySelector('#status').textContent = 'Historical data is missing. Run the documented demo export command first.';
} else {
  for (const [id,name] of Object.entries(window.HISTORY.stations)) station.add(new Option(name,id));
  for (let i=1;i<=12;i++) month.add(new Option(new Date(2025,i-1,1).toLocaleString('en-US',{month:'long'}),String(i).padStart(2,'0')));
  station.value='120115005';month.value='06';station.addEventListener('change',render);month.addEventListener('change',render);render();
  if (document.modelContext?.registerTool) {
    const lifecycle = new AbortController();
    window.addEventListener('pagehide', () => lifecycle.abort(), {once:true});
    try {
      Promise.resolve(document.modelContext.registerTool({
        name:'select_historical_period', description:'Select a station and month in the historical PM2.5 explorer.',
        inputSchema:{type:'object',properties:{station:{type:'string',enum:Object.keys(window.HISTORY.stations)},month:{type:'string',pattern:'^(0[1-9]|1[0-2])$'}},required:['station','month'],additionalProperties:false},
        annotations:{readOnlyHint:false},
        execute(input) {
          if (!input || !Object.hasOwn(window.HISTORY.stations,input.station) || !/^(0[1-9]|1[0-2])$/.test(input.month)) throw new Error('Choose a valid station and month');
          station.value=input.station;month.value=input.month;render();
          return {status:document.querySelector('#status').textContent,days:Number(document.querySelector('#count').textContent)};
        }
      },{signal:lifecycle.signal})).catch(() => {});
    } catch (_) { /* The visible selectors remain available. */ }
  }
}
