/* Product-facing views. Source facts and membership live in reviewed-data.json. */
function heading(eyebrow,title,description,actions=''){
  return `<div class="page-heading"><div><h1>${title}</h1>${description?`<p>${description}</p>`:''}</div>${actions?`<div class="heading-actions">${actions}</div>`:''}</div>`;
}
function humanEvidenceDate(value){
  const m=String(value||'').match(/\d{4}-\d{2}-\d{2}/);
  return m?new Intl.DateTimeFormat('en-GB',{day:'numeric',month:'short',year:'numeric',timeZone:'UTC'}).format(new Date(m[0]+'T12:00:00Z')):(value||'Not recorded');
}
function targetCard(r){
  const b=r.brief;
  return `<article class="target-card job-card" data-job-card="${r.poolId}">
    <div class="job-card-head">${logo(r)}<div><button class="target-company" data-open="${r.id}">${esc(b.company)}</button><p class="target-role">${esc(b.role)}</p></div><button class="icon-button ${state.bookmarks.has(r.id)?'saved':''}" data-bookmark="${r.id}" aria-label="${state.bookmarks.has(r.id)?'Unsave':'Save'} ${esc(r.company)}" aria-pressed="${state.bookmarks.has(r.id)}">${icon('bookmark')}</button></div>
    <div class="job-card-status">${badge(r.group==='target'?`Priority ${r.priority}`:r.group==='screen'?'Worth screening':'Reserve / stretch',r.group==='target'?'teal':'amber')}${r.applicationPreparation?badge(r.applicationPreparation.ready===false?'Draft needs an answer':'Prepared · not submitted','teal'):''}<span>Open when checked ${niceDate(r.last)}</span></div>
    <p class="job-work">${esc(b.work)}</p>
    <dl class="job-facts"><div><dt>Location</dt><dd>${esc(b.location)}</dd></div><div><dt>Pay</dt><dd>${esc(b.pay.trim())}</dd></div></dl>
    <div class="job-takeaway"><strong>Why it fits</strong><p>${esc(b.fit)}</p></div>
    <div class="job-question"><strong>Before applying</strong><p>${esc(b.question)}</p></div>${r.applicationPreparation?`<div class="job-question"><strong>Application draft</strong><p>${esc(r.applicationPreparation.next_step)}</p></div>`:''}
    <div class="target-footer"><label class="compare-check"><input type="checkbox" data-compare="${r.id}" ${state.compare.includes(r.id)?'checked':''}>Compare</label><button class="text-button" data-open="${r.id}">Full job brief ${icon('arrow')}</button></div>
  </article>`;
}
function nextStepPanel(){
  const n=UI.nextStep;if(!n)return '';
  return `<section class="next-step-panel"><div><span class="tiny-label">${esc(n.label)}</span><h2>${esc(n.title)}</h2><p>${n.html}</p></div><button class="button" ${n.open?`data-open="${esc(n.open)}"`:`data-view="${esc(n.view||'pipeline')}"`}>${esc(n.button||'Review the process')} ${icon('arrow')}</button></section>`;
}
function attentionItems(){
  const items=UI.attention||current().filter(r=>r.owner===UI.self).concat(current().filter(r=>r.owner!==UI.self&&r.stage!=='Applied')).slice(0,3)
    .map(r=>({tone:r.owner===UI.self?'amber':'teal',label:r.owner===UI.self?'Your move':'With them',title:`${r.company}: ${r.stage}`,text:r.nextAction,open:r.id,aria:'Review '+r.company}));
  if(!items.length)return '<p class="detail-summary" data-empty-state="attention">Nothing needs attention yet. Current applications and conversations appear here.</p>';
  return items.map(a=>`<div class="action-summary"><span class="action-label${a.tone?' '+esc(a.tone):''}">${esc(a.label)}</span><div><strong>${esc(a.title)}</strong><p>${esc(a.text)}</p></div><button class="icon-button" ${a.open?`data-open="${esc(a.open)}"`:`data-view="${esc(a.view||'pipeline')}"`} aria-label="${esc(a.aria||'Review')}">${icon('arrow')}</button></div>`).join('\n  ');
}
function overview(){
  const c=DATA.poolCounts;
  return heading('','Your job search',esc(UI.overviewSubtitle||'Snapshot: '+humanEvidenceDate(DATA.asOf)+'.'),`<button class="button" data-action="export">${icon('download')}Export snapshot</button><button class="button primary" data-view="targets">Choose the next application ${icon('arrow')}</button>`)+`
  <div class="stats-grid">${stat('Jobs worth screening',String(c.queue),`${c.priority} priorities · ${c.screening} other options · ${c.reserves} reserves`,'target')}${stat('Submitted applications',String(current().filter(r=>r.stage==='Applied').length),'Waiting for employer updates','briefcase')}${stat('Beyond CV review',esc(UI.beyondStat?.value??String(beyondCv())),esc(UI.beyondStat?.context??'Processes past the application stage'),'checkCircle')}${stat('Your turn',String(current().filter(r=>r.owner===UI.self).length),'Current conversations needing a step or decision','compass')}</div>
  ${nextStepPanel()}
  <section><div class="section-heading"><div><h2>${c.priority?'Start with these priorities':'Next candidates to screen'}</h2><p>A technical match is a reason to ask questions. Pay, contracting and support still need agreement.</p></div><button class="text-button" data-view="targets">All ${c.queue} candidates ${icon('arrow')}</button></div>${targets().length?`<div class="target-grid">${targets().slice(0,3).map(targetCard).join('')}</div>`:'<div class="company-blank" data-empty-state="candidates">No candidate jobs yet. Scout results appear here once the reviewed pool has live, eligible roles.</div>'}${targets().length>3?`<div class="also-next"><span>More candidates: <strong>${targets().slice(3,5).map(r=>esc(r.brief.company)).join(' and ')}</strong>.</span><button class="text-button" data-view="targets">Compare the full next round ${icon('arrow')}</button></div>`:''}</section>
  <div class="overview-bottom"><section class="panel"><div class="panel-heading"><div><h2>What needs attention</h2><p>The next useful step for each process.</p></div></div>
  ${attentionItems()}</section>${pipelinePanel()}</div>
  <div class="reading-note"><strong>How to read this workspace</strong><p>The ${c.queue} candidate jobs have not been applied to. The ${current().length} current applications and conversations are tracked separately. Closed, unverified, paused and excluded jobs stay in the research history.</p><button class="text-button" data-view="sources">See dates and evidence coverage ${icon('arrow')}</button></div>`;
}
function targetView(){
  const c=DATA.poolCounts;
  return `<div class="targets-page">${heading('','Choose your next application','Review the next conditional roles. The full library remains available under All researched jobs.',`<button class="button" data-action="compare-open" ${state.compare.length<2?'disabled':''}>Compare selected ${icon('arrow')}</button>`)}
  <div class="queue-context"><div><strong>${c.queue} open jobs worth screening</strong><p>None has every commercial requirement agreed. “Open” describes the vacancy at the last check.</p></div><button class="text-button" data-view="sources">Dated checks ${icon('arrow')}</button></div>
  <div class="filter-bar target-controls"><div class="filter-pills">${[['target','Start here',c.priority],['screen','Other candidates',c.screening],['reserve','Reserves & stretches',c.reserves]].map(([key,label,n])=>`<button class="filter-pill ${state.targetGroup===key?'active':''}" data-target-group="${key}" aria-pressed="${state.targetGroup===key}">${label}<span>${n}</span></button>`).join('')}</div><label class="target-search">${icon('search')}<input class="input" id="target-search" type="search" placeholder="Find a candidate…" aria-label="Search candidate jobs" value="${esc(state.targetQuery)}"></label></div>
  <div id="candidate-results">${candidateResults()}</div>
  <section class="audit-section"><div class="section-heading"><div><h2>Why the other ${c.audit_only} jobs are outside this round</h2><p>They remain in the research pool, with a reason and a condition for reconsidering them.</p></div></div>${auditGroups()}</section></div>`;
}
function candidateResults(){
  const rows=DATA.opportunities.filter(r=>r.group===state.targetGroup&&(!state.targetQuery||[r.company,r.role,...Object.values(r.brief)].join(' ').toLowerCase().includes(state.targetQuery.toLowerCase())));
  const intro={target:'The strongest starting points for a short, practical conversation.',screen:'Conditional discussions with specific technical, location or commercial questions.',reserve:'Live alternatives with extra technical, seniority or process tradeoffs. Keep the effort proportionate.'};
  return `<p class="candidate-intro">${intro[state.targetGroup]}</p>${rows.length?`<div class="target-grid">${rows.map(targetCard).join('')}</div>`:'<div class="company-blank">No candidates match this search in the selected group.</div>'}<p class="result-count">${rows.length} shown · ${DATA.poolCounts.queue} candidates across the queue groups</p>`;
}
function auditGroups(){
  const groups=[['Applied','Already applied','These roles are tracked under applications and conversations. No reapplication.'],['Risk hold','Paused for company concerns','Review the company and project risks before investing more time.'],['Unverified','Needs a fresh vacancy check','Access failures and uncertain role mappings are not proof a vacancy is open.'],['Exclude current role','Does not fit this search','These exact roles conflict with location, technical scope or seniority requirements.'],['Vacancy closed','Closed original vacancies','No application to these requisitions. A replacement needs its own verification.']];
  const queued=new Set(DATA.opportunities.filter(r=>r.poolId).map(r=>r.poolId));
  for(const key of new Set(DATA.poolAudit.filter(j=>!queued.has(j.poolId)).map(j=>j.bucket)))if(!groups.some(g=>g[0]===key))groups.push([key,key,'Retained history; see the specific reason and next action.']);
  return groups.map(([key,label,description])=>{const rows=DATA.poolAudit.filter(j=>j.bucket===key&&!queued.has(j.poolId));return `<details class="audit-group" data-audit-bucket="${esc(key)}"><summary><span>${label}<small>${description}</small></span><span class="audit-count">${rows.length}</span></summary><div class="audit-list">${rows.map(j=>`<article><div><button class="audit-company" data-pool-record="${j.poolId}">${esc(j.brief.company)}</button><p class="small muted">${esc(j.brief.role)}</p></div><p>${esc(j.brief.watch)}</p><button class="text-button" data-pool-record="${j.poolId}">Read context ${icon('arrow')}</button></article>`).join('')}</div></details>`;}).join('');
}
function filteredOpportunities(){
  return DATA.opportunities.filter(r=>(state.scope==='all'?(!r.poolId||!!state.query):r.group===state.scope)&&(state.stage==='all'||r.stage===state.stage)&&(!state.query||[r.company,r.role,r.summary,r.notes,r.pay,...r.tags].join(' ').toLowerCase().includes(state.query.toLowerCase())));
}
function opportunityTable(rows){
  return `<div class="table-wrap"><table class="human-pipeline"><thead><tr><th>Company & role</th><th>Where it stands</th><th>Next useful step</th><th>Last update</th><th></th></tr></thead><tbody>${rows.map(r=>`<tr><td><div class="company-cell">${logo(r)}<button data-open="${r.id}"><strong>${esc(r.brief?.company||r.company)}</strong><small>${esc(r.brief?.role||r.role)}</small></button></div></td><td>${pillStage(r)}<p class="small muted status-context">${esc(r.owner===UI.self?'Your step or decision':({Them:'Waiting for their update',Hold:'Paused until you resume',None:'No action pending'})[r.owner]||r.owner)}</p></td><td class="next-cell">${esc(r.brief?.question||r.nextAction)}</td><td class="age">${niceDate(r.last)}<br><span class="small">${r.last.slice(0,4)}</span></td><td><button class="icon-button" data-open="${r.id}" aria-label="Open ${esc(r.company)}">${icon('arrow')}</button></td></tr>`).join('')}</tbody></table></div>`;
}
function companyView(){
  return heading('','Know the company behind the role','Employer, agency and client are separate checks. Missing evidence stays visible.')+`<div class="queue-context"><div><strong>${DATA.companies.length} dated company and agency checks</strong><p>Research coverage varies. These are evidence summaries, not credit ratings or guarantees.</p></div><label class="target-search">${icon('search')}<input class="input" type="search" id="company-search" aria-label="Search company checks" placeholder="Find a company…" value="${esc(state.companyQuery)}"></label></div><div id="company-results">${companyResults()}</div>`;
}
function companyResults(){
  const rows=DATA.companies.filter(c=>[c.company,c.main_risk,c.judgement].join(' ').toLowerCase().includes(state.companyQuery.toLowerCase()));
  return rows.length?`<div class="company-grid">${rows.map(c=>{const jobs=DATA.poolAudit.filter(j=>j.companyId===c.id);const queued=jobs.filter(j=>DATA.opportunities.some(r=>r.poolId===j.poolId));return `<article class="company-card"><div class="company-card-top">${logo({company:c.company,companyId:c.id})}<div><h3>${esc(c.company)}</h3><p>See dated dossier for check dates</p></div></div><span class="company-reading">${queued.length?'A candidate in your next round':jobs.length?'Retained in the research pool':'Application / recruiter context'}</span><div class="job-takeaway"><strong>Main point before proceeding</strong><p>${esc(c.readableSummary)}</p></div><div class="company-card-foot"><span>${c.sources.length} linked sources · partial coverage</span><button class="text-button" data-company="${c.id}">Read company brief ${icon('arrow')}</button></div></article>`;}).join('')}</div>`:'<div class="company-blank">No company checks match this search.</div>';
}
function researchView(){
  const rows=researchRows(),page=rows.slice(state.researchPage*20,state.researchPage*20+20),choices=[...new Set(DATA.research.map(r=>r.decision))].filter(Boolean).sort();
  return heading('','All researched jobs','The complete register includes old vacancies and unsuitable roles. Start with Next applications for the current candidate list.')+`<div class="filter-bar"><span class="inline-field">${DATA.research.length} historical and current records · original check dates preserved</span><div class="filter-right"><input class="input" type="search" id="research-search" placeholder="Search company, role or concern…" aria-label="Search research archive" value="${esc(state.researchQuery)}"><select class="select" id="research-decision" aria-label="Research decision"><option value="all">All original research decisions</option>${choices.map(c=>`<option ${state.researchDecision===c?'selected':''}>${esc(c)}</option>`).join('')}</select></div></div><div id="research-results">${researchTable(page)}${pagination(rows.length,state.researchPage,20,'research')}</div>`;
}
function readingForResearch(r){
  const j=DATA.poolAudit.find(j=>j.poolId===r.poolId);
  if(j)return {label:({'Applied':'Application submitted','Priority screen':'Priority candidate','Screen first':'Other candidate','Reserve / stretch':'Reserve / stretch','Risk hold':'Company concerns','Unverified':'Needs verification','Exclude current role':'Outside current criteria','Vacancy closed':'Vacancy closed'})[j.bucket],detail:j.brief.watch,tone:['Priority screen','Screen first'].includes(j.bucket)?'teal':'',date:j.appliedDate||j.checkedAt.slice(0,10)};
  if(/rejected/i.test(r.applicationState))return {label:'Application rejected',detail:r.nextAction||'Retained as application history.',tone:'',date:r.checked};
  if(/submitted|applied/i.test(r.applicationState)&&!/not applied|never submitted|unsubmitted/i.test(r.applicationState))return {label:'Application at this company',detail:r.nextAction||'See applications and conversations for the process.',tone:'blue',date:r.checked};
  return {label:/closed/i.test(r.decision+' '+r.disposition)?'Historical closed vacancy':'Historical research',detail:r.risk,date:r.checked,tone:''};
}
function researchTable(rows){
  return rows.length?`<div class="table-wrap"><table class="research-table"><thead><tr><th>Company & role</th><th>How to read this record</th><th>Main point</th><th>Evidence date</th><th></th></tr></thead><tbody>${rows.map(r=>{const x=readingForResearch(r),j=DATA.poolAudit.find(j=>j.poolId===r.poolId);return `<tr><td class="research-name"><strong>${esc(j?.brief.company||r.company)}</strong><p>${esc(j?.brief.role||r.role)}</p></td><td>${badge(x.label,x.tone)}<p class="small muted status-context">${esc(j?.brief.location||r.location||'Location requires checking')}</p></td><td class="research-risk">${esc(x.detail)}</td><td class="check-age">${esc(humanEvidenceDate(x.date))}</td><td><button class="icon-button" data-research="${r.id}" aria-label="Read ${esc(r.company)} research">${icon('arrow')}</button></td></tr>`;}).join('')}</tbody></table></div>`:empty('No matching research','Try a broader term or a different decision.');
}
function sourceView(){
  return heading('','Where this picture comes from','A dated workspace built from the personal tracker, job postings, application evidence and company research.',`<a class="button" href="${esc(DATA.sheetUrl)}" target="_blank" rel="noopener">Open Google tracker ${icon('external')}</a>`)+`
  <div class="source-date-panel">${(UI.sourcePanels||[{title:'Job-pool snapshot',date:humanEvidenceDate(DATA.asOf)+' · per-role dates',text:`${DATA.poolCounts.pool} original vacancies reviewed; ${DATA.poolCounts.queue} retained as screening candidates.`},{title:'Tracker readback',date:humanEvidenceDate(DATA.sheetReadAt),text:'Operational tracker tabs captured for this build. The page does not reconnect when opened.'}]).map(p=>`<div><strong>${esc(p.title)}</strong><span>${esc(p.date)}</span><p>${esc(p.text)}</p></div>`).join('')}</div>
  <section class="panel"><div class="panel-heading"><div><h2>What is covered — and where gaps remain</h2><p>Access gaps limit the conclusion. They do not mean an application or vacancy has closed.</p></div></div><div class="coverage-list">${DATA.coverage.map(c=>`<div class="coverage-item"><h3>${esc(c.name)}</h3>${badge(c.state==='Read'?'Checked':c.state==='Partial'?'Partial research':'Access needed',c.state==='Blocked'?'amber':c.state==='Partial'?'blue':'teal')}<p>${esc(c.detail.replaceAll('All36','All 36'))}</p><small>${esc(c.date)}</small></div>`).join('')}</div></section>
  <section class="working-evidence"><h2>Read the full context</h2><div class="evidence-links">${DATA.sources.map(([title,url,detail],i)=>i<2?`<button class="source-link source-document-button" data-document="${i===0?'status':'plan'}">${icon('archive')}<div><strong>${esc(title)}</strong><p>${esc(detail)}</p></div></button>`:`<a class="source-link" href="${esc(safeUrl(url))}" target="_blank" rel="noopener">${icon('external')}<div><strong>${esc(title)}</strong><p>${esc(detail)}</p></div></a>`).join('')}</div></section>
  <details class="supporting-detail"><summary>Application records <span>${DATA.applicationDocs.length} dossiers</span></summary><div class="application-library">${DATA.applicationDocs.map((d,i)=>`<button class="application-doc" data-application="${i}">${icon('archive')}<span>${esc(d.title)}</span>${icon('arrow')}</button>`).join('')}</div></details>
  <details class="supporting-detail"><summary>Tracker corrections and publication details <span>Supporting audit</span></summary><p class="detail-summary">${DATA.updates.length} earlier application-status corrections are retained as history. The current pool revision is <code>${esc(DATA.publicationRevision)}</code>.</p><div class="pending-list">${DATA.updates.map(u=>`<button class="pending-item" data-update="${u.number}"><span class="pending-number">${String(u.number).padStart(2,'0')}</span><span>${esc(u.title)}</span>${icon('arrow')}</button>`).join('')}</div></details>
  <details class="supporting-detail"><summary>Inspect the spreadsheet snapshot <span>${DATA.sourceTabs.length} captured tabs</span></summary><p class="detail-summary">The five operational tabs were read back ${humanEvidenceDate(DATA.sheetReadAt)}. Other tabs retain their earlier capture dates. This page does not reconnect to Google when opened.</p><div class="source-controls"><label>Tab<select class="select" id="source-tab">${DATA.sourceTabs.map(t=>`<option ${t.name===state.sourceTab?'selected':''}>${esc(t.name)}</option>`).join('')}</select></label><input class="input" type="search" id="source-search" aria-label="Search selected sheet tab" placeholder="Search this tab…" value="${esc(state.sourceQuery)}"></div><div id="source-results">${sourceTable()}</div></details>`;
}
function detailOverview(r){
  if(!r.brief)return processOverview(r);
  const b=r.brief;
  return `<div class="detail-next"><div class="eyebrow">FIRST QUESTION TO RESOLVE</div><p>${esc(b.question)}</p></div>
    <div class="brief-points"><section><h3>The work</h3><p>${esc(b.work)}</p></section><section><h3>Why it is on your list</h3><p>${esc(b.fit)}</p></section><section class="watch-point"><h3>What could block it</h3><p>${esc(b.watch)}</p></section></div>
    <section class="detail-section"><h3>The practical picture</h3><div class="practical-summary"><div><span>Location</span><strong>${esc(b.location)}</strong></div><div><span>Published pay</span><strong>${esc(b.pay.trim())}</strong></div></div><p class="terms-context">${esc(UI.termsContext||'Published salary and contractor invoicing are different. A published range does not establish an approved package for your location.')}</p><div class="gate-grid">${(UI.gates||[]).map(g=>`<div class="gate-box ${r.gates[g.label]==='confirmed'?'supported':'unknown'}">${esc(g.title)}<strong>${esc(r.gates[g.label]==='confirmed'?g.confirmed:'Still to confirm')}</strong></div>`).join('')}</div></section>
    <details class="supporting-detail exact-terms"><summary>Full advert terms and screening context</summary><dl class="readable-terms">${[['Exact advertised role',r.role],['Location wording',r.advert.location],['Contract wording',r.advert.contract],['Hours and support',r.advert.hours],['Published pay wording',r.advert.pay],['Technical requirements',Array.isArray(r.advert.requirements)?r.advert.requirements.join(' · '):r.advert.requirements],['Full screening question',r.nextAction]].map(([key,value])=>`<div><dt>${key}</dt><dd>${esc(value)}</dd></div>`).join('')}</dl></details>
    <section class="detail-section"><h3>Company background in one point</h3><p class="detail-summary">${esc(firm(r.companyId)?.readableSummary||'Company evidence remains incomplete.')}</p><button class="text-button" style="margin-top:12px" data-detail-tab="background">Read the company brief ${icon('arrow')}</button></section>`;
}
function renderDetail(r){
  const c=firm(r.companyId),b=r.brief;
  $('#detail-dialog').innerHTML=`<div class="detail-top"><span class="eyebrow">${b?'JOB BRIEF':'APPLICATION / CONVERSATION'}</span><div class="detail-actions"><button class="icon-button ${state.bookmarks.has(r.id)?'saved':''}" data-bookmark="${r.id}" aria-label="${state.bookmarks.has(r.id)?'Unsave':'Save'} ${esc(r.company)}" aria-pressed="${state.bookmarks.has(r.id)}">${icon('bookmark')}</button><button class="icon-button" data-close="detail-dialog" aria-label="Close details">${icon('close')}</button></div></div><div class="detail-body"><div class="detail-company">${logo(r,true)}<div><h2 id="detail-title">${esc(b?.company||r.company)}</h2><p>${esc(b?.role||r.role)}</p></div></div><div class="detail-meta">${b?badge(r.group==='target'?'Priority candidate':r.group==='screen'?'Other candidate':'Reserve / stretch','teal'):pillStage(r)}${badge(b?'Vacancy checked '+niceDate(r.last):'Last update '+niceDate(r.last))}</div>${!b?`<p class="detail-summary">${esc(r.summary||r.nextAction)}</p>`:''}<div class="detail-tabs" role="tablist" aria-label="Opportunity details">${[['overview','Job & next step'],['background','Company background'],['evidence','Evidence & notes']].map(([id,label])=>`<button class="detail-tab ${state.detailTab===id?'active':''}" data-detail-tab="${id}" role="tab" id="detail-tab-${id}" aria-selected="${state.detailTab===id}" aria-controls="detail-panel">${label}</button>`).join('')}</div><div id="detail-panel" role="tabpanel" aria-labelledby="detail-tab-${state.detailTab}">${state.detailTab==='overview'?detailOverview(r):state.detailTab==='background'?detailCompany(c,r):detailEvidence(r)}</div></div>`;
}
function companyBrief(c,r){
  const chunks=c.body.split(/^## /m).slice(1).map(x=>({title:x.split('\n')[0],text:x.slice(x.indexOf('\n')+1).trim()}));
  const identity=chunks.find(x=>/identity|product|company overview/i.test(x.title));
  const questions=chunks.find(x=>/before proceeding|questions|recommendation/i.test(x.title));
  return `<div class="company-brief-lead"><span class="tiny-label">WHAT MATTERS FOR YOUR DECISION</span><p>${esc(c.readableSummary)}</p><div class="brief-meta">Checked ${humanEvidenceDate(c.checked_at)} · ${c.sources.length} linked sources · partial evidence</div></div>
    ${identity?`<section class="detail-section"><h3>Who they are</h3><div class="dossier">${markdown(identity.text.split('\n\n')[0],c.dossierUrl)}</div></section>`:''}
    <section class="detail-section"><h3>Before committing time</h3>${questions?`<div class="dossier">${markdown(questions.text,c.dossierUrl)}</div>`:`<p class="detail-summary">${esc(r?.brief?.question||r?.nextAction||UI.companyQuestionFallback||'Establish the actual employer and client, current project funding, location terms, working hours and payment protections. The full research below records what could and could not be verified.')}</p>`}</section>
    ${Object.hasOwn(UI.intermediaries||{},c.id)?(i=>`<div class="reading-note"><strong>${esc(i.title||'There is also an intermediary')}</strong><p>${esc(i.text)}</p><button class="text-button" data-company="${esc(i.company)}">${esc(i.button||'Read the intermediary check ↗')}</button></div>`)(UI.intermediaries[c.id]):''}
    <details class="supporting-detail"><summary>Evidence, reputation and unresolved questions <span>Full dated research</span></summary><div class="dossier">${markdown(c.body,c.dossierUrl)}</div></details>
    <div class="detail-evidence">${link('Open original company research',c.dossierUrl)}</div>`;
}
function detailCompany(c,r){return c?companyBrief(c,r):`<div class="detail-section company-blank">A current company brief is not attached to ${esc(r.company)}. Missing research does not establish low risk.</div>`;}
function openCompany(id){
  const c=firm(id);if(!c)return;
  const r=DATA.opportunities.find(r=>r.companyId===id);
  if(r){openOpportunity(r.id,'background');return;}
  state.detailId=null;
  $('#detail-dialog').innerHTML=`<div class="detail-top"><span class="eyebrow">COMPANY BRIEF</span><button class="icon-button" data-close="detail-dialog" aria-label="Close company check">${icon('close')}</button></div><div class="detail-body"><h2 id="detail-title">${esc(c.company)}</h2>${companyBrief(c,null)}</div>`;
  openDialog($('#detail-dialog'));
}
function openPoolRecord(id){
  const candidate=DATA.opportunities.find(r=>r.poolId===id||r.researchPoolId===id);if(candidate){openOpportunity(candidate.id);return;}
  const j=DATA.poolAudit.find(j=>j.poolId===id);if(!j)return;
  state.detailId=null;
  const labels={'Risk hold':'Paused for company concerns','Unverified':'Needs a fresh vacancy check','Exclude current role':'Outside current search criteria','Vacancy closed':'Original vacancy closed'};
  $('#detail-dialog').innerHTML=`<div class="detail-top"><span class="eyebrow">RESEARCH CONTEXT · OUTSIDE THIS ROUND</span><button class="icon-button" data-close="detail-dialog" aria-label="Close research context">${icon('close')}</button></div><div class="detail-body"><h2 id="detail-title">${esc(j.brief.company)}</h2><p class="detail-summary">${esc(j.brief.role)}</p><div class="detail-meta">${badge(labels[j.bucket],'amber')}${badge('Source state: '+j.verificationState)}</div><div class="detail-next"><div class="eyebrow">WHY IT IS NOT IN THE APPLICATION QUEUE</div><p>${esc(j.brief.watch)}</p></div><div class="brief-points"><section><h3>What the role involved</h3><p>${esc(j.brief.work)}</p></section><section><h3>What would need to change</h3><p>${esc(j.brief.question)}</p></section></div><details class="supporting-detail"><summary>Original research wording</summary><p class="detail-summary">${esc(j.nextAction)}</p></details><section class="detail-section"><h3>Company context</h3><p class="detail-summary">${esc(firm(j.companyId)?.readableSummary||'No complete company clearance is established.')}</p><button class="text-button" data-company="${j.companyId}">Read the company check ${icon('arrow')}</button></section><div class="detail-evidence">${link('Original role — may be unavailable',j.sourceUrl)}</div></div>`;
  openDialog($('#detail-dialog'));
}
function inlineMarkdown(text,base=UI.companiesBase||''){
  const links=[];
  text=text.replace(/\[([^\]]+)\]\(([^\s]+?)\)/g,(_,label,url)=>{let resolved='#';try{resolved=safeUrl(new URL(url,new URL(base,location.href)).href);}catch{}const token=`LINKTOKEN${links.length}END`;links.push(`<a href="${esc(resolved)}" target="_blank" rel="noopener noreferrer">${esc(label)}</a>`);return token;});
  return esc(text).replace(/\*\*(.+?)\*\*/g,'<strong>$1</strong>').replace(/`([^`]+)`/g,'<code>$1</code>').replace(/LINKTOKEN(\d+)END/g,(_,i)=>links[Number(i)]||'');
}
function markdown(text,base=UI.companiesBase||''){
  const lines=(text||'').split('\n');let out='',list=null,inCode=false,code=[];
  const closeList=()=>{if(list){out+=`</${list}>`;list=null;}};
  const tableCells=line=>line.trim().replace(/^\||\|$/g,'').split('|').map(x=>x.trim());
  for(let i=0;i<lines.length;i++){
    const line=lines[i];
    if(/^```/.test(line)){closeList();if(inCode){out+=`<pre class="formatted-code"><code>${esc(code.join('\n'))}</code></pre>`;code=[];}inCode=!inCode;continue;}
    if(inCode){code.push(line);continue;}
    if(/^# /.test(line)||/^\s*[-*]{3,}\s*$/.test(line))continue;
    if(line.includes('|')&&i+1<lines.length&&/^\s*\|?\s*:?-{3,}/.test(lines[i+1])){
      closeList();const headers=tableCells(line),rows=[];i+=2;
      while(i<lines.length&&lines[i].includes('|')&&lines[i].trim()){rows.push(tableCells(lines[i]));i++;}i--;
      out+=`<div class="table-wrap document-table"><table><thead><tr>${headers.map(h=>`<th>${inlineMarkdown(h,base)}</th>`).join('')}</tr></thead><tbody>${rows.map(r=>`<tr>${headers.map((_,n)=>`<td>${inlineMarkdown(r[n]||'',base)}</td>`).join('')}</tr>`).join('')}</tbody></table></div>`;continue;
    }
    const bullet=/^\s*[-+] (.+)$/.exec(line),ordered=/^\s*\d+\. (.+)$/.exec(line);
    if(bullet||ordered){const tag=bullet?'ul':'ol';if(list!==tag){closeList();out+=`<${tag}>`;list=tag;}out+=`<li>${inlineMarkdown((bullet||ordered)[1],base)}</li>`;continue;}
    closeList();
    if(/^### /.test(line))out+=`<h3>${inlineMarkdown(line.slice(4),base)}</h3>`;
    else if(/^## /.test(line))out+=`<h2>${inlineMarkdown(line.slice(3),base)}</h2>`;
    else if(/^> /.test(line))out+=`<blockquote>${inlineMarkdown(line.slice(2),base)}</blockquote>`;
    else if(line.trim())out+=`<p>${inlineMarkdown(line,base)}</p>`;
  }
  closeList();if(inCode)out+=`<pre class="formatted-code"><code>${esc(code.join('\n'))}</code></pre>`;
  return out;
}
function openDocument(kind,index){
  const app=kind==='application'?DATA.applicationDocs[index]:null;
  const title=app?app.title:kind==='status'?'Current applications and conversations':'Next-application plan';
  const body=app?app.body:kind==='status'?DATA.statusDocument:DATA.planDocument;
  const url=app?app.path:kind==='status'?UI.statusDocumentUrl||'#':UI.planDocumentUrl||'#';
  state.detailId=null;
  $('#detail-dialog').innerHTML=`<div class="detail-top"><span class="eyebrow">FULL CONTEXT · DATED RESEARCH</span><button class="icon-button" data-close="detail-dialog" aria-label="Close source document">${icon('close')}</button></div><div class="detail-body"><h2 id="detail-title">${esc(title.replace(/^# /,''))}</h2><div class="detail-evidence" style="margin:16px 0">${link('Open original document',url)}</div><div class="dossier formatted-document">${markdown(body,url)}</div></div>`;
  openDialog($('#detail-dialog'));
}
function openResearch(id){
  const r=DATA.research.find(r=>r.id===id);if(!r)return;
  if(r.poolId){openPoolRecord(r.poolId);return;}
  const reading=readingForResearch(r);state.detailId=null;
  $('#detail-dialog').innerHTML=`<div class="detail-top"><span class="eyebrow">RESEARCH HISTORY</span><button class="icon-button" data-close="detail-dialog" aria-label="Close research">${icon('close')}</button></div><div class="detail-body"><h2 id="detail-title">${esc(r.company)}</h2><p class="detail-summary">${esc(r.role)}</p><div class="detail-meta">${badge(reading.label,reading.tone)}${badge('Original evidence: '+humanEvidenceDate(r.checked))}</div><div class="detail-next"><div class="eyebrow">HOW TO READ THIS RECORD</div><p>${esc(reading.detail)}</p></div><dl class="readable-terms">${[['Application evidence',r.applicationState||'No submission evidence'],['Next step',r.nextAction||'Recheck before considering an application'],['Work and technical scope',r.tech],['Why it was considered',r.why],['Published pay',r.pay||'Not published'],['Country and contract',[r.location,r.model,r.contract].filter(Boolean).join(' · ')],['Support and on-call',r.oncall||'Not stated']].map(([key,v])=>`<div><dt>${key}</dt><dd>${esc(v)}</dd></div>`).join('')}</dl><details class="supporting-detail"><summary>Original research assessment</summary><p class="detail-summary">${esc(r.decision)} · technical fit ${esc(r.fit||'not scored')}. This was a research aid, not a hiring probability or application status.</p></details><div class="detail-evidence">${link('Original tracker row',r.source)}</div></div>`;
  openDialog($('#detail-dialog'));
}
function insights(){
  const INS=UI.insights||{},c=DATA.poolCounts,curr=current(),stages=['Applied','Recruiter lead','Technical interview expected','Task submitted'];
  const parts=[['Applied','Submitted applications',c.buckets.Applied||0,'pool-priority'],['Priority screen','Start here',c.priority,'pool-priority','target'],['Screen first','Other candidates',c.screening,'pool-screen','screen'],['Reserve / stretch','Reserves / stretches',c.reserves,'pool-reserve','reserve'],['Risk hold','Company concerns',c.buckets['Risk hold']||0,'pool-hold'],['Unverified','Needs verification',c.buckets.Unverified||0,'pool-unknown'],['Exclude current role','Outside criteria',c.buckets['Exclude current role']||0,'pool-excluded'],['Vacancy closed','Closed originals',c.buckets['Vacancy closed']||0,'pool-closed']];
  const inventory=[['current','Current processes'],['older','Older conversations'],['hold','Paused by you'],['platform','Platform review'],['closed','Rejected applications'],['archived','Portal archived'],['declined','Not pursuing']].map(([group,label])=>[label,DATA.opportunities.filter(r=>r.group===group).length]);
  const max=Math.max(...stages.map(s=>curr.filter(r=>r.stage===s).length),1);
  return heading('','Understand the whole search','Candidate jobs, submitted applications and older conversations are different populations.')+`
  <section class="panel pool-composition"><div class="panel-heading"><div><h2>What happened to the ${c.pool} reviewed roles?</h2><p>${c.queue} are still worth screening. The remaining ${c.audit_only} have a documented reason to stay outside this round.</p></div></div><div class="pool-stack" role="img" aria-label="${parts.map(x=>x[1]+': '+x[2]).join(', ')}">${parts.map(([,label,n,cls])=>`<span class="${cls}" style="flex:${n}" title="${esc(label)}: ${n}"></span>`).join('')}</div><div class="pool-legend">${parts.map(([bucket,label,n,cls,group])=>`<button ${group?`data-insight-group="${group}"`:`data-audit-bucket="${esc(bucket)}"`}><i class="${cls}"></i><span>${label}</span><strong>${n}</strong>${icon('arrow')}</button>`).join('')}</div><p class="metric-note">These categories describe one research snapshot. They are not stages of a conversion funnel or a prediction of offers.</p></section>
  <div class="insight-grid" style="margin-top:24px"><section class="panel insight-card"><h2>Where the ${curr.length} current processes stand</h2><div class="horizontal-bars">${stages.map(s=>{const n=curr.filter(r=>r.stage===s).length;return `<div class="bar-line"><span>${s==='Technical interview expected'?'Technical interview expected':s==='Applied'?'Applications sent':s==='Recruiter lead'?'Recruiter conversations':s}</span><div class="bar-track"><div class="bar-fill" style="width:${n/max*100}%"></div></div><strong>${n}</strong></div>`;}).join('')}</div><p class="metric-note">${esc(INS.stagesNote||'Stages reflect the latest verified evidence for each process, not a prediction of offers.')}</p></section>
  <section class="panel insight-card"><h2>Who has the next step?</h2><div class="owner-summary"><div><strong>${curr.filter(r=>r.owner===UI.self).length}</strong><span>With you</span><p>${esc(INS.selfNote||'Replies, decisions or preparation that are your step.')}</p></div><div><strong>${curr.filter(r=>r.owner==='Them').length}</strong><span>With them</span><p>${esc(INS.themNote||'Employer updates, task feedback or a concrete project match.')}</p></div></div>${INS.ownerNote?`<p class="metric-note">${esc(INS.ownerNote)}</p>`:''}</section>
  <section class="panel insight-card"><h2>Application waiting time</h2><div class="waiting-cohorts">${(INS.waitingCohorts||[...new Set(curr.filter(r=>r.stage==='Applied').map(r=>r.last))].sort().reverse().slice(0,4).map(d=>[d,new Intl.DateTimeFormat('en-GB',{day:'numeric',month:'long',timeZone:'UTC'}).format(new Date(d+'T12:00:00Z'))])).map(([date,label])=>{const n=curr.filter(r=>r.stage==='Applied'&&r.last===date).length;return `<div><strong>${n}</strong><span>applications sent ${label}</span><small>${dayAge(date)} calendar days as of ${humanEvidenceDate(DATA.asOf)}</small></div>`;}).join('')}</div>${curr.some(r=>r.stage==='Applied')?'':'<p class="small muted">No submitted applications yet.</p>'}<p class="metric-note">${esc(INS.waitingNote||'Calendar days since each application was sent. Waiting time alone does not mean a rejection.')}</p></section>
  <section class="panel insight-card"><h2>Keep the history in context</h2><div class="inventory-breakdown">${inventory.map(([label,n])=>`<div><span>${label}</span><strong>${n}</strong></div>`).join('')}</div><p class="metric-note">Candidate jobs are counted separately. An older conversation does not establish an open vacancy or a submitted application.</p></section></div>`;
}
