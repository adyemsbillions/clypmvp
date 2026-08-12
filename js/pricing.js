document.querySelectorAll('[data-checkout]').forEach(btn=>btn.addEventListener('click',()=>{
  const old=btn.textContent;
  btn.textContent='Coming after editor lock-in';
  btn.disabled=true;
  setTimeout(()=>{btn.textContent=old;btn.disabled=false},1800);
}));
