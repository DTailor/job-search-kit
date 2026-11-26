"""Build the private, self-contained Waypoint dashboard from a job-search workspace.

Everything person-specific comes from workspace.json (person, tracker tabs, paths,
gates) and the optional <dashboard>/data/instance.json overrides file. See DATA.md.

Usage: python3 <dashboard>/build.py [--workspace DIR]
The workspace root is DIR, else $JOB_HUNT_WORKSPACE, else the nearest ancestor of
the current directory containing workspace.json. Stdlib only; no network.
"""
from pathlib import Path
import html as htmllib
import json
import os
import re
import sys
from datetime import datetime, timezone
from urllib.parse import quote

HERE = Path(__file__).resolve().parent
if '--workspace' in sys.argv:
    os.environ['JOB_HUNT_WORKSPACE'] = str(Path(sys.argv[sys.argv.index('--workspace') + 1]).resolve())


def _import_tools():
    """Prefer the workspace's own tools/, else the kit tools/ next to this dashboard."""
    roots = []
    if os.environ.get('JOB_HUNT_WORKSPACE'):
        roots.append(Path(os.environ['JOB_HUNT_WORKSPACE']))
    roots += [HERE.parent, Path.cwd(), *Path.cwd().parents]
    for base in roots:
        if (base / 'tools/workspace.py').is_file() and (base / 'tools/job_pool.py').is_file():
            sys.path.insert(0, str(base))
            from tools import workspace, job_pool
            return workspace, job_pool
    raise SystemExit('tools/workspace.py and tools/job_pool.py not found')


ws, job_pool = _import_tools()
ROOT = ws.root()
DASH = ws.path('dashboard')
DATA_DIR = ws.path('data')
PERSON = ws.person()
SELF = PERSON.get('short_name') or PERSON['name'].split()[0]
TZ = ws.timezone() if hasattr(ws, 'timezone') else PERSON['timezone']
TZ_CITY = TZ.split('/')[-1].replace('_', ' ')


def opt_path(key, default):
    try:
        return ws.path(key)
    except KeyError:
        return DATA_DIR / default


def read_json(path, default=None):
    return json.loads(path.read_text()) if path.is_file() else default


def rel(path):
    """Link from the generated page (in the dashboard folder) to a workspace file."""
    return os.path.relpath(path, DASH)


INSTANCE = read_json(DASH / 'data/instance.json', {})
UI = INSTANCE.get('ui', {})
snapshot_path = DASH / 'data/tracker-snapshot.json'
if not snapshot_path.is_file():
    raise SystemExit(f'Missing {snapshot_path}: capture the tracker readback first (see DATA.md)')
SHEET = json.loads(snapshot_path.read_text())
SHEET_URL = SHEET.get('spreadsheet_url') or ws.sheet_url()
GATES = list(ws.gates()['dashboard'].items()) if hasattr(ws, 'gates') else [
    ('Location', 'location'), ('Pay', 'pay'), ('Hours', 'hours'), ('Term', 'term')]
GATE_VALUES = {'pass': 'confirmed', 'fail': 'concern', 'unclear': 'unknown'}


def gate_states(gates):
    return {label: GATE_VALUES.get((gates or {}).get(key), 'unknown') for label, key in GATES}


def mail(thread):
    return f"https://mail.google.com/mail/u/?authuser={quote(PERSON['email'], safe='')}#all/{thread}"


def record(id, company, role, group, stage, owner, last, action, **kw):
    return dict(id=id, company=company, role=role, group=group, stage=stage, owner=owner,
                last=last, nextAction=action, channel=kw.pop('channel', 'Gmail'),
                pay=kw.pop('pay', 'Not established'), route=kw.pop('route', 'Unconfirmed'),
                tags=kw.pop('tags', ['Python', 'Backend']), gates=kw.pop('gates', {}),
                sources=kw.pop('sources', []), questions=kw.pop('questions', []),
                timeline=kw.pop('timeline', []), notes=kw.pop('notes', ''), **kw)


