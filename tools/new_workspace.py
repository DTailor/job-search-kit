"""Scaffold a new person's job-search workspace from the kit. Stdlib only; no network.

  python3 tools/new_workspace.py TARGET [--kit KIT] [--template PATH]
      Copies kit-managed files (kit.json), writes TARGET/workspace.json from
      templates/workspace.example.json if absent, creates the configured folders and
      empty-but-valid data files (pool, automation manifest/cache/catalogue/policy,
      tracker base + initial readback, portal targets, dashboard data). Existing
      files are never overwritten. Edit workspace.json, then create the tracker.

  python3 tools/new_workspace.py TARGET --sheet-requests
      Prints {"requests": [...]} for one Google Sheets batchUpdate: addSheet for each
      configured tab (sheetId omitted when the configured id is 0/null, so Sheets
      assigns one; copy the assigned ids back into workspace.json) and the title,
      headline and header rows the tools expect. Nothing is sent anywhere.
"""
import argparse
import datetime as dt
import json
import os
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import kit_sync  # noqa: E402

TITLES = {'queue': 'Application queue — next roles to discuss',
          'audit': 'Research audit — monitored originals and reasons',
          'pipeline': 'Active pipeline — applications and recruiter conversations',
          'shortlist': 'Shortlist · status detail; live application candidates are in Application queue'}
QUEUE_HEADERS = ['#', 'Priority', 'Company', 'Role', 'Next action', 'Unresolved gates', 'Pay', 'Company risk',
                 'Checked', 'Job link', 'Background dossier', 'Stable ID / source lineage', 'Queue membership']
AUDIT_HEADERS = ['Order', 'Priority', 'Company', 'Role', 'Next action', 'Unresolved gates', 'Published pay / basis',
                 'Company background / main risk', 'Vacancy checked', 'Job link', 'Background dossier',
                 'Stable ID / source lineage', 'Queue membership']
PIPELINE_HEADERS = ['Opportunity / contact', 'Progress', 'Next action', 'Action owner', 'Deadline / checkpoint',
                    'Terms discussed', 'Open points / constraints', 'Last verified', 'Source']
SHORTLIST_HEADERS = ['#', 'Decision', 'Technical fit /10', 'Company', 'Role', 'Required tech / keywords',
                     'Location / contract', 'Pay (as published)', 'Pay verdict',
                     'Pay evidence (third-party and inferred, labelled)', 'Contract route (B2B entity?)',
                     'Hours / on-call', 'Why it fits', 'Main risk, and what to ask first', 'Posted', 'Role checked',
                     'Status', 'Next step', 'Notes', 'Current readiness']


def all_roles_headers(gates):
    """A:W. F:H are the configured gate columns (labelled from gates.dashboard)."""
    label = {v: k for k, v in gates['dashboard'].items()}
    cols = [label.get(k, k.replace('_', ' ').capitalize()) for k in gates['all_roles_columns']]
    assert len(cols) == 3, 'gates.all_roles_columns must name exactly three gates (columns F:H)'
    return (['Decision', 'Technical fit /10', 'Company', 'Role', 'Required tech / keywords'] + cols +
            ['Location', 'Work model', 'Contract', 'Pay (published)', 'On-call', 'Why it fits',
             'Gaps, risk or reason dropped', 'Checked', 'Application state', 'Current disposition',
             'Next action / queue', 'Reconciled', 'Stage evidence', 'Exact role URL', 'Company background / coverage'])


def headers(cfg):
    import workspace as ws
    gates = {**ws.DEFAULT_GATES, **cfg.get('gates', {})}
    return {'all_roles': all_roles_headers(gates), 'queue': QUEUE_HEADERS, 'audit': AUDIT_HEADERS,
            'pipeline': PIPELINE_HEADERS, 'shortlist': SHORTLIST_HEADERS}


def header_row(cfg, key):
    return int(cfg['tracker']['tabs'][key].get('header_row', cfg['tracker'].get('header_row', 1)))


def initial_tabs(cfg, rev):
    """{key: values} for an empty tracker: title row, headline rows 2-3, header row."""
    out = {}
    for key, head in headers(cfg).items():
        h = header_row(cfg, key)
        rows = [[''] for _ in range(h - 1)] + [head]
        if h >= 2:
            rows[0] = [TITLES.get(key, cfg['tracker']['tabs'][key]['title'])]
        if key != 'all_roles':
            assert h >= 4, f'tracker.tabs.{key}: header_row must be at least 4 (title + two headline rows)'
            rows[1] = ['No published roles yet.' if key != 'pipeline' else 'No applications or conversations yet.']
            rows[2] = ['0 current processes' if key == 'pipeline' else f'Revision {rev}']
        out[key] = rows
    return out


