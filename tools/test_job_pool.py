import unittest
from tools import workspace as ws
from tools.job_pool import counts, load_current, queue_eligible, queue_jobs, revision, validate


class PoolRules(unittest.TestCase):
    def setUp(self):
        self.job = dict(pool_id='fixture', original_url='https://example.org/req/1',
                        verification_state='live', bucket='Priority screen',
                        decision='Screen first', application_state='Not applied',
                        gates={'location':'unclear','pay':'unclear'}, priority=1)

    def test_live_conditional_candidate_is_allowed(self):
        self.assertTrue(queue_eligible(self.job))

    def test_closed_cannot_leak_through_a_stale_priority_label(self):
        self.job['verification_state']='closed'
        self.assertFalse(queue_eligible(self.job))

    def test_unavailable_never_becomes_a_live_application_target(self):
        for state in ('blocked','unclear','unavailable'):
            self.assertFalse(queue_eligible(dict(self.job, verification_state=state)))

    def test_holds_and_exclusions_are_audit_only(self):
        for bucket in ('Risk hold','Unverified','Exclude current role','Vacancy closed'):
            self.assertFalse(queue_eligible(dict(self.job,bucket=bucket)))

    def test_submitted_rejected_and_human_hold_never_requeue(self):
        for state in ('Applied','Submitted','Rejected'):
            self.assertFalse(queue_eligible(dict(self.job,application_state=state)))
        self.assertFalse(queue_eligible(dict(self.job,human_hold=True)))

    def test_hard_gate_failure_excludes_despite_priority_label(self):
        self.assertFalse(queue_eligible(dict(self.job,gates={'location':'fail'})))

    def test_partition_preserves_every_research_record(self):
        closed=dict(self.job,pool_id='closed',original_url='https://example.org/closed',
                    verification_state='closed',bucket='Vacancy closed')
        c=counts([self.job,closed]);self.assertEqual((c['pool'],c['queue'],c['audit_only']),(2,1,1))

    def test_revision_detects_a_changed_source_state(self):
        old=revision([self.job]);changed=dict(self.job,verification_state='closed')
        self.assertNotEqual(old,revision([changed]))
        with self.assertRaises(ValueError):validate({'jobs':[changed],'revision':old})

    def test_real_published_views_have_no_closed_or_unverified_targets(self):
        data=load_current();queue=queue_jobs(data['jobs'])
        self.assertTrue(all(j['verification_state']=='live' for j in queue))
        self.assertTrue(all(j['bucket'] not in ('Risk hold','Unverified','Exclude current role','Vacancy closed') for j in queue))
        # Workspace-specific regressions: companies that must never re-enter the queue.
        never=set(ws.check_option('never_queue_companies',[]))
        self.assertFalse(any(j['company'] in never for j in queue))

    def test_completed_round_can_have_an_empty_queue_without_losing_history(self):
        applied=dict(self.job,application_state='Applied',bucket='Applied')
        self.assertEqual(queue_jobs([applied]),[])
        result=counts([applied])
        self.assertEqual((result['pool'],result['queue'],result['audit_only']),(1,0,1))
