"""Spec-driven tracker publication: plan -> (MCP batchUpdate) -> verify -> finalize.

Replaces the per-event publish.py copies. Google Sheets writes still go through the
Sheets connector (no local credentials); this tool produces the exact payloads,
the ranges to read back, checks the readback, and does all local work.

  python3 tools/tracker_publish.py plan SPEC.json
      -> OUTDIR/requests.json (pass verbatim to update_spreadsheet)
         OUTDIR/readback-ranges.json (pass each range to get_values)
  python3 tools/tracker_publish.py verify OUTDIR READBACK.json [--find-replace N,M]
      READBACK.json: list of raw get_values responses ({"range","values"}), any order.
  python3 tools/tracker_publish.py attest OUTDIR RANGE... --note TEXT [--find-replace N,M]
      when the connector output can't be saved: record which ranges were read back and compared.
  python3 tools/tracker_publish.py finalize OUTDIR
      writes pool/manifest/catalogue/dashboard data, moves the base pointer,
      rebuilds the dashboard and runs every consistency check.

Spec (JSON):
{
  "label": "6 Nov status", "date": "2026-11-06", "outdir": "<paths.status>/evidence-2026-11-06",
  "pool": {"pool-15": {"bucket": "Rejected", "application_state": "...", "next_action": "..."}},
  "active_pipeline": {
     "edit":   [{"match": "Acme ·", "set": {"B": "...", "H": "..."}, "append": {"I": "\\nhttps://..."}}],
     "insert": [{"after": "Example Co", "row": ["A", "B", "C", "D", "E", "F", "G", "H", "I"]}]},
  "new_jobs": [{"job": {<full pool record without pool_id; original_url required>},
                "presentation": {"company","role","work","fit","watch","question","location","pay"},
                "decision_cell": "Screen first", "tech_fit": "7.5", "company_summary": "dashboard firm summary (default: background.main_risk)", "stage_evidence": "...", "background_cell": "..."}],
  "shortlist_status": {"pool-04": "Interviewing"},
  "presentation": {"pool-92": {"watch": "...", "question": "..."}},
  "headlines": {"pipeline": ["row 2", "row 3"], "queue": ["row 2", "row 3"], "shortlist": ["row 2", "row 3"]},
  "snapshot_note": "dashboard capture note"
}
Shortlist rows that match a changed pool job (exact company + original title) follow the pool:
R = next_action; Q (Status) = the explicit shortlist_status if given (one of SHORTLIST_STATUS),
else Rejected/Withdrawn from the bucket, else Applied when the row still says Not contacted
(Interviewing/Offer/On hold are never downgraded); T, when it holds the derived
"<bucket>; audit only; revision <rev>" form, is rewritten with the current bucket.
A pool entry that replaces "background" also rewrites that job's All roles W company line and
its dashboard firm summary; "presentation" updates an existing job's dashboard brief fields.
Closed candidacies in Active pipeline B start with "Rejected <date>" or
"Closed by employer <date>" (for example a filled role); the dashboard groups both as closed.
Optional live_readback points to a fresh five-tab readback with a sheets array.
After reviewing drift, use it to compute writes against actual live cells while
preserving the finalized local base as the intended starting state. This repairs
missed publication batches without silently adopting an older live revision.

new_jobs (scout additions) get the next pool ids, an appended All roles row (A:W from the
record), a monitor-manifest entry and an editorial brief; Queue/Audit rows follow from the pool.
All roles Q:T is derived from the pool (R = "<bucket>; original <verification_state>", the
rule check_job_views enforces). Unchanged rows keep their reconciled date; only the
revision is swapped (findReplace).

Tab titles, sheet ids, header rows and every path come from workspace.json. Headline
keys may be tab roles (queue, pipeline, shortlist) or the configured tab titles.
"""
import copy, json, re, subprocess, sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from tools import workspace as ws  # noqa: E402
from tools.job_pool import counts, load_current, queue_jobs, revision, sheet_rows, validate  # noqa: E402

