const stages=[...document.querySelectorAll('.stage')];
const rail=[...document.querySelectorAll('.rail li')];
const progress=document.getElementById('railProgress');

function activate(i){
  stages.forEach((el,n)=>el.classList.toggle('active',n===i));
  rail.forEach((el,n)=>el.classList.toggle('active',n===i));
  if(progress) progress.style.height=((i/(stages.length-1))*100)+'%';
}

const observer=new IntersectionObserver(entries=>{
  const hit=entries.filter(e=>e.isIntersecting).sort((a,b)=>b.intersectionRatio-a.intersectionRatio)[0];
  if(!hit) return;
  activate(Number(hit.target.dataset.stage)-1);
},{threshold:[.38,.52,.66],rootMargin:'-14% 0px -20% 0px'});

stages.forEach(stage=>observer.observe(stage));
