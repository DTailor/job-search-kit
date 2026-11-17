# Refresh the tracked application pool

Use job-scout's evidence and company-background rules for the current tracked pool, rather than opening a new market-wide scout. This workflow runs only when `refresh.enabled` is true and the person has authorized the schedule (record the authorization and its date in `profile/PREFERENCES.md`). The schedule authorizes public research and local reports; it does not authorize outgoing actions or unattended tracker writes.

## Canonical inputs and outputs

- `<paths.automation>/pool.json`: monitored identities with stable `pool_id` and original URL/requisition; reviewed facts live in `<paths.pool>`.
- `<paths.automation>/latest.json`: research cache. New unattended results are pending publication; failed/cached-only checks do not advance successful source dates. `<paths.pool>` remains the reviewed published pool.
- `<paths.automation>/catalogue.json`: local application/human-decision snapshot. Check the current personal tracker when available before effort, and exclude submitted/rejected/human-held firms. Local evidence and live tracker dates remain distinct.
- A refresh helper (for example `tools/job_refresh.py plan` / `run --dry-run` / `run`) computes a deterministic freshness/exclusion plan and invokes the configured agent only for due work. It reads no API keys or auth files.
- Dated `<paths.automation>/runs/<date>/<run>/` reports, ledgers, source captures and local company-update proposals. Preserve stable IDs and explicit source failures.

## Lightweight run

The freshness/exclusion helper runs without a model and exits immediately when nothing is due. Due work uses one short-lived agent session with a wall timeout and an overall search limit, no subagents, no recursive CLI processes, no browser automation and no local model. Ambiguities are reported for manual review rather than spawning more processes. Record the model, timeout and search limit the person chose in `profile/PREFERENCES.md` (Workflow notes > job-refresh). A full manual audit across several models is a deliberate one-off, not the recurring schedule. Keep one helper, one JSON policy and one prompt instead of separate agent configurations or a service. Routing/search limits are instructions, not an enforceable spending cap; keep actual usage logs locally.

## Freshness and cache

Active roles: once per calendar day in `person.timezone`. Closed/failed-gate roles: seven days. Unavailable checks: three-day backoff. Company dossiers: thirty days, earlier on a material signal. Human-held/submitted firms stay excluded until a human decision changes.

Capture the current public response before comparing a normalized content hash. A cached hash alone is not a new check. Save URL, exact requisition, response/capture timestamp, source type, availability and bounded excerpts. Access failure is not vacancy closure; a live JS shell is not a verified posting. Keep original and possible replacements separate. Reuse same-day primary evidence explicitly if a later fetch fails; record both times/states.

Maintain separate counts: monitored pool, live exact postings, unavailable/closed, priority screening targets, other screening candidates, reserves/stretches, firm-risk holds and exclusions. Unpublished pay or unresolved contract details may justify screening; they do not make a role fully cleared. Do not shrink the entire pool to the top priorities and call the remainder ineligible.

## Human review

No messages, applications, assessments, accounts, consents, calendar actions, profile edits or uploads. Scheduled runs produce local proposed tracker changes and evidence, not live Sheets mutations. Interactive follow-up work may incorporate these results under the person's standing tracker authority, if recorded; remap affected rows, preserve native structure and read back. The unattended schedule itself remains local-only. job-archive refreshes the local automation catalogue/exclusions when recording a confirmed submission.

The scheduler (`refresh.runner`, for example a macOS LaunchAgent or cron entry) runs at `refresh.weekday_time` in `person.timezone`. It needs the logged-in machine, network and working agent authentication; there is no cloud uptime guarantee. The helper enforces one run at a time and a wall timeout.

Publication contract: review cache proposals into `<paths.pool>`, use the shared queue predicate in `tools/job_pool.py`, reconcile all tracker/dashboard views by exact URL and revision, and run `python3 tools/tracker_publish.py checks`. Scheduled automation cannot publish tracker changes. Closed, blocked or unclear originals never qualify for the queue.
