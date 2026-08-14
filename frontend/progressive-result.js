(function(root){
  'use strict';

  function lineChunks(text, targetCount){
    const lines=String(text||'').match(/[^\n]*\n|[^\n]+$/g)||[];
    const size=Math.max(1,Math.ceil(lines.length/Math.max(1,targetCount||lines.length)));
    const chunks=[];
    for(let i=0;i<lines.length;i+=size) chunks.push(lines.slice(i,i+size).join(''));
    return chunks;
  }

  function reveal(options){
    const target=options.target,fullText=String(options.text||''),status=options.status,skip=options.skip;
    let timer=null,index=0,current='';
    const reduced=!options.forceMotion&&root.matchMedia&&root.matchMedia('(prefers-reduced-motion: reduce)').matches;
    const chunks=lineChunks(fullText,Math.min(42,Math.max(8,fullText.split('\n').length)));
    const interval=Math.max(45,Math.min(230,Math.round(3800/Math.max(chunks.length,1))));
    const finish=()=>{if(timer)root.clearInterval(timer);timer=null;target.textContent=fullText;if(status)status.textContent='Protected document ready';if(skip)skip.hidden=true;target.scrollTop=target.scrollHeight;};
    if(!target)throw new TypeError('A progressive reveal target is required.');
    if(reduced||!chunks.length){finish();return {finish,isComplete:()=>true};}
    current=chunks[index++]||'';target.textContent=current;if(status)status.textContent='Revealing protected document…';if(skip){skip.hidden=false;skip.onclick=finish;}
    target.scrollTop=target.scrollHeight;
    if(index>=chunks.length){finish();return {finish,isComplete:()=>true};}
    timer=root.setInterval(()=>{
      const follow=target.scrollHeight-target.scrollTop-target.clientHeight<90;
      current+=chunks[index++];target.textContent=current;
      if(follow)target.scrollTop=target.scrollHeight;
      if(index>=chunks.length)finish();
    },interval);
    return {finish,isComplete:()=>timer===null};
  }

  root.MedNexusProgressiveResult={lineChunks,reveal};
  if(typeof module!=='undefined'&&module.exports)module.exports=root.MedNexusProgressiveResult;
})(typeof window!=='undefined'?window:globalThis);