def sheet_requests(cfg):
    import job_pool
    tabs = initial_tabs(cfg, job_pool.revision([]))
    reqs, unassigned = [], []
    for key, rows in tabs.items():
        t = cfg['tracker']['tabs'][key]
        props = {'title': t['title'], 'gridProperties': {'frozenRowCount': header_row(cfg, key),
                                                         'columnCount': max(26, len(rows[-1]))}}
        if t.get('sheet_id'):
            props['sheetId'] = t['sheet_id']
        else:
            unassigned.append(key)
        reqs.append({'addSheet': {'properties': props}})
    for key, rows in tabs.items():
        t = cfg['tracker']['tabs'][key]
        if not t.get('sheet_id'):
            continue  # needs the id Sheets assigns; rerun after updating workspace.json
        for ri, row in enumerate(rows):
            if not any(row):
                continue
            reqs.append({'updateCells': {
                'range': {'sheetId': t['sheet_id'], 'startRowIndex': ri, 'endRowIndex': ri + 1,
                          'startColumnIndex': 0, 'endColumnIndex': len(row)},
                'rows': [{'values': [{'userEnteredValue': {'stringValue': v}} for v in row]}],
                'fields': 'userEnteredValue'}})
    return dict(spreadsheet_id=cfg['tracker']['spreadsheet_id'], requests=reqs,
                note=('Tabs without a configured sheet_id: ' + ', '.join(unassigned) +
                      '. Run addSheet first, copy the assigned sheetIds into workspace.json, '
                      'then rerun --sheet-requests and send only the updateCells requests.') if unassigned else
                'Send as one batchUpdate; existing tabs with these ids/titles will make addSheet fail.')


def write_new(path, value):
    """Create path with JSON/text content unless it already exists. Returns True if written."""
    path = Path(path)
    if path.exists():
        return False
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(value if isinstance(value, str) else json.dumps(value, ensure_ascii=False, indent=2) + '\n')
    return True


