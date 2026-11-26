"""Read-only, stdlib consistency check of the published pool and local readbacks.

This verifies captured Sheets values, not a fresh network read. After authorized
online edits, capture the five operational tabs before running this check.
Every path, tab title, sheet id and gate key comes from workspace.json.
"""
import json
import re
try:
    from tools import workspace as ws
    from tools.job_pool import ROOT, load_current, queue_jobs, sheet_rows, counts
except ModuleNotFoundError:
    import workspace as ws
    from job_pool import ROOT, load_current, queue_jobs, sheet_rows, counts


def rel(key, *parts):
    """Workspace-relative path string for paths.<key>/<parts>."""
    return str(ws.path(key).joinpath(*parts).relative_to(ws.root()))


def read(relative):
    return json.loads((ROOT / relative).read_text())


def check():
    state = load_current()
    jobs, rev = state['jobs'], state['revision']
    queue = queue_jobs(jobs)
    T = {k: ws.tab_title(k) for k in ws.TAB_KEYS}
    H = {k: ws.header_row(k) for k in ws.TAB_KEYS}  # 1-based header row == 0-based first data row
    gates = ws.gates()
    snapshot = read(rel('dashboard', 'data', 'tracker-snapshot.json'))
    dashboard = read(rel('dashboard', 'data', 'reviewed-data.json'))
    presentation = read(rel('dashboard', 'data', 'presentation.json'))
    assert presentation['source_revision'] == rev, 'Editorial briefs need review against current facts'
    assert set(presentation['jobs']) == {j['pool_id'] for j in jobs}
    tabs = {s['sheet']: s['values'] for s in snapshot['sheets']}
    assert snapshot['publication_revision'] == dashboard['publicationRevision'] == rev
    assert dashboard['poolCounts'] == counts(jobs)
    for key, members in [('queue', queue), ('audit', jobs)]:
        name = T[key]
        rows = tabs[name]
        expected = [[str(v) for v in r] for r in sheet_rows(members)]
        actual = [[str(v) for v in r[:13]] for r in rows[H[key]:] if len(r) > 1 and r[1]]
        assert actual == expected, name+' membership or facts drift'
        assert rev in rows[2][0], name+' revision drift'

    all_rows = tabs[T['all_roles']][H['all_roles']:]
    allrows = {r[21]: r for r in all_rows if len(r) > 21 and r[21]}
    for j in jobs:
        r = allrows[j['original_url']]
        assert r[16] == j['application_state'], j['pool_id']+' application-state drift'
        assert r[17] == j['bucket']+'; original '+j['verification_state']
        assert r[18] == j['next_action'] and rev in r[19]
        assert r[5:8] == [j['gates'][k] for k in gates['all_roles_columns']]
        assert j['background']['path'] in r[22]
        if j['verification_state'] == 'live':
            assert r[11] == j['pay_published'], j['pool_id']+' published-pay drift'

    cards = {r['poolId']: r for r in dashboard['opportunities'] if r.get('poolId')}
    assert set(cards) == {j['pool_id'] for j in queue}, 'Dashboard membership drift'
    gate_values = {'pass': 'confirmed', 'fail': 'concern', 'unclear': 'unknown'}
    for j in queue:
        r = cards[j['pool_id']]
        assert r['brief'] == presentation['jobs'][j['pool_id']]
        assert r['nextAction'] == j['next_action'] and r['pay'] == j['pay_published']
        assert r['group'] == {'Priority screen': 'target', 'Screen first': 'screen', 'Reserve / stretch': 'reserve'}[j['bucket']]
        assert r['sources'][0][1] == j['original_url']
        for label, key in gates['dashboard'].items():
            assert r['gates'][label] == gate_values[j['gates'][key]]

    audit = {j['poolId']: j for j in dashboard['poolAudit']}
    assert set(audit) == {j['pool_id'] for j in jobs}
    for j in jobs:
        a = audit[j['pool_id']]
        assert (a['bucket'], a['verificationState'], a['sourceUrl'], a['gates'], a['nextAction']) == (
            j['bucket'], j['verification_state'], j['original_url'], j['gates'], j['next_action'])
        assert a['brief'] == presentation['jobs'][j['pool_id']]
    for c in dashboard['companies']:
        assert c['readableSummary'] == presentation['companies'][c['id']]

    overlaps = 0
    shortlist = tabs[T['shortlist']][H['shortlist']:]
    for j in jobs:
        for r in shortlist:
            if len(r) > 19 and r[3:5] == [j['company'], j['original_title']]:
                assert r[17] == j['next_action'] and rev in r[19]
                closed = {'Rejected': 'Rejected', 'Withdrawn': 'Withdrawn'}.get(j['bucket'])
                assert not closed or r[16] == closed, f"Shortlist status {r[16]!r} for {j['pool_id']} ({j['bucket']})"
                derived = re.match(r'^(.+); audit only; revision [0-9a-f]{16}$', str(r[19]))
                assert not derived or derived.group(1) == j['bucket'], f"Shortlist readiness {r[19]!r} for {j['pool_id']} ({j['bucket']})"
                overlaps += 1
    for r in shortlist:
        if len(r) > 19 and r[1] == 'Closed':
            assert '; queued;' not in r[19], 'Closed Shortlist sibling requeued'

    pool = read(rel('automation', 'pool.json'))
    assert pool['revision'] == rev
    assert {j['pool_id'] for j in pool['jobs']} == {j['pool_id'] for j in jobs}
    assert all('bucket' not in j for j in pool['jobs']), 'Monitor manifest must not duplicate disposition'
    latest = read(rel('automation', 'latest.json'))
    if latest.get('review_status') == 'reviewed baseline':
        assert latest['published_revision'] == rev
        assert latest['jobs'] == jobs
    else:
        assert latest.get('review_status') == 'pending publication', 'Cache cannot silently publish'

    catalogue = read(rel('automation', 'catalogue.json'))
    assert catalogue['published_revision'] == rev
    catalogue_rows = catalogue['jobs']
    expected_catalogue = [r for r in all_rows if len(r) > 17 and r[2]]
    assert len(catalogue_rows) == len(expected_catalogue)
    for c, r in zip(catalogue_rows, expected_catalogue):
        assert [c['company'], c['title'], c['application_state'], c['disposition']] == [r[2], r[3], r[16], r[17]]

    html_path = ws.path('dashboard') / 'index.html'
    html_checked = html_path.is_file()
    if html_checked:  # a freshly scaffolded workspace has no built dashboard yet
        html = html_path.read_text()
        embedded, _ = json.JSONDecoder().raw_decode(html.split('const DATA = ', 1)[1])
        assert embedded == dashboard, 'Generated HTML dataset drift'
    source_tabs = {t['name']: t['values'] for t in dashboard['sourceTabs']}
    for key in ('queue', 'audit', 'all_roles', 'shortlist', 'pipeline'):
        assert source_tabs[T[key]] == tabs[T[key]], 'Embedded source snapshot drift: '+T[key]
    pipeline = tabs[T['pipeline']]
    current_count = re.match(r'(\d+) current processes', pipeline[2][0])
    assert current_count and int(current_count.group(1)) == sum(r['group'] == 'current' for r in dashboard['opportunities']), 'Current process count drift'
    gid = f"#gid={ws.tab('pipeline')['sheet_id']}&range="
    for item in dashboard['opportunities']:
        if gid not in item.get('sheetSource', ''):
            continue
        row = pipeline[item['sheetRow']-1]
        assert item['summary'] == row[1] and item['nextAction'] == row[2], 'Process stage/action drift: '+item['id']
        if str(row[1]).startswith('Rejected '):
            assert (item['group'], item['stage'], item['owner']) == ('closed', 'Rejected', 'None'), 'Rejection still presented as current: '+item['id']
    return dict(revision=rev, **counts(jobs), shortlist_exact_overlaps=overlaps,
                captured_tabs_checked=5, dashboard_html_checked=html_checked, network_refresh=False,
                result='Published views agree; source access gaps remain explicit')


if __name__ == '__main__':
    print(json.dumps(check(), indent=2))
