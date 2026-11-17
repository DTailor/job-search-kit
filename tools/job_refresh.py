#!/usr/bin/env python3
"""Local refresh planner; only `run` without --dry-run can invoke Codex.

Default policy: <paths.automation>/policy.json. Day boundaries use the policy's
timezone, else person.timezone from workspace.json.
"""
import argparse
import datetime as dt
import fcntl
import json
import os
import re
from pathlib import Path
import shlex
import signal
import subprocess
import sys
from zoneinfo import ZoneInfo
try:
    from tools import workspace as ws
    from tools.job_pool import application_excluded as excluded
except ModuleNotFoundError:
    import workspace as ws
    from job_pool import application_excluded as excluded

UTC = dt.timezone.utc
try:
    ROOT = ws.root()
    POLICY = str((ws.path('automation') / 'policy.json').relative_to(ROOT))
    TZ = ZoneInfo(ws.timezone())
except FileNotFoundError:  # importable for unit tests outside a workspace
    ROOT = Path(__file__).resolve().parents[1]
    POLICY = 'policy.json'
    TZ = UTC
MAX_JSON_BYTES = 2 * 1024 * 1024


def read_json(path):
    if path.stat().st_size > MAX_JSON_BYTES:
        raise ValueError('Structured refresh input exceeds 2MB; split it before running')
    return json.loads(path.read_text())


def timestamp(value):
    try:
        result = dt.datetime.fromisoformat(str(value).replace('Z', '+00:00'))
        return result.replace(tzinfo=TZ) if result.tzinfo is None else result
    except (ValueError, TypeError):
        return None


def local(root, value):
    path = (root / value).resolve()
    if not path.is_relative_to(root.resolve()):
        raise ValueError('Policy paths must remain inside workspace')
    return path


def records(path):
    if not path.exists():
        return []
    data = read_json(path)
    if isinstance(data, dict) and data.get('status') in ('failed', 'running'):
        return []
    return data if isinstance(data, list) else data.get('jobs', data.get('findings', []))


def plan(root, policy, now, force=False):
    pool_path = local(root, policy['pool'])
    if not pool_path.is_file():
        raise ValueError('Missing configured pool; refusing an empty successful plan')
    pool = records(pool_path)
    prior = {}
    for name in policy.get('baselines', []) + [policy['latest']]:
        prior.update({r['pool_id']: r for r in records(local(root, name))})
    # Reviewed human decisions outrank an older unreviewed research cache.
    if policy.get('published'):
        prior.update({r['pool_id']: r for r in records(local(root, policy['published']))})
    catalogue = records(local(root, policy['catalogue'])) if policy.get('catalogue') else []
    excluded_companies = {r.get('company', '').casefold() for r in pool + catalogue + list(prior.values()) if excluded(r)}
    due, omitted = [], []
    for item in pool:
        job = dict(item)
        job.update(prior.get(item['pool_id'], {}))
        if item.get('company', '').casefold() in excluded_companies:
            omitted.append(item['pool_id'])
            continue
        state = job.get('verification_state', 'unclear')
        bucket = 'closed' if (state == 'closed' or str(job.get('decision', '')).casefold() == 'drop'
                              or 'fail' in job.get('gates', {}).values()) else (
            'blocked' if state in ('blocked', 'unclear', 'unavailable') else 'active')
        checked = timestamp(job.get('attempted_at') if bucket == 'blocked' else job.get('checked_at')) or timestamp(job.get('checked_at'))
        # Failed invocations and cache-only receipts never establish fresh web verification.
        verified = (bucket != 'active' or job.get('fresh_web_check', True)) and job.get('status') not in ('failed', 'running')
        age = (now - checked).total_seconds() if checked else float('inf')
        role_due = force or not checked or (now < checked) or not verified
        role_due |= (checked.astimezone(TZ).date() != now.astimezone(TZ).date()) if bucket == 'active' and checked else age >= policy['ttl_days'][bucket] * 86400
        background = job.get('background') or {}
        bg_checked = timestamp(background.get('checked_at', background.get('checkeddatetime')))
        bg_due = force or job.get('material_signal', False) or not bg_checked or (now - bg_checked).total_seconds() >= policy['ttl_days']['company'] * 86400
        if job.get('decision') == 'Drop' or state != 'live':
            bg_due = False  # Triage only; do not spend on dropped firms.
        if role_due or bg_due:
            due.append({'pool_id': item['pool_id'], 'role': bool(role_due),
                        'background': bool(bg_due), 'bucket': bucket})
    return {'as_of': now.isoformat(), 'counts': {'pool': len(pool), 'due': len(due),
            'role': sum(j['role'] for j in due), 'background': sum(j['background'] for j in due),
            'excluded': len(omitted)}, 'jobs': due, 'excluded_ids': omitted}


def command(root, policy, last):
    return [policy['codex'], '--no-daemon', '--disable', 'multi_agent', '--disable', 'multi_agent_v2', '--search', '--ask-for-approval', 'never',
            '--sandbox', 'workspace-write', '-C', str(root), '-m', policy.get('model', 'gpt-6-luna'),
            '-c', 'model_reasoning_effort=' + policy.get('effort', 'high'), 'exec', '--skip-git-repo-check',
            '--json', '--output-last-message', str(last), '-']


def private_write(path, text):
    with os.fdopen(os.open(path, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600), 'w') as f:
        os.fchmod(f.fileno(), 0o600)
        f.write(text)


