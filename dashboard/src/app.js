'use strict';
const $ = (s, root=document) => root.querySelector(s);
const $$ = (s, root=document) => [...root.querySelectorAll(s)];
const esc = v => String(v ?? '').replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
const icons = {
  grid:'<rect x="3" y="3" width="7" height="7" rx="1.5"/><rect x="14" y="3" width="7" height="7" rx="1.5"/><rect x="3" y="14" width="7" height="7" rx="1.5"/><rect x="14" y="14" width="7" height="7" rx="1.5"/>',
  pipeline:'<rect x="3" y="4" width="5" height="16" rx="1"/><rect x="10" y="4" width="5" height="11" rx="1"/><rect x="17" y="4" width="4" height="14" rx="1"/>',
  target:'<circle cx="12" cy="12" r="8"/><circle cx="12" cy="12" r="4"/><path d="m12 12 8-8m-4 0h4v4"/>',
  company:'<path d="M4 21V5l9-2v18M13 8h7v13M2 21h20M7 7v1m3-2v1M7 11v1m3-2v1m-3 4v1m3-2v1m6-5v1m0 3v1"/>',
  archive:'<rect x="3" y="3" width="18" height="4" rx="1"/><path d="M5 7v13h14V7m-10 4h6"/>',
  chart:'<path d="M4 3v17h17M8 16V9m5 7V5m5 11v-5"/>',
  database:'<ellipse cx="12" cy="5" rx="8" ry="3"/><path d="M4 5v7c0 4 16 4 16 0V5M4 12v6c0 4 16 4 16 0v-6"/>',
  search:'<circle cx="10.5" cy="10.5" r="6.5"/><path d="m16 16 4 4"/>',
  chevronDown:'<path d="m7 10 5 5 5-5"/>',arrow:'<path d="M4 12h15m-6-6 6 6-6 6"/>',external:'<path d="M14 3h7v7m0-7L10 14M10 4H4v16h16v-6"/>',
  calendar:'<rect x="3" y="5" width="18" height="16" rx="2"/><path d="M7 3v4m10-4v4M3 11h18m-13 4h3"/>',
  check:'<path d="m5 12 4 4L19 6"/>',checkCircle:'<circle cx="12" cy="12" r="9"/><path d="m8 12 3 3 5-6"/>',
  clock:'<circle cx="12" cy="12" r="9"/><path d="M12 7v5l3 2"/>',
  alert:'<path d="m12 3 10 18H2L12 3Z"/><path d="M12 9v5m0 3v.2"/>',
  bookmark:'<path d="M6 3h12v18l-6-4-6 4V3Z"/>',briefcase:'<rect x="3" y="7" width="18" height="13" rx="2"/><path d="M8 7V4h8v3M3 12c6 3 12 3 18 0m-9 0v4"/>',
  close:'<path d="m6 6 12 12M6 18 18 6"/>',list:'<path d="M8 5h13M8 12h13M8 19h13M3 5h.1M3 12h.1M3 19h.1"/>',
  pin:'<path d="m14 3 7 7-4 1-4 5-3-2-6 7 5-8-2-3 6-4 1-3Z"/>',
  copy:'<rect x="8" y="8" width="13" height="13" rx="2"/><path d="M16 8V3H3v13h5"/>',
  download:'<path d="M12 3v12m-5-5 5 5 5-5M4 16v5h16v-5"/>',
  globe:'<circle cx="12" cy="12" r="9"/><ellipse cx="12" cy="12" rx="4" ry="9"/><path d="M3 12h18"/>',
  shield:'<path d="m12 3 8 3v6c0 5-8 9-8 9s-8-4-8-9V6l8-3Z"/><path d="m8 12 3 3 5-6"/>',
  compass:'<circle cx="12" cy="12" r="9"/><path d="m16 8-2 6-6 2 2-6 6-2Z"/>',
  money:'<rect x="2" y="5" width="20" height="14" rx="2"/><circle cx="12" cy="12" r="3"/><path d="M6 9v.1M18 15v.1"/>',
};
const icon = name => `<svg viewBox="0 0 24 24" aria-hidden="true">${icons[name] || icons.briefcase}</svg>`;
const hydrateIcons = () => $$('[data-icon]').forEach(el=>el.innerHTML=icon(el.dataset.icon));
const UI = DATA.ui || {};
const GATE_LABELS = (UI.gates||[]).map(g=>g.label);
const storageKey = UI.storageKey || 'waypoint-v1';
let saved = {};
try { saved = JSON.parse(localStorage.getItem(storageKey)||'{}') || {}; } catch {}
const state = {view:'overview',scope:'current',stage:'all',query:'',layout:saved.layout||'list',compare:[],
  bookmarks:new Set(saved.bookmarks||[]), notes:saved.notes||{}, done:new Set(saved.done||[]),
  researchDecision:'all',researchPage:0,researchQuery:'',sourceTab:UI.allRolesTab||(DATA.sourceTabs[0]||{}).name||'',sourcePage:0,sourceQuery:'',
  targetGroup:DATA.poolCounts.priority?'target':'screen',targetQuery:'',companyQuery:'',detailId:null,detailTab:'overview',returnFocus:null};