def from_instance(spec):
    spec = dict(spec)
    head = [spec.pop(k) for k in ('id', 'company', 'role', 'group', 'stage', 'owner', 'last', 'nextAction')]
    return record(*head, **spec)


# Hand-curated process records (recruiter threads, historical applications) are
# instance data; candidate cards and submissions are derived from the pool.
R = [from_instance(r) for r in INSTANCE.get('records', {}).get('before_queue', [])]

POOL_REVIEW = job_pool.load_current(ws.path('pool'))
POOL_JOBS = POOL_REVIEW['jobs']
assert SHEET.get('publication_revision') == POOL_REVIEW['revision'], 'Refresh the tracker readback before rebuilding published views'
PRESENTATION = read_json(DASH / 'data/presentation.json')
if PRESENTATION is None:
    assert not POOL_JOBS, 'data/presentation.json (editorial briefs) is required once the pool has jobs'
    PRESENTATION = dict(source_revision=POOL_REVIEW['revision'], jobs={}, companies={})
assert PRESENTATION['source_revision'] == POOL_REVIEW['revision'], 'Review editorial briefs against the new pool revision'
assert set(PRESENTATION['jobs']) == {j['pool_id'] for j in POOL_JOBS}
QUEUE = job_pool.queue_jobs(POOL_JOBS)
POOL_COUNTS = job_pool.counts(POOL_JOBS)
AS_OF = POOL_REVIEW.get('as_of') or str(SHEET.get('checked_at', ''))[:10] or datetime.now(timezone.utc).date().isoformat()
card_ids = INSTANCE.get('card_ids', {})
for n, item in enumerate(QUEUE, 1):
    id = card_ids.get(item['pool_id'], 'market-' + item['pool_id'])
    group = {'Priority screen': 'target', 'Screen first': 'screen', 'Reserve / stretch': 'reserve'}[item['bucket']]
    tech = item['required_tech']
    tags = (tech if isinstance(tech, list) else tech.split(';'))[:3]
    R.append(record(id, item['company'], item['title'], group, 'Reserve' if group == 'reserve' else 'Screen first', SELF, item['checked_at'][:10],
        item['next_action'], companyId=Path(item['background']['path']).stem, poolId=item['pool_id'],
        priority=n if group == 'target' else None, channel='Employer posting', tags=tags, pay=item['pay_published'], route=item['contract_text'],
        brief=PRESENTATION['jobs'][item['pool_id']],
        advert=dict(location=item['location_text'], contract=item['contract_text'], hours=item['hours_oncall'], pay=item['pay_published'], requirements=item['required_tech']),
        fit=item['why_fits'], summary=item['next_action'], risk=item['background']['main_risk'],
        gates=gate_states(item['gates']),
        questions=[item['main_risk_and_first_question']], sources=[['Original exact role', item['original_url']]],
        notes='Verified live; source date ' + item['checked_at'] + '. ' + item['background'].get('coverage', 'Partial check')))

# Verified submissions; process records, separate from unsubmitted pool cards.
ARCHIVE_FILES = sorted(DATA_DIR.glob(INSTANCE.get('submissions_glob', 'archive-*/submissions.json')))
SUBMISSIONS = [m for p in ARCHIVE_FILES for m in json.loads(p.read_text())['submissions']]
LATEST_ARCHIVE = max(ARCHIVE_FILES, key=lambda p: json.loads(p.read_text())['recorded_at']).parent if ARCHIVE_FILES else None
LATEST_SUMMARY = next((DATA_DIR / p for p in INSTANCE.get('summary_documents', []) if (DATA_DIR / p).is_file()), None)
if LATEST_SUMMARY is None and LATEST_ARCHIVE and (LATEST_ARCHIVE / 'README.md').is_file():
    LATEST_SUMMARY = LATEST_ARCHIVE / 'README.md'
STATUS_DIR = ws.path('status')
STATUS_FILES = sorted(STATUS_DIR.glob('????-??-??.md')) if STATUS_DIR.is_dir() else []
LATEST_STATUS = STATUS_FILES[-1] if STATUS_FILES else None
if LATEST_STATUS and (LATEST_SUMMARY is None or LATEST_STATUS.stem >= AS_OF):
    LATEST_SUMMARY = LATEST_STATUS