ROOT = ws.root()
POINTER = ws.path('tracker_base')
DASH_DATA = ws.path('dashboard') / 'data'
AUTOMATION = ws.path('automation')
T = {k: ws.tab_title(k) for k in ws.TAB_KEYS}
H = {k: ws.header_row(k) for k in ws.TAB_KEYS}
WIDTH = {T['all_roles']: 23, T['queue']: 13, T['audit']: 13, T['pipeline']: 9, T['shortlist']: 20}
COL = {c: i for i, c in enumerate('ABCDEFGHIJKLMNOPQRSTUVW')}
SHORTLIST_STATUS = ('Not contacted', 'Asked screening Qs', 'Applied', 'Interviewing', 'Offer', 'On hold', 'Rejected', 'Withdrawn')
BUCKET_STATUS = {'Rejected': 'Rejected', 'Withdrawn': 'Withdrawn'}
READINESS = re.compile(r'^.+; audit only; revision [0-9a-f]{16}$')
read = lambda p: json.loads(Path(p).read_text())


def background_cell(bg):
    """All roles W: the dated company-background line derived from a pool record's background."""
    return f"{bg['checked_at']} — {bg['judgement']}. {bg['main_risk']} {bg['path']}"


def shortlist_sync(row, job, rev, status=None):
    """Bring a Shortlist row that mirrors a pool job in line with it (R, Q, derived T)."""
    row[17] = job['next_action']
    status = status or BUCKET_STATUS.get(job['bucket'])
    if status:
        row[16] = status
    elif job['bucket'] == 'Applied' and str(row[16]).strip() in ('', 'Not contacted'):
        row[16] = 'Applied'
    if READINESS.match(str(row[19])):
        row[19] = f"{job['bucket']}; audit only; revision {rev}"


def dump(p, v):
    Path(p).write_text(json.dumps(v, ensure_ascii=False, indent=2) + '\n')


def cell(rows, r, c):
    value = rows[r][c] if r < len(rows) and c < len(rows[r]) else ''
    return '' if value is None else value


def a1(sheet, r0, c0, c1):
    return f"'{sheet}'!{'ABCDEFGHIJKLMNOPQRSTUVW'[c0]}{r0 + 1}:{'ABCDEFGHIJKLMNOPQRSTUVW'[c1 - 1]}{r0 + 1}"


def heading(heads, key):
    return heads.get(key, heads.get(T[key]))


def quote_range(rng):
    sheet, _, cells = rng.rpartition('!')
    return rng if not sheet or sheet.startswith("'") else f"'{sheet}'!{cells}"


def base_path():
    return ROOT / read(POINTER)['readback']