let toastTimer;
function persist(){try{localStorage.setItem(storageKey,JSON.stringify({bookmarks:[...state.bookmarks],notes:state.notes,done:[...state.done],layout:state.layout}));}catch{toast('Your browser could not save locally. You can still export your notes.');}}
function toast(message){$('#toast').textContent=message;$('#toast').classList.add('visible');clearTimeout(toastTimer);toastTimer=setTimeout(()=>$('#toast').classList.remove('visible'),2800);}
function safeUrl(value){try{const url=new URL(value,location.href);return ['https:','http:','file:'].includes(url.protocol)?url.href:'#';}catch{return '#';}}
const link = (label,url,cls='') => `<a class="${cls}" href="${esc(safeUrl(url))}" target="_blank" rel="noopener noreferrer">${esc(label)} ${icon('external')}</a>`;
const opp = id => DATA.opportunities.find(r=>r.id===id);
const firm = id => DATA.companies.find(c=>c.id===id);
const current = () => DATA.opportunities.filter(r=>r.group==='current');
const beyondCv = () => current().filter(r=>!['Applied','Recruiter lead'].includes(r.stage)).length;
const targets = () => {const p=DATA.opportunities.filter(r=>r.group==='target').sort((a,b)=>a.priority-b.priority);return p.length?p:DATA.opportunities.filter(r=>r.group==='screen');};
const initials = name => (Object.hasOwn(UI.initials||{},name)&&UI.initials[name] || name.split(/[\s/]+/).slice(0,2).map(w=>w[0]).join('').toUpperCase());
const logo = (r,large=false) => `<span class="company-logo logo-${esc(r.companyId||r.id)}${large?' large':''}">${esc(initials(r.company))}</span>`;
const dayAge = date => Math.max(0,Math.round((Date.parse(DATA.asOf+'T12:00:00Z')-Date.parse(date+'T12:00:00Z'))/86400000));
const niceDate = date => {const d=new Date(String(date||'').slice(0,10)+'T12:00:00Z');return isNaN(d)?'—':new Intl.DateTimeFormat('en-GB',{day:'numeric',month:'short',timeZone:'UTC'}).format(d);};
const stageTone = stage => ['Task submitted','Intro booked'].includes(stage)?'teal':['Recruiter lead','Screen first','Reserve','On hold','Older lead'].includes(stage)?'amber':stage==='Rejected'?'red':stage==='Review pending'?'blue':'';
const badge = (label,tone='')=>`<span class="pill ${tone}">${esc(label)}</span>`;
const pillStage = r=>badge(r.stage,stageTone(r.stage));
function owner(r){return `<span class="owner ${r.owner==='Them'?'them':''}"><span class="mini-avatar">${r.owner===UI.self?esc(UI.avatar):r.owner==='Them'?'↗':'—'}</span>${esc(r.owner===UI.self?'You':r.owner==='Them'?'Them':r.owner)}</span>`;}
const navItems = [['overview','grid','Overview',null],['pipeline','pipeline','Applications & conversations',current().length],['targets','target','Next applications',DATA.poolCounts.queue],['companies','company','Company checks',DATA.companies.length],['research','archive','All researched jobs',DATA.research.length],['insights','chart','Insights',null],['sources','database','Details & sources',null]];
const titles = Object.fromEntries(navItems.map(([id,,label])=>[id,label]));
function renderNav(){ $('#nav').innerHTML = navItems.map(([id,ico,label,count],i)=>`${i===5?'<div class="nav-divider"></div>':''}<button class="nav-item ${state.view===id?'active':''}" data-view="${id}" ${state.view===id?'aria-current="page"':''}>${icon(ico)}${label}${count!==null?`<span class="nav-count">${count}</span>`:''}</button>`).join(''); }
function setView(view,opts={}){
  state.view=titles[view]?view:'overview';
  if(opts.scope)state.scope=opts.scope;
  if(opts.stage)state.stage=opts.stage;
  if(!opts.keepQuery){state.query='';$('#global-search').value='';}
  $('#sidebar').classList.remove('open');
  history.replaceState(null,'','#'+state.view);
  render();window.scrollTo({top:0,behavior:'instant'});
}

