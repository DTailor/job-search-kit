"""Shared, dependency-free rules for the published job pool and its views.

Paths come from workspace.json (paths.pool); see tools/workspace.py.
"""
from pathlib import Path
import collections
import hashlib
import json
import re
try:
    from tools import workspace
except ModuleNotFoundError:
    import workspace

try:
    ROOT = workspace.root()
    CURRENT = workspace.path('pool')
except FileNotFoundError:  # importable for unit tests outside a workspace
    ROOT = Path(__file__).resolve().parents[1]
    CURRENT = None
QUEUE_BUCKETS = frozenset(('Priority screen', 'Screen first', 'Reserve / stretch'))


def application_excluded(job):
    labels = [str(job.get(k, '')).strip().casefold() for k in
              ('application_state', 'application_status', 'status', 'bucket',
               'current_bucket', 'disposition', 'human_disposition')]
    affirmative = re.compile(r'^(?:related\s+company\s+)?(?:application\s+)?(?:applied|submitted|rejected)(?:$|[\s:;|—–(])')
    applications = any(affirmative.match(label) for label in labels)
    human = str(job.get('human_disposition', '')).strip().casefold()
    return applications or job.get('human_hold') is True or human in ('hold', 'on hold') or any(
        label in ('human hold', 'hold human', 'human-held') for label in labels)


def queue_eligible(job):
    return (job.get('verification_state') == 'live'
            and job.get('bucket') in QUEUE_BUCKETS
            and job.get('decision') != 'Drop'
            and not application_excluded(job)
            and 'fail' not in (job.get('gates') or {}).values())


def queue_jobs(jobs):
    return sorted((j for j in jobs if queue_eligible(j)), key=lambda j: j.get('priority', 9999))


def counts(jobs):
    queue = queue_jobs(jobs)
    return dict(pool=len(jobs), queue=len(queue),
                priority=sum(j['bucket'] == 'Priority screen' for j in queue),
                screening=sum(j['bucket'] == 'Screen first' for j in queue),
                reserves=sum(j['bucket'] == 'Reserve / stretch' for j in queue),
                audit_only=len(jobs)-len(queue),
                verification=dict(collections.Counter(j['verification_state'] for j in jobs)),
                buckets=dict(collections.Counter(j['bucket'] for j in jobs)))


def revision(jobs):
    # Sheet row numbers are layout, not job identity or facts.
    stable = [{k: v for k, v in j.items() if k not in ('catalogue_row', 'original_catalogue_row')}
              for j in sorted(jobs, key=lambda j: j['pool_id'])]
    return hashlib.sha256(json.dumps(stable, sort_keys=True, ensure_ascii=False).encode()).hexdigest()[:16]


def validate(data):
    jobs = data['jobs']
    if len({j['pool_id'] for j in jobs}) != len(jobs):
        raise ValueError('Duplicate pool_id')
    if len({j['original_url'] for j in jobs}) != len(jobs):
        raise ValueError('Duplicate original requisition URL')
    if data.get('revision') != revision(jobs):
        raise ValueError('Published revision does not match job facts')
    for j in jobs:
        if j.get('verification_state') == 'closed' and j.get('bucket') in QUEUE_BUCKETS:
            raise ValueError('Closed original has an actionable disposition: '+j['pool_id'])
        if j.get('bucket') == 'Priority screen' and not queue_eligible(j):
            raise ValueError('Priority target lacks live, unexcluded source state: '+j['pool_id'])
    return data


def load_current(path=None):
    path = Path(path or CURRENT or workspace.path('pool'))
    if path.stat().st_size > 2 * 1024 * 1024:
        raise ValueError('Published state exceeds 2MB')
    return validate(json.loads(path.read_text()))


def sheet_rows(jobs):
    rows=[]
    for n,j in enumerate(jobs,1):
        lineage=j['pool_id']+'; original URL/requisition retained'
        for key in ('matching_official_role','replacement'):
            if j.get(key):lineage+='; separate '+key+': '+j[key]['url']
        rows.append([n,j['bucket'],j['company'],j['original_title'],j['next_action'],
                     '; '.join(k+': '+v for k,v in j['gates'].items()),j['pay_published'],
                     j['background']['main_risk'],j['verification_state']+' — '+j['checked_at'],
                     j['original_url'],j['background']['path'],lineage,
                     ('Queued; ' if queue_eligible(j) else 'Audit only; ')+j['background']['judgement']])
    return rows


if __name__ == '__main__':
    state = load_current()
    print(json.dumps(dict(revision=state['revision'], **counts(state['jobs'])), indent=2))