def plan(spec_path):
    spec = read(spec_path); out = ROOT / spec['outdir']; out.mkdir(parents=True, exist_ok=True)
    dump(out / 'spec.json', spec)
    state = load_current(); old = state['revision']
    dump(out / 'pool-before.json', state)
    base = read(base_path()); orig = {s['sheet']: s['values'] for s in base['sheets']}; tabs = copy.deepcopy(orig)
    if spec.get('live_readback'):
        live = read(ROOT / spec['live_readback'])
        live_tabs = {s['sheet']: s['values'] for s in live['sheets']}
        assert all(name in live_tabs for name in orig), 'live_readback must cover every managed tab'
        orig = {name: live_tabs[name] for name in orig}
    ids = {s['sheet']: s['sheet_id'] for s in base['sheets']}
    by = {j['pool_id']: j for j in state['jobs']}
    for pid, fields in spec.get('pool', {}).items():
        by[pid].update(fields)
    statuses = spec.get('shortlist_status', {})
    for pid, s in statuses.items():
        assert pid in by, f'shortlist_status: unknown pool id {pid}'
        assert s in SHORTLIST_STATUS, f'shortlist_status {pid}: {s!r} not one of {SHORTLIST_STATUS}'
    AR = T['all_roles']; added = []
    next_id = max(int(j['pool_id'].split('-')[1]) for j in state['jobs']) + 1 if state['jobs'] else 1
    for n in spec.get('new_jobs', []):
        job = dict(n['job']); job.setdefault('original_url', job['url']); job.setdefault('original_title', job['title'])
        assert all(j['original_url'] != job['original_url'] for j in state['jobs']), 'already in pool: ' + job['original_url']
        assert not any(len(r) > 21 and r[21] == job['original_url'] for r in tabs[AR][H['all_roles']:]), 'already in All roles: ' + job['original_url']
        job['pool_id'] = f'pool-{next_id}'; next_id += 1
        job['catalogue_row'] = len(tabs[AR]) + 1
        g = job['gates']; bg = job['background']
        tabs[AR].append([n.get('decision_cell', job['decision']), str(n.get('tech_fit', job.get('technical_fit', ''))), job['company'], job['title'],
                         job['required_tech'], *[g.get(k, 'unclear') for k in ws.gates().get('all_roles_columns', ['romania', 'hours', 'pay'])],
                         job['location_text'], job['work_model'], job['contract_text'], job['pay_published'], job['hours_oncall'], job['why_fits'],
                         job['main_risk_and_first_question'], job['checked_at'], job['application_state'], '', job['next_action'], '',
                         n.get('stage_evidence', job['url']), job['original_url'],
                         n.get('background_cell', background_cell(bg))])
        state['jobs'].append(job); by[job['pool_id']] = job; added.append(dict(pool_id=job['pool_id'], presentation=n['presentation'], company_id=Path(bg['path']).stem,
                          company_summary=n.get('company_summary', bg['main_risk'])))
    state.update(as_of=spec['date'], source_snapshot=spec['outdir'], revision=revision(state['jobs']))
    validate(state); rev = state['revision']; queue = queue_jobs(state['jobs'])
    changed = set(spec.get('pool', {})) | {a['pool_id'] for a in added}
    AR, Q, AU, AP, SL = (T[k] for k in ('all_roles', 'queue', 'audit', 'pipeline', 'shortlist'))
    for job in state['jobs']:
        row = next(r for r in tabs[AR][H['all_roles']:] if len(r) > 21 and r[21] == job['original_url'])
        if job['pool_id'] in changed:
            row[16:20] = [job['application_state'], f"{job['bucket']}; original {job['verification_state']}",
                          job['next_action'], f"{spec['date']}; publication {rev}"]
            if 'background' in spec.get('pool', {}).get(job['pool_id'], {}) and len(row) > 22:
                row[22] = background_cell(job['background'])
        else:
            row[19] = str(row[19]).replace(old, rev)
    heads = spec.get('headlines', {})
    q_head = heading(heads, 'queue') or [f"{spec['label']}. {len(queue)} queued. Revision {rev}", '']
    for name, key, members in [(Q, 'queue', queue), (AU, 'audit', state['jobs'])]:
        prev = tabs[name]; h = H[key]; assert h >= 3, f'{name}: headline rows 2-3 must precede the header'
        tabs[name] = [prev[0], [q_head[0]], [q_head[1].replace('{rev}', rev)]] + prev[3:h] + sheet_rows(members)
        if len(tabs[name]) < len(prev):
            tabs[name] += [[''] * 13] * (len(prev) - len(tabs[name]))
    ap = tabs[AP]; inserts = []
    for e in spec.get('active_pipeline', {}).get('edit', []):
        hits = [i for i, r in enumerate(ap) if r and str(r[0]).startswith(e['match'])]
        assert len(hits) == 1, f"Active pipeline match {e['match']!r}: {len(hits)} rows"
        r = ap[hits[0]]; r += [''] * (9 - len(r))
        for c, v in e.get('set', {}).items(): r[COL[c]] = v
        for c, v in e.get('append', {}).items():
            if v.strip() not in r[COL[c]]: r[COL[c]] += v
    for ins in spec.get('active_pipeline', {}).get('insert', []):
        at = next(i for i, r in enumerate(ap) if r and str(r[0]).startswith(ins['after'])) + 1
        assert len(ins['row']) == 9; ap.insert(at, ins['row']); inserts.append(at)
    if heading(heads, 'pipeline'): ap[1], ap[2] = [heading(heads, 'pipeline')[0]], [heading(heads, 'pipeline')[1]]
    sl = tabs[SL]
    if heading(heads, 'shortlist'): sl[1], sl[2] = [heading(heads, 'shortlist')[0]], [heading(heads, 'shortlist')[1].replace('{rev}', rev)]
    for row in sl[H['shortlist']:]:
        if len(row) >= 20:
            row[19] = str(row[19]).replace(old, rev)
            match = next((j for j in state['jobs'] if row[3:5] == [j['company'], j['original_title']]), None)
            if match and (match['pool_id'] in changed or match['pool_id'] in statuses):
                shortlist_sync(row, match, rev, statuses.get(match['pool_id']))
    reqs = [{'findReplace': {'find': old, 'replacement': rev, 'sheetId': ids[n], 'matchCase': True}} for n in (AR, SL)] if old != rev else []
    expect_fr = [sum(old in str(c) for r in orig[n] for c in r) for n in (AR, SL)] if old != rev else [0, 0]  # Sheets reports cells changed, not rows
    for at in inserts:
        reqs.append({'insertDimension': {'range': {'sheetId': ids[AP], 'dimension': 'ROWS', 'startIndex': at, 'endIndex': at + 1}, 'inheritFromBefore': True}})
        reqs.append({'copyPaste': {'source': {'sheetId': ids[AP], 'startRowIndex': at - 1, 'endRowIndex': at, 'startColumnIndex': 0, 'endColumnIndex': 9},
                     'destination': {'sheetId': ids[AP], 'startRowIndex': at, 'endRowIndex': at + 1, 'startColumnIndex': 0, 'endColumnIndex': 9}, 'pasteType': 'PASTE_FORMAT'}})

    grid = {s['sheet']: _parse(f"'{s['sheet']}'!{s['range']}")[3] + 1 for s in base['sheets'] if s.get('range')}
    for name, rows in tabs.items():
        extra = len(rows) + (len(inserts) if name == AP else 0) - grid.get(name, len(rows))
        if name != AP and extra > 0:
            reqs.append({'appendDimension': {'sheetId': ids[name], 'dimension': 'ROWS', 'length': extra}})

    for addition in added:
        row = by[addition['pool_id']]['catalogue_row'] - 1
        source = next((i for i in range(row - 1, H['all_roles'] - 1, -1)
                       if cell(tabs[AR], i, 0) == cell(tabs[AR], row, 0)), row - 1)
        for paste_type in ('PASTE_FORMAT', 'PASTE_DATA_VALIDATION'):
            reqs.append({'copyPaste': {'source': {'sheetId': ids[AR], 'startRowIndex': source, 'endRowIndex': source + 1, 'startColumnIndex': 0, 'endColumnIndex': WIDTH[AR]},
                         'destination': {'sheetId': ids[AR], 'startRowIndex': row, 'endRowIndex': row + 1, 'startColumnIndex': 0, 'endColumnIndex': WIDTH[AR]}, 'pasteType': paste_type}})

    def src_index(name, ri):
        if name != AP: return ri
        return ri - sum(1 for at in inserts if at < ri) if ri not in inserts else None
    changes, ranges = [], []
    for name, rows in tabs.items():
        for ri in range(len(rows)):
            sri = src_index(name, ri)
            if sri is None: ch = list(range(9))
            else:
                ch = [c for c in range(WIDTH[name]) if str(cell(rows, ri, c)) != str(cell(orig[name], sri, c))]
                ch = [c for c in ch if not (name in (AR, SL) and str(cell(orig[name], sri, c)).replace(old, rev) == str(cell(rows, ri, c)))]
            if not ch: continue
            s, e = min(ch), max(ch) + 1
            vals = [cell(rows, ri, c) for c in range(s, e)]
            reqs.append({'updateCells': {'range': {'sheetId': ids[name], 'startRowIndex': ri, 'endRowIndex': ri + 1, 'startColumnIndex': s, 'endColumnIndex': e},
                         'rows': [{'values': [{'userEnteredValue': {'numberValue': v} if isinstance(v, (int, float)) else {'stringValue': str(v)}} for v in vals]}], 'fields': 'userEnteredValue'}})
            ranges.append(dict(range=a1(name, ri, s, e), values=[[str(v) for v in vals]]))
            changes += [dict(sheet=name, row=ri, column=c, value=cell(rows, ri, c)) for c in range(s, e)]
    for at in inserts:
        reqs.append({'autoResizeDimensions': {'dimensions': {'sheetId': ids[AP], 'dimension': 'ROWS', 'startIndex': at, 'endIndex': at + 1}}})
    dump(out / 'pool-planned.json', state); dump(out / 'planned-values.json', tabs); dump(out / 'new-jobs.json', added)
    dump(out / 'requests.json', reqs); dump(out / 'changes.json', changes)
    dump(out / 'readback-ranges.json', dict(ranges=ranges, find_replace_expected=expect_fr))
    print(json.dumps(dict(revision=rev, requests=len(reqs), changed_cells=len(changes),
                          readback_ranges=[r['range'] for r in ranges], find_replace_expected=expect_fr, **counts(state['jobs'])), ensure_ascii=False))


