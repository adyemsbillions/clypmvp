const form=document.querySelector('form'),msg=document.getElementById('formMessage');
if(form){
  form.addEventListener('submit',async e=>{
    e.preventDefault();
    const endpoint=form.id==='loginForm'?'api/auth/login.php':'api/auth/register.php';
    const payload=Object.fromEntries(new FormData(form));
    const btn=form.querySelector('button[type=submit]');
    btn.disabled=true;const original=btn.textContent;btn.textContent='Please wait…';
    try{
      const res=await fetch(endpoint,{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(payload)});
      const data=await res.json().catch(()=>({ok:false,message:'Invalid server response'}));
      if(res.ok&&data.ok){
        msg.style.color='#2f7a45';msg.textContent=data.message||'Success';
        setTimeout(()=>location.href='app.html',250);
      }else{
        msg.style.color='#b23d34';msg.textContent=data.message||'Could not continue';
      }
    }catch(err){
      msg.style.color='#b23d34';
      msg.textContent='Could not reach the local PHP server. Start Clyp with python start_local.py.';
    }finally{btn.disabled=false;btn.textContent=original}
  });
}
