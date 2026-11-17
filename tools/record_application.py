"""Record one submitted application in every local place at once. Stdlib only.

  python3 tools/record_application.py POOL_ID --time "YYYY-MM-DD HH:MM" --route "Lever form"
        --receipt URL --evidence "email receipt" [--answers answers.json] [--posting raw.html]
        [--archive DIR] [--pay-sent TEXT] [--next TEXT] [--notes TEXT]

Writes (never overwriting existing files except the round archive, which it appends to):
  <paths.applications>/<slug>/application.md   timeline with exactly what was submitted
  <paths.applications>/<slug>/posting.md       posting text from --posting (saved HTML) if given
  <archive>/submissions.json                   dashboard submission record (appended)
  <archive>/publish-<slug>/spec.json           tracker_publish spec: pool -> Applied + Active pipeline row
Then run:  python3 tools/tracker_publish.py plan <archive>/publish-<slug>/spec.json
Times are local to person.timezone. The person submits; this only records it.
"""
import argparse, datetime as dt, html, json, re, sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from tools import workspace as ws  # noqa: E402
from tools.job_pool import load_current  # noqa: E402


def slug(text):
    return re.sub(r'[^a-z0-9]+', '-', text.lower())[:40].strip('-')


def text_of(raw):
    t = re.sub(r'<script.*?</script>|<style.*?</style>', ' ', raw, flags=re.S | re.I)
    t = re.sub(r'<(br|/p|/li|/h\d|/div)[^>]*>', '\n', t, flags=re.I)
    t = html.unescape(re.sub(r'<[^>]+>', ' ', t))
    return '\n'.join(line.strip() for line in t.splitlines() if line.strip())


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('pool_id'); ap.add_argument('--time', required=True); ap.add_argument('--route', required=True)
    ap.add_argument('--receipt', required=True); ap.add_argument('--evidence', default='email receipt')
    ap.add_argument('--answers'); ap.add_argument('--posting'); ap.add_argument('--archive')
    ap.add_argument('--pay-sent', default='No salary field; no salary figure submitted.')
    ap.add_argument('--next'); ap.add_argument('--notes', default='')
    a = ap.parse_args(argv)
    cfg, root = ws.load(), ws.root()
    job = next(j for j in load_current()['jobs'] if j['pool_id'] == a.pool_id)
    date, clock = a.time.split()
    company = job['company'].split(' / ')[0].split(' (')[0]
    short = company.split(',')[0]
    key = slug(short)
    folder = ws.path('applications') / f"{key}_{slug(job['original_title'])[:24].strip('-')}"
    folder.mkdir(parents=True, exist_ok=True)
    archive = Path(a.archive) if a.archive else ws.path('data') / f'archive-{date}-applications'
    archive = archive if archive.is_absolute() else root / archive
    archive.mkdir(parents=True, exist_ok=True)
    answers = json.loads(Path(a.answers).read_text()) if a.answers else {}
    bg = job.get('background') or {}
    risk = bg.get('main_risk') if isinstance(bg, dict) else ''
    nxt = a.next or f"Await {short} review. If contacted, clarify the open terms in the dossier. Do not reapply."
    person = ws.person()

    sent = '\n'.join(f'  - {k}: {v}' for k, v in answers.items()) or '  - (fields not recorded)'
    app_md = folder / 'application.md'
    entry = (f"- {date} {clock} ({person['timezone']}): **Applied** via {a.route}; {person.get('short_name') or person['name']} submitted. "
             f"Evidence: {a.evidence} — {a.receipt}\n  Submitted (as filled by the agent and reviewed by the person; phone/consents typed by the person, not recorded):\n{sent}\n"
             f"  Pay sent: {a.pay_sent}\n" + (f"  Notes: {a.notes}\n" if a.notes else ''))
    if app_md.exists():
        app_md.write_text(app_md.read_text().rstrip() + '\n' + entry)
    else:
        app_md.write_text(f"# {job['company']} — {job['original_title']}\n\nRole: {job['original_url']}. Dossier: {bg.get('path', '') if isinstance(bg, dict) else ''}.\n\n## Timeline\n\n{entry}\n## Next\n\n{nxt}\n")
    if a.posting and not (folder / 'posting.md').exists():
        (folder / 'posting.md').write_text(f"# Posting — {job['company']}: {job['original_title']}\n\nSource: {job['original_url']} (saved {date}).\n\n" + text_of(Path(a.posting).read_text(errors='ignore')) + '\n')

    subs_file = archive / 'submissions.json'
    subs = json.loads(subs_file.read_text()) if subs_file.exists() else dict(recorded_at=None, account=person['email'], submissions=[])
    subs['submissions'] = [s for s in subs['submissions'] if s['pool_id'] != a.pool_id] + [dict(
        key=key, pool_id=a.pool_id, folder=folder.name, company=job['company'], role=job['original_title'], date=date, time=clock,
        prepared_date=date, route=a.route, original_url=job['original_url'], receipt_url=a.receipt,
        background=bg.get('path', '') if isinstance(bg, dict) else '', risk=risk or job.get('main_risk_and_first_question', ''),
        gates=job.get('gates', {}), contract=job.get('contract_text', ''), evidence_kind=a.evidence, pay_sent=a.pay_sent)]
    subs['recorded_at'] = dt.datetime.now(dt.timezone.utc).isoformat(timespec='seconds')
    subs_file.write_text(json.dumps(subs, ensure_ascii=False, indent=2) + '\n')

    state = f"Applied {date} {clock} — {a.evidence} verified"
    pub = archive / f'publish-{key}'; pub.mkdir(exist_ok=True)
    pipeline = cfg['tracker']['tabs']['pipeline']['title']
    spec = dict(label=f"{date}: {short} applied", date=date, outdir=str(pub.relative_to(root)),
                pool={a.pool_id: dict(bucket='Applied', application_state=state, next_action=nxt)},
                active_pipeline=dict(insert=[dict(after='__LAST_APPLIED__', row=[
                    f"{job['company']} · {job['original_title']}",
                    f"Applied {date} {clock} via {a.route} ({person.get('short_name') or person['name']} submitted). {a.evidence} verified.",
                    nxt, short, 'No stated deadline', a.pay_sent,
                    (risk or '') + (f' {a.notes}' if a.notes else ''),
                    f"{date} — {a.evidence}", f"{job['original_url']}\n{a.receipt}"])]),
                snapshot_note=f"{date}: {short} applied {clock} ({a.evidence}).")
    (pub / 'spec.json').write_text(json.dumps(spec, ensure_ascii=False, indent=1) + '\n')
    print(json.dumps(dict(application=str(folder.relative_to(root)), submissions=str(subs_file.relative_to(root)),
                          spec=str((pub / 'spec.json').relative_to(root)),
                          next=f"set active_pipeline.insert[0].after (row to insert after in '{pipeline}') and headlines, then tracker_publish.py plan"), indent=1))


if __name__ == '__main__':
    main()