function stat(label,value,context,ico){return `<div class="stat"><div class="stat-label">${label}<span class="stat-icon">${icon(ico)}</span></div><div class="stat-value">${value}</div><div class="stat-context">${context}</div></div>`;}
function gateInline(r){return `<div class="gates-inline">${GATE_LABELS.slice(0,3).map(name=>`<span class="gate-${r.gates[name]||'unknown'}"><span class="gate-dot"></span>${name}</span>`).join('')}</div>`;}

function pipelinePanel(){
  const stages=[['Applied','stack-applied'],['Recruiter lead','stack-lead'],['Intro booked','stack-intro'],['Task submitted','stack-task']].map(([name,cls])=>[name,current().filter(r=>r.stage===name).length,cls]);
  return `<section class="panel"><div class="panel-heading"><div><h2>Current applications & conversations</h2><p>Where your ${current().length} current opportunities stand</p></div><span class="quiet-pill">${esc(UI.progressingLabel??beyondCv()+' progressing')}</span></div><div class="pipeline-stack" role="group" aria-label="Current pipeline: ${stages.map(([n,c])=>c+' '+n).join(', ')}">${stages.map(([name,n,cls])=>`<button class="${cls}" style="flex:${n}" data-stage-link="${name}" aria-label="Show ${n} ${name.toLowerCase()} opportunities"></button>`).join('')}</div><div class="stage-legend">${stages.map(([name,n,cls])=>`<button data-stage-link="${name}"><span class="legend-label"><i class="swatch ${cls}"></i>${name==='Recruiter lead'?'Recruiter leads':name==='Applied'?'Applied':name}</span><strong class="legend-number">${n}</strong></button>`).join('')}</div><div class="panel-foot"><span><strong>${esc((UI.pipelineFoot||[beyondCv()+' processes beyond CV review.'])[0])}</strong>${UI.pipelineFoot&&UI.pipelineFoot[1]?' '+esc(UI.pipelineFoot[1]):''}</span><button class="text-button" data-view="pipeline">Open pipeline ${icon('arrow')}</button></div></section>`;
}

const scopes=[['current','Current'],['all','All process records'],['older','Older conversations'],['hold','Paused by you'],['closed','Rejected'],['archived','Portal archived'],['declined','Not pursuing'],['platform','Platform work']];