A1 = re.compile(r"^'?(.*?)'?!([A-Z]+)(\d+)(?::([A-Z]+)(\d+))?$")


def _col(letters):
    n = 0
    for ch in letters:
        n = n * 26 + ord(ch) - 64
    return n - 1


def _parse(rng):
    m = A1.match(rng)
    sheet, c0, r0, c1, r1 = m.groups()
    return sheet, int(r0) - 1, _col(c0), int(r1 or r0) - 1, _col(c1 or c0)


def _lookup(got, rng):
    """Values for rng from any readback block that covers it (exact or larger range)."""
    sheet, r0, c0, r1, c1 = _parse(rng)
    for block, values in got.items():
        bs, br0, bc0, br1, bc1 = _parse(block)
        if bs == sheet and br0 <= r0 and bc0 <= c0 and r1 <= br1 and c1 <= bc1:
            rows = []
            for r in range(r0, r1 + 1):
                row = values[r - br0] if r - br0 < len(values) else []
                rows.append([str(row[c - bc0]) if c - bc0 < len(row) and row[c - bc0] is not None else '' for c in range(c0, c1 + 1)])
            return rows
    return None


def verify(outdir, readback_file, find_replace=None):
    """READBACK.json: list of raw get_values responses. Each may be the exact changed range
    or any larger block covering it (e.g. a whole tab), so a few reads can verify many ranges."""
    out = ROOT / outdir; exp = read(out / 'readback-ranges.json'); got = read(readback_file)
    got = {quote_range(g['range']): g.get('values', []) for g in (got if isinstance(got, list) else [got])}
    items = []
    for r in exp['ranges']:
        g = _lookup(got, r['range'])
        ok = g is not None and g[0] == [str(v) for v in r['values'][0]]
        items.append(dict(range=r['range'], match=ok, missing=g is None))
    fr_ok = find_replace is None or list(find_replace) == exp['find_replace_expected']
    res = dict(checked_at=__import__('datetime').datetime.now(__import__('datetime').timezone.utc).isoformat(timespec='seconds'),
               method='Sheets connector values.get of every changed range; findReplace replies compared with planned counts',
               all_match=all(i['match'] for i in items) and fr_ok, find_replace=dict(expected=exp['find_replace_expected'], got=find_replace), items=items)
    dump(out / 'readback-checks.json', res)
    bad = [i['range'] for i in items if not i['match']]
    print(json.dumps(dict(all_match=res['all_match'], mismatched=bad, find_replace_ok=fr_ok)))
    sys.exit(0 if res['all_match'] else 1)


