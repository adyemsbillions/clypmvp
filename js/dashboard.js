const modal=document.getElementById('createModal'),content=document.getElementById('modalContent'),upload=document.getElementById('flyerUpload');
const esc=s=>String(s??'').replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
function openModal(html){content.innerHTML=html;modal.classList.add('open');modal.setAttribute('aria-hidden','false')}
function closeModal(){modal.classList.remove('open');modal.setAttribute('aria-hidden','true')}
function setModalBusy(text,detail='Clyp is building hierarchy, colour, imagery and editable layers.'){content.innerHTML=`<div class="brief-form ai-working"><span class="kicker">CLYP AI</span><h2>${esc(text)}</h2><p>${esc(detail)}</p><div class="ai-loader"><i></i></div></div>`}
function modalError(message,back){content.innerHTML=`<div class="brief-form"><span class="kicker">COULDN'T CONTINUE</span><h2>${esc(message)}</h2><p>Clyp reached the AI service, but the request could not be completed. The error above is the useful part; retry after correcting it.</p><div class="brief-actions"><button class="button ghost" data-close>Close</button><button class="button" id="retryAction">Try again</button></div></div>`;document.getElementById('retryAction').onclick=back}
modal.addEventListener('click',e=>{if(e.target===modal||e.target.matches('[data-close]'))closeModal()});

async function api(url,options={}){const res=await fetch(url,options);const data=await res.json().catch(()=>({ok:false,message:'Invalid server response'}));if(!res.ok||!data.ok)throw Object.assign(new Error(data.message||'Request failed'),{data,status:res.status});return data}

const option=(value,label,selected=false)=>`<option value="${value}" ${selected?'selected':''}>${label}</option>`;
function aiForm(){return `<form class="brief-form create-ai-form" id="briefForm">
  <span class="kicker">CREATE WITH AI</span>
  <h2>Tell Clyp what you’re making.</h2>
  <p>Give Clyp the content, then optionally art-direct the result. Leave anything on <b>AI choose</b> when you want Clyp to decide.</p>
  <label class="brief-main">What do you need?<textarea name="brief" rows="5" required placeholder="e.g. Make a premium tech summit flyer for founders and product leaders in Lagos."></textarea></label>
  <label>Format<select name="format">${option('Instagram portrait · 1080 × 1350','Instagram portrait · 1080 × 1350',true)}${option('Square · 1080 × 1080','Square · 1080 × 1080')}${option('Story · 1080 × 1920','Story · 1080 × 1920')}${option('A4 document','A4 document')}</select></label>
  <div class="preference-head"><div><strong>Visual direction</strong><small>Optional controls — Clyp still handles the detailed art direction.</small></div><span>V5.2</span></div>
  <div class="preference-grid">
    <label>Category<select name="category">${option('auto','AI detect',true)}${option('technology','Tech')}${option('worship','Church / Worship')}${option('corporate','Business / Corporate')}${option('education','Education')}${option('beauty','Beauty / Fashion')}${option('food','Food')}${option('real-estate','Real Estate')}${option('music','Music / Nightlife')}${option('sale','Promotion / Sale')}${option('general','Other')}</select></label>
    <label>Visual mood<select name="visual_mood">${option('auto','AI choose',true)}${option('bright','Bright')}${option('dark','Dark')}${option('balanced','Balanced')}${option('soft','Soft')}</select></label>
    <label>Imagery<select name="imagery_mode">${option('auto','AI choose',true)}${option('photo','Real photo')}${option('illustration','Illustration')}${option('both','Photo + illustration/graphics')}${option('none','No imagery')}</select></label>
    <label>Image subject<select name="image_subject">${option('auto','AI choose',true)}${option('people','People')}${option('objects','Objects / products')}${option('abstract','Abstract visuals')}${option('mixed','Mixed')}</select></label>
    <label>Colour style<select name="colour_style">${option('auto','AI choose',true)}${option('bold','Bold / vibrant')}${option('premium','Premium / elegant')}${option('clean','Clean / minimal')}${option('corporate','Corporate / restrained')}</select></label>
    <label>Design density<select name="design_density">${option('minimal','Minimal')}${option('standard','Standard',true)}${option('rich','Rich / detailed')}</select></label>
  </div>
  <label class="enhancement-toggle"><input type="checkbox" name="professional_enhancements" checked><span><strong>Professional enhancements</strong><small>Allow Clyp to add purposeful light, gradients, overlays, dividers, badges, frames, motifs and depth.</small></span></label>
  <div class="preference-note" id="preferenceNote">AI choose uses category-aware defaults. Tech, worship, beauty, food and real-estate designs normally receive a relevant visual anchor unless you choose “No imagery”.</div>
  <div class="brief-actions"><button type="button" class="button ghost" data-close>Cancel</button><button class="button" type="submit">Create design</button></div>
</form>`}