function pipeline(){
  const rows=filteredOpportunities();
  const stageChoices=[...new Set(DATA.opportunities.filter(r=>state.scope==='all'?(!r.poolId||!!state.query):r.group===state.scope).map(r=>r.stage))];
  return heading('YOUR OPPORTUNITIES','Applications and conversations','Submitted applications and recruiter conversations, with older, paused and closed records kept in their own groups.',`<button class="button" data-action="bookmarks">${icon('bookmark')}Saved · ${state.bookmarks.size}</button>`)+
    `<div class="filter-bar"><div class="filter-pills">${scopes.map(([key,label])=>`<button class="filter-pill ${state.scope===key?'active':''}" data-scope="${key}" aria-label="${label} ${DATA.opportunities.filter(r=>key==='all'?!r.poolId:r.group===key).length}" aria-pressed="${state.scope===key}">${label}<span>${DATA.opportunities.filter(r=>key==='all'?!r.poolId:r.group===key).length}</span></button>`).join('')}</div><div class="filter-right"><select class="select" id="stage-filter" aria-label="Filter by stage"><option value="all">All stages</option>${stageChoices.map(s=>`<option ${state.stage===s?'selected':''}>${esc(s)}</option>`).join('')}</select><div class="view-switch" aria-label="Pipeline layout"><button class="${state.layout==='list'?'active':''}" data-layout="list" aria-label="Table view" aria-pressed="${state.layout==='list'}">${icon('list')}</button><button class="${state.layout==='board'?'active':''}" data-layout="board" aria-label="Board view" aria-pressed="${state.layout==='board'}">${icon('pipeline')}</button></div></div></div>
    ${rows.length?(state.layout==='board'?board(rows):opportunityTable(rows)):empty('No matching opportunities','Try another stage, group or search term.')}
    <p class="result-count">${rows.length} ${rows.length===1?'record':'records'}${state.query?` matching “${esc(state.query)}”`:''} · ${esc(UI.statusAsOf??'Status as of '+niceDate(DATA.asOf)+'.')} An older date does not mean a vacancy is still open.</p>`;
}

function board(rows){const stages=[...new Set(rows.map(r=>r.stage))];const preferred=['Task submitted','Technical interview expected','Intro booked','Recruiter lead','Applied','Screen first','Older lead','On hold','Rejected','Archived','Not pursuing','Review pending','Reserve'];const ordered=[...new Set([...preferred.filter(s=>stages.includes(s)),...stages])];return `<div class="board">${ordered.map(stage=>`<section class="board-lane"><div class="lane-head">${esc(stage)}<span>${rows.filter(r=>r.stage===stage).length}</span></div>${rows.filter(r=>r.stage===stage).map(r=>`<button class="board-card" data-open="${r.id}">${logo(r)}<h3>${esc(r.company)}</h3><p>${esc(r.role)}</p><div class="board-card-foot"><span>${r.owner===UI.self?'Your move':r.owner==='Them'?'With them':r.owner}</span><span>${niceDate(r.last)}</span></div></button>`).join('')}</section>`).join('')}</div>`;}
function empty(title,description){return `<div class="empty-state">${icon('search')}<h3>${title}</h3><p>${description}</p><button class="button" data-action="clear-filters">Clear filters</button></div>`;}


function researchRows(){return DATA.research.filter(r=>(state.researchDecision==='all'||r.decision===state.researchDecision)&&(!state.researchQuery||Object.values(r).join(' ').toLowerCase().includes(state.researchQuery.toLowerCase())));}


function pagination(total,page,size,prefix){return `<div class="pagination"><span>${total?`${page*size+1}–${Math.min(total,(page+1)*size)}`:'0'} of ${total}</span><div><button class="button compact" data-page="${prefix}" data-delta="-1" ${page===0?'disabled':''}>Previous</button><span>${page+1} / ${Math.max(1,Math.ceil(total/size))}</span><button class="button compact" data-page="${prefix}" data-delta="1" ${(page+1)*size>=total?'disabled':''}>Next</button></div></div>`;}

