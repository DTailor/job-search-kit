import datetime as dt
import json
from pathlib import Path
import subprocess
import tempfile
import unittest
from unittest.mock import patch
from zoneinfo import ZoneInfo
try:
    from tools import job_refresh as refresh
except ModuleNotFoundError:
    import job_refresh as refresh


class RefreshTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        # Fixtures use a fixed UTC+2 local zone, independent of the workspace person.
        tz = patch.object(refresh, 'TZ', ZoneInfo('Etc/GMT-2'))
        tz.start()
        self.addCleanup(tz.stop)
        self.policy = {'pool': 'pool.json', 'latest': 'latest.json',
                       'catalogue': 'catalogue.json', 'ttl_days': {'active': 1,
                       'closed': 7, 'blocked': 3, 'company': 30}}
        self.now = refresh.timestamp('2026-11-03T09:00:00+02:00')
        self.job = {'pool_id': 'a', 'company': 'Firm', 'verification_state': 'live',
                    'checked_at': '2026-11-02T23:00:00+02:00', 'decision': 'Screen first',
                    'background': {'checked_at': '2026-11-02T10:00:00+02:00'}}

    def plan(self, job=None, force=False):
        (self.root / 'pool.json').write_text(json.dumps([job or self.job]))
        return refresh.plan(self.root, self.policy, self.now, force)

    def test_next_day_due_even_under_24_hours(self):
        self.assertTrue(self.plan()['jobs'][0]['role'])

    def test_latest_submission_excludes_without_spending(self):
        (self.root / 'latest.json').write_text(json.dumps([dict(self.job, application_state='Applied')]))
        result = self.plan(force=True)
        self.assertEqual(result['counts']['excluded'], 1)
        self.assertEqual(result['counts']['due'], 0)

    def test_published_human_hold_overrides_stale_cache(self):
        self.policy['published']='published.json'
        (self.root/'latest.json').write_text(json.dumps([self.job]))
        (self.root/'published.json').write_text(json.dumps({'jobs':[
            dict(self.job,human_hold=True)]}))
        result=self.plan(force=True)
        self.assertEqual(result['counts']['excluded'],1)
        self.assertEqual(result['counts']['due'],0)

    def test_oversized_json_is_rejected_before_loading(self):
        p = self.root / 'oversized.json'
        with p.open('wb') as f:
            f.truncate(refresh.MAX_JSON_BYTES + 1)
        with self.assertRaises(ValueError):
            refresh.read_json(p)

    def test_same_day_and_timezone_reuse(self):
        self.job['checked_at'] = '2026-11-02T22:30:00Z'  # Nov 3 in the UTC+2 fixture zone
        self.assertEqual(self.plan()['counts']['due'], 0)
        self.assertEqual(self.plan(force=True)['counts']['due'], 1)

    def test_blocked_retry_ttl_not_live_freshness(self):
        self.job.update(verification_state='blocked', fresh_web_check=False,
                        attempted_at='2026-11-01T10:00:00+02:00')
        self.assertEqual(self.plan()['counts']['due'], 0)
        self.job['attempted_at'] = '2026-10-30T10:00:00+02:00'
        self.assertTrue(self.plan()['jobs'][0]['role'])

    def test_closed_and_failed_gate_seven_days(self):
        for state in ('closed', 'live'):
            self.job.update(verification_state=state, gates={'location': 'fail'})
            self.assertEqual(self.plan()['counts']['due'], 0)
            self.job['checked_at'] = '2026-10-26T09:00:00+02:00'
            self.assertTrue(self.plan()['jobs'][0]['role'])
            self.job['checked_at'] = '2026-11-02T23:00:00+02:00'

    def test_company_exclusion_beats_force(self):
        (self.root / 'catalogue.json').write_text(json.dumps({'jobs': [
            {'company': 'FIRM', 'application_state': 'Applied'}]}))
        self.assertEqual(self.plan(force=True)['counts']['excluded'], 1)

    def test_negative_application_phrases_remain_eligible(self):
        for phrase in ('Not applied', 'Never submitted', 'Unsubmitted', 'Not rejected'):
            with self.subTest(phrase=phrase):
                self.job['application_state'] = phrase
                self.assertEqual(self.plan()['counts']['excluded'], 0)
                self.assertEqual(self.plan()['counts']['due'], 1)

    def test_submitted_sibling_excludes_company(self):
        (self.root / 'catalogue.json').write_text(json.dumps({'jobs': [
            {'pool_id': 'sibling', 'company': 'Firm', 'application_state': 'Submitted'}]}))
        self.job['application_state'] = 'Not applied'
        self.assertEqual(self.plan(force=True)['counts']['excluded'], 1)

    def test_only_explicit_human_hold_excludes(self):
        for field in ('decision', 'disposition', 'current_bucket', 'status'):
            with self.subTest(field=field):
                self.assertFalse(refresh.excluded({field: 'Hold'}))
        self.assertFalse(refresh.excluded({'disposition': 'On hold'}))
        self.assertTrue(refresh.excluded({'human_disposition': 'Hold'}))
        self.assertTrue(refresh.excluded({'human_hold': True}))
        self.assertTrue(refresh.excluded({'current_bucket': 'Human hold'}))

    def test_dropped_fit_uses_weekly_ttl_even_if_blocked(self):
        self.job.update(decision='Drop', fresh_web_check=False)
        for state in ('live', 'blocked'):
            with self.subTest(state=state):
                self.job['verification_state'] = state
                self.assertEqual(self.plan()['counts']['due'], 0)
                self.assertTrue(self.plan(force=True)['jobs'][0]['role'])
                old = dict(self.job, checked_at='2026-10-26T09:00:00+02:00')
                self.assertTrue(self.plan(old)['jobs'][0]['role'])

    def test_background_ttl_and_material_signal(self):
        self.job['checked_at'] = self.now.isoformat()
        self.job['background']['checked_at'] = '2026-10-01T09:00:00+03:00'
        self.assertTrue(self.plan()['jobs'][0]['background'])
        self.job['background']['checked_at'] = self.now.isoformat()
        self.job['material_signal'] = True
        self.assertTrue(self.plan()['jobs'][0]['background'])

    def test_failed_latest_does_not_refresh_baseline(self):
        (self.root / 'latest.json').write_text(json.dumps({'status': 'failed', 'jobs': [
            dict(self.job, checked_at=self.now.isoformat())]}))
        self.assertTrue(self.plan()['jobs'][0]['role'])

    def test_cache_only_not_successful_web_check(self):
        self.job.update(checked_at=self.now.isoformat(), fresh_web_check=False)
        self.assertTrue(self.plan()['jobs'][0]['role'])

    @patch.object(refresh.subprocess, 'Popen')
    def test_dry_run_never_starts_process(self, popen):
        self.plan()
        self.policy.update(runs='runs', prompt='prompt.md', codex='/fake/codex',
                           timeout_seconds=9999, boundaries={'max_workers': 3})
        (self.root / 'policy.json').write_text(json.dumps(self.policy))
        with patch.object(refresh, 'ROOT', self.root), patch('builtins.print') as output:
            self.assertEqual(refresh.main(['run', '--dry-run', '--policy', 'policy.json',
                             '--now', self.now.isoformat()]), 0)
        popen.assert_not_called()
        payload = json.loads(output.call_args.args[0])
        self.assertEqual(payload['boundaries']['timeout_seconds'], 2700)
        self.assertIn('--no-daemon', payload['command'])
        self.assertIn('--disable multi_agent', payload['command'])
        self.assertIn('--search --ask-for-approval never', payload['command'])
        self.assertIn('--json --output-last-message', payload['command'])
        self.assertFalse(payload['paid_call_started'])

    @patch.object(refresh.subprocess, 'Popen')
    def test_failed_invocation_and_timeout_receipts(self, popen):
        proc = popen.return_value
        proc.returncode = 7
        proc.communicate.return_value = (None, None)
        result = refresh.invoke(['fake'], 'prompt', self.root, 3)
        self.assertEqual(result['status'], 'failed')
        self.assertIn('exit 7', result['error'])
        self.assertFalse(popen.call_args.kwargs.get('shell', False))
        proc.pid = 999999
        proc.communicate.side_effect = [subprocess.TimeoutExpired(['fake'], 3), (None, None)]
        with patch.object(refresh.os, 'killpg') as kill:
            result = refresh.invoke(['fake'], 'prompt', self.root, 3)
        self.assertEqual(result['status'], 'failed')
        kill.assert_called_once()
        self.assertEqual((self.root / 'receipt.json').stat().st_mode & 0o777, 0o600)


if __name__ == '__main__':
    unittest.main()