function payloadFromForm(form){
  const fd=new FormData(form);
  return {
    brief:String(fd.get('brief')||''),
    format:String(fd.get('format')||''),
    preferences:{
      category:String(fd.get('category')||'auto'),
      visual_mood:String(fd.get('visual_mood')||'auto'),
      imagery_mode:String(fd.get('imagery_mode')||'auto'),
      image_subject:String(fd.get('image_subject')||'auto'),
      colour_style:String(fd.get('colour_style')||'auto'),
      design_density:String(fd.get('design_density')||'standard'),
      professional_enhancements:fd.get('professional_enhancements')==='on'
    }
  };
}
function wireAiForm(){
  const form=document.getElementById('briefForm');
  form.onsubmit=async e=>{
    e.preventDefault();
    const payload=payloadFromForm(e.target);
    const imageChoice=payload.preferences.imagery_mode;
    const asksImage=imageChoice!=='none'&&(imageChoice!=='auto'||/realistic image|realistic photo|photograph|photography|photo of|image of|portrait of|people|person|worshipper|model|illustration|hero image|cinematic|tech event|technology event/i.test(payload.brief||''));
    setModalBusy(asksImage?'Art-directing layout + visual system…':'Designing your first direction…',asksImage?'Clyp is building the editable composition, selecting the right imagery strategy and creating category-aware visual depth.':'Clyp is building hierarchy, colour, typography and editable layers.');
    try{
      const data=await api('/api/ai/generate',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(payload)});
      if(!Array.isArray(data.design?.layers)||!data.design.layers.length)throw new Error('Clyp received an empty design response. V5.2 blocks empty canvases; please retry.');
      const meta={warnings:data.warnings||[],imagery_required:!!data.imagery_required,image_model:data.image_model||'',density:data.density||null,preferences:data.preferences||payload.preferences};
      try{sessionStorage.setItem('clyp:generationMeta',JSON.stringify(meta))}catch{}
      let saved=null;try{saved=ClypStore.save(data.design)}catch{}
      if(saved?.id){location.href='editor.html?id='+encodeURIComponent(saved.id);return}
      try{sessionStorage.setItem('clyp:generatedDesign',JSON.stringify(data.design));location.href='editor.html?mode=ai'}catch{throw new Error('The generated design contains a large embedded image that exceeded browser storage. Try again with online imagery or a smaller local asset.')}
    }catch(err){modalError(err.message,()=>{openModal(aiForm());wireAiForm()})}
  };
}
document.querySelector('[data-action="ai"]').onclick=()=>{openModal(aiForm());wireAiForm()};

document.querySelector('[data-action="upload"]').onclick=()=>openModal(`<div class="brief-form"><span class="kicker">EDIT A FLYER</span><h2>Upload your existing design.</h2><p>Clyp will preserve the source aspect ratio, keep photographs/logos/complex graphics as source image layers, and trace editable text and simple shapes on top.</p><button class="upload-drop" id="pickUpload"><strong>Choose JPG, PNG or PDF</strong><p>Maximum 7 MB in this local build.</p></button></div>`);
modal.addEventListener('click',e=>{if(e.target.closest('#pickUpload'))upload.click()});
function imageDimensions(dataUrl){return new Promise(resolve=>{const img=new Image();img.onload=()=>resolve({width:img.naturalWidth||0,height:img.naturalHeight||0});img.onerror=()=>resolve({width:0,height:0});img.src=dataUrl})}
upload.onchange=async()=>{const file=upload.files[0];if(!file)return;if(file.size>7*1024*1024){modalError('That file is larger than 7 MB.',()=>upload.click());return}const reader=new FileReader();reader.onload=async()=>{setModalBusy('Tracing the source design…','Clyp is preserving complex visuals, source proportions and editable text/shapes.');try{const dims=file.type.startsWith('image/')?await imageDimensions(reader.result):{width:0,height:0};const data=await api('/api/ai/reconstruct',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({data_url:reader.result,filename:file.name,source_width:dims.width,source_height:dims.height})});data.design.assets={...(data.design.assets||{}),source_upload:reader.result};data.design.source={filename:file.name,mime:file.type||'',width:dims.width,height:dims.height};for(const layer of data.design.layers||[]){if(layer.type==='image')layer.asset='source_upload'}try{sessionStorage.setItem('clyp:generatedDesign',JSON.stringify(data.design))}catch{throw new Error('This upload is too large for temporary browser storage in Fast Dev mode. Try a smaller/compressed image for now.')}location.href='editor.html?mode=reconstruct';}catch(err){modalError(err.message,()=>upload.click())}};reader.readAsDataURL(file)};

document.querySelector('[data-action="template"]').onclick=()=>location.href='templates.html';
function formatDate(s){if(!s)return'Just now';const d=new Date(s);return Number.isNaN(d.getTime())?'Just now':new Intl.DateTimeFormat(undefined,{month:'short',day:'numeric',hour:'numeric',minute:'2-digit'}).format(d)}
function renderRecent(){const el=document.getElementById('recentProjects');const projects=ClypStore.list();if(!projects.length){el.innerHTML='<div class="empty-projects"><strong>No designs yet.</strong><span>Create with AI, upload a flyer, or choose a template. Your work saves locally and opens instantly.</span></div>';return}el.innerHTML=projects.slice(0,6).map(p=>`<a class="recent-project" href="editor.html?id=${encodeURIComponent(p.id)}"><div class="project-thumb" style="background:${esc(p.canvas?.bg||'#e6e8ff')}"><div class="mini-title">${esc((p.name||'Untitled').toUpperCase())}</div></div><div class="project-info"><strong>${esc(p.name||'Untitled design')}</strong><small>${formatDate(p.updated_at)} · ${esc(p.format||'1080 × 1350')}</small></div></a>`).join('')}
document.getElementById('refreshProjects').onclick=renderRecent;document.getElementById('todayLabel').textContent=new Intl.DateTimeFormat(undefined,{weekday:'long',day:'numeric',month:'long'}).format(new Date());renderRecent();if(new URLSearchParams(location.search).get('upload')==='1') document.querySelector('[data-action="upload"]').click();