function sourceRows(){const tab=DATA.sourceTabs.find(t=>t.name===state.sourceTab);return tab.values.map((cells,index)=>({cells,index})).filter(row=>!state.sourceQuery||row.cells.join(' ').toLowerCase().includes(state.sourceQuery.toLowerCase()));}
function sourceTable(){const tab=DATA.sourceTabs.find(t=>t.name===state.sourceTab),all=sourceRows(),rows=all.slice(state.sourcePage*15,state.sourcePage*15+15),width=Math.max(...tab.values.map(r=>r.length));if(!all.length)return `<div class="empty-state"><h3>No matching rows in ${esc(tab.name)}</h3><p>Try another term, or choose a different source tab.</p><button class="button" data-action="source-clear">Clear source search</button></div>`;return `<div class="table-wrap"><table class="source-raw"><thead><tr><th>Row</th>${Array.from({length:width},(_,i)=>`<th>${String.fromCharCode(65+i)}</th>`).join('')}</tr></thead><tbody>${rows.map(({cells,index})=>`<tr><td>${index+1}</td>${Array.from({length:width},(_,i)=>{const v=String(cells[i]??'');return `<td>${v.length>140?`<details><summary><span class="cell-preview">${esc(v.slice(0,140))}…</span>Read cell</summary>${esc(v)}</details>`:esc(v)}</td>`;}).join('')}</tr>`).join('')}</tbody></table></div>${pagination(all.length,state.sourcePage,15,'source')}<a class="text-button" href="${esc(tab.url)}" target="_blank" rel="noopener">Open ${esc(tab.name)} in Google Sheets ${icon('external')}</a>`;}
function render(){renderNav();$('#crumb').textContent=titles[state.view];const views={overview,pipeline,targets:targetView,companies:companyView,research:researchView,insights,sources:sourceView};$('#main').innerHTML=`<div class="fade-in">${views[state.view]()}</div>`;renderCompareTray();hydrateIcons();}
function renderCompareTray(){const tray=$('#compare-tray');tray.hidden=!state.compare.length;tray.innerHTML=`<span>${state.compare.length} ${state.compare.length===1?'role':'roles'} selected</span><button class="button compact" data-action="compare-open" ${state.compare.length<2?'disabled':''}>Compare roles ${icon('arrow')}</button><button class="text-button" data-action="compare-clear">Clear</button>`;}
function openDialog(el){state.returnFocus=document.activeElement;if(!el.open)el.showModal();}
function closeDialog(el){el.close();if(state.returnFocus?.isConnected)state.returnFocus.focus();}


function openOpportunity(id,tab='overview'){state.detailId=id;state.detailTab=tab;const r=opp(id);if(!r)return;renderDetail(r);openDialog($('#detail-dialog'));}

function processOverview(r){return `<div class="detail-next"><div class="eyebrow">${r.owner==='Them'?'WITH THEM':r.owner==='Hold'?'ON HOLD':'NEXT MOVE'}</div><p>${esc(r.nextAction)}</p></div>${Object.keys(r.gates).length?`<section class="detail-section"><h3>The practical gates</h3><div class="gate-grid">${GATE_LABELS.map(key=>`<div class="gate-box ${r.gates[key]||'unknown'}">${key}<strong>${({confirmed:'Confirmed',unknown:'Not confirmed',concern:'Concern',conflict:'Conflicting evidence',conditional:'Conditional'})[r.gates[key]||'unknown']}</strong></div>`).join('')}</div></section>`:''}<section class="detail-section"><h3>Terms & fit</h3><dl class="detail-terms"><dt>Compensation</dt><dd>${esc(r.pay)}</dd><dt>Arrangement</dt><dd>${esc(r.route)}</dd><dt>Next owner</dt><dd>${r.owner===UI.self?'You':esc(r.owner)}</dd>${r.fit?`<dt>Technical fit</dt><dd>${esc(r.fit)}</dd>`:''}</dl></section>${r.questions.length?`<section class="detail-section"><h3>Questions before the next step</h3><ol class="question-list">${r.questions.map(q=>`<li>${esc(q)}</li>`).join('')}</ol><button class="text-button" data-copy="${r.id}">${icon('copy')}Copy questions</button></section>`:''}${r.mismatch?`<div class="mismatch"><strong>Newer evidence differs from the sheet</strong>${esc(r.mismatch)} The correction was applied during reconciliation.</div>`:''}${r.notes?`<section class="detail-section"><h3>Keep this distinction</h3><p class="detail-summary">${esc(r.notes)}</p></section>`:''}<section class="detail-section"><h3>Company background</h3>${firm(r.companyId)?`<p class="detail-summary">${esc(firm(r.companyId).main_risk)}</p><button class="text-button" style="margin-top:10px" data-detail-tab="background">Read the dated check ${icon('arrow')}</button>`:'<div class="company-blank">No fresh company dossier is attached to this opportunity yet. Historical spreadsheet research is available under Sources; it is not a current background clearance.</div>'}</section>`;}

