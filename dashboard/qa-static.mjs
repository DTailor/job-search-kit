// Read-only product smoke checks. No browser, server, package install or network.
// Usage: node qa-static.mjs [dashboard-dir]   (default: this file's directory)
// The dashboard dir holds data/reviewed-data.json written by build.py. An empty
// workspace (no pool jobs, no processes) is checked in empty-state mode.
import fs from 'node:fs';
import vm from 'node:vm';
import assert from 'node:assert/strict';
import path from 'node:path';
const here=path.dirname(new URL(import.meta.url).pathname);
const dir=path.resolve(process.argv[2]||here);
const DATA=JSON.parse(fs.readFileSync(path.join(dir,'data/reviewed-data.json'),'utf8'));
const emptyMode=DATA.poolCounts.pool===0&&DATA.opportunities.length===0;
const elements=new Map();
const document={querySelector:s=>{if(!elements.has(s))elements.set(s,{showModal(){},close(){}});return elements.get(s)},querySelectorAll:()=>[]};
const context=vm.createContext({DATA,document,URL,location:{href:'file://'+path.join(dir,'index.html')},localStorage:{getItem:()=>null},Intl,Date,Set,Map,clearTimeout,setTimeout});
const source=fs.readFileSync(path.join(here,'src/presentation.js'),'utf8')+'\n'+fs.readFileSync(path.join(here,'src/app.js'),'utf8').split("document.addEventListener('click'")[0];
vm.runInContext(source,context);
const evaluate=js=>vm.runInContext(js,context);
for(const fn of ['overview','targetView','pipeline','companyView','researchView','insights','sourceView']){
  const html=evaluate(fn+'()');assert.ok(html.length>100);assert.ok(!html.includes('undefined'),fn+' contains undefined');assert.ok(!html.includes('NaN'),fn+' contains NaN');
}
for(const [group,count] of [['target',DATA.poolCounts.priority],['screen',DATA.poolCounts.screening],['reserve',DATA.poolCounts.reserves]]){
  evaluate(`state.targetGroup='${group}';state.targetQuery=''`);
  assert.equal((evaluate('candidateResults()').match(/data-job-card=/g)||[]).length,count);
}
const firstCandidate=DATA.opportunities.find(r=>r.poolId);
if(firstCandidate){
  evaluate(`state.targetGroup=${JSON.stringify(firstCandidate.group)};state.targetQuery=${JSON.stringify(firstCandidate.company)}`);
  assert.ok((evaluate('candidateResults()').match(/data-job-card=/g)||[]).length>=1);
}else{
  assert.equal(DATA.poolCounts.queue,0);
  assert.equal((evaluate('candidateResults()').match(/data-job-card=/g)||[]).length,0);
}
evaluate("state.targetQuery='no-such-candidate-xyz'");assert.match(evaluate('candidateResults()'),/No candidates match/);
const audit=evaluate('auditGroups()');
const queued=new Set(DATA.opportunities.filter(r=>r.poolId).map(r=>r.poolId));
for(const job of DATA.poolAudit){
  assert.equal(audit.includes(`data-pool-record="${job.poolId}"`),!queued.has(job.poolId));
  evaluate(`openPoolRecord('${job.poolId}')`);
}
for(const job of DATA.opportunities)for(const tab of ['overview','background','evidence'])evaluate(`state.detailTab='${tab}';renderDetail(opp(${JSON.stringify(job.id)}))`);
for(const company of DATA.companies)evaluate(`openCompany('${company.id}')`);
evaluate("state.scope='all';state.query='';state.stage='all'");assert.equal(evaluate('filteredOpportunities().length'),DATA.opportunities.filter(r=>!r.poolId).length);
evaluate("state.scope='current';state.stage='Applied'");assert.equal(evaluate('filteredOpportunities().length'),DATA.opportunities.filter(r=>r.group==='current'&&r.stage==='Applied').length);
if(DATA.companies.length){evaluate(`state.companyQuery=${JSON.stringify(DATA.companies[0].company)}`);assert.ok((evaluate('companyResults()').match(/class="company-card"/g)||[]).length>=1);}
evaluate("state.companyQuery='no-such-company-xyz'");assert.match(evaluate('companyResults()'),/No company checks match/);
const hasTable=text=>/^\s*\|?\s*:?-{3,}/m.test(text||'');
evaluate("openDocument('plan')");let html=elements.get('#detail-dialog').innerHTML;
assert.ok(!html.includes('source-document'),'No raw-document dump');
if(hasTable(DATA.planDocument))assert.ok(html.includes('document-table'),'Plan must render Markdown tables');
evaluate("openDocument('status')");
if(hasTable(DATA.statusDocument))assert.ok(elements.get('#detail-dialog').innerHTML.includes('document-table'));
assert.equal(evaluate("markdown('<script>alert(1)</script>')"),'<p>&lt;script&gt;alert(1)&lt;/script&gt;</p>');
assert.match(evaluate("markdown('[Unsafe](javascript:alert)')"),/href="#"/);
assert.equal(DATA.poolAudit.length,DATA.poolCounts.pool);
if(emptyMode){
  const page=evaluate('overview()');
  assert.match(page,/data-empty-state="candidates"/,'Overview must show the empty candidate state');
  assert.match(page,/data-empty-state="attention"/,'Overview must show the empty attention state');
  evaluate("state.scope='current';state.stage='all'");assert.match(evaluate('pipeline()'),/No matching opportunities/);
}
console.log(JSON.stringify({result:'passed',mode:emptyMode?'empty-state':'populated',views:7,candidate_groups:[DATA.poolCounts.priority,DATA.poolCounts.screening,DATA.poolCounts.reserves],candidate_search_and_empty_state:true,process_population_and_filters:true,opportunity_panels:DATA.opportunities.length*3,pool_drawers:DATA.poolAudit.length,company_briefs:DATA.companies.length,formatted_documents:true,source_links_and_html_escaping:true,browser:false,network:false}));