def attest(outdir, read_ranges, note, find_replace=None):
    """Record a readback the agent compared by reading the connector output itself (no file).
    Honest label: method says agent comparison; every planned range must fall inside a read range."""
    out = ROOT / outdir; exp = read(out / 'readback-ranges.json')
    blocks = {quote_range(r): None for r in read_ranges}
    items = []
    for r in exp['ranges']:
        sheet, r0, c0, r1, c1 = _parse(r['range'])
        covered = any((lambda b: b[0] == sheet and b[1] <= r0 and b[2] <= c0 and r1 <= b[3] and c1 <= b[4])(_parse(b)) for b in blocks)
        items.append(dict(range=r['range'], match=covered, missing=not covered))
    fr_ok = find_replace is None or list(find_replace) == exp['find_replace_expected']
    res = dict(checked_at=__import__('datetime').datetime.now(__import__('datetime').timezone.utc).isoformat(timespec='seconds'),
               method='Agent compared Sheets connector get_values output with planned values (attested, not machine-diffed): ' + note,
               read_ranges=list(blocks), all_match=all(i['match'] for i in items) and fr_ok,
               find_replace=dict(expected=exp['find_replace_expected'], got=find_replace), items=items)
    dump(out / 'readback-checks.json', res)
    print(json.dumps(dict(all_match=res['all_match'], uncovered=[i['range'] for i in items if not i['match']], find_replace_ok=fr_ok)))
    sys.exit(0 if res['all_match'] else 1)