EVIDENCE = {
    'sent email': ('Sent application',
        'Application email verified in personal Gmail Sent, with CV attached. Waiting for employer review.',
        lambda m: 'The application record distinguishes the verified sent metadata from the last verified draft and any recovered sent body.',
        lambda m: 'Application sent' + (' at ' + m['time'] + ' ' + TZ_CITY if m.get('time') else '') + '; personal Gmail Sent verified.'),
    'browser confirmation': ('Submission confirmation',
        f'{SELF} reports submitted; the employer form confirmation was verified. Waiting for employer review.',
        lambda m: m.get('email_receipt_note', 'No email receipt found.') + ' Exact submission time and final uploaded file content were not independently recovered; submission does not establish a passed screen.',
        lambda m: f'{SELF} reports submitted; employer form success page verified. Exact submission time not recorded.'),
    'user report': ('Application record',
        f'Applied per {SELF}’s report. Waiting for employer review.',
        lambda m: 'No independent receipt or success-page verification recorded.',
        lambda m: f'{SELF} reports the application submitted; exact time not recorded.'),
}
RECEIPT = ('Application receipt',
    'Employer application receipt verified in personal Gmail. Waiting for employer review.',
    lambda m: 'Prepared form content is retained as history; the receipt does not reproduce the final submitted payload.',
    lambda m: 'Confirmation received' + (' at ' + m['time'] + ' ' + TZ_CITY if m.get('time') else '') + '; receipt verified.')
APPLICATIONS = opt_path('applications', 'applications')
for m in SUBMISSIONS:
    j = next(j for j in POOL_JOBS if j['pool_id'] == m['pool_id'])
    source_label, summary, evidence_note, event = EVIDENCE.get(m.get('evidence_kind', 'employer confirmation'), RECEIPT)
    R.append(record(m['key'], m['company'], m['role'], 'current', 'Applied', 'Them', m['date'],
        j['next_action'], companyId=Path(m['background']).stem,
        researchPoolId=m['pool_id'], channel=m['route'], pay=m.get('pay_sent', 'Unpublished; prepared expectation in application record'), route=m['contract'],
        tags=['Python', 'Applied'], summary=summary,
        notes=m['risk'] + ' ' + evidence_note(m),
        gates=gate_states(m['gates']),
        timeline=[[m.get('prepared_date', INSTANCE.get('submission_defaults', {}).get('prepared_date', m['date'])), 'Application materials prepared.'], [m['date'], event(m)]],
        sources=[[source_label, m['receipt_url']], ['Exact role', m['original_url']], ['Application record', rel(APPLICATIONS / m['folder'] / 'application.md')]]))

R += [from_instance(r) for r in INSTANCE.get('records', {}).get('after_submissions', [])]

# Reviewed process changes apply to both curated and submission-derived cards.
for r in R:
    r.update(INSTANCE.get('process_overrides', {}).get(r['id'], {}))

# Tracker readback: tab titles, gids and header rows come from workspace.json.
sheet_by_name = {x['sheet']: x for x in SHEET['sheets']}


def tab_values(key):
    return (sheet_by_name.get(ws.tab_title(key)) or {}).get('values', [])


def header_row(key):
    return ws.header_row(key) if hasattr(ws, 'header_row') else int(ws.tab(key).get('header_row', 1))


def gid(key):
    return ws.tab(key)['sheet_id']


short, pipeline, all_roles = tab_values('shortlist'), tab_values('pipeline'), tab_values('all_roles')
SHORT_HEAD, PIPE_HEAD, ALL_HEAD = header_row('shortlist'), header_row('pipeline'), header_row('all_roles')


def urls(value):
    return {url.rstrip('.,/') for url in re.findall(r'https?://[^\s]+', str(value))}


def company_key(value):
    return re.sub(r'\s*\([^)]*\)', '', value).split(' / ')[0].strip().casefold().rstrip('.')


