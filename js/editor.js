(() => {
  'use strict';

  const $ = id => document.getElementById(id);
  const requiredIds = [
    'designCanvas','canvasStage','layerList','properties','propertyEmpty','toast','projectName','saveStatus',
    'editorLeft','editorRight','leftPanel','localImageInput','mobilePropsBtn','closePropsBtn','aiCommand','aiSend'
  ];
  const missing = requiredIds.filter(id => !$(id));
  if (missing.length) {
    document.body.innerHTML = `<main style="max-width:720px;margin:8vh auto;padding:28px;font-family:Inter,system-ui;background:#fff;border:1px solid #ddd;border-radius:18px"><h1>Clyp editor could not start</h1><p>The build is missing required editor controls: <b>${missing.join(', ')}</b>.</p><p>Use the complete V5.1 project so editor.html and editor.js stay in sync.</p></main>`;
    throw new Error(`Clyp editor DOM mismatch: ${missing.join(', ')}`);
  }

  const canvas = $('designCanvas');
  const canvasStage = $('canvasStage');
  const layerList = $('layerList');
  const props = $('properties');
  const empty = $('propertyEmpty');
  const toast = $('toast');
  const projectName = $('projectName');
  const saveStatus = $('saveStatus');
  const panel = $('leftPanel');
  const qs = new URLSearchParams(location.search);

  let selected = null;
  let history = [];
  let future = [];
  let saveTimer = null;
  let viewScale = 1;
  let interaction = null;
  let raf = 0;
  let currentPanel = 'templates';

  // ---------------------------------------------------------------------------
  // Font catalogue — Google fonts are loaded on demand instead of downloading a
  // huge pack at page load. This keeps mobile and slower PCs responsive.
  // ---------------------------------------------------------------------------
  const FONT_CATALOG = {
    'Display': ['Bebas Neue','Anton','Archivo Black','Barlow Condensed','League Spartan','Oswald','Teko','Big Shoulders Display','Alfa Slab One','Bungee','Abril Fatface','Fjalla One','Staatliches','Black Ops One','Russo One','Archivo Narrow','IBM Plex Sans Condensed','Saira Condensed'],
    'Expressive / tech': ['Unbounded','Righteous','Orbitron','Chakra Petch','Syncopate'],
    'Modern sans': ['Inter','Manrope','Plus Jakarta Sans','DM Sans','Poppins','Montserrat','Work Sans','Source Sans 3','Space Grotesk','Sora','Outfit','Urbanist','Raleway','Figtree','Nunito Sans','Lato','Roboto Condensed','Mulish','Rubik','Karla','Public Sans','IBM Plex Sans','Assistant','Barlow','Archivo','Cabin','Lexend','Noto Sans'],
    'Editorial': ['Playfair Display','DM Serif Display','Cormorant Garamond','Libre Baskerville','Merriweather','Bodoni Moda','Cinzel','Lora','EB Garamond','Spectral','Crimson Pro','Prata','Italiana','Marcellus','Cormorant','Cardo','Source Serif 4'],
    'System': ['Impact','Arial Black','Arial Narrow','Arial','Georgia','Times New Roman','Trebuchet MS','Verdana','system-ui']
  };
  const GOOGLE_FONTS = new Set(Object.entries(FONT_CATALOG).filter(([group])=>group!=='System').flatMap(([,fonts])=>fonts));
  const loadedFonts = new Set(['Inter','Manrope']);

  function ensureFontLoaded(font) {
    if (!font || !GOOGLE_FONTS.has(font) || loadedFonts.has(font)) return;
    loadedFonts.add(font);
    const link = document.createElement('link');
    link.rel = 'stylesheet';
    link.dataset.clypFont = font;
    link.href = `https://fonts.googleapis.com/css2?family=${font.trim().replace(/\s+/g,'+')}&display=swap`;
    document.head.appendChild(link);
  }

  function buildFontSelect() {
    const sel = $('propFont');
    sel.innerHTML = '';
    Object.entries(FONT_CATALOG).forEach(([group, fonts]) => {
      const optgroup = document.createElement('optgroup');
      optgroup.label = group;
      fonts.forEach(font => {
        const option = document.createElement('option');
        option.value = option.textContent = font;
        optgroup.appendChild(option);
      });
      sel.appendChild(optgroup);
    });
  }
  buildFontSelect();

  // ---------------------------------------------------------------------------
  // Editable vector icon library. These are simple SVG primitives, not images.
  // ---------------------------------------------------------------------------
  const ICONS = {
    'calendar': '<rect x="3" y="5" width="18" height="16" rx="2"/><path d="M16 3v4M8 3v4M3 10h18"/>',
    'clock': '<circle cx="12" cy="12" r="9"/><path d="M12 7v5l3 2"/>',
    'map-pin': '<path d="M20 10c0 5-8 11-8 11S4 15 4 10a8 8 0 1 1 16 0Z"/><circle cx="12" cy="10" r="2.5"/>',
    'phone': '<path d="M6.5 3h3l1.4 4-2 1.8a16 16 0 0 0 6.3 6.3l1.8-2 4 1.4v3c0 1.4-1.1 2.5-2.5 2.5C10.5 20 4 13.5 4 5.5 4 4.1 5.1 3 6.5 3Z"/>',
    'mail': '<rect x="3" y="5" width="18" height="14" rx="2"/><path d="m4 7 8 6 8-6"/>',
    'globe': '<circle cx="12" cy="12" r="9"/><path d="M3 12h18M12 3a15 15 0 0 1 0 18M12 3a15 15 0 0 0 0 18"/>',
    'link': '<path d="M10 13a5 5 0 0 0 7.1.1l2-2a5 5 0 0 0-7.1-7.1l-1.2 1.2M14 11a5 5 0 0 0-7.1-.1l-2 2A5 5 0 0 0 12 20l1.2-1.2"/>',
    'user': '<circle cx="12" cy="8" r="4"/><path d="M4 21a8 8 0 0 1 16 0"/>',
    'users': '<circle cx="9" cy="8" r="3.5"/><path d="M2.5 20a6.5 6.5 0 0 1 13 0M16 6.5a3 3 0 0 1 0 5.8M18 20a5.5 5.5 0 0 0-3.2-5"/>',
    'mic': '<rect x="9" y="3" width="6" height="11" rx="3"/><path d="M5.5 11a6.5 6.5 0 0 0 13 0M12 17.5V22M8.5 22h7"/>',
    'music': '<path d="M9 18V6l10-2v12M9 8l10-2"/><circle cx="6.5" cy="18" r="2.5"/><circle cx="16.5" cy="16" r="2.5"/>',
    'camera': '<path d="M4 7h4l1.5-2h5L16 7h4a2 2 0 0 1 2 2v9a2 2 0 0 1-2 2H4a2 2 0 0 1-2-2V9a2 2 0 0 1 2-2Z"/><circle cx="12" cy="13" r="4"/>',
    'shopping-bag': '<path d="M5 8h14l1 13H4L5 8Z"/><path d="M9 10V7a3 3 0 0 1 6 0v3"/>',
    'tag': '<path d="M3 12V4h8l10 10-7 7L3 12Z"/><circle cx="8" cy="8" r="1.4"/>',
    'home': '<path d="m3 11 9-8 9 8"/><path d="M5 10v11h14V10M9 21v-6h6v6"/>',
    'building': '<rect x="4" y="3" width="11" height="18"/><path d="M8 7h3M8 11h3M8 15h3M15 9h5v12h-5M18 13h.1M18 17h.1"/>',
    'briefcase': '<rect x="3" y="7" width="18" height="13" rx="2"/><path d="M9 7V4h6v3M3 12h18M10 12v2h4v-2"/>',
    'graduation-cap': '<path d="m2 9 10-5 10 5-10 5L2 9Z"/><path d="M6 11v5c3 2 9 2 12 0v-5M22 9v6"/>',
    'book': '<path d="M3 5a4 4 0 0 1 4-2h5v17H7a4 4 0 0 0-4 2V5ZM21 5a4 4 0 0 0-4-2h-5v17h5a4 4 0 0 1 4 2V5Z"/>',
    'trophy': '<path d="M8 4h8v5a4 4 0 0 1-8 0V4Z"/><path d="M8 6H4v2a4 4 0 0 0 4 4M16 6h4v2a4 4 0 0 1-4 4M12 13v5M8 21h8M10 18h4"/>',
    'football': '<circle cx="12" cy="12" r="9"/><path d="m12 8 3 2-1 3h-4l-1-3 3-2ZM9 10 6 8M15 10l3-2M10 13l-1 4M14 13l1 4M9 17l-3 1M15 17l3 1"/>',
    'utensils': '<path d="M7 3v7M4 3v5a3 3 0 0 0 6 0V3M7 11v10M15 3v18M15 3c4 2 4 8 0 10"/>',
    'leaf': '<path d="M20 4C11 4 5 9 5 16c0 2 1 4 3 5 7-1 12-7 12-17Z"/><path d="M5 20c3-5 7-8 12-11"/>',
    'bolt': '<path d="m13 2-8 12h7l-1 8 8-12h-7l1-8Z"/>',
    'shield': '<path d="M12 3 4 6v6c0 5 3.5 8 8 10 4.5-2 8-5 8-10V6l-8-3Z"/><path d="m9 12 2 2 4-5"/>',
    'lock': '<rect x="5" y="10" width="14" height="11" rx="2"/><path d="M8 10V7a4 4 0 0 1 8 0v3M12 14v3"/>',
    'ticket': '<path d="M3 7h18v4a2 2 0 0 0 0 4v4H3v-4a2 2 0 0 0 0-4V7Z"/><path d="M12 7v12" stroke-dasharray="2 2"/>',
    'megaphone': '<path d="m3 11 13-5v12L3 13v-2Z"/><path d="M7 14l2 6h4l-2-5M18 9c2 1 2 5 0 6"/>',
    'gift': '<rect x="3" y="9" width="18" height="12"/><path d="M12 9v12M3 13h18M12 9H7a3 3 0 1 1 3-3c0 2 2 3 2 3Zm0 0h5a3 3 0 1 0-3-3c0 2-2 3-2 3Z"/>',
    'play': '<circle cx="12" cy="12" r="9"/><path d="m10 8 6 4-6 4Z" fill="currentColor" stroke="none"/>',
    'instagram': '<rect x="3" y="3" width="18" height="18" rx="5"/><circle cx="12" cy="12" r="4"/><circle cx="17.5" cy="6.5" r=".7" fill="currentColor" stroke="none"/>',
    'facebook': '<path d="M14 8h4V4h-4c-3 0-5 2-5 5v3H6v4h3v6h4v-6h4l1-4h-5V9c0-.6.4-1 1-1Z"/>',
    'youtube': '<rect x="2.5" y="6" width="19" height="12" rx="4"/><path d="m10 9 5 3-5 3Z" fill="currentColor" stroke="none"/>',
    'linkedin': '<rect x="3" y="3" width="18" height="18" rx="2"/><path d="M8 10v7M8 7v.1M12 17v-7M12 13a4 4 0 0 1 7 2.5V17"/>',
    'whatsapp': '<circle cx="12" cy="12" r="9"/><path d="m5 20 1-4a8 8 0 0 1-1-4M9 8c1 4 3 6 7 7"/>',
    'x-social': '<path d="M5 4 19 20M19 4 5 20"/>',
    'check': '<path d="m5 12 4 4L19 6"/>',
    'arrow-right': '<path d="M4 12h15M14 7l5 5-5 5"/>',
    'star': '<path d="m12 3 2.7 5.5 6.1.9-4.4 4.3 1 6.1-5.4-2.9-5.4 2.9 1-6.1-4.4-4.3 6.1-.9Z"/>',
    'heart': '<path d="M20.8 5.6c-2.2-2.2-5.8-2.2-8 0L12 6.4l-.8-.8a5.7 5.7 0 0 0-8 8L12 22l8.8-8.4a5.7 5.7 0 0 0 0-8Z"/>',
    'cross': '<path d="M10 2h4v7h7v4h-7v9h-4v-9H3V9h7Z"/>',
    'spark': '<path d="M12 2c.7 5.3 2.7 7.3 8 8-5.3.7-7.3 2.7-8 8-.7-5.3-2.7-7.3-8-8 5.3-.7 7.3-2.7 8-8Z"/><path d="M19 15c.3 2.1 1.1 2.9 3 3.2-1.9.3-2.7 1.1-3 3.2-.3-2.1-1.1-2.9-3-3.2 1.9-.3 2.7-1.1 3-3.2Z"/>',
  };  function iconSvg(name) {
    const body = ICONS[name] || ICONS.star;
    return `<svg viewBox="0 0 24 24" aria-hidden="true" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round">${body}</svg>`;
  }
  function buildIconSelect() {
    const sel = $('propIcon');
    sel.innerHTML = Object.keys(ICONS).map(name => `<option value="${name}">${name.replace(/-/g,' ')}</option>`).join('');
  }
  buildIconSelect();

  const SHAPE_KINDS = [
    ['rect','Rectangle'],['rounded','Rounded card'],['ellipse','Circle / ellipse'],['pill','Pill'],['line','Line'],['dashed-line','Dashed line'],
    ['triangle','Triangle'],['diamond','Diamond'],['pentagon','Pentagon'],['hexagon','Hexagon'],['octagon','Octagon'],['star','Star'],['burst','Burst'],['arrow','Arrow'],['chevron','Chevron'],['ribbon','Ribbon'],['semicircle','Semicircle'],['parallelogram','Parallelogram'],['trapezoid','Trapezoid'],
    ['pattern-dots','Dot pattern'],['pattern-lines','Stripe pattern'],['pattern-grid','Grid pattern'],['pattern-checker','Checker pattern'],['pattern-cross','Crosshatch']
  ];
  $('propKind').innerHTML = SHAPE_KINDS.map(([value,label]) => `<option value="${value}">${label}</option>`).join('');

  // ---------------------------------------------------------------------------
  // Palettes — deliberately restrained, category-aware starting systems.
  // ---------------------------------------------------------------------------
  const PALETTES = [
    {name:'Worship Ember',strategy:'analogous',dominant:'#210705',support:'#6D1B12',accent:'#F0B429',light:'#FFF4E6',dark:'#120302'},
    {name:'Midnight Gold',strategy:'complementary',dominant:'#101828',support:'#1D2939',accent:'#F4C95D',light:'#F8FAFC',dark:'#070B12'},
    {name:'Corporate Blue',strategy:'monochromatic',dominant:'#0B1F3A',support:'#EAF0F7',accent:'#2F6BFF',light:'#FFFFFF',dark:'#08111F'},
    {name:'Tech Electric',strategy:'analogous',dominant:'#0B1020',support:'#18223D',accent:'#6C7CFF',light:'#F4F6FF',dark:'#050811'},
    {name:'Beauty Rose',strategy:'analogous',dominant:'#F6ECE8',support:'#D7B7AD',accent:'#A7575B',light:'#FFFBF9',dark:'#352221'},
    {name:'Luxury Olive',strategy:'complementary',dominant:'#172018',support:'#DAD3BF',accent:'#C6A15B',light:'#FBF7EE',dark:'#0B0E0B'},
    {name:'Food Heat',strategy:'analogous',dominant:'#2A0E08',support:'#A73E18',accent:'#F4B942',light:'#FFF4E3',dark:'#160603'},
    {name:'Real Estate',strategy:'complementary',dominant:'#10231D',support:'#D9E2DC',accent:'#B9975B',light:'#FAFBF8',dark:'#07110E'},
    {name:'Fashion Mono',strategy:'monochromatic',dominant:'#111111',support:'#E8E5E0',accent:'#D84A4A',light:'#FAF9F6',dark:'#050505'},
    {name:'Event Violet',strategy:'split-complementary',dominant:'#151021',support:'#33275A',accent:'#FFB84D',light:'#F6F1FF',dark:'#09060E'}
  ];

  const templateMeta = {
    1:['Sunday Gathering','#1f2445','#ffffff','#f4c95d','THE GATHERING 2026','YOUTH\nCONFERENCE','24 AUG · 4:00 PM · LAGOS'],
    2:['Founder Meetup','#f0ede6','#171815','#ff5d3d','FOUNDERS MEETUP','BUILD\nWHAT\nMATTERS.','SATURDAY · 10AM · LAGOS'],
    3:['Night Session','#171815','#ffffff','#665cff','FRIDAY NIGHT','NIGHT\nSESSION','FRIDAY · 8PM'],
    4:['Open Day','#dfe7ff','#20368b','#20368b','DISCOVER YOUR NEXT STEP','OPEN\nDAY','LEARN · EXPLORE · DECIDE'],
    5:['Weekend Brunch','#f8d7c7','#6d2d24','#ff633f','SATURDAY + SUNDAY','BRUNCH\nTHIS\nWEEKEND','10AM — 3PM'],
    6:['Open House','#e9e2d6','#2f322e','#79806d','A SPACE TO COME HOME TO','OPEN\nHOUSE','IKOYI · SATURDAY'],
    7:['Weekend Sale','#f4f0ff','#3430a3','#ff5c62','CRAVII','WEEKEND\nSALE','UP TO 30% OFF'],
    8:['New Drop','#d9f0cc','#182016','#182016','LIMITED RELEASE','NEW\nDROP','AVAILABLE FRIDAY'],
    9:['Product Launch','#12141a','#eff1ff','#4e5dff','MEET THE NEW','INTRODUCING\nNOVA','BUILT FOR TEAMS'],
    10:['Lookbook','#f3e8e5','#331f1e','#a45d4b','NEW COLLECTION','FORM /\nFALL 26','THE NEW SILHOUETTE'],
    11:['Skin Session','#eee7dd','#50443a','#b18476','PERSONAL CONSULTATION','SKIN\nSESSION','BOOK YOUR SESSION'],
    12:['Now Hiring','#e9edf1','#18212c','#305a7c','COME BUILD WITH US','WE ARE\nHIRING','JOIN OUR TEAM']
  };

  function templateDesign(id=1) {
    const t = templateMeta[id] || templateMeta[1];
    return {
      id:null,name:t[0],format:'1080 × 1350',
      canvas:{width:432,height:540,bg:t[1]},assets:{},
      palette:{strategy:'complementary',dominant:t[1],support:'#EEF0EA',accent:t[3],light:t[2],dark:'#111111'},
      layers:[
        {type:'shape',name:'Atmosphere',kind:'ellipse',fill:'radial',x:210,y:-90,w:330,h:330,color:t[3],color2:t[1],opacity:.28,shadow_color:t[3],shadow_opacity:.22,shadow_blur:70},
        {type:'shape',name:'Accent rail',kind:'rect',fill:'solid',x:356,y:0,w:76,h:540,color:t[3],opacity:.95},
        {type:'shape',name:'Outer frame',kind:'rect',fill:'solid',x:22,y:22,w:388,h:496,color:t[2],opacity:.01,stroke_color:t[2],stroke_width:1},
        {type:'shape',name:'Kicker bar',kind:'rect',fill:'solid',x:40,y:42,w:34,h:4,color:t[3]},
        {type:'text',name:'Kicker',x:40,y:56,w:280,h:28,text:t[4],size:11,weight:750,color:t[2],spacing:1.6,font:'Inter',line:1.05},
        {type:'text',name:'Headline',x:40,y:145,w:320,h:190,text:t[5],size:50,weight:800,color:t[2],spacing:-.5,line:.88,font:'League Spartan'},
        {type:'shape',name:'Headline rule',kind:'line',fill:'solid',x:40,y:355,w:80,h:4,color:t[3]},
        {type:'text',name:'Details',x:40,y:380,w:300,h:42,text:t[6],size:11,weight:700,color:t[2],spacing:.5,font:'Inter',line:1.2},
        {type:'icon',name:'Time icon',icon:'clock',x:40,y:449,w:18,h:18,color:t[3],opacity:1},
        {type:'text',name:'CTA',x:68,y:450,w:230,h:22,text:'SHOW UP. MAKE IT COUNT.',size:10,weight:700,color:t[2],spacing:.4,font:'Inter',line:1.05},
        {type:'shape',name:'Footer line',kind:'line',fill:'solid',x:40,y:490,w:270,h:1,color:t[2],opacity:.28},
        {type:'shape',name:'Corner accent',kind:'triangle',fill:'solid',x:320,y:445,w:90,h:73,color:t[3],opacity:.34,rotation:0}
      ]
    };
  }
  function defaultDesign(){ return templateDesign(1); }
  let design = defaultDesign();

  function clone(v){ return JSON.parse(JSON.stringify(v)); }
  function escapeHtml(s){ return String(s ?? '').replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c])); }
  function localAssetUrl(src){
    const value=String(src||'').trim();
    if(!/^https?:\/\//i.test(value)) return value;
    return '/api/assets/fetch?url='+encodeURIComponent(value);
  }
  function adaptDesign(d){
    if(!d || typeof d !== 'object') return defaultDesign();
    const layers=Array.isArray(d.layers)?d.layers.filter(Boolean).map(layer=>{
      if(!layer || layer.type!=='image' || !layer.src) return layer;
      const copy={...layer};
      // Online assets are served back through Clyp's same-origin image proxy. This
      // makes editor rendering reliable and keeps PNG export from being tainted by
      // third-party CORS policies. Data URLs/local uploads remain untouched.
      copy.src=localAssetUrl(copy.src);
      return copy;
    }):[];
    return {
      id:d.id ?? null,name:d.name || 'Untitled design',format:d.format || '1080 × 1350',created_at:d.created_at,updated_at:d.updated_at,
      source:d.source || null,assets:(d.assets && typeof d.assets === 'object') ? d.assets : {},palette:(d.palette && typeof d.palette === 'object') ? d.palette : {},quality:(d.quality && typeof d.quality === 'object') ? d.quality : {},
      canvas:{width:Number(d.canvas?.width)||432,height:Number(d.canvas?.height)||540,bg:d.canvas?.bg||'#1f2445'},layers
    };
  }
  async function api(url,options={}){
    const res = await fetch(url,options);
    const data = await res.json().catch(()=>({ok:false,message:'Invalid server response'}));
    if(!res.ok || !data.ok) throw Object.assign(new Error(data.message||'Request failed'),{data,status:res.status});
    return data;
  }

  function load() {
    let loaded = false;
    const id = qs.get('id');
    if(id){
      const saved = ClypStore.get(id);
      if(saved){ design = adaptDesign(saved); loaded = true; }
    }
    if(!loaded){
      const generated = sessionStorage.getItem('clyp:generatedDesign');
      if((qs.get('mode')==='ai'||qs.get('mode')==='reconstruct') && generated){
        try{
          const parsed = JSON.parse(generated);
          design = adaptDesign(parsed);
          loaded = true;
          sessionStorage.removeItem('clyp:generatedDesign');
        }catch(err){ console.warn('Could not parse generated design',err); }
      }
    }
    if(!loaded){
      const tid = Number(qs.get('template') || localStorage.getItem('clyp:selectedTemplate'));
      if(tid){ design = templateDesign(tid); loaded = true; }
    }
    if(!Array.isArray(design.layers) || design.layers.length === 0){
      design = defaultDesign();
      queueMicrotask(()=>showToast('Clyp recovered an empty project with a starter composition. Your canvas will never open blank.',6500));
    }
    projectName.value = design.name;
    renderCanvas(); renderLayers(); renderProps(); fitCanvasToStage();
    updateSaveStatus(design.id ? 'Saved locally' : 'Not saved yet');
    try{
      const meta = JSON.parse(sessionStorage.getItem('clyp:generationMeta')||'null');
      if(meta){
        sessionStorage.removeItem('clyp:generationMeta');
        if(meta.warnings?.length) showToast(meta.warnings.join(' · '),6500);
      }
    }catch{}
  }

  // ---------------------------------------------------------------------------
  // Rendering
  // ---------------------------------------------------------------------------
  function baseRotation(l){ return `rotate(${Number(l.rotation)||0}deg)`; }
  function imageSource(l){ return l.src || design.assets?.[l.asset||'source_upload'] || ''; }
  function rgba(hex,opacity=1){
    const m=String(hex||'#000000').match(/^#([0-9a-f]{6})$/i);
    if(!m) return `rgba(0,0,0,${opacity})`;
    const n=parseInt(m[1],16);
    return `rgba(${(n>>16)&255},${(n>>8)&255},${n&255},${Math.max(0,Math.min(1,Number(opacity)||0))})`;
  }
  function layerShadow(l){
    const o=Number(l.shadow_opacity)||0;
    if(o<=0) return 'none';
    return `${Number(l.shadow_x)||0}px ${Number(l.shadow_y)||0}px ${Math.max(0,Number(l.shadow_blur)||0)}px ${rgba(l.shadow_color||'#000000',o)}`;
  }
  function shapeFill(l){
    const c=l.color||'#4e5dff', c2=l.color2||c;
    if(l.kind==='pattern-dots') return `radial-gradient(circle, ${c} 1.4px, transparent 1.6px)`;
    if(l.kind==='pattern-lines') return `repeating-linear-gradient(${Number(l.gradient_angle)||135}deg, ${c} 0 2px, transparent 2px 10px)`;
    if(l.kind==='pattern-grid') return `linear-gradient(${rgba(c,.35)} 1px,transparent 1px),linear-gradient(90deg,${rgba(c,.35)} 1px,transparent 1px)`;
    if(l.kind==='pattern-checker') return `conic-gradient(${c} 25%, transparent 0 50%, ${c} 0 75%, transparent 0)`;
    if(l.kind==='pattern-cross') return `repeating-linear-gradient(45deg,${rgba(c,.6)} 0 1px,transparent 1px 9px),repeating-linear-gradient(-45deg,${rgba(c,.4)} 0 1px,transparent 1px 9px)`;
    if(l.fill==='linear') return `linear-gradient(${Number(l.gradient_angle)||135}deg, ${c}, ${c2})`;
    if(l.fill==='radial') return `radial-gradient(circle at 50% 50%, ${c} 0%, ${c2} 72%, ${rgba(c2,0)} 100%)`;
    return c;
  }
  function maskCss(mask){
    return ({
      'fade-bottom':'linear-gradient(to bottom,#000 0%,#000 66%,transparent 100%)',
      'fade-left':'linear-gradient(to right,transparent 0%,#000 28%,#000 100%)',
      'fade-right':'linear-gradient(to left,transparent 0%,#000 28%,#000 100%)',
      'soft-ellipse':'radial-gradient(ellipse at center,#000 48%,rgba(0,0,0,.88) 66%,transparent 100%)'
    })[mask] || 'none';
  }
  function clipForKind(kind){
    return ({
      triangle:'polygon(50% 0,100% 100%,0 100%)',
      diamond:'polygon(50% 0,100% 50%,50% 100%,0 50%)',
      pentagon:'polygon(50% 0,100% 38%,82% 100%,18% 100%,0 38%)',
      hexagon:'polygon(25% 0,75% 0,100% 50%,75% 100%,25% 100%,0 50%)',
      octagon:'polygon(30% 0,70% 0,100% 30%,100% 70%,70% 100%,30% 100%,0 70%,0 30%)',
      star:'polygon(50% 0,61% 35%,98% 35%,68% 57%,79% 100%,50% 72%,21% 100%,32% 57%,2% 35%,39% 35%)',
      burst:'polygon(50% 0,60% 30%,82% 8%,78% 37%,100% 32%,82% 52%,100% 67%,72% 66%,80% 96%,57% 76%,50% 100%,43% 76%,20% 96%,28% 66%,0 67%,18% 52%,0 32%,22% 37%,18% 8%,40% 30%)',
      arrow:'polygon(0 32%,66% 32%,66% 0,100% 50%,66% 100%,66% 68%,0 68%)',
      chevron:'polygon(0 0,70% 0,100% 50%,70% 100%,0 100%,30% 50%)',
      ribbon:'polygon(0 0,100% 0,86% 50%,100% 100%,0 100%,14% 50%)',
      semicircle:'ellipse(50% 100% at 50% 100%)',
      parallelogram:'polygon(20% 0,100% 0,80% 100%,0 100%)',
      trapezoid:'polygon(18% 0,82% 0,100% 100%,0 100%)'
    })[kind] || 'none';
  }
  function applyImageCrop(el,l,w=Number(l.w)||80,h=Number(l.h)||40){
    const src=imageSource(l);
    el.style.backgroundImage=src?`url(${JSON.stringify(src)})`:'none';
    el.style.backgroundRepeat='no-repeat';
    el.style.backgroundColor='#ddd';
    const c=Array.isArray(l.crop)&&l.crop.length===4?l.crop.map(Number):null;
    if(c){
      const left=Math.max(0,Math.min(1000,c[0]))/1000,top=Math.max(0,Math.min(1000,c[1]))/1000,right=Math.max(left+.001,Math.min(1000,c[2])/1000),bottom=Math.max(top+.001,Math.min(1000,c[3])/1000),cw=right-left,ch=bottom-top,bgW=w/cw,bgH=h/ch;
      el.style.backgroundSize=`${bgW}px ${bgH}px`;el.style.backgroundPosition=`${-left*bgW}px ${-top*bgH}px`;
    } else {
      el.style.backgroundSize=l.fit==='contain'?'contain':'cover';
      el.style.backgroundPosition=`${Number.isFinite(+l.focal_x)?l.focal_x:50}% ${Number.isFinite(+l.focal_y)?l.focal_y:50}%`;
    }
  }
  function layerElement(l,i){
    const el=document.createElement('div');
    el.className='canvas-element '+l.type+(l.kind?' kind-'+l.kind:'');
    el.dataset.index=i;el.style.zIndex=String(i+1);
    if(l.type==='text') { ensureFontLoaded(l.font); el.textContent=l.text||''; }
    if(l.type==='icon') el.innerHTML=iconSvg(l.icon||'star');
    if(l.type==='image'){ el.setAttribute('role','img');el.setAttribute('aria-label',l.name||'Image'); if(l.placeholder){el.classList.add('image-placeholder');el.innerHTML='<span><b>ADD HERO IMAGE</b><small>Images → Upload or Online</small></span>';} }
    applyLayerStyle(el,l);
    return el;
  }
  function applyLayerStyle(el,l){
    Object.assign(el.style,{
      left:(l.x||0)+'px',top:(l.y||0)+'px',width:(l.w||80)+'px',height:(l.h||40)+'px',opacity:l.opacity??1,
      transform:baseRotation(l),transformOrigin:'center center',clipPath:'none',border:'0',boxShadow:'none',textShadow:'none',webkitTextStroke:'0 transparent',filter:'none',mixBlendMode:'normal',maskImage:'none',webkitMaskImage:'none',backgroundImage:'none',backgroundSize:'auto',color:l.color||'#111111'
    });
    if(l.type==='text'){
      ensureFontLoaded(l.font);
      Object.assign(el.style,{fontSize:(l.size||16)+'px',fontWeight:l.weight||500,color:l.color||'#111',lineHeight:l.line||1.05,letterSpacing:(l.spacing||0)+'px',fontFamily:`"${l.font||'Inter'}", Inter, system-ui, sans-serif`,textAlign:l.align||'left',textShadow:layerShadow(l),webkitTextStroke:`${Number(l.text_stroke_width)||0}px ${l.text_stroke_color||'#000000'}`});
    } else if(l.type==='shape'){
      const kind=l.kind||'rect';let radius=l.radius||'0';
      if(kind==='rounded') radius=radius==='0'?'18px':radius;
      if(kind==='ellipse') radius='50%';
      if(kind==='pill'||kind==='line'||kind==='dashed-line') radius='999px';
      Object.assign(el.style,{background:shapeFill(l),borderRadius:radius,boxShadow:layerShadow(l),border:`${Math.max(0,Number(l.stroke_width)||0)}px ${kind==='dashed-line'?'dashed':'solid'} ${l.stroke_color||'transparent'}`,clipPath:clipForKind(kind)});
      if(kind==='pattern-dots') el.style.backgroundSize='12px 12px';
      if(kind==='pattern-grid') el.style.backgroundSize='16px 16px';
      if(kind==='pattern-checker') el.style.backgroundSize='20px 20px';
      if(kind==='pattern-cross') el.style.backgroundSize='18px 18px';
    } else if(l.type==='icon'){
      Object.assign(el.style,{color:l.color||'#111111',display:'grid',placeItems:'center',filter:`drop-shadow(${Number(l.shadow_x)||0}px ${Number(l.shadow_y)||0}px ${Math.max(0,Number(l.shadow_blur)||0)}px ${rgba(l.shadow_color||'#000000',Number(l.shadow_opacity)||0)})`});
      const svg=el.querySelector('svg');if(svg){svg.style.width='100%';svg.style.height='100%';}
    } else if(l.type==='image'){
      const mask=maskCss(l.mask);
      Object.assign(el.style,{borderRadius:l.radius||'0',overflow:'hidden',filter:`brightness(${Number(l.brightness)||1}) contrast(${Number(l.contrast)||1}) saturate(${Number(l.saturation)||1}) blur(${Number(l.blur)||0}px)`,mixBlendMode:l.blend_mode||'normal',maskImage:mask,webkitMaskImage:mask,maskSize:'100% 100%',webkitMaskSize:'100% 100%',boxShadow:layerShadow(l)});
      applyImageCrop(el,l);
      if(l.placeholder && !imageSource(l)){el.style.backgroundImage=`linear-gradient(135deg,${rgba(design.palette?.accent||'#5362ff',.24)},${rgba(design.palette?.dark||'#111111',.92)})`;}
    }
  }
  function renderCanvas(){
    canvas.style.width=design.canvas.width+'px';canvas.style.height=design.canvas.height+'px';canvas.style.background=design.canvas.bg;canvas.innerHTML='';
    design.layers.forEach((l,i)=>canvas.appendChild(layerElement(l,i)));
    const box=document.createElement('div');box.className='selection-box';box.id='selectionBox';box.innerHTML='<span class="resize-handle" title="Resize"></span>';canvas.appendChild(box);updateSelectionBox();
  }
  function elementFor(i){ return canvas.querySelector(`.canvas-element[data-index="${i}"]`); }
  function selectionBox(){ return $('selectionBox'); }
  function updateSelectionBox(){
    const box=selectionBox();if(!box)return;
    if(selected===null||!design.layers[selected]){box.classList.remove('visible');return;}
    const l=design.layers[selected];Object.assign(box.style,{left:(l.x||0)+'px',top:(l.y||0)+'px',width:(l.w||80)+'px',height:(l.h||40)+'px',zIndex:String(design.layers.length+20),transform:baseRotation(l),transformOrigin:'center center'});box.classList.add('visible');
  }
  function setSelected(i){ selected=i;canvas.querySelectorAll('.canvas-element.is-selected').forEach(el=>el.classList.remove('is-selected'));const el=elementFor(i);if(el)el.classList.add('is-selected');updateSelectionBox();renderLayers();renderProps(); }
  function clearSelection(){ selected=null;canvas.querySelectorAll('.canvas-element.is-selected').forEach(el=>el.classList.remove('is-selected'));updateSelectionBox();renderLayers();renderProps(); }
  function snapshot(){ history.push(JSON.stringify(design));if(history.length>60)history.shift();future=[]; }
  function restore(serialized){ design=adaptDesign(JSON.parse(serialized));projectName.value=design.name;renderCanvas();renderLayers();renderProps();markDirty(); }

  // Smooth pointer interaction: no full canvas re-render while dragging.
  canvas.addEventListener('pointerdown',e=>{
    const handle=e.target.closest('.resize-handle'),target=e.target.closest('.canvas-element');
    if(handle&&selected!==null){startResize(e);return;}
    if(!target){clearSelection();return;}
    e.preventDefault();const i=Number(target.dataset.index);setSelected(i);startDrag(e,target,i);
  });
  function startDrag(e,el,i){const l=design.layers[i];snapshot();const box=selectionBox();interaction={kind:'drag',id:e.pointerId,el,box,l,startX:e.clientX,startY:e.clientY,ox:l.x||0,oy:l.y||0,dx:0,dy:0};canvas.setPointerCapture?.(e.pointerId);el.classList.add('dragging');document.body.classList.add('is-dragging');}
  function startResize(e){e.preventDefault();e.stopPropagation();const l=design.layers[selected];snapshot();const el=elementFor(selected),box=selectionBox();interaction={kind:'resize',id:e.pointerId,el,box,l,startX:e.clientX,startY:e.clientY,ow:l.w||80,oh:l.h||40,w:l.w||80,h:l.h||40};canvas.setPointerCapture?.(e.pointerId);document.body.classList.add('is-resizing');}
  canvas.addEventListener('pointermove',e=>{if(!interaction||e.pointerId!==interaction.id)return;const factor=Math.max(.2,viewScale);if(interaction.kind==='drag'){interaction.dx=(e.clientX-interaction.startX)/factor;interaction.dy=(e.clientY-interaction.startY)/factor;}else{interaction.w=Math.max(18,interaction.ow+(e.clientX-interaction.startX)/factor);interaction.h=Math.max(12,interaction.oh+(e.clientY-interaction.startY)/factor);}if(!raf)raf=requestAnimationFrame(paintInteraction);});
  function paintInteraction(){raf=0;if(!interaction)return;if(interaction.kind==='drag'){const l=interaction.l,x=Math.max(-(l.w||80)+12,Math.min(design.canvas.width-12,interaction.ox+interaction.dx)),y=Math.max(-(l.h||40)+12,Math.min(design.canvas.height-12,interaction.oy+interaction.dy));interaction.nextX=Math.round(x);interaction.nextY=Math.round(y);const tx=interaction.nextX-interaction.ox,ty=interaction.nextY-interaction.oy;interaction.el.style.transform=`translate3d(${tx}px,${ty}px,0) ${baseRotation(l)}`;interaction.box.style.transform=`translate3d(${tx}px,${ty}px,0) ${baseRotation(l)}`;}else{interaction.nextW=Math.round(Math.min(design.canvas.width-(interaction.l.x||0)+120,interaction.w));interaction.nextH=Math.round(Math.min(design.canvas.height-(interaction.l.y||0)+120,interaction.h));interaction.el.style.width=interaction.nextW+'px';interaction.el.style.height=interaction.nextH+'px';if(interaction.l.type==='image')applyImageCrop(interaction.el,interaction.l,interaction.nextW,interaction.nextH);interaction.box.style.width=interaction.nextW+'px';interaction.box.style.height=interaction.nextH+'px';}}
  function finishInteraction(e){if(!interaction||e.pointerId!==interaction.id)return;if(raf){cancelAnimationFrame(raf);paintInteraction();}const done=interaction;if(done.kind==='drag'){done.l.x=done.nextX??done.ox;done.l.y=done.nextY??done.oy;done.el.classList.remove('dragging');}else{done.l.w=done.nextW??done.ow;done.l.h=done.nextH??done.oh;}applyLayerStyle(done.el,done.l);interaction=null;document.body.classList.remove('is-dragging','is-resizing');renderProps();updateSelectionBox();markDirty();scheduleSave();}
  canvas.addEventListener('pointerup',finishInteraction);canvas.addEventListener('pointercancel',finishInteraction);

  // ---------------------------------------------------------------------------
  // Layers and properties
  // ---------------------------------------------------------------------------
  function renderLayers(){
    $('layerCount').textContent=design.layers.length;
    layerList.innerHTML=[...design.layers].map((l,i)=>`<button class="layer-item ${selected===i?'active':''}" data-i="${i}"><span class="layer-type">${l.type==='text'?'T':l.type==='image'?'▧':l.type==='icon'?'◉':'◇'}</span><span class="layer-name">${escapeHtml(l.name||'Layer')}</span><span class="layer-grip">⋮</span></button>`).reverse().join('');
    layerList.querySelectorAll('.layer-item').forEach(el=>el.onclick=()=>setSelected(Number(el.dataset.i)));
  }
  function setDisplay(id,show){const el=$(id);if(el)el.style.display=show?'flex':'none';}
  function setVal(id,value){const el=$(id);if(el)el.value=value??'';}
  function numericRadius(v){const m=String(v||'0').match(/[\d.]+/);return m?Number(m[0]):0;}
  function ensureFontOption(font){const sel=$('propFont');if(!sel||!font)return;if(![...sel.options].some(o=>o.value===font)){const o=document.createElement('option');o.value=o.textContent=font;sel.appendChild(o);}ensureFontLoaded(font);}
  function renderProps(){
    const l=selected===null?null:design.layers[selected];empty.hidden=!!l;props.hidden=!l;if(!l)return;
    const text=l.type==='text',shape=l.type==='shape',image=l.type==='image',icon=l.type==='icon';
    ['textContentLabel','fontFamilyLabel','fontSizeLabel','fontWeightLabel','typeSpacingLabel','alignLabel'].forEach(id=>setDisplay(id,text));
    setDisplay('iconKindLabel',icon);
    setDisplay('shapeKindLabel',shape);setDisplay('fillTypeLabel',shape);setDisplay('secondColorLabel',shape);setDisplay('strokeLabel',shape);setDisplay('shadowLabel',shape||text||icon);setDisplay('primaryColorLabel',shape||text||icon);
    ['imageFitLabel','imageBlendLabel','imageMaskLabel','imageGradeLabel','imageRadiusLabel'].forEach(id=>setDisplay(id,image));
    $('autoBlendBtn').style.display=image?'inline-flex':'none';
    setVal('propX',l.x||0);setVal('propY',l.y||0);setVal('propW',l.w||80);setVal('propH',l.h||40);setVal('propOpacity',l.opacity??1);
    setVal('propText',l.text||'');setVal('propFontSize',l.size||16);ensureFontOption(l.font);setVal('propFont',l.font||'Inter');setVal('propWeight',l.weight||500);setVal('propTracking',l.spacing||0);setVal('propLine',l.line||1.05);setVal('propAlign',l.align||'left');
    setVal('propIcon',l.icon||'star');setVal('propKind',l.kind||'rect');setVal('propFill',l.fill||'solid');setVal('propColor',l.color||'#111111');setVal('propColor2',l.color2||l.color||'#4e5dff');setVal('propGradientAngle',l.gradient_angle||135);setVal('propStrokeColor',l.stroke_color||'#000000');setVal('propStrokeWidth',l.stroke_width||0);setVal('propShadowOpacity',l.shadow_opacity||0);setVal('propShadowBlur',l.shadow_blur||18);
    setVal('propImageFit',l.fit||'cover');setVal('propBlend',l.blend_mode||'normal');setVal('propMask',l.mask||'none');setVal('propBrightness',l.brightness??1);setVal('propContrast',l.contrast??1);setVal('propSaturation',l.saturation??1);setVal('propImageRadius',numericRadius(l.radius));
  }
  function updateOne(key,value){
    if(selected===null)return;const l=design.layers[selected];l[key]=value;const el=elementFor(selected);
    if(el){if(key==='text')el.textContent=value;if(key==='icon')el.innerHTML=iconSvg(value);applyLayerStyle(el,l);}updateSelectionBox();markDirty();scheduleSave();
  }
  function wireProp(id,key,transform=Number){const input=$(id);if(!input)return;let snapped=false;input.addEventListener('focus',()=>snapped=false);input.addEventListener('input',e=>{if(selected===null)return;if(!snapped){snapshot();snapped=true;}updateOne(key,transform(e.target.value));});input.addEventListener('change',()=>snapped=false);}
  ['propX','propY','propW','propH','propOpacity','propFontSize','propWeight','propTracking','propLine','propGradientAngle','propStrokeWidth','propShadowOpacity','propShadowBlur','propBrightness','propContrast','propSaturation'].forEach(id=>wireProp(id,({propX:'x',propY:'y',propW:'w',propH:'h',propOpacity:'opacity',propFontSize:'size',propWeight:'weight',propTracking:'spacing',propLine:'line',propGradientAngle:'gradient_angle',propStrokeWidth:'stroke_width',propShadowOpacity:'shadow_opacity',propShadowBlur:'shadow_blur',propBrightness:'brightness',propContrast:'contrast',propSaturation:'saturation'})[id]));
  wireProp('propText','text',String);wireProp('propFont','font',String);wireProp('propAlign','align',String);wireProp('propIcon','icon',String);wireProp('propKind','kind',String);wireProp('propFill','fill',String);wireProp('propColor','color',String);wireProp('propColor2','color2',String);wireProp('propStrokeColor','stroke_color',String);wireProp('propImageFit','fit',String);wireProp('propBlend','blend_mode',String);wireProp('propMask','mask',String);wireProp('propImageRadius','radius',v=>`${Math.max(0,Number(v)||0)}px`);

  $('deleteBtn').onclick=()=>deleteSelected();
  function deleteSelected(){if(selected===null)return;snapshot();design.layers.splice(selected,1);selected=null;renderCanvas();renderLayers();renderProps();markDirty();scheduleSave();}
  $('duplicateBtn').onclick=()=>{if(selected===null)return;snapshot();const l=clone(design.layers[selected]);l.x=(l.x||0)+14;l.y=(l.y||0)+14;l.name=(l.name||'Layer')+' copy';design.layers.push(l);renderCanvas();setSelected(design.layers.length-1);markDirty();scheduleSave();};
  $('undoBtn').onclick=()=>{if(!history.length)return;future.push(JSON.stringify(design));restore(history.pop());};
  $('redoBtn').onclick=()=>{if(!future.length)return;history.push(JSON.stringify(design));restore(future.pop());};

  // ---------------------------------------------------------------------------
  // Storage
  // ---------------------------------------------------------------------------
  function updateSaveStatus(text){saveStatus.textContent=text;}
  function markDirty(){updateSaveStatus('Unsaved changes');}
  function save(showMessage=true){
    design.name=projectName.value.trim()||'Untitled design';
    try{
      const saved=ClypStore.save(design);design=adaptDesign(saved);
      if(!qs.get('id'))history.replaceState(null,'','editor.html?id='+encodeURIComponent(design.id));
      updateSaveStatus('Saved locally');if(showMessage)showToast('Saved instantly on this device');return saved;
    }catch(err){updateSaveStatus('Could not save locally');showToast('Browser storage is full. Large local images can fill local storage; remove them or export the project.',5200);return design;}
  }
  function scheduleSave(){clearTimeout(saveTimer);saveTimer=setTimeout(()=>save(false),650);}
  $('saveBtn').onclick=()=>save(true);projectName.addEventListener('input',()=>{design.name=projectName.value;markDirty();scheduleSave();});
  function showToast(t,ms=2400){toast.textContent=t;toast.classList.add('show');clearTimeout(showToast.timer);showToast.timer=setTimeout(()=>toast.classList.remove('show'),ms);}

  // ---------------------------------------------------------------------------
  // AI editing
  // ---------------------------------------------------------------------------
  async function runAiEdit(command){
    snapshot();showToast('Clyp is art-directing the change…');
    const assets=design.assets||{},source=design.source||null,aiDesign=clone(design);delete aiDesign.assets;delete aiDesign.source;
    const data=await api('/api/ai/edit',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({command,project_id:design.id||'',design:aiDesign})});
    const id=design.id,name=design.name,format=design.format,created=design.created_at;
    design=adaptDesign(data.design);design.id=id;design.name=name;design.format=format;design.created_at=created;design.assets=assets;design.source=source;
    if(!design.layers.length) throw new Error('AI returned an empty layer stack; Clyp kept your previous design instead.');
    projectName.value=design.name;selected=null;renderCanvas();renderLayers();renderProps();markDirty();save(false);return data;
  }
  $('aiSend').onclick=async()=>{const input=$('aiCommand'),btn=$('aiSend'),cmd=input.value.trim();if(!cmd)return;btn.disabled=true;btn.innerHTML='<span class="mini-spinner"></span>Working';try{await runAiEdit(cmd);input.value='';showToast('AI edit applied');}catch(err){const previous=history.pop();if(previous)restore(previous);showToast(err.message,5200);}finally{btn.disabled=false;btn.textContent='Send';}};
  $('aiCommand').addEventListener('keydown',e=>{if(e.key==='Enter'&&!e.shiftKey){e.preventDefault();$('aiSend').click();}});
  $('autoBlendBtn').onclick=async()=>{if(selected===null||design.layers[selected]?.type!=='image')return;const l=design.layers[selected],name=l.name||'selected image';const btn=$('autoBlendBtn');btn.disabled=true;btn.textContent='✦ Blending…';try{await runAiEdit(`Professionally integrate the image layer named "${name}" into this design. Preserve the image itself and every factual text layer. Improve crop, size, position, colour grade, blend/mask treatment, readability overlay, surrounding geometry, spacing and contrast so it looks intentionally art-directed rather than pasted on. Keep effects category-appropriate and restrained.`);showToast('Image professionally integrated');}catch(err){showToast(err.message,5200);}finally{btn.disabled=false;btn.textContent='✦ Auto blend image';}};

  function safeFileName(ext='png'){return (design.name||'clyp-design').trim().replace(/[^a-z0-9-_]+/gi,'-').replace(/^-+|-+$/g,'').toLowerCase()+'.'+ext;}
  function targetExportWidth(){
    const f=String(design.format||'').toLowerCase();
    if(f.includes('a4'))return 2480;
    if(f.includes('1920')||design.canvas.height/design.canvas.width>1.55)return 1080;
    if(f.includes('1080'))return 1080;
    return Math.max(1080,Math.round(design.canvas.width*2.5));
  }
  async function ensureExportRenderer(){
    if(window.html2canvas)return window.html2canvas;
    const urls=['https://cdnjs.cloudflare.com/ajax/libs/html2canvas/1.4.1/html2canvas.min.js','https://cdn.jsdelivr.net/npm/html2canvas@1.4.1/dist/html2canvas.min.js'];
    let last;
    for(const src of urls){
      try{
        await new Promise((resolve,reject)=>{const script=document.createElement('script');script.src=src;script.async=true;script.crossOrigin='anonymous';script.onload=resolve;script.onerror=()=>reject(new Error('Could not load PNG renderer'));document.head.appendChild(script);});
        if(window.html2canvas)return window.html2canvas;
      }catch(err){last=err;}
    }
    throw last||new Error('PNG export renderer could not be loaded. Check your internet connection and retry.');
  }
  async function exportPng(){
    save(false);
    const btn=$('exportBtn'),oldText=btn.textContent;btn.disabled=true;btn.innerHTML='<span class="mini-spinner"></span> Exporting';
    const oldTransform=canvas.style.transform,oldOrigin=canvas.style.transformOrigin;
    try{
      design.layers.filter(l=>l.type==='text').forEach(l=>ensureFontLoaded(l.font));
      if(document.fonts?.ready)await document.fonts.ready;
      const html2canvas=await ensureExportRenderer();
      canvas.classList.add('exporting');canvas.style.transform='none';canvas.style.transformOrigin='top left';
      await new Promise(r=>requestAnimationFrame(()=>requestAnimationFrame(r)));
      const targetW=targetExportWidth();const scale=Math.max(1,targetW/design.canvas.width);
      const rendered=await html2canvas(canvas,{backgroundColor:design.canvas.bg||null,scale,useCORS:true,allowTaint:false,logging:false,width:design.canvas.width,height:design.canvas.height,windowWidth:design.canvas.width,windowHeight:design.canvas.height,scrollX:0,scrollY:0});
      const blob=await new Promise((resolve,reject)=>rendered.toBlob(b=>b?resolve(b):reject(new Error('Browser could not create the PNG.')),'image/png'));
      const a=document.createElement('a');a.href=URL.createObjectURL(blob);a.download=safeFileName('png');document.body.appendChild(a);a.click();a.remove();setTimeout(()=>URL.revokeObjectURL(a.href),1200);
      showToast(`PNG exported at ${rendered.width} × ${rendered.height}`,4200);
    }catch(err){showToast(`PNG export failed: ${err.message}`,6500);}
    finally{canvas.classList.remove('exporting');canvas.style.transform=oldTransform;canvas.style.transformOrigin=oldOrigin;btn.disabled=false;btn.textContent=oldText||'Export PNG';}
  }
  function exportProjectJson(){save(false);const payload=JSON.stringify(design,null,2);const blob=new Blob([payload],{type:'application/json'});const a=document.createElement('a');a.href=URL.createObjectURL(blob);a.download=safeFileName('clyp.json');a.click();setTimeout(()=>URL.revokeObjectURL(a.href),500);showToast('Editable project backup exported');}
  $('exportBtn').onclick=exportPng;
  $('exportBtn').title='Export PNG image';

  // Zoom is relative to the 75% base visual scale used by the editor.
  function setZoom(pct){viewScale=pct/75;canvas.style.transform=`scale(${viewScale})`;canvas.style.transformOrigin='top center';$('zoomValue').textContent=pct+'%';}
  $('zoomSelect').onchange=e=>setZoom(parseInt(e.target.value,10)||75);
  function fitCanvasToStage(){requestAnimationFrame(()=>{const avail=Math.max(220,canvasStage.clientWidth-(innerWidth<=820?24:90)),natural=design.canvas.width,ratio=Math.min(1.25,avail/natural),pct=Math.max(50,Math.min(125,Math.round(75*ratio/5)*5));$('zoomSelect').value=pct+'%';setZoom(pct);});}
  window.addEventListener('resize',()=>{clearTimeout(window.__clypResize);window.__clypResize=setTimeout(fitCanvasToStage,100);});

  // ---------------------------------------------------------------------------
  // Add assets/elements
  // ---------------------------------------------------------------------------
  function addLayer(shape){snapshot();design.layers.push(shape);renderCanvas();setSelected(design.layers.length-1);markDirty();scheduleSave();}
  function centreImageLayer(src,name='Image',extra={}){const w=Math.round(design.canvas.width*.82),h=Math.round(Math.min(design.canvas.height*.62,w*.82));addLayer({type:'image',name,x:Math.round((design.canvas.width-w)/2),y:Math.round((design.canvas.height-h)/2),w,h,src,source_kind:'local',fit:'cover',blend_mode:'normal',mask:'none',brightness:1,contrast:1,saturation:1,blur:0,radius:'0',...extra});}
  function compressImageFile(file,maxDim=1800,quality=.88){return new Promise((resolve,reject)=>{const r=new FileReader();r.onerror=()=>reject(new Error('Could not read that image.'));r.onload=()=>{const img=new Image();img.onerror=()=>reject(new Error('That image could not be decoded.'));img.onload=()=>{let w=img.naturalWidth,h=img.naturalHeight,scale=Math.min(1,maxDim/Math.max(w,h));w=Math.max(1,Math.round(w*scale));h=Math.max(1,Math.round(h*scale));const c=document.createElement('canvas');c.width=w;c.height=h;const ctx=c.getContext('2d');ctx.drawImage(img,0,0,w,h);resolve({dataUrl:c.toDataURL('image/webp',quality),width:w,height:h});};img.src=r.result;};r.readAsDataURL(file);});}

  const ELEMENT_PRESETS = [
    ['rect','Rectangle','Structure'],['rounded','Rounded card','Structure'],['ellipse','Circle','Structure'],['pill','Pill / badge','Structure'],['line','Divider line','Structure'],['dashed-line','Dashed line','Structure'],['frame','Outline frame','Structure'],['info-card','Info card','Structure'],['photo-frame','Photo frame','Structure'],['footer','Footer panel','Structure'],['top-panel','Top panel','Structure'],['split-panel','Split panel','Structure'],['caption-strip','Caption strip','Structure'],['info-strip','Information strip','Structure'],['cta-card','CTA card','Structure'],['quote-card','Quote card','Structure'],['ring','Outline circle','Structure'],['double-frame','Double-look frame','Structure'],
    ['triangle','Triangle','Geometry'],['diamond','Diamond','Geometry'],['pentagon','Pentagon','Geometry'],['hexagon','Hexagon','Geometry'],['octagon','Octagon','Geometry'],['star','Star','Geometry'],['burst','Burst','Geometry'],['arrow','Arrow','Geometry'],['chevron','Chevron','Geometry'],['ribbon','Ribbon','Geometry'],['semicircle','Semicircle','Geometry'],['parallelogram','Parallelogram','Geometry'],['trapezoid','Trapezoid','Geometry'],
    ['gradient','Linear gradient','Light & depth'],['glow','Radial light','Light & depth'],['spotlight','Spotlight beam','Light & depth'],['vignette','Vignette overlay','Light & depth'],['glass','Glass panel','Light & depth'],['fade','Readability fade','Light & depth'],['top-fade','Top readability fade','Light & depth'],['side-fade','Side readability fade','Light & depth'],['colour-wash','Colour wash','Light & depth'],['shadow-card','Shadow surface','Light & depth'],['light-streak','Light streak','Light & depth'],['warm-bloom','Warm bloom','Light & depth'],['cool-bloom','Cool bloom','Light & depth'],
    ['pattern-dots','Dot pattern','Patterns'],['pattern-lines','Diagonal stripes','Patterns'],['pattern-grid','Grid pattern','Patterns'],['pattern-checker','Checker pattern','Patterns'],['pattern-cross','Crosshatch','Patterns'],
    ['highlight','Highlight bar','Accents'],['rail','Side rail','Accents'],['underline','Headline underline','Accents'],['corner','Corner block','Accents'],['badge-circle','Number disk','Accents'],['tab','Section tab','Accents'],['slash','Diagonal slash','Accents'],['micro-rule','Micro rule','Accents'],['price-pill','Price / offer pill','Accents'],['date-chip','Date chip','Accents'],['vertical-label','Vertical label bar','Accents'],['accent-disc','Accent disc','Accents'],['soft-divider','Soft divider','Accents'],['mini-frame','Mini frame','Accents']
  ];
  function presetLayer(id){
    const A=design.palette?.accent||'#5362ff',D=design.palette?.dark||'#181916',L=design.palette?.light||'#ffffff',S=design.palette?.support||'#d9dce8';
    const common={type:'shape',name:id.replace(/-/g,' ').replace(/\b\w/g,m=>m.toUpperCase()),x:90,y:110,w:150,h:80,color:A,opacity:1,rotation:0};
    const map={
      rect:{...common,kind:'rect',fill:'solid'},rounded:{...common,kind:'rounded',fill:'solid',radius:'20px'},ellipse:{...common,kind:'ellipse',fill:'solid',w:110,h:110},pill:{...common,kind:'pill',fill:'solid',w:150,h:42},line:{...common,kind:'line',fill:'solid',w:190,h:3,color:D},'dashed-line':{...common,kind:'dashed-line',fill:'solid',w:190,h:4,color:'transparent',stroke_color:D,stroke_width:2},frame:{...common,kind:'rect',fill:'solid',x:40,y:40,w:design.canvas.width-80,h:design.canvas.height-80,color:L,opacity:.02,stroke_color:L,stroke_width:2,radius:'4px'},
      triangle:{...common,kind:'triangle',fill:'solid',w:110,h:95},diamond:{...common,kind:'diamond',fill:'solid',w:100,h:100},pentagon:{...common,kind:'pentagon',fill:'solid',w:105,h:100},hexagon:{...common,kind:'hexagon',fill:'solid',w:110,h:100},octagon:{...common,kind:'octagon',fill:'solid',w:105,h:105},star:{...common,kind:'star',fill:'solid',w:100,h:100},burst:{...common,kind:'burst',fill:'solid',w:110,h:110},arrow:{...common,kind:'arrow',fill:'solid',w:150,h:72},chevron:{...common,kind:'chevron',fill:'solid',w:130,h:70},ribbon:{...common,kind:'ribbon',fill:'solid',w:160,h:58},semicircle:{...common,kind:'semicircle',fill:'solid',w:150,h:80},parallelogram:{...common,kind:'parallelogram',fill:'solid',w:140,h:70},trapezoid:{...common,kind:'trapezoid',fill:'solid',w:140,h:80},
      gradient:{...common,kind:'rect',fill:'linear',w:260,h:180,color:D,color2:A,gradient_angle:135,opacity:.9,radius:'18px'},glow:{...common,kind:'ellipse',fill:'radial',w:260,h:260,color:A,color2:D,opacity:.38,shadow_color:A,shadow_opacity:.4,shadow_blur:90},spotlight:{...common,kind:'parallelogram',fill:'linear',x:230,y:-40,w:110,h:360,color:A,color2:D,gradient_angle:180,opacity:.2,rotation:18},vignette:{...common,kind:'rect',fill:'radial',x:0,y:0,w:design.canvas.width,h:design.canvas.height,color:D,color2:'#000000',opacity:.34},glass:{...common,kind:'rounded',fill:'solid',w:250,h:120,color:L,opacity:.14,stroke_color:L,stroke_width:1,radius:'20px',shadow_color:D,shadow_opacity:.15,shadow_blur:28},fade:{...common,kind:'rect',fill:'linear',x:0,y:Math.round(design.canvas.height*.55),w:design.canvas.width,h:Math.round(design.canvas.height*.45),color:D,color2:'#000000',gradient_angle:180,opacity:.45},'colour-wash':{...common,kind:'rect',fill:'linear',x:0,y:0,w:design.canvas.width,h:design.canvas.height,color:A,color2:D,gradient_angle:135,opacity:.26},'shadow-card':{...common,kind:'rounded',fill:'solid',w:255,h:135,color:S,opacity:.96,radius:'18px',shadow_color:D,shadow_opacity:.22,shadow_y:16,shadow_blur:32},
      'pattern-dots':{...common,kind:'pattern-dots',fill:'solid',w:220,h:170,color:A,opacity:.45},'pattern-lines':{...common,kind:'pattern-lines',fill:'solid',w:220,h:170,color:A,opacity:.3,gradient_angle:135},'pattern-grid':{...common,kind:'pattern-grid',fill:'solid',w:220,h:170,color:A,opacity:.35},'pattern-checker':{...common,kind:'pattern-checker',fill:'solid',w:220,h:170,color:A,opacity:.25},'pattern-cross':{...common,kind:'pattern-cross',fill:'solid',w:220,h:170,color:A,opacity:.28},
      highlight:{...common,kind:'rect',fill:'solid',w:130,h:10,color:A},rail:{...common,kind:'rect',fill:'solid',x:0,y:0,w:12,h:design.canvas.height,color:A},underline:{...common,kind:'line',fill:'solid',w:130,h:5,color:A},corner:{...common,kind:'triangle',fill:'solid',x:design.canvas.width-105,y:design.canvas.height-90,w:105,h:90,color:A,opacity:.55},'badge-circle':{...common,kind:'ellipse',fill:'solid',w:58,h:58,color:A},tab:{...common,kind:'rounded',fill:'solid',w:105,h:34,color:A,radius:'8px'},slash:{...common,kind:'parallelogram',fill:'solid',w:18,h:90,color:A,rotation:18},'micro-rule':{...common,kind:'line',fill:'solid',w:48,h:2,color:A},footer:{...common,kind:'rect',fill:'solid',x:0,y:design.canvas.height-90,w:design.canvas.width,h:90,color:D,opacity:.92},'info-card':{...common,kind:'rounded',fill:'solid',w:280,h:110,color:S,opacity:.96,radius:'16px',stroke_color:A,stroke_width:1},'photo-frame':{...common,kind:'rounded',fill:'solid',w:230,h:250,color:'transparent',opacity:1,radius:'18px',stroke_color:L,stroke_width:3},'top-panel':{...common,kind:'rect',fill:'solid',x:0,y:0,w:design.canvas.width,h:115,color:D,opacity:.72},'split-panel':{...common,kind:'rect',fill:'solid',x:0,y:0,w:Math.round(design.canvas.width*.44),h:design.canvas.height,color:D,opacity:.78},'caption-strip':{...common,kind:'rounded',fill:'solid',w:270,h:52,color:D,opacity:.86,radius:'10px'},'info-strip':{...common,kind:'rounded',fill:'solid',w:320,h:76,color:L,opacity:.11,radius:'12px',stroke_color:L,stroke_width:1},'cta-card':{...common,kind:'rounded',fill:'solid',w:280,h:70,color:A,opacity:.96,radius:'14px',shadow_color:D,shadow_opacity:.2,shadow_y:10,shadow_blur:24},'quote-card':{...common,kind:'rounded',fill:'solid',w:300,h:150,color:L,opacity:.1,radius:'18px',stroke_color:L,stroke_width:1},'ring':{...common,kind:'ellipse',fill:'solid',w:120,h:120,color:'transparent',stroke_color:A,stroke_width:3},'double-frame':{...common,kind:'rect',fill:'solid',x:30,y:30,w:design.canvas.width-60,h:design.canvas.height-60,color:'transparent',stroke_color:L,stroke_width:3,opacity:.7},'top-fade':{...common,kind:'rect',fill:'linear',x:0,y:0,w:design.canvas.width,h:Math.round(design.canvas.height*.35),color:D,color2:'#000000',gradient_angle:0,opacity:.5},'side-fade':{...common,kind:'rect',fill:'linear',x:0,y:0,w:Math.round(design.canvas.width*.62),h:design.canvas.height,color:D,color2:'#000000',gradient_angle:90,opacity:.52},'light-streak':{...common,kind:'parallelogram',fill:'linear',x:250,y:-60,w:52,h:360,color:A,color2:L,gradient_angle:180,opacity:.22,rotation:20,shadow_color:A,shadow_opacity:.26,shadow_blur:60},'warm-bloom':{...common,kind:'ellipse',fill:'radial',x:220,y:-40,w:280,h:280,color:'#FFB347',color2:D,opacity:.3,shadow_color:'#FF9F43',shadow_opacity:.3,shadow_blur:90},'cool-bloom':{...common,kind:'ellipse',fill:'radial',x:220,y:-40,w:280,h:280,color:'#6EA8FF',color2:D,opacity:.26,shadow_color:'#6EA8FF',shadow_opacity:.25,shadow_blur:90},'price-pill':{...common,kind:'pill',fill:'solid',w:160,h:48,color:A,radius:'999px'},'date-chip':{...common,kind:'rounded',fill:'solid',w:120,h:38,color:L,opacity:.14,radius:'10px',stroke_color:L,stroke_width:1},'vertical-label':{...common,kind:'rounded',fill:'solid',w:36,h:145,color:A,radius:'8px'},'accent-disc':{...common,kind:'ellipse',fill:'solid',w:72,h:72,color:A,opacity:.9},'soft-divider':{...common,kind:'line',fill:'linear',w:210,h:2,color:L,color2:A,gradient_angle:90,opacity:.55},'mini-frame':{...common,kind:'rect',fill:'solid',w:110,h:80,color:'transparent',stroke_color:A,stroke_width:2,opacity:.8}
    };
    return map[id]||map.rect;
  }

  function localImagePanel(){return `<div class="asset-tabs"><button class="asset-tab active" data-asset-tab="local">Upload</button><button class="asset-tab" data-asset-tab="ai">AI image</button><button class="asset-tab" data-asset-tab="online">Online</button></div><div id="assetPanelBody"></div>`;}
  function renderAssetSubpanel(kind){
    const body=$('assetPanelBody');if(!body)return;document.querySelectorAll('.asset-tab').forEach(b=>b.classList.toggle('active',b.dataset.assetTab===kind));
    if(kind==='local'){body.innerHTML=`<div class="asset-intro"><strong>Add your own image</strong><p>Clyp optimises it locally. Then crop, grade, mask and blend it professionally.</p></div><button class="upload-drop compact-upload" id="pickLocalImage"><strong>Choose image</strong><span>JPG · PNG · WebP · GIF</span></button>`;$('pickLocalImage').onclick=()=>$('localImageInput').click();}
    if(kind==='ai'){body.innerHTML=`<div class="asset-intro"><strong>Generate a visual asset</strong><p>Create the photo or illustration only. Clyp keeps typography and layout editable.</p></div><textarea class="asset-prompt" id="assetPrompt" rows="4" placeholder="e.g. joyful African worshippers on a modern church stage, warm amber rim light, realistic photography, darker copy space on the left, no text"></textarea><button class="button full" id="generateAsset">Generate image</button><small class="asset-note">If your Gemini image quota is unavailable, Clyp can continue with an online fallback.</small>`;$('generateAsset').onclick=generateAiAsset;}
    if(kind==='online'){body.innerHTML=`<div class="asset-intro"><strong>Find openly licensed imagery</strong><p>Search Openverse. Attribution details stay attached to the image layer.</p></div><div class="asset-search"><input id="onlineAssetQuery" placeholder="Search photos or illustrations"><button id="onlineAssetSearch">Search</button></div><div class="asset-results" id="assetResults"><div class="asset-empty">Search for a useful image, then Clyp will place it as an editable image layer.</div></div>`;$('onlineAssetSearch').onclick=searchOnlineAssets;$('onlineAssetQuery').addEventListener('keydown',e=>{if(e.key==='Enter')searchOnlineAssets();});}
  }
  async function generateAiAsset(){const prompt=$('assetPrompt')?.value.trim(),btn=$('generateAsset');if(!prompt)return showToast('Describe the image you want.');btn.disabled=true;btn.innerHTML='<span class="mini-spinner"></span> Generating…';try{const data=await api('/api/ai/image-generate',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({prompt,width:design.canvas.width,height:Math.round(design.canvas.height*.65)})});const src=data.data_url||data.src;if(!src)throw new Error('No image source was returned.');centreImageLayer(src,data.source_kind==='online'?'Openverse visual':'AI visual',{source_kind:data.source_kind||'ai',asset_prompt:prompt,stock_query:data.stock_query||'',attribution:data.attribution||null});showToast(data.warning||'Image added — select it and use Auto blend',6500);}catch(err){showToast(err.message,6500);}finally{btn.disabled=false;btn.textContent='Generate image';}}
  async function searchOnlineAssets(){const q=$('onlineAssetQuery')?.value.trim(),out=$('assetResults');if(!q)return;out.innerHTML='<div class="asset-empty"><span class="mini-spinner dark"></span> Searching Openverse…</div>';try{const data=await api('/api/assets/search?q='+encodeURIComponent(q));if(!data.results?.length){out.innerHTML='<div class="asset-empty">No suitable results. Try a broader search.</div>';return;}out.innerHTML=data.results.map((r,i)=>{const thumb='/api/assets/fetch?url='+encodeURIComponent(r.thumbnail||r.url);return `<button class="asset-result" data-result="${i}"><img src="${escapeHtml(thumb)}" alt=""><span><b>${escapeHtml(r.title||'Image')}</b><small>${escapeHtml(r.creator||'Unknown')} · ${escapeHtml((r.license||'open').toUpperCase())}</small></span></button>`;}).join('');out.querySelectorAll('.asset-result').forEach(btn=>btn.onclick=()=>{const r=data.results[Number(btn.dataset.result)],src='/api/assets/fetch?url='+encodeURIComponent(r.url||r.thumbnail);centreImageLayer(src,r.title||'Online image',{source_kind:'online',attribution:{creator:r.creator,license:r.license,license_url:r.license_url,landing_url:r.landing_url,attribution:r.attribution}});showToast('Online image added — attribution retained');});}catch(err){out.innerHTML=`<div class="asset-empty error">${escapeHtml(err.message)}</div>`;}}

  $('localImageInput').addEventListener('change',async e=>{for(const file of [...e.target.files]){if(!file.type.startsWith('image/'))continue;try{showToast('Optimising local image…');const img=await compressImageFile(file);centreImageLayer(img.dataUrl,file.name.replace(/\.[^.]+$/,''),{source_kind:'local',natural_width:img.width,natural_height:img.height});showToast('Local image added');}catch(err){showToast(err.message,4200);}}e.target.value='';});

  function renderElementPanel(){
    const groups=['Structure','Geometry','Light & depth','Patterns','Accents'];
    return `<div class="panel-heading"><span>Elements</span><small>${ELEMENT_PRESETS.length + Object.keys(ICONS).length}+ editable tools</small></div>` + groups.map(group=>`<div class="element-section"><h4>${group}</h4><div class="tool-grid element-grid">${ELEMENT_PRESETS.filter(p=>p[2]===group).map(([id,label])=>`<button class="tool-tile element-preset" data-element="${id}"><span class="element-glyph ${id}"></span>${label}</button>`).join('')}</div></div>`).join('') + `<div class="element-section"><h4>Icons</h4><div class="icon-grid">${Object.keys(ICONS).map(name=>`<button class="icon-tile" data-icon="${name}" title="${name}">${iconSvg(name)}<span>${name.replace(/-/g,' ')}</span></button>`).join('')}</div></div>`;
  }
  function fontLibraryMarkup(filter=''){
    const term=String(filter||'').trim().toLowerCase();
    const cards=[];
    Object.entries(FONT_CATALOG).forEach(([group,fonts])=>{
      const matches=fonts.filter(font=>!term || font.toLowerCase().includes(term) || group.toLowerCase().includes(term));
      if(!matches.length)return;
      cards.push(`<div class="font-group"><h4>${escapeHtml(group)}</h4><div class="font-library-grid">${matches.map(font=>`<button class="font-card" data-font="${escapeHtml(font)}"><span class="font-preview" data-font-preview="${escapeHtml(font)}">Ag</span><span><b>${escapeHtml(font)}</b><small>Apply to selected text</small></span></button>`).join('')}</div></div>`);
    });
    return cards.join('') || '<div class="asset-empty">No typefaces match that search.</div>';
  }
  function applyFontFromLibrary(font){
    ensureFontLoaded(font);
    if(selected!==null && design.layers[selected]?.type==='text'){
      snapshot();design.layers[selected].font=font;applyLayerStyle(elementFor(selected),design.layers[selected]);renderProps();markDirty();scheduleSave();showToast(`${font} applied`);return;
    }
    addLayer({type:'text',name:'Headline',x:50,y:80,w:320,h:105,text:'YOUR HEADLINE',size:50,weight:800,color:isDark(design.canvas.bg)?(design.palette?.light||'#ffffff'):(design.palette?.dark||'#111111'),font,line:.9,spacing:-.3});
    showToast(`${font} loaded — headline added`);
  }
  function wireFontLibrary(){
    const holder=$('fontLibrary');if(!holder)return;
    holder.querySelectorAll('[data-font]').forEach(btn=>{
      const font=btn.dataset.font;
      btn.addEventListener('pointerenter',()=>{ensureFontLoaded(font);const sample=btn.querySelector('[data-font-preview]');if(sample)sample.style.fontFamily=`"${font}", Inter, sans-serif`;},{once:true});
      btn.onclick=()=>applyFontFromLibrary(font);
    });
  }
  function renderTextPanel(){
    const pairings=[
      ['Bold event','Bebas Neue','Manrope'],['Condensed','Oswald','Inter'],['Modern premium','League Spartan','Plus Jakarta Sans'],['Editorial','Playfair Display','Manrope'],['Luxury serif','DM Serif Display','Inter'],['Fashion','Bodoni Moda','DM Sans'],['Tech','Space Grotesk','Inter'],['Sharp condensed','Barlow Condensed','Manrope'],['Contemporary','Archivo Black','DM Sans']
    ];
    return `<div class="panel-heading"><span>Text & fonts</span><small>${Object.values(FONT_CATALOG).flat().length} typefaces</small></div>
      <div class="text-add-grid"><button class="tool-tile" id="addHeading"><b class="text-sample heading">Aa</b><span>Display heading</span></button><button class="tool-tile" id="addSubheading"><b class="text-sample">Aa</b><span>Subheading</span></button><button class="tool-tile" id="addBody"><b class="text-sample body">Aa</b><span>Body / details</span></button></div>
      <div class="font-pairings"><h4>Professional pairings</h4>${pairings.map((p,i)=>`<button class="font-pair" data-pair="${i}"><strong>${escapeHtml(p[0])}</strong><small>${escapeHtml(p[1])} + ${escapeHtml(p[2])}</small></button>`).join('')}</div>
      <div class="font-library-head"><div><h4>Font library</h4><small>Hover to preview · click to apply</small></div><input id="fontSearch" placeholder="Search fonts…" autocomplete="off"></div>
      <div id="fontLibrary" class="font-library">${fontLibraryMarkup('')}</div>`;
  }
  function renderColourPanel(){
    return `<div class="panel-heading"><span>Colour systems</span><small>Curated starting palettes</small></div><p class="panel-note">Apply a professional palette, then refine individual layers in Properties.</p><div class="palette-list">${PALETTES.map((p,i)=>`<button class="palette-card" data-palette="${i}"><span class="palette-swatches"><i style="background:${p.dominant}"></i><i style="background:${p.support}"></i><i style="background:${p.accent}"></i><i style="background:${p.light}"></i><i style="background:${p.dark}"></i></span><span><b>${p.name}</b><small>${p.strategy}</small></span></button>`).join('')}</div>`;
  }
  function applyPalettePreset(p){
    snapshot();const old=design.palette||{};const roleMap={};['dominant','support','accent','light','dark'].forEach(role=>{if(old[role])roleMap[String(old[role]).toLowerCase()]=p[role];});
    design.canvas.bg=p.dominant;design.palette=clone(p);
    design.layers.forEach(l=>{
      if(l.color && roleMap[String(l.color).toLowerCase()]) l.color=roleMap[String(l.color).toLowerCase()];
      if(l.color2 && roleMap[String(l.color2).toLowerCase()]) l.color2=roleMap[String(l.color2).toLowerCase()];
      if(/accent|highlight|badge|rail|glow|light/i.test(l.name||'') && l.type!=='text') l.color=p.accent;
      if(l.type==='text' && /headline|title|kicker/i.test(l.name||'')) l.color=isDark(p.dominant)?p.light:p.dark;
    });
    renderCanvas();renderLayers();renderProps();markDirty();scheduleSave();showToast(`${p.name} palette applied`);
  }
  function isDark(hex){const m=String(hex).match(/^#([0-9a-f]{6})$/i);if(!m)return false;const n=parseInt(m[1],16),r=(n>>16)&255,g=(n>>8)&255,b=n&255;return (r*299+g*587+b*114)/1000<145;}

  function showPanel(type){
    currentPanel=type;document.querySelectorAll('.tool-tab').forEach(b=>b.classList.toggle('active',b.dataset.panel===type));
    const content={
      templates:`<div class="panel-heading"><span>Templates</span><small>Start polished</small></div><button class="tool-tile featured" onclick="location.href='templates.html'"><span>Browse template library</span><b>→</b></button><div class="asset-intro"><strong>Design density V5.1</strong><p>Generated flyers are now checked for visual depth and meaningful layer density before Clyp returns them.</p></div>`,
      elements:renderElementPanel(),text:renderTextPanel(),colors:renderColourPanel(),uploads:localImagePanel()
    }[type] || '';
    panel.innerHTML=content;
    if(type==='elements'){
      panel.querySelectorAll('[data-element]').forEach(btn=>btn.onclick=()=>addLayer(presetLayer(btn.dataset.element)));
      panel.querySelectorAll('[data-icon]').forEach(btn=>btn.onclick=()=>{const icon=btn.dataset.icon;addLayer({type:'icon',name:`${icon.replace(/-/g,' ')} icon`,icon,x:80,y:100,w:28,h:28,color:design.palette?.accent||'#5362ff',opacity:1,rotation:0});});
    }
    if(type==='text'){
      $('addHeading').onclick=()=>addLayer({type:'text',name:'Headline',x:50,y:80,w:320,h:105,text:'YOUR HEADLINE',size:50,weight:800,color:isDark(design.canvas.bg)?(design.palette?.light||'#ffffff'):(design.palette?.dark||'#111111'),font:'League Spartan',line:.9,spacing:-.3});
      $('addSubheading').onclick=()=>addLayer({type:'text',name:'Subheading',x:50,y:190,w:310,h:48,text:'Supporting message',size:23,weight:700,color:isDark(design.canvas.bg)?(design.palette?.light||'#ffffff'):(design.palette?.dark||'#222222'),font:'Manrope',line:1});
      $('addBody').onclick=()=>addLayer({type:'text',name:'Body text',x:50,y:260,w:310,h:65,text:'Add supporting information here.',size:15,weight:500,color:isDark(design.canvas.bg)?(design.palette?.light||'#ffffff'):(design.palette?.dark||'#333333'),font:'Inter',line:1.25});
      const pairings=[['Bebas Neue','Manrope'],['Oswald','Inter'],['League Spartan','Plus Jakarta Sans'],['Playfair Display','Manrope'],['DM Serif Display','Inter'],['Bodoni Moda','DM Sans'],['Space Grotesk','Inter'],['Barlow Condensed','Manrope'],['Archivo Black','DM Sans']];
      panel.querySelectorAll('[data-pair]').forEach(btn=>btn.onclick=()=>{const [display,support]=pairings[Number(btn.dataset.pair)];ensureFontLoaded(display);ensureFontLoaded(support);if(selected!==null&&design.layers[selected]?.type==='text'){snapshot();design.layers[selected].font=display;applyLayerStyle(elementFor(selected),design.layers[selected]);renderProps();markDirty();scheduleSave();showToast(`${display} applied. ${support} is ready for supporting copy.`);}else showToast(`${display} + ${support} loaded. Select a text layer or choose a font below.`);});
      wireFontLibrary();
      $('fontSearch').addEventListener('input',e=>{$('fontLibrary').innerHTML=fontLibraryMarkup(e.target.value);wireFontLibrary();});
    }
    if(type==='colors') panel.querySelectorAll('[data-palette]').forEach(btn=>btn.onclick=()=>applyPalettePreset(PALETTES[Number(btn.dataset.palette)]));
    if(type==='uploads'){document.querySelectorAll('.asset-tab').forEach(b=>b.onclick=()=>renderAssetSubpanel(b.dataset.assetTab));renderAssetSubpanel('local');}
  }

  document.querySelectorAll('.tool-tab').forEach(b=>b.onclick=()=>{$('editorLeft').classList.add('mobile-panel-open');showPanel(b.dataset.panel);});

  // Keyboard controls
  document.addEventListener('keydown',e=>{
    if(['INPUT','TEXTAREA','SELECT'].includes(document.activeElement?.tagName))return;
    if((e.ctrlKey||e.metaKey)&&e.key.toLowerCase()==='z'){e.preventDefault();(e.shiftKey?$('redoBtn'):$('undoBtn')).click();return;}
    if((e.key==='Delete'||e.key==='Backspace')&&selected!==null){e.preventDefault();deleteSelected();return;}
    if(selected!==null&&['ArrowLeft','ArrowRight','ArrowUp','ArrowDown'].includes(e.key)){e.preventDefault();snapshot();const l=design.layers[selected],step=e.shiftKey?10:1;if(e.key==='ArrowLeft')l.x-=step;if(e.key==='ArrowRight')l.x+=step;if(e.key==='ArrowUp')l.y-=step;if(e.key==='ArrowDown')l.y+=step;applyLayerStyle(elementFor(selected),l);updateSelectionBox();renderProps();markDirty();scheduleSave();}
  });

  $('mobilePropsBtn').onclick=()=>$('editorRight').classList.add('mobile-open');
  $('closePropsBtn').onclick=()=>$('editorRight').classList.remove('mobile-open');
  canvasStage.addEventListener('pointerdown',e=>{if(innerWidth<=820&&e.target===canvasStage)$('editorLeft').classList.remove('mobile-panel-open');});

  showPanel('templates');
  load();
})();