def scaffold(target, kit, template):
    target.mkdir(parents=True, exist_ok=True)
    created = []
    if write_new(target / 'workspace.json', Path(template).read_text()):
        created.append('workspace.json')
    for src, dest, status in kit_sync.plan(kit, target):
        if status == 'new':
            dest.parent.mkdir(parents=True, exist_ok=True)
            dest.write_bytes(src.read_bytes())
            created.append(str(dest.relative_to(target)))

    os.environ['JOB_HUNT_WORKSPACE'] = str(target)
    import workspace as ws
    import job_pool
    ws.load.cache_clear()
    cfg = ws.load(str(target))
    p = lambda key: target / cfg['paths'][key]  # noqa: E731
    for key, value in cfg['paths'].items():
        if value and not Path(value).suffix:
            p(key).mkdir(parents=True, exist_ok=True)
    rev = job_pool.revision([])
    now = dt.datetime.now(dt.timezone.utc).isoformat(timespec='seconds')
    rel = lambda path: str(Path(path).relative_to(target))  # noqa: E731
    auto, status, dash = p('automation'), p('status'), p('dashboard') / 'data'
    pool_rel = cfg['paths']['pool']
    tabs = initial_tabs(cfg, rev)
    sheets = [dict(sheet=cfg['tracker']['tabs'][k]['title'], sheet_id=cfg['tracker']['tabs'][k]['sheet_id'],
                   range=f"A1:{'ABCDEFGHIJKLMNOPQRSTUVW'[len(v[-1]) - 1]}{len(v)}", checked_at=now, values=v)
              for k, v in tabs.items()]
    readback = status / 'initial-tracker-readback.json'
    counts = job_pool.counts([])
    files = {
        p('pool'): dict(schema_version=1, as_of=now, published_at=None, source_snapshot=None, revision=rev,
                        jobs=[], search_preferences={}),
        auto / 'pool.json': dict(purpose='Monitored identities only; this is not an application queue',
                                 published_source=pool_rel, revision=rev, jobs=[]),
        auto / 'latest.json': dict(purpose='Unreviewed research cache; not published queue state',
                                   review_status='pending publication', jobs=[]),
        auto / 'catalogue.json': dict(purpose='Full role library mirrored from the All roles tab', checked_at=now,
                                      published_revision=rev, jobs=[], supporting_views_pending=False),
        auto / 'policy.json': dict(
            pool=rel(auto / 'pool.json'), latest=rel(auto / 'latest.json'), catalogue=rel(auto / 'catalogue.json'),
            baselines=[], runs=rel(auto / 'runs'), prompt=rel(auto / 'daily-prompt.md'), codex='codex',
            timezone=cfg['person']['timezone'], ttl_days=dict(active=1, closed=7, blocked=3, company=30),
            timeout_seconds=2700,
            boundaries=dict(max_workers=0, batch_size=12, max_search_queries=12,
                            cost='No enforceable currency/token cap; wall timeout is enforced.'),
            mode='lightweight_single_session', model='REPLACE_WITH_MODEL', effort='high', published=pool_rel),
        auto / 'daily-prompt.md': ('# Daily pool refresh\n\nRe-check each due role and company named in RUN INPUT. '
                                   'Write ledger.json and report.md to output_dir. Research only: never apply, '
                                   'message, log in or change the tracker.\n'),
        readback: dict(checked_at=now, method='Scaffolded empty tracker (not read from Google Sheets)', sheets=sheets),
        p('tracker_base'): dict(readback=rel(readback), revision=rev, updated=now[:10]),
        p('portal_targets'): [],
        dash / 'tracker-snapshot.json': dict(
            checked_at=now, account=cfg['person']['email'], spreadsheet_id=cfg['tracker']['spreadsheet_id'],
            spreadsheet_url=f"https://docs.google.com/spreadsheets/d/{cfg['tracker']['spreadsheet_id']}/edit",
            title='Job search tracker', publication_revision=rev, capture_note='Scaffolded empty tracker',
            sheets=sheets),
        dash / 'presentation.json': dict(purpose='Reviewed editorial briefs keyed by pool_id / company id',
                                         source_revision=rev, jobs={}, companies={}),
        dash / 'reviewed-data.json': dict(
            product='Job search dashboard', asOf=now[:10], timezone=cfg['person']['timezone'], builtAt=now,
            sheetReadAt=now, sheetUrl=f"https://docs.google.com/spreadsheets/d/{cfg['tracker']['spreadsheet_id']}/edit",
            opportunities=[], companies=[], research=[], reconciliation=[], poolCounts=counts,
            publicationRevision=rev, poolAudit=[], sourceTabs=[dict(name=s['sheet'], values=s['values']) for s in sheets],
            statusDocument='', planDocument='', updates=[], applicationDocs=[], constraints=[], tasks=[], coverage=[], sources=[]),
    }
    for path, value in files.items():
        if write_new(path, value):
            created.append(rel(path))
    # Person-owned starting documents: copied once from kit templates, never overwritten.
    for tpl in sorted((kit / 'templates' / 'profile').glob('*.md')):
        if write_new(p('profile') / tpl.name, tpl.read_text()):
            created.append(rel(p('profile') / tpl.name))
    if (kit / 'AGENTS.template.md').is_file() and write_new(target / 'AGENTS.md', (kit / 'AGENTS.template.md').read_text()):
        created.append('AGENTS.md')
    return created


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('target')
    ap.add_argument('--kit', default=str(HERE.parent))
    ap.add_argument('--template', help='workspace.json template (default: KIT/templates/workspace.example.json)')
    ap.add_argument('--sheet-requests', action='store_true')
    args = ap.parse_args(argv)
    target = Path(args.target).resolve()
    if args.sheet_requests:
        os.environ['JOB_HUNT_WORKSPACE'] = str(target)
        cfg = json.loads((target / 'workspace.json').read_text())
        print(json.dumps(sheet_requests(cfg), ensure_ascii=False, indent=1))
        return 0
    kit = Path(args.kit).resolve()
    if not (kit / 'kit.json').is_file():
        sys.exit(f'{kit}: kit.json not found (pass --kit)')
    created = scaffold(target, kit, args.template or kit / 'templates' / 'workspace.example.json')
    print(json.dumps(dict(workspace=str(target), created=created,
                          next=['Edit workspace.json (person, tracker.spreadsheet_id, tabs, paths, gates)',
                                'Write profile/PROFILE.md and profile/PREFERENCES.md',
                                'python3 tools/new_workspace.py . --sheet-requests  -> send via the Sheets connector',
                                'python3 tools/tracker_publish.py checks']), indent=1))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