# An Active pipeline Progress cell that starts "Rejected <date>" or "Closed by employer <date>"
# (for example a filled role) marks a candidacy the employer ended; both count as closed.
EMPLOYER_CLOSED = re.compile(r'^(Rejected|Closed by employer)\b')


def process_row(item):
    """Resolve the pipeline row by evidence URL, with unique company fallback.

    Sheet positions and dated submission archives do not own current stages.
    Ambiguous matches are refused rather than silently choosing another role.
    """
    candidates = [(n, row) for n, row in enumerate(pipeline[PIPE_HEAD:], PIPE_HEAD + 1) if len(row) > 8 and row[0]]
    source_urls = {url.rstrip('.,/') for _, url in item['sources']}
    exact = [(n, row) for n, row in candidates if source_urls & urls(row[8])]
    if not exact:
        exact = [(n, row) for n, row in candidates if company_key(row[0].split(' · ')[0]) == company_key(item['company'])]
    if len(exact) > 1:
        raise ValueError('Ambiguous Active pipeline match: ' + item['id'])
    return exact[0] if exact else None


aliases = INSTANCE.get('shortlist_aliases', {})
short_header = short[SHORT_HEAD - 1] if len(short) >= SHORT_HEAD else []
for r in R:
    prefix = aliases.get(r['id'], r['company']).lower()
    match = next(((n, row) for n, row in enumerate(short[SHORT_HEAD:], SHORT_HEAD + 1) if len(row) > 4 and str(row[3] or '').lower() == prefix), None)
    if match:
        n, row = match; r['sheetRow'] = n; r['sheetStatus'] = row[16] if len(row) > 16 else ''
        r['sheetSource'] = SHEET_URL + f'#gid={gid("shortlist")}&range=D{n}:T{n}'
        r['sheetDetails'] = {str(short_header[i]): v for i, v in enumerate(row) if i < len(short_header) and v not in ('', None)}
    matched = process_row(r) if r['group'] not in ('target', 'screen', 'reserve') else None
    if matched:
        n, row = matched
        r['sheetRow'] = n; r['sheetStatus'] = row[1]; r['sheetSource'] = SHEET_URL + f'#gid={gid("pipeline")}&range=A{n}:I{n}'
        r.update(summary=row[1], nextAction=row[2], statusVerifiedAt=row[7],
                 notes=row[6] + ' Source verification: ' + row[7])
        if r['group'] == 'current' and row[3]:
            r['owner'] = SELF if row[3] == SELF else 'Them'
        closure = EMPLOYER_CLOSED.match(str(row[1]))
        if closure:
            event = re.search(r'\b\d{4}-\d{2}-\d{2}\b', row[1])
            r.update(group='closed', stage=closure.group(1), owner='None', last=event.group(0) if event else r['last'], questions=[])
            r['timeline'].append([r['last'], row[1]])
        for url in sorted(urls(row[8])):
            if url not in {source.rstrip('.,/') for _, source in r['sources']}:
                r['sources'].append(['Current pipeline evidence', url])
    if not r['timeline']: r['timeline'] = [[r['last'], r.get('summary', r['nextAction'])]]
    r['mismatch'] = None  # Discrepancies are resolved in tracker reconciliation, not on the page.

COMPANIES = opt_path('companies', 'companies')
company_index = read_json(COMPANIES / 'index.json', {'companies': []})['companies']
companies = []
for c in company_index:
    text = (COMPANIES / c['dossier']).read_text()
    refs = []
    for label, url in re.findall(r'\[([^\]]+)\]\((https?://[^\s]+?)\)', text):
        if url not in [x[1] for x in refs]: refs.append([label, url])
    stem = Path(c['dossier']).stem
    companies.append(dict(id=stem, **c, body=text, sources=refs,
      dossierUrl=rel(COMPANIES / c['dossier']),
      readableSummary=PRESENTATION['companies'].get(stem, c.get('main_risk', ''))))

