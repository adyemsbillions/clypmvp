const templates=[
{id:1,cat:'Church',name:'Sunday Gathering',style:'Editorial',bg:'#1f2445',fg:'#fff',accent:'#f4c95d',title:'SUNDAY\nGATHERING',sub:'Worship · Word · Community'},
{id:2,cat:'Business',name:'Founder Meetup',style:'Minimal',bg:'#f0ede6',fg:'#191a17',accent:'#ff5d3d',title:'BUILD\nWHAT\nMATTERS',sub:'Founders Meetup · Lagos'},
{id:3,cat:'Events',name:'Night Session',style:'Bold',bg:'#171815',fg:'#fff',accent:'#665cff',title:'NIGHT\nSESSION',sub:'FRIDAY · 8PM'},
{id:4,cat:'Education',name:'Open Day',style:'Swiss',bg:'#dfe7ff',fg:'#20368b',accent:'#20368b',title:'OPEN\nDAY',sub:'Learn. Explore. Decide.'},
{id:5,cat:'Food',name:'Weekend Brunch',style:'Warm',bg:'#f8d7c7',fg:'#6d2d24',accent:'#ff633f',title:'BRUNCH\nTHIS\nWEEKEND',sub:'10AM — 3PM'},
{id:6,cat:'Real Estate',name:'Open House',style:'Premium',bg:'#e9e2d6',fg:'#2f322e',accent:'#79806d',title:'OPEN\nHOUSE',sub:'Ikoyi · Saturday'},
{id:7,cat:'Promotions',name:'Weekend Sale',style:'Retail',bg:'#f4f0ff',fg:'#3430a3',accent:'#ff5c62',title:'WEEKEND\nSALE',sub:'Up to 30% off'},
{id:8,cat:'Social Media',name:'New Drop',style:'Street',bg:'#d9f0cc',fg:'#182016',accent:'#182016',title:'NEW\nDROP',sub:'Available Friday'},
{id:9,cat:'Technology',name:'Product Launch',style:'Digital',bg:'#12141a',fg:'#eff1ff',accent:'#4e5dff',title:'INTRODUCING\nNOVA',sub:'Built for teams'},
{id:10,cat:'Fashion',name:'Lookbook',style:'Editorial',bg:'#f3e8e5',fg:'#331f1e',accent:'#a45d4b',title:'FORM /\nFALL 26',sub:'New collection'},
{id:11,cat:'Beauty',name:'Skin Session',style:'Soft',bg:'#eee7dd',fg:'#50443a',accent:'#b18476',title:'SKIN\nSESSION',sub:'Book your consultation'},
{id:12,cat:'Announcements',name:'Now Hiring',style:'Corporate',bg:'#e9edf1',fg:'#18212c',accent:'#305a7c',title:'WE ARE\nHIRING',sub:'Join our team'}
];
const gallery=document.getElementById('templateGallery'),filters=document.getElementById('templateFilters');
const cats=['All',...new Set(templates.map(t=>t.cat))];
function renderFilters(active='All'){filters.innerHTML=cats.map(c=>`<button class="filter-chip ${c===active?'active':''}" data-cat="${c}">${c}</button>`).join('');filters.querySelectorAll('button').forEach(b=>b.onclick=()=>{renderFilters(b.dataset.cat);renderGallery(b.dataset.cat)})}
function renderGallery(cat='All'){gallery.innerHTML=templates.filter(t=>cat==='All'||t.cat===cat).map(t=>`<article class="template-card"><div class="template-preview" style="background:${t.bg};color:${t.fg}"><div style="width:34px;height:4px;background:${t.accent}"></div><h3>${t.title.replace(/\n/g,'<br>')}</h3><div class="preview-foot"><span>${t.sub}</span><span>CLYP</span></div></div><div class="template-meta"><div><strong>${t.name}</strong><small>${t.cat} · ${t.style}</small></div><button onclick="useTemplate(${t.id})">Use</button></div></article>`).join('')}
window.useTemplate=id=>{localStorage.setItem('clyp:selectedTemplate',String(id));location.href='editor.html?template='+id};renderFilters();renderGallery();