function detailEvidence(r){return `<section class="detail-section"><h3>Verified timeline</h3><div class="detail-timeline">${r.timeline.map(([date,text])=>`<div class="detail-event"><time>${niceDate(date)} ${String(date).slice(0,4)}</time><p>${esc(text)}</p></div>`).join('')}</div></section><section class="detail-section"><h3>Evidence links</h3><div class="detail-evidence">${r.sources.map(([label,url])=>link(label,url)).join('')}${r.sheetSource?link('Tracker row',r.sheetSource):''}</div></section>${r.sheetStatus?`<div class="mismatch"><strong>Original sheet value</strong>${esc(r.sheetStatus)}${r.mismatch?'<p style="margin-top:7px">'+esc(r.mismatch)+'</p>':''}</div>`:''}<section class="detail-section"><h3>Your private note <span class="saved-notice" id="note-saved"></span></h3><textarea class="note-area" id="private-note" data-note="${r.id}" aria-label="Private note for ${esc(r.company)}" placeholder="What do you want to remember or ask next?">${esc(state.notes[r.id]||'')}</textarea><p class="note-hint">Saved on this device. Does not change the spreadsheet, send a message or update the verified stage.</p></section>`;}


function openUpdate(number){const u=DATA.updates.find(u=>u.number===number);if(!u)return;state.detailId=null;$('#detail-dialog').innerHTML=`<div class="detail-top"><span class="eyebrow">APPLIED TRACKER CORRECTION · ${u.number}</span><button class="icon-button" data-close="detail-dialog" aria-label="Close proposed change">${icon('close')}</button></div><div class="detail-body"><h2 id="detail-title">${esc(u.title)}</h2><div class="detail-meta">${badge(u.state,'teal')}${badge(UI.updateBadge||'Tracker reconciliation')}</div><div class="dossier">${markdown(u.detail)}</div><div class="callout">This is the audit of an authorized, verified tracker write. The HTML prototype itself has no write access.</div><div class="detail-evidence">${link('Full reconciliation status',UI.updateStatusUrl||UI.statusUrl||'#')}</div></div>`;openDialog($('#detail-dialog'));}
function compareRoles(){if(state.compare.length<2)return;const rows=state.compare.map(opp).filter(Boolean);$('#compare-dialog').innerHTML=`<div class="detail-top"><div><span class="eyebrow">A SIDE-BY-SIDE DECISION</span><h2 id="compare-title" style="margin-top:5px;font-size:20px">Compare your next targets</h2></div><button class="icon-button" data-close="compare-dialog" aria-label="Close comparison">${icon('close')}</button></div><div class="compare-body"><div class="table-wrap"><table class="compare-table"><thead><tr><th>Screening criteria</th>${rows.map(r=>`<th>${esc(r.company)}<p class="small muted" style="font-weight:400;margin-top:6px">${esc(r.role)}</p></th>`).join('')}</tr></thead><tbody>${[['Technical overlap',r=>r.fit],['Country & contract',r=>r.route],['Compensation basis',r=>r.pay],['Main role blocker',r=>r.risk],['Company background',r=>firm(r.companyId)?.main_risk||'Not checked'],['First question',r=>r.questions[0]],['Evidence',r=>r.sources.map(([name,url])=>link(name,url)).join(' ')]].map(([label,fn])=>`<tr><td>${label}</td>${rows.map(r=>`<td>${label==='Evidence'?fn(r):esc(fn(r))}</td>`).join('')}</tr>`).join('')}</tbody></table></div><p class="metric-note">${esc(UI.compareNote||'All targets remain conditional. A stronger technical match does not resolve location eligibility, support hours or contract security.')}</p></div>`;openDialog($('#compare-dialog'));}
function preferences(){const items=[['briefcase',DATA.constraints.role],['globe',DATA.constraints.location],['clock',DATA.constraints.hours],['money',DATA.constraints.money],['calendar',DATA.constraints.term],['shield',DATA.constraints.pager]];$('#preferences-dialog').innerHTML=`<div class="preferences-top"><div><div class="eyebrow">YOUR SEARCH CRITERIA</div><h2 id="preferences-title">The work should fit you.</h2></div><button class="icon-button" data-close="preferences-dialog" aria-label="Close search criteria">${icon('close')}</button></div><div class="preferences-list">${items.map(([ico,text])=>`<div class="preference-item">${icon(ico)}${esc(text)}</div>`).join('')}</div>${UI.preferencesNote?`<p>${esc(UI.preferencesNote)}</p>`:''}`;openDialog($('#preferences-dialog'));}
function downloadSnapshot(){const reviewed={asOf:DATA.asOf,publicationRevision:DATA.publicationRevision,poolCounts:DATA.poolCounts,editorialBriefs:'Summaries reviewed against published revision',poolAudit:DATA.poolAudit,sourceSheet:DATA.sheetUrl,sourceRead:DATA.sheetReadAt,opportunities:DATA.opportunities.map(({sheetDetails,...r})=>({...r,saved:state.bookmarks.has(r.id),privateNote:state.notes[r.id]||''})),companies:DATA.companies.map(({body,...c})=>c),trackerCorrections:DATA.updates,coverage:DATA.coverage};const blob=new Blob([JSON.stringify(reviewed,null,2)],{type:'application/json'});const url=URL.createObjectURL(blob);const a=document.createElement('a');a.href=url;a.download=UI.snapshotFilename||`waypoint-search-snapshot-${DATA.asOf}.json`;a.click();setTimeout(()=>URL.revokeObjectURL(url),1000);toast('Snapshot exported. The exported file is local; the tracker reconciliation was already saved.');}
async function copyQuestions(id){const r=opp(id);try{await navigator.clipboard.writeText(r.questions.map((q,i)=>`${i+1}. ${q}`).join('\n'));toast('Questions copied. Nothing sent.');}catch{toast('Clipboard unavailable. Select the questions in the detail view to copy.');}}