def run_checks():
    dash = ws.path('dashboard').relative_to(ROOT)
    cmds = [['python3', f'{dash}/build.py'], ['python3', 'tools/check_job_views.py'],
            ['node', '--max-old-space-size=64', f'{dash}/qa-static.mjs'],
            ['python3', '-m', 'pytest', '-q', 'tools/test_job_pool.py', 'tools/test_job_views.py', 'tools/test_job_refresh.py', 'tools/test_tracker_publish.py', 'tools/test_ats_census.py']]
    for c in cmds:
        script = next((a for a in c[1:] if a.endswith(('.py', '.mjs')) and not a.startswith('tools/test_')), None)
        if script and not (ROOT / script).is_file():
            print(f'skip {" ".join(c)} :: {script} not present in this workspace'); continue
        p = subprocess.run(c, cwd=ROOT, capture_output=True, text=True)
        tail = (p.stdout + p.stderr).strip().splitlines()[-1:] or ['']
        print(f"{'ok ' if p.returncode == 0 else 'FAIL'} {' '.join(c)} :: {tail[0][:140]}")
        if p.returncode: print((p.stdout + p.stderr)[-2000:]); sys.exit(1)


def finalize(outdir):
    out = ROOT / outdir; spec = read(out / 'spec.json')
    tabs = read(out / 'planned-values.json'); base = read(base_path())
    meta = {s['sheet']: {k: v for k, v in s.items() if k != 'values'} for s in base['sheets']}
    state = validate(read(out / 'pool-planned.json')); rev = state['revision']
    assert load_current()['revision'] == read(out / 'pool-before.json')['revision'], 'pool changed since plan'
    rb = read(out / 'readback-checks.json'); assert rb['all_match'], rb
    now = rb['checked_at']; state['published_at'] = now
    for name, rows in tabs.items():
        if meta[name].get('range'):
            _, r0, c0, r1, c1 = _parse(f"'{name}'!{meta[name]['range']}")
            if r0 == 0 and c0 == 0:
                meta[name]['range'] = f"A1:{'ABCDEFGHIJKLMNOPQRSTUVW'[c1]}{max(r1 + 1, len(rows))}"
    sheets = [dict(meta[n], values=[[('' if v is None else str(v)) for v in r] for r in rows], checked_at=now) for n, rows in tabs.items()]
    dump(out / 'tracker-readback.json', dict(checked_at=now, method=rb['method'], sheets=sheets))
    by = {j['pool_id']: j for j in state['jobs']}
    manifest = read(AUTOMATION / 'pool.json'); manifest['revision'] = rev
    for m in manifest['jobs']:
        if m['pool_id'] in spec.get('pool', {}): m['application_state'] = by[m['pool_id']]['application_state']
    added = read(out / 'new-jobs.json') if (out / 'new-jobs.json').is_file() else []
    for a in added:
        j = by[a['pool_id']]
        manifest['jobs'].append({k: j[k] for k in ('pool_id', 'company', 'title', 'original_url', 'url', 'application_state', 'original_title', 'verification_state')})
    cat = read(AUTOMATION / 'catalogue.json')
    cat.update(checked_at=spec['date'], published_revision=rev, supporting_views_pending=False)
    cat['jobs'] = [dict(company=r[2], title=r[3], application_state=r[16], disposition=r[17], next_action=r[18], original_url=r[21], source_checked_at=r[15])
                   for r in tabs[T['all_roles']][H['all_roles']:] if len(r) > 21 and r[2]]
    snap = read(DASH_DATA / 'tracker-snapshot.json')
    snap.update(checked_at=now, publication_revision=rev, sheets=sheets, capture_note=spec.get('snapshot_note', spec['label']))
    pres = read(DASH_DATA / 'presentation.json'); pres['source_revision'] = rev
    for a in added:
        pres['jobs'][a['pool_id']] = a['presentation']
        pres['companies'].setdefault(a['company_id'], a['company_summary'])
    for pid, fields in spec.get('presentation', {}).items():
        assert pid in pres['jobs'], f'presentation: no dashboard brief for {pid}'
        pres['jobs'][pid].update(fields)
    for pid, fields in spec.get('pool', {}).items():
        if 'background' in fields:
            bg = by[pid]['background']
            pres['companies'][Path(bg['path']).stem] = bg['main_risk']
    # dossiers kept for firms without a pool record (held or rejected leads) still need a dashboard summary
    index = ws.path('companies') / 'index.json' if 'companies' in ws.load()['paths'] else None
    if index and index.is_file():
        for c in read(index).get('companies', []):
            if c.get('dossier'):
                pres['companies'].setdefault(Path(c['dossier']).stem, c.get('main_risk', ''))
    for p, v in [(ws.path('pool'), state), (AUTOMATION / 'pool.json', manifest),
                 (AUTOMATION / 'catalogue.json', cat), (DASH_DATA / 'tracker-snapshot.json', snap),
                 (DASH_DATA / 'presentation.json', pres)]:
        dump(p, v)
    dump(POINTER, dict(readback=str((out / 'tracker-readback.json').relative_to(ROOT)), revision=rev, updated=now))
    print(json.dumps(dict(revision=rev, **counts(state['jobs']))))
    run_checks()


if __name__ == '__main__':
    cmd, *a = sys.argv[1:]
    if cmd == 'plan': plan(a[0])
    elif cmd == 'verify':
        fr = None
        if '--find-replace' in a: fr = [int(x) for x in a[a.index('--find-replace') + 1].split(',')]
        verify(a[0], a[1], fr)
    elif cmd == 'attest':
        fr = [int(x) for x in a[a.index('--find-replace') + 1].split(',')] if '--find-replace' in a else None
        note = a[a.index('--note') + 1] if '--note' in a else ''
        rngs = [x for x in a[1:] if not x.startswith('--') and x not in (note,) and (fr is None or x != a[a.index('--find-replace') + 1])]
        attest(a[0], rngs, note, fr)
    elif cmd == 'finalize': finalize(a[0])
    elif cmd == 'checks': run_checks()
    else: sys.exit(__doc__)