# Column F holds the first gate (workspace gates.all_roles_columns[0]); the field keeps that gate's key.
FIRST_GATE_COLUMN = (ws.gates().get('all_roles_columns') or ['location'])[0] if hasattr(ws, 'gates') else 'location'
research = []
pool_by_url = {j['original_url']: j['pool_id'] for j in POOL_JOBS}
for n, row in enumerate(all_roles[ALL_HEAD:], ALL_HEAD + 1):
    if len(row) < 4 or not row[2]: continue
    cell = lambda i: row[i] if len(row) > i and row[i] is not None else ''
    research.append(dict(id=f'research-{n}', company=cell(2), role=cell(3), decision=cell(0), fit=cell(1),
      tech=cell(4), **{FIRST_GATE_COLUMN: cell(5)}, hours=cell(6), payGate=cell(7), location=cell(8), model=cell(9),
      contract=cell(10), pay=cell(11), oncall=cell(12), why=cell(13), risk=cell(14), checked=cell(15), applicationState=cell(16), disposition=cell(17), nextAction=cell(18),
      originalUrl=cell(21), poolId=pool_by_url.get(cell(21)),
      source=SHEET_URL + f'#gid={gid("all_roles")}&range=A{n}:W{n}'))

# Application preparation is separate from submission and pool membership.
for prepared_path in sorted(DATA_DIR.glob(INSTANCE.get('prepared_glob', 'apply-*/prepared.json'))):
    for item in json.loads(prepared_path.read_text())['items']:
        if item.get('state') == 'Applied' or any(m['key'] == item['key'] for m in SUBMISSIONS): continue
        match = next((r for r in R if r['id'] == item['key']), None)
        if match:
            match['applicationPreparation'] = item
            date = item.get('prepared_at', prepared_path.parent.name.removeprefix('apply-'))[:10]
            match['timeline'].append([date, 'Application draft prepared; not submitted. ' + item['next_step']])


def section(text, start, end):
    """Text between two '## ' headings; empty when the start heading is absent."""
    if start not in text:
        return ''
    body = text.split(start, 1)[1]
    return body.split(end, 1)[0] if end in body else re.split(r'(?m)^## ', body, maxsplit=1)[0]


fallback = INSTANCE.get('status_fallback')
status_file = LATEST_STATUS or (DATA_DIR / fallback if fallback and (DATA_DIR / fallback).is_file() else None)
status = status_file.read_text() if status_file else ''
updates = []
for number, body in re.findall(r'(?m)^(\d+)\. (.+)$', section(status, '## Tracker changes made', '## Threads opened')):
    title = re.match(r'\*\*(.+?)\*\*', body)
    updates.append(dict(number=int(number), title=title.group(1).rstrip(':') if title else body[:90], detail=body, state='Applied and read-back verified'))

appdocs = []
for f in sorted(APPLICATIONS.glob('*/application.md')) if APPLICATIONS.is_dir() else []:
    text = f.read_text(); appdocs.append(dict(company=f.parent.name, title=(text.splitlines() or [f.parent.name])[0].lstrip('# '), path=rel(f), body=text))

summary_text = LATEST_SUMMARY.read_text() if LATEST_SUMMARY else ''
if LATEST_STATUS != LATEST_SUMMARY:
    status = '\n\n---\n\n'.join(x for x in (summary_text, status) if x)
PLANS = opt_path('plans', 'plans')
plan_file = DATA_DIR / INSTANCE['plan_document'] if INSTANCE.get('plan_document') else (sorted(PLANS.glob('????-??-??*.md'))[-1:] or [None])[0] if PLANS.is_dir() else None
plan_text = plan_file.read_text() if plan_file and plan_file.is_file() else ''
plan_document = '\n\n---\n\n'.join(x for x in (summary_text, plan_text) if x)