document.addEventListener('click',event=>{
  const el=event.target.closest('button,a[data-view]');if(!el)return;
  if(el.dataset.insightGroup){state.targetGroup=el.dataset.insightGroup;setView('targets');return;}
  if(el.dataset.auditBucket){setView('targets');const panel=[...document.querySelectorAll('.audit-group')].find(x=>x.dataset.auditBucket===el.dataset.auditBucket);if(panel){panel.open=true;panel.scrollIntoView({block:'start'});}return;}
  if(el.dataset.targetGroup){state.targetGroup=el.dataset.targetGroup;render();return;}
  if(el.dataset.poolRecord){openPoolRecord(el.dataset.poolRecord);return;}
  if(el.dataset.view){event.preventDefault();setView(el.dataset.view);return;}
  if(el.dataset.open){openOpportunity(el.dataset.open);return;}
  if(el.dataset.company){openCompany(el.dataset.company);return;}
  if(el.dataset.document){openDocument(el.dataset.document);return;}
  if(el.dataset.application!==undefined){openDocument('application',Number(el.dataset.application));return;}
  if(el.dataset.close){closeDialog($('#'+el.dataset.close));return;}
  if(el.dataset.bookmark){const id=el.dataset.bookmark;state.bookmarks.has(id)?state.bookmarks.delete(id):state.bookmarks.add(id);persist();const isSaved=state.bookmarks.has(id);$$(`[data-bookmark="${id}"]`).forEach(b=>{b.classList.toggle('saved',isSaved);b.setAttribute('aria-pressed',String(isSaved));b.setAttribute('aria-label',`${isSaved?'Unsave':'Save'} ${opp(id).company}`);});toast(isSaved?'Saved on this device.':'Removed from saved roles.');return;}
  if(el.dataset.scope){state.scope=el.dataset.scope;state.stage='all';render();return;}
  if(el.dataset.layout){state.layout=el.dataset.layout;persist();render();return;}
  if(el.dataset.stageLink){setView('pipeline',{scope:'current',stage:el.dataset.stageLink});return;}
  if(el.dataset.detailTab){state.detailTab=el.dataset.detailTab;if(state.detailId){const y=$('#detail-dialog').scrollTop;renderDetail(opp(state.detailId));$('#detail-dialog').scrollTop=y;}return;}
  if(el.dataset.research){openResearch(el.dataset.research);return;}
  if(el.dataset.update){openUpdate(Number(el.dataset.update));return;}
  if(el.dataset.copy){copyQuestions(el.dataset.copy);return;}
  if(el.dataset.page){if(el.dataset.page==='research'){state.researchPage+=Number(el.dataset.delta);$('#research-results').innerHTML=researchTable(researchRows().slice(state.researchPage*20,state.researchPage*20+20))+pagination(researchRows().length,state.researchPage,20,'research');}else{state.sourcePage+=Number(el.dataset.delta);$('#source-results').innerHTML=sourceTable();}return;}
  switch(el.dataset.action){
    case 'menu':$('#sidebar').classList.toggle('open');break;
    case 'preferences':preferences();break;
    case 'source-clear':state.sourceQuery='';state.sourcePage=0;$('#source-search').value='';$('#source-results').innerHTML=sourceTable();break;
    case 'export':downloadSnapshot();break;
    case 'compare-open':compareRoles();break;
    case 'compare-clear':state.compare=[];render();break;
    case 'clear-filters':state.query='';state.stage='all';state.researchDecision='all';state.researchQuery='';state.researchPage=0;$('#global-search').value='';render();break;
    case 'bookmarks':{const rows=DATA.opportunities.filter(r=>state.bookmarks.has(r.id));state.detailId=null;$('#detail-dialog').innerHTML=`<div class="detail-top"><h2 id="detail-title">Saved opportunities</h2><button class="icon-button" data-close="detail-dialog" aria-label="Close saved roles">${icon('close')}</button></div><div class="detail-body">${rows.length?opportunityTable(rows):'<div class="company-blank">Save a role with the bookmark icon. Your choices stay on this browser.</div>'}</div>`;openDialog($('#detail-dialog'));break;}
  }
});
document.addEventListener('change',event=>{
  const el=event.target;
  if(el.dataset.compare){const id=el.dataset.compare;if(el.checked&&!state.compare.includes(id))state.compare.push(id);else if(!el.checked)state.compare=state.compare.filter(x=>x!==id);$$(`[data-compare="${id}"]`).forEach(x=>x.checked=el.checked);renderCompareTray();const button=$('.heading-actions [data-action="compare-open"]');if(button)button.disabled=state.compare.length<2;return;}
  if(el.id==='stage-filter'){state.stage=el.value;render();}
  if(el.id==='research-decision'){state.researchDecision=el.value;state.researchPage=0;$('#research-results').innerHTML=researchTable(researchRows().slice(0,20))+pagination(researchRows().length,0,20,'research');}
  if(el.id==='source-tab'){state.sourceTab=el.value;state.sourcePage=0;state.sourceQuery='';$('#source-search').value='';$('#source-results').innerHTML=sourceTable();}
});
document.addEventListener('input',event=>{
  const el=event.target;
  if(el.id==='target-search'){state.targetQuery=el.value;$('#candidate-results').innerHTML=candidateResults();return;}
  if(el.id==='company-search'){state.companyQuery=el.value;$('#company-results').innerHTML=companyResults();return;}
  if(el.id==='global-search'){state.query=el.value;state.scope='all';state.stage='all';state.view='pipeline';history.replaceState(null,'','#pipeline');render();}
  if(el.id==='research-search'){state.researchQuery=el.value;state.researchPage=0;$('#research-results').innerHTML=researchTable(researchRows().slice(0,20))+pagination(researchRows().length,0,20,'research');}
  if(el.id==='source-search'){state.sourceQuery=el.value;state.sourcePage=0;$('#source-results').innerHTML=sourceTable();}
  if(el.dataset.note){state.notes[el.dataset.note]=el.value;persist();$('#note-saved').textContent='Saved locally';}
});
document.addEventListener('keydown',event=>{
  if(event.key==='/'&&!['INPUT','TEXTAREA','SELECT'].includes(document.activeElement.tagName)&&!$$('dialog[open]').length){event.preventDefault();$('#global-search').focus();}
  if(event.key==='Escape')$('#sidebar').classList.remove('open');
});
$$('dialog').forEach(dialog=>dialog.addEventListener('click',event=>{if(event.target!==dialog)return;const b=dialog.getBoundingClientRect();if(event.clientX<b.left||event.clientX>b.right||event.clientY<b.top||event.clientY>b.bottom)closeDialog(dialog);}));
window.addEventListener('hashchange',()=>{const view=location.hash.slice(1);if(titles[view]&&view!==state.view)setView(view);});
state.view=titles[location.hash.slice(1)]?location.hash.slice(1):'overview';
render();
