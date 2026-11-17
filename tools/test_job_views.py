"""Regression tests for drift between real published views (no network/browser).

Mutations are synthetic, so they work for any workspace, including an empty one.
"""
import copy
import unittest
from unittest.mock import patch
from tools import check_job_views as views
from tools import workspace as ws


def tab_values(data, key):
    return next(t['values'] for t in data['sheets'] if t['sheet'] == ws.tab_title(key))


class PublishedViewDrift(unittest.TestCase):
    def rejects(self, path, mutate):
        original = views.read
        def changed(relative):
            value = original(relative)
            if relative.endswith(path):
                value = copy.deepcopy(value)
                mutate(value)
            return value
        with patch.object(views, 'read', side_effect=changed):
            with self.assertRaises(AssertionError):
                views.check()

    def test_published_views_currently_agree(self):
        self.assertTrue(views.check()['result'])

    def test_closed_role_cannot_reappear_in_queue_snapshot(self):
        def mutate(data):
            audit = tab_values(data, 'audit')[ws.header_row('audit'):]
            closed = next((r for r in audit if len(r) > 1 and r[1] == 'Vacancy closed'), None)
            closed = closed or ['1', 'Vacancy closed', 'Fixture Co', 'Closed role'] + [''] * 9
            tab_values(data, 'queue').insert(ws.header_row('queue'), closed)
        self.rejects('tracker-snapshot.json', mutate)

    def test_dashboard_cannot_keep_a_stale_gate(self):
        def mutate(data):
            label = next(iter(ws.gates()['dashboard']))
            queued = next((r for r in data['opportunities'] if r.get('poolId')), None)
            if queued:
                queued['gates'][label] = 'concern'
            elif data['poolAudit']:
                data['poolAudit'][0]['gates'][ws.gates()['dashboard'][label]] = 'concern'
            else:  # empty pool: an audit card without a pool record is drift too
                data['poolAudit'].append({'poolId': 'fixture', 'gates': {}})
        self.rejects('reviewed-data.json', mutate)

    def test_closed_sibling_cannot_inherit_live_requisition_disposition(self):
        def mutate(data):
            tab_values(data, 'shortlist').append(
                ['99', 'Closed', '', 'Fixture sibling Co', 'Fixture role'] + [''] * 14 + ['Screen first; queued; stale sibling join'])
        self.rejects('tracker-snapshot.json', mutate)

    def test_revision_mismatch_is_detected(self):
        self.rejects('reviewed-data.json', lambda d: d.update(publicationRevision='stale'))