def fill(value):
    """Format {queue}/{pool}/... counts, {latest_summary}/{plan} links, {sheet_checked_at}/{as_of} in instance text."""
    if isinstance(value, str):
        links = dict(latest_summary=rel(LATEST_SUMMARY) if LATEST_SUMMARY else '#', plan=rel(plan_file) if plan_file else '#',
                     sheet_checked_at=SHEET.get('checked_at', ''), as_of=AS_OF)
        return re.sub(r'\{(\w+)\}', lambda m: str({**POOL_COUNTS, **links}.get(m.group(1), m.group(0))), value)
    if isinstance(value, list): return [fill(x) for x in value]
    if isinstance(value, dict): return {k: fill(v) for k, v in value.items()}
    return value


search = ws.load().get('search', {})
DEFAULT_CONSTRAINTS = dict(role=' / '.join(search.get('role_titles', [])[:2]) or 'Target roles in profile', location=PERSON.get('location', ''),
    hours=search.get('work_model', ''), money='See profile preferences', term='See profile preferences', pager='See profile preferences')
DEFAULT_COVERAGE = [dict(name='Tracker', state='Read', detail='Operational tabs captured in the tracker snapshot.', date=SHEET.get('checked_at', ''))]
DEFAULT_SOURCES = [['Latest status', '{latest_summary}', 'Current stages, owners and dates'], ['Application plan', '{plan}', 'Priority queue and drafts']]
gate_text = [('Country & hiring route', 'Location fits the advert'), ('Approved compensation', 'Advert supports this'),
             ('Hours & support', 'Advert supports this'), ('Long-term agreement', 'Permanent role advertised')]
ui = dict(self=SELF, avatar=''.join(w[0] for w in PERSON['name'].split()[:2]).upper(), allRolesTab=ws.tab_title('all_roles'),
          gates=[dict(label=label, key=key, title=(UI.get('gateText', {}).get(label) or gate_text[min(i, 3)])[0],
                      confirmed=(UI.get('gateText', {}).get(label) or gate_text[min(i, 3)])[1]) for i, (label, key) in enumerate(GATES)],
          statusDocumentUrl=rel(LATEST_SUMMARY) if LATEST_SUMMARY else '#', planDocumentUrl=rel(plan_file) if plan_file else '#',
          companiesBase=rel(COMPANIES) + '/', statusUrl=rel(status_file) if status_file else '#')
ui.update(fill({k: v for k, v in UI.items() if k not in ('title', 'description', 'northStar', 'snapshotPill', 'footerEvidence', 'gateText')}))

DATA = dict(
    product=INSTANCE.get('product', 'Waypoint'), asOf=AS_OF, timezone=TZ,
    builtAt=datetime.now(timezone.utc).isoformat(), sheetReadAt=SHEET.get('checked_at', ''),
    sheetUrl=SHEET_URL, opportunities=R, companies=companies, research=research, reconciliation=POOL_COUNTS, poolCounts=POOL_COUNTS, publicationRevision=POOL_REVIEW['revision'],
    poolAudit=[dict(poolId=j['pool_id'], company=j['company'], role=j['original_title'], bucket=j['bucket'], verificationState=j['verification_state'],
        checkedAt=j['checked_at'], appliedDate=j.get('applied_date'), applicationState=j['application_state'], sourceUrl=j['original_url'], nextAction=j['next_action'], gates=j['gates'],
        companyId=Path(j['background']['path']).stem, brief=PRESENTATION['jobs'][j['pool_id']]) for j in POOL_JOBS],
    sourceTabs=[dict(name=x['sheet'], sheetId=x['sheet_id'], range=x['range'], values=x['values'], checkedAt=x.get('checked_at', SHEET.get('checked_at', '')), url=SHEET_URL + f"#gid={x['sheet_id']}") for x in SHEET['sheets']],
    updates=updates, applicationDocs=appdocs,
    statusDocument=status, planDocument=plan_document,
    constraints=fill(INSTANCE.get('constraints', DEFAULT_CONSTRAINTS)),
    tasks=fill(INSTANCE.get('tasks', [])),
    coverage=SHEET.get('coverage', fill(INSTANCE.get('coverage', DEFAULT_COVERAGE))),
    sources=fill(INSTANCE.get('sources', DEFAULT_SOURCES)),
    ui=ui)