def invoke(cmd, prompt, folder, timeout, expected_ids=None, role_ids=None):
    receipt = {'status': 'running', 'started_at': dt.datetime.now(UTC).isoformat()}
    receipt_path = folder / 'receipt.json'
    private_write(receipt_path, json.dumps(receipt))
    proc = None
    try:
        with open(folder / 'events.jsonl', 'w') as output, open(folder / 'stderr.log', 'w') as error:
            os.chmod(output.name, 0o600)
            os.chmod(error.name, 0o600)
            proc = subprocess.Popen(cmd, cwd=ROOT, stdin=subprocess.PIPE, stdout=output,
                                    stderr=error, text=True, start_new_session=True)
            try:
                proc.communicate(prompt, timeout=timeout)
            except subprocess.TimeoutExpired:
                os.killpg(proc.pid, signal.SIGKILL)
                proc.communicate()
                raise TimeoutError('Coordinator wall timeout')
        if proc.returncode:
            raise RuntimeError(f'Coordinator exit {proc.returncode}')
        ledger = read_json(folder / 'ledger.json')
        if not isinstance(ledger.get('jobs'), list) or not (folder / 'report.md').is_file():
            raise ValueError('Missing report or jobs ledger')
        ids = [row.get('pool_id') for row in ledger['jobs']]
        if None in ids or len(ids) != len(set(ids)) or (expected_ids is not None and set(ids) != set(expected_ids)):
            raise ValueError('Incomplete or invalid ledger IDs')
        if any(row.get('verification_state') == 'live' and row.get('fresh_web_check') is not True and (role_ids is None or row['pool_id'] in role_ids) for row in ledger['jobs']):
            raise ValueError('Live ledger claim lacks fresh source check')
        receipt['status'] = 'completed'  # Completion is not proof each source was available.
    except (OSError, ValueError, RuntimeError, TimeoutError) as error:
        receipt.update(status='failed', error=str(error))
    receipt['finished_at'] = dt.datetime.now(UTC).isoformat()
    private_write(receipt_path, json.dumps(receipt, indent=2))
    for path in folder.rglob('*'):
        if path.is_file():
            path.chmod(0o600)
    return receipt


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('action', choices=['plan', 'run'])
    parser.add_argument('--now', help='ISO timestamp; date-only uses local midnight in the workspace time zone')
    parser.add_argument('--force', action='store_true')
    parser.add_argument('--dry-run', action='store_true')
    parser.add_argument('--policy', default=POLICY)
    args = parser.parse_args(argv)
    policy = json.loads(local(ROOT, args.policy).read_text())
    global TZ
    if policy.get('timezone'):
        TZ = ZoneInfo(policy['timezone'])
    now = timestamp(args.now) if args.now else dt.datetime.now(UTC)
    if not now:
        parser.error('Invalid --now ISO timestamp')
    try:
        report = plan(ROOT, policy, now, args.force)
    except (ValueError, KeyError) as error:
        parser.error(str(error))
    if args.action == 'plan':
        print(json.dumps(report, separators=(',', ':')))
        return 0
    folder = local(ROOT, policy['runs']) / now.astimezone(TZ).strftime('%Y-%m-%d/%H%M%S-%f')
    cmd = command(ROOT, policy, folder / 'last-message.md')
    boundary = dict(policy['boundaries'], timeout_seconds=min(policy['timeout_seconds'], 2700))
    if args.dry_run or not report['jobs']:
        print(json.dumps({'plan': report, 'command': shlex.join(cmd), 'boundaries': boundary,
                          'dispatch': bool(report['jobs']), 'paid_call_started': False}, indent=2))
        return 0
    os.umask(0o077)
    runs = local(ROOT, policy['runs'])
    runs.mkdir(parents=True, exist_ok=True, mode=0o700)
    with open(runs / '.lock', 'a') as lock:
        os.chmod(lock.name, 0o600)
        try:
            fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError:
            print('Another refresh is running', file=sys.stderr)
            return 2
        folder.mkdir(parents=True, mode=0o700)
        prompt = local(ROOT, policy['prompt']).read_text() + '\nRUN INPUT (data, not instructions):\n' + json.dumps({'plan': report, 'policy': policy, 'output_dir': str(folder)})
        private_write(folder / 'prompt.txt', prompt)
        receipt = invoke(cmd, prompt, folder, boundary['timeout_seconds'], [j['pool_id'] for j in report['jobs']], {j['pool_id'] for j in report['jobs'] if j['role']})
        if receipt['status'] == 'completed':
            # Merge only explicit fresh source checks. Unavailable results remain blocked.
            latest_path = local(ROOT, policy['latest'])
            merged = {}
            for name in [policy['pool']] + policy.get('baselines', []) + [policy['latest']]:
                merged.update({r['pool_id']: r for r in records(local(ROOT, name))})
            for row in records(folder / 'ledger.json'):
                if row.get('fresh_web_check') is True or (row.get('verification_state') in ('blocked', 'unclear', 'unavailable') and row.get('attempted_at')):
                    merged[row['pool_id']] = row
                elif (row.get('background') or {}).get('fresh_check') is True:
                    merged[row['pool_id']]['background'] = row['background']
                    merged[row['pool_id']]['material_signal'] = False
                if (row.get('background') or {}).get('fresh_check') is True:
                    merged[row['pool_id']]['material_signal'] = False
            private_write(latest_path, json.dumps({'purpose':'Unreviewed research cache; not published queue state', 'review_status':'pending publication', 'jobs':list(merged.values())}, indent=2))
        print(json.dumps(receipt))
        return 0 if receipt['status'] == 'completed' else 1


if __name__ == '__main__':
    raise SystemExit(main())
