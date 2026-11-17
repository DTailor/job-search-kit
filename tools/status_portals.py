"""Read every candidate portal/inbox surface in one run, in the agent's own new Safari tab.

  python3 tools/status_portals.py [YYYY-MM-DD]

Targets: workspace.json paths.portal_targets ([{name, url, needle, gate?}]).
Browser CLI: accounts.browser.path (Safari Act). Opens a NEW agent tab per target (never
reuses the person's own tabs; a login page's beforeunload guard cannot block the next
target) and closes it with its close token after reading. Reads each target, saves raw evidence to
<paths.status>/evidence-<date>/portal-<name>.json and prints one compact line per source:
state = read | gate (login/OTP page: stop, never request codes) | error.
No clicks, logins, consents, OTP requests or form submissions.
"""
import datetime, json, re, subprocess, sys, time
from pathlib import Path
from urllib.parse import urlsplit

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from tools import workspace as ws  # noqa: E402

ROOT = ws.root()
CLI = ws.browser_cli()
TARGETS = ws.path('portal_targets')
GATE = re.compile(r'(Sign In|Sign in to|Log in|one-time-passcode|Request one-time|Zaloguj|Password\*)', re.I)
LOGIN_URL = re.compile(r'/(login|signin|sign-in|generate-otp)\b', re.I)


def call(*a, timeout=30):
    p = subprocess.run([CLI, *a], capture_output=True, text=True, timeout=timeout)
    try:
        return json.loads(p.stdout or p.stderr)
    except ValueError:
        return {'ok': False, 'error': 'non-JSON CLI response'}


def tab_ids():
    return {f"{t['window']}.{t['tab']}": t.get('url', '') for t in call('tabs').get('tabs', [])}


def close(tab, opened, left_open):
    """Close the agent's own tab: token first; after a redirect (login/SSO/other origin) the
    token no longer proves ownership, so force-close the tab this run opened and read.
    A close that times out (Cloudflare challenge pages stall AppleEvents) is checked
    against the tab list instead of being retried blindly."""
    token = opened.get('close_token')
    res = call('close', '--tab', tab, '--token', token) if token else {'ok': False, 'code': 'no_token'}
    if not res.get('ok') and res.get('code') in ('tab_not_owned', 'no_token'):
        res = call('close', '--tab', tab, '--force')
    if not res.get('ok') and res.get('code') == 'backend_timeout':
        res = {'ok': tab not in tab_ids()}
    if not res.get('ok'):
        left_open.append(tab)


def main():
    args = [a for a in sys.argv[1:] if not a.startswith('-')]
    if len(args) != len(sys.argv[1:]) or (args and not re.fullmatch(r'\d{4}-\d{2}-\d{2}[a-z]?', args[0])):
        sys.exit(__doc__)
    day = args[0] if args else datetime.date.today().isoformat()
    if not CLI:
        sys.exit(json.dumps({'error': 'accounts.browser.path is not configured in workspace.json'}))
    out = ws.path('status') / f'evidence-{day}'
    if any(out.glob('portal-*.json')):  # never overwrite an earlier sweep's evidence
        sys.exit(json.dumps({'error': f'{out.name} already holds portal evidence; rerun with a new suffix, e.g. {day[:10]}x'}))
    out.mkdir(parents=True, exist_ok=True)
    summary, left_open = [], []
    for t in json.loads(TARGETS.read_text()):
        before = tab_ids()
        opened = call('open', '--url', t['url'], timeout=45)
        if opened.get('ok'):
            tab = f"{opened['tab']['window']}.{opened['tab']['tab']}"
        else:  # e.g. target_changed: the tab exists but redirected while opening, so no token was issued
            # Safari can register the tab after open_tab's AppleEvent timed out: poll before giving up
            for _ in range(10):
                new = [k for k in tab_ids() if k not in before]
                if new:
                    break
                time.sleep(2)
            if len(new) != 1:
                summary.append(dict(name=t['name'], state='error', detail=opened)); continue
            tab = new[0]
        ready = call('wait', '--tab', tab, '--text', t['needle'], '--timeout', '10')
        if ready.get('code') == 'target_changed':  # site redirect (SSO, login, latest thread): wait again on the new page
            ready = call('wait', '--tab', tab, '--text', t['needle'], '--timeout', '10')
        page = call('read', '--tab', tab, '--limit', '15000')
        text = re.sub(r'\s+', ' ', page.get('text', ''))
        href = page.get('href') or ''
        if urlsplit(href).netloc and urlsplit(href).netloc != urlsplit(t['url']).netloc:
            # a late redirect from the previous target can land after navigate; never save another site's page as this one
            summary.append(dict(name=t['name'], state='error', href=href, detail='page read from another host; retry this target'))
            close(tab, opened, left_open)
            continue
        # A login URL is a gate even when the needle matches: sign-in pages often greet
        # the person by name. Safari Act 0.13+ also flags challenge pages instead of hiding them.
        gated = bool(LOGIN_URL.search(urlsplit(href).path)) or bool(page.get('challenge')) \
            or (not ready.get('found') and bool(GATE.search(text[:1500])))
        (out / f"portal-{t['name']}.json").write_text(json.dumps(dict(target=t, ready=ready, page=page), ensure_ascii=False, indent=1))
        i = text.find(t['needle'])
        summary.append(dict(name=t['name'], state='gate' if gated else ('read' if ready.get('found') else 'read-no-needle'),
                            href=page.get('href'), excerpt=text[max(0, i - 200): i + 600] if i >= 0 else text[:500]))
        close(tab, opened, left_open)
    (out / 'portal-summary.json').write_text(json.dumps(dict(checked_at=datetime.datetime.now().astimezone().isoformat(timespec='seconds'),
                                                             agent_tabs_left_open=left_open, sources=summary), ensure_ascii=False, indent=1))
    for s in summary:
        print(f"[{s['state']}] {s['name']}: {s.get('excerpt', s.get('detail'))!s:.400}")
    owner = ws.person().get('short_name') or ws.person()['name']
    print(f"agent tabs closed; left open: {left_open or 'none'}; {owner}'s tabs untouched")


if __name__ == '__main__':
    main()