REDACT = [re.compile(p) for p in INSTANCE.get('redact_patterns', [])]


def sanitize(value):
    if isinstance(value, str):
        for pattern in REDACT:
            value = pattern.sub('[phone omitted]', value)
        return value
    if isinstance(value, list): return [sanitize(x) for x in value]
    if isinstance(value, dict): return {k: sanitize(v) for k, v in value.items()}
    return value


DATA = sanitize(DATA)
# Consistency with the tracker readback. The count line is optional (empty trackers).
current_count = re.match(r'(\d+) current processes', str(pipeline[2][0])) if len(pipeline) > 2 and pipeline[2] else None
assert current_count is None or len([r for r in R if r['group'] == 'current']) == int(current_count.group(1)), 'Current process count differs from the working tracker'
assert len([r for r in R if r['group'] == 'target']) == POOL_COUNTS['priority']
closed_count = sum(bool(row and len(row) > 1 and (EMPLOYER_CLOSED.match(str(row[1])) or (str(row[1]).startswith('Closed ') and 'employer rejection' in row[1]))) for row in pipeline[PIPE_HEAD:])
assert len([r for r in R if r['group'] == 'closed']) == closed_count, 'Employer-closed (rejected or closed by employer) count differs from the working tracker'
assert len(companies) == len(company_index)
assert len(appdocs) == (len(list(APPLICATIONS.glob('*/application.md'))) if APPLICATIONS.is_dir() else 0)
assert {r['poolId'] for r in R if r.get('poolId')} == {j['pool_id'] for j in QUEUE}
assert len({r['id'] for r in R}) == len(R)

e = lambda s: htmllib.escape(str(s), quote=True)
nice = lambda d: datetime.fromisoformat(d[:10]).strftime('%-d %b') if re.match(r'\d{4}-\d{2}-\d{2}', str(d)) else str(d)
page = {
    '{{TITLE}}': e(UI.get('title', f'Waypoint — {SELF}’s search workspace')),
    '{{DESCRIPTION}}': e(UI.get('description', f'Waypoint — a private job-search workspace for {PERSON["name"]}. Evidence, opportunities and the next move in one place.')),
    '{{NORTH_STAR}}': '<br>'.join(e(x) for x in UI.get('northStar', [' / '.join(search.get('role_titles', [])[:1]) or 'Your target roles', search.get('work_model', '')]) if x),
    '{{AVATAR}}': e(ui['avatar']), '{{PERSON_NAME}}': e(PERSON['name']),
    '{{SNAPSHOT_PILL}}': e(UI.get('snapshotPill', nice(AS_OF) + ' snapshot')),
    '{{FOOTER_EVIDENCE}}': e(UI.get('footerEvidence', f'Evidence as of {nice(AS_OF)} {AS_OF[:4]} · {TZ}')),
}
encoded = json.dumps(DATA, ensure_ascii=False).replace('</', '<\\/').replace('\u2028', '\\u2028').replace('\u2029', '\\u2029')
html = (HERE / 'src/template.html').read_text()
for key, value in page.items():
    html = html.replace(key, value)
instance_css = DASH / 'data/instance.css'  # optional per-instance styles, e.g. company logo colours
html = html.replace('/*__STYLES__*/', (HERE / 'src/styles.css').read_text().replace('/*__INSTANCE_STYLES__*/', instance_css.read_text().strip() if instance_css.is_file() else '')).replace('/*__DATA__*/', 'const DATA = ' + encoded + ';').replace('/*__APP__*/', (HERE / 'src/presentation.js').read_text() + '\n' + (HERE / 'src/app.js').read_text())
(DASH / 'data').mkdir(parents=True, exist_ok=True)
(DASH / 'index.html').write_text(html)
(DASH / 'data/reviewed-data.json').write_text(json.dumps(DATA, ensure_ascii=False, indent=2))
print(f'Built index.html: {len(html.encode()):,} bytes; {len(R)} opportunities; {len(research)} research rows; {len(companies)} firm dossiers; {len(updates)} applied updates.')
