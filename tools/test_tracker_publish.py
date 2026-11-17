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


if __name__ == '__main__':
    unittest.main()
