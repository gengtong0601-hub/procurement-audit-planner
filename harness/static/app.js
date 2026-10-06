const $ = id => document.getElementById(id);
let current = null, lastStage = '', renderedRisks = '', polling = null;
const escape = value => String(value ?? '').replace(/[&<>"']/g, c => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
function error(message) { $('error').textContent = message; $('error').hidden = !message; }
async function api(path, options={}) {
  const headers = {'Content-Type':'application/json', ...options.headers};
  if(current) headers['X-Run-Token'] = current.token;
  if($('access').value) headers.Authorization = 'Bearer ' + $('access').value;
  const response = await fetch(path,{...options,headers});
  const data = await response.json();
  if(!response.ok) throw Error(data.error || 'Request failed. Please retry.');
  return data;
}
async function action(button, operation) {
  error(''); button.disabled=true;
  try { await operation(); } catch(e) { error(e.message); }
  finally { button.disabled=false; }
}
$('mode').addEventListener('change',()=>{
  const live=$('mode').value==='live'; $('token-field').hidden=!live;
  $('mode-note').textContent=live?'Runs independent agents through the server’s Claude API account. Model calls incur API usage.':'Uses real, precomputed evidence and prepared judgments. No live Claude calls.';
});
$('start').addEventListener('click',()=>action($('start'),async()=>{
  current=await api('/api/runs',{method:'POST',body:JSON.stringify({mode:$('mode').value})});
  sessionStorage.setItem('audit-run',JSON.stringify(current)); renderedRisks='';
  await refresh(); clearInterval(polling); polling=setInterval(refresh,1800);
}));
function risks(data){
  const signature=JSON.stringify(data.risks);
  if(signature===renderedRisks)return;
  renderedRisks=signature;
  $('risk-count').textContent=data.risks.length+' risks to review';
  $('risks').innerHTML=data.risks.map(r=>`<article class="risk" data-risk="${escape(r.id)}"><div class="risk-heading"><h3><span class="code">${escape(r.id)}</span>${escape(r.title)}</h3><span class="score">${r.computed_score ?? "—"}<small class="muted"> / 25</small></span></div><p>${escape(r.statement)}</p><details><summary>Evidence & rating rationale</summary><p><b>Likelihood ${r.likelihood.score}:</b> ${escape(r.display_likelihood ?? r.likelihood.justification)}</p><p><b>Impact ${r.impact.score}:</b> ${escape(r.display_impact ?? r.impact.justification)}</p><p><b>Proposed focus:</b> ${escape(r.proposed_focus)}</p></details><div class="decision-row"><label>Decision<select class="decision"><option value="">Choose a decision…</option><option value="approve">Approve</option><option value="amend">Amend ratings</option><option value="reject">Reject</option></select></label><label>Reason / reviewer comments<textarea class="comment" placeholder="Required when amending or rejecting"></textarea></label><div class="amend-scores" hidden><label>Likelihood<input class="likelihood" type="number" min="1" max="5" value="${r.likelihood.score}"></label><label>Impact<input class="impact" type="number" min="1" max="5" value="${r.impact.score}"></label></div></div></article>`).join('');
  document.querySelectorAll('.decision').forEach(select=>select.addEventListener('change',()=>{select.closest('.risk').querySelector('.amend-scores').hidden=select.value!=='amend';}));
}
async function refresh(){
  if(!current)return;
  try{
    const data=await api('/api/runs/'+current.id);
    $('setup').hidden=true; $('workspace').hidden=false;
    $('mode-badge').textContent=data.mode==='live'?'LIVE CLAUDE API HARNESS':'PREPARED DEMONSTRATION · NO LIVE CLAUDE';
    const busy=data.stage==='preparing'||(data.stage==='approved'&&data.planning_started);
    $('stage-text').textContent=busy?'Working… your evidence trail updates below.':data.stage.replaceAll('-',' ');
    document.querySelectorAll('#steps>div').forEach(el=>el.classList.toggle('active',el.dataset.stage===data.stage));
    const p=data.population;
    const vals=[['Payments analysed',p.rows_after_exclusions],['Months covered',p.months_covered],['Risks for review',data.risks.length]];
    $('metrics').innerHTML=vals.map(([label,value])=>`<div class="metric"><span>${label}</span><strong>${value==null?'—':Number(value).toLocaleString()}</strong></div>`).join('');
    const unresolved=Object.entries(data.parameters).filter(([key,value])=>value.value==null).map(([key])=>key);
    $('parameter-note').textContent=unresolved.length?'Unresolved statutory parameters: '+unresolved.join(', ')+'. Affected tests remain unavailable; the published local thresholds can still be analysed.':'All configured threshold parameters have values. Review their sources before relying on them.';
    risks(data);
    document.querySelectorAll('.decision-row').forEach(el=>el.hidden=data.stage!=='risk-review');
    $('review-controls').hidden=data.stage!=='risk-review';
    $('plan-controls').hidden=data.stage!=='approved'||Boolean(data.planning_started);
    $('signoff-controls').hidden=data.stage!=='sign-off'; $('complete').hidden=data.stage!=='complete';
    $('events').innerHTML=data.events.map(e=>`<li><b>${escape(e.role)}</b>${escape(e.message)}<br><time>${escape(new Date(e.at).toLocaleTimeString())}</time></li>`).join('');
    $('documents').innerHTML=data.documents.map(name=>`<button data-doc="${escape(name)}">${escape(name)} ↗</button>`).join('');
    document.querySelectorAll('[data-doc]').forEach(b=>b.addEventListener('click',()=>showDocument(b.dataset.doc)));
    if(data.error)error(data.error);
    if(!busy){clearInterval(polling);polling=null;}
    lastStage=data.stage;
  }catch(e){error(e.message);clearInterval(polling);}
}
$('submit-decisions').addEventListener('click',()=>action($('submit-decisions'),async()=>{
  const decisions=[...document.querySelectorAll('.risk')].map(el=>({id:el.dataset.risk,decision:el.querySelector('.decision').value,comment:el.querySelector('.comment').value,likelihood:Number(el.querySelector('.likelihood').value),impact:Number(el.querySelector('.impact').value)}));
  await api(`/api/runs/${current.id}/decisions`,{method:'POST',body:JSON.stringify({reviewer:$('reviewer').value,decisions})});await refresh();
}));
$('build-plan').addEventListener('click',()=>action($('build-plan'),async()=>{
  await api(`/api/runs/${current.id}/plan`,{method:'POST',body:'{}'});await refresh();polling=setInterval(refresh,1800);
}));
$('signoff').addEventListener('click',()=>action($('signoff'),async()=>{
  await api(`/api/runs/${current.id}/signoff`,{method:'POST',body:JSON.stringify({name:$('signer').value})});await refresh();
}));
async function showDocument(name){try{const doc=await api(`/api/runs/${current.id}/documents/${name}`);$('doc-title').textContent=doc.name;$('doc-content').textContent=doc.text;$('document-dialog').showModal();}catch(e){error(e.message);}}
$('close-document').addEventListener('click',()=>$('document-dialog').close());
$('new-review').addEventListener('click',()=>{
  if(current){const previous=JSON.parse(sessionStorage.getItem('audit-run-history')||'[]');previous.push(current);sessionStorage.setItem('audit-run-history',JSON.stringify(previous));}
  clearInterval(polling);polling=null;current=null;renderedRisks='';
  sessionStorage.removeItem('audit-run');error('');$('workspace').hidden=true;$('setup').hidden=false;
});
$('download').addEventListener('click',()=>action($('download'),async()=>{
  const response=await fetch(`/api/runs/${current.id}/download`,{headers:{'X-Run-Token':current.token}});
  if(!response.ok)throw Error('Download unavailable.');
  const url=URL.createObjectURL(await response.blob()),a=document.createElement('a');a.href=url;a.download='audit-planning-pack.zip';a.click();setTimeout(()=>URL.revokeObjectURL(url),1000);
}));
api('/api/config').then(config=>{if(!config.prepared_available){$('start').disabled=true;error('Prepared data is not ready: '+config.missing.join(', '));}if(!config.live_available){$('mode').querySelector('[value="live"]').disabled=true;}}).catch(e=>error(e.message));
try{const saved=sessionStorage.getItem('audit-run');if(saved){current=JSON.parse(saved);refresh();polling=setInterval(refresh,1800);}}catch(e){sessionStorage.removeItem('audit-run');}
