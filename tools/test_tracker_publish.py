"""Publication planning against reviewed live drift never adopts stale views."""
import copy
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
from tools import tracker_publish as publish


class LiveReadbackPlanning(unittest.TestCase):
    def test_connector_null_is_blank_but_zero_and_literal_none_are_preserved(self):
        values = {"'Fixture'!A1:D1": [[None, 0, 'None']]}
        self.assertEqual(publish._lookup(values, "'Fixture'!A1:D1"), [['', '0', 'None', '']])
        self.assertEqual(publish.cell([[None, 0]], 0, 0), '')
        self.assertEqual(publish.cell([[None, 0]], 0, 1), 0)

    def test_stale_live_queue_and_revision_are_repaired_from_finalized_base(self):
        state = publish.load_current()
        base_path = publish.base_path()
        canonical = publish.read(base_path)
        live = copy.deepcopy(canonical)
        queue = next(s for s in live['sheets'] if s['sheet'] == publish.T['queue'])
        queue['values'][1] = ['stale headline']
        queue['values'][4][4] = 'stale next action'
        all_roles = next(s for s in live['sheets'] if s['sheet'] == publish.T['all_roles'])
        for row in all_roles['values']:
            for c, value in enumerate(row):
                if isinstance(value, str):
                    row[c] = value.replace(state['revision'], 'older-revision')
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            (root / 'live.json').write_text(json.dumps(live))
            spec = root / 'spec.json'
            spec.write_text(json.dumps(dict(label='fixture', date='2026-11-13', outdir='plan', live_readback='live.json')))
            with patch.object(publish, 'ROOT', root), patch.object(publish, 'base_path', return_value=base_path), patch.object(publish, 'load_current', return_value=copy.deepcopy(state)):
                publish.plan(spec)
            planned = publish.read(root / 'plan/planned-values.json')
            expected_queue = next(s for s in canonical['sheets'] if s['sheet'] == publish.T['queue'])['values']
            self.assertEqual(planned[publish.T['queue']][4][4], expected_queue[4][4])
            changes = publish.read(root / 'plan/changes.json')
            self.assertTrue(any(c['sheet'] == publish.T['all_roles'] for c in changes))
            self.assertTrue(any(c['sheet'] == publish.T['queue'] and c['row'] == 4 for c in changes))
            self.assertEqual(publish.read(root / 'plan/readback-ranges.json')['find_replace_expected'][0], 0)
            self.assertNotIn('older-revision', json.dumps(planned))

    def test_partial_live_snapshot_is_refused(self):
        base_path = publish.base_path()
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            (root / 'live.json').write_text(json.dumps({'sheets': []}))
            spec = root / 'spec.json'
            spec.write_text(json.dumps(dict(label='fixture', date='2026-11-13', outdir='plan', live_readback='live.json')))
            with patch.object(publish, 'ROOT', root), patch.object(publish, 'base_path', return_value=base_path):
                with self.assertRaisesRegex(AssertionError, 'every managed tab'):
                    publish.plan(spec)


class BackgroundRefresh(unittest.TestCase):
    def test_pool_background_change_rewrites_all_roles_company_line(self):
        state = publish.load_current()
        base_path = publish.base_path()
        job = state['jobs'][0]
        bg = dict(job['background'], checked_at='2026-11-26', judgement='Fixture judgement', main_risk='Fixture risk.')
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            spec = root / 'spec.json'
            spec.write_text(json.dumps(dict(label='fixture', date='2026-11-26', outdir='plan',
                                            pool={job['pool_id']: {'background': bg}})))
            with patch.object(publish, 'ROOT', root), patch.object(publish, 'base_path', return_value=base_path), patch.object(publish, 'load_current', return_value=copy.deepcopy(state)):
                publish.plan(spec)
            planned = publish.read(root / 'plan/planned-values.json')[publish.T['all_roles']]
            row = next(r for r in planned if len(r) > 22 and r[21] == job['original_url'])
            self.assertEqual(row[22], publish.background_cell(bg))
            self.assertTrue(row[22].startswith('2026-11-26 — Fixture judgement. Fixture risk.'))


class ShortlistSync(unittest.TestCase):
    REV = '0123456789abcdef'

    def row(self, status, readiness):
        row = [''] * 20
        row[16], row[17], row[19] = status, 'old next step', readiness
        return row

    def test_rejected_bucket_sets_status_and_derived_readiness(self):
        row = self.row('Applied', 'Applied; audit only; revision fedcba9876543210')
        publish.shortlist_sync(row, dict(bucket='Rejected', next_action='Closed.'), self.REV)
        self.assertEqual(row[16:20], ['Rejected', 'Closed.', '', f'Rejected; audit only; revision {self.REV}'])

    def test_applied_bucket_never_downgrades_a_finer_stage(self):
        row = self.row('Interviewing', 'Applied; audit only; revision fedcba9876543210')
        publish.shortlist_sync(row, dict(bucket='Applied', next_action='Await result.'), self.REV)
        self.assertEqual(row[16], 'Interviewing')
        row = self.row('Not contacted', 'free text kept')
        publish.shortlist_sync(row, dict(bucket='Applied', next_action='Await result.'), self.REV)
        self.assertEqual((row[16], row[19]), ('Applied', 'free text kept'))

    def test_explicit_status_wins(self):
        row = self.row('Applied', 'Applied; audit only; revision fedcba9876543210')
        publish.shortlist_sync(row, dict(bucket='Applied', next_action='Round 2 done.'), self.REV, 'Interviewing')
        self.assertEqual(row[16], 'Interviewing')

    def test_unknown_explicit_status_is_refused(self):
        state = publish.load_current()
        base_path = publish.base_path()
        pid = state['jobs'][0]['pool_id']
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            spec = root / 'spec.json'
            spec.write_text(json.dumps(dict(label='fixture', date='2026-11-25', outdir='plan', shortlist_status={pid: 'Hired?'})))
            with patch.object(publish, 'ROOT', root), patch.object(publish, 'base_path', return_value=base_path), patch.object(publish, 'load_current', return_value=copy.deepcopy(state)):
                with self.assertRaisesRegex(AssertionError, 'not one of'):
                    publish.plan(spec)


if __name__ == '__main__':
    unittest.main()
