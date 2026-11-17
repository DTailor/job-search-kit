# Wide discovery for job-scout

Use when the person asks to expand the lookup or when ordinary scouting repeatedly returns the same employers. This reference complements job-scout; company-background and action boundaries remain in force. Apply `profile/PREFERENCES.md` (Workflow notes > scout-discovery) and the dated access notes in `profile/SOURCES.md`.

## Search the unexplored surface

Reconcile the current catalogue, monitored pool, pipeline, applications and dated rejects once. Keep an exact-requisition dedup set plus company-level application and human-hold exclusions. A past rejection of one requisition is not a permanent company-wide exclusion; preserve the one-application-per-company preference unless the person changes it. An old access failure does not establish closure.

Build a discovery matrix across independent routes:

- Broad boards and local/contract boards relevant to the person's field and country (see `profile/SOURCES.md`).
- Employer ATS domains beyond the known boards: Ashby, Greenhouse, Lever, SmartRecruiters, Teamtailor, Personio, Recruitee, Workable, Comeet, Breezy and JazzHR when surfaced. Use `tools/ats_census.py` to enumerate and read them at scale instead of probing slugs by hand; read every surviving group, not a sample, and report the funnel counts.
- Agencies with concrete engagements; separate recruiter, payer and client. Generic talent-pool registration is not a job.
- Investor/accelerator portfolios and employer career pages in sectors that hire the person's role. Verify portfolio membership: syndicated listings on an investor board need not be investees.
- Existing-employer boards for genuinely new requisitions. This is one route, not a substitute for employer discovery.

Vary titles (use every variant in `search.role_titles` and `profile/PROFILE.md`, plus adjacent titles with the same substantive work), skill terms and location/contract wording. Use both broad searches and targeted skill/tool queries. Do not require every title to contain every keyword; verify the actual work and level in the body. Do not require a contract term in every query: many suitable employers use contractor, freelance, independent services or omit the route. Evidence of an excluded contract form is still a hold under the person's current preferences.

Do not globally exclude common buzzwords from discovery: a role may mention a technology or trend without requiring specialist expertise. Read must-haves, optional skills and actual work separately. Do not add out-of-scope roles to increase counts.

## Depth and stopping

Inspect pagination and active filters before treating a search as exhausted. Validate filters against returned category, seniority and location fields: an endpoint may silently ignore unsupported query parameters while returning HTTP 200. Derive current syntax from actual responses rather than assuming an old example is permanent, and record working syntax as a dated note in `profile/SOURCES.md`. Complete a promising filtered window or record its cap and next cursor. For signed-in searches, inspect inherited salary/location/date filters without changing saved preferences. For ATS APIs, distinguish listing cards from fetched role descriptions and report endpoint pagination limits. Zero picks from a bounded first page says nothing about the rest of that board.

When a route mostly repeats known companies, switch vocabulary, geography/contract wording or employer source rather than repeatedly recrawling the same feed. Continue with independent underexplored routes while they produce plausible new employers. Finish with useful verified picks or an explicit coverage boundary and remaining routes; never claim a market-wide absence from an exhausted queue. A requested pick count is a maximum, not a target to pad.

Revisit low-yield sources during wide runs. Three zero-yield checks can justify lower frequency, not permanent retirement. Separate `blocked`, `partial`, `exhausted` and `reused` in the ledger; blocked/partial runs do not count as successful zero-yield inventories. An access error triggers recovery work, not source deferral.

Use an access ladder: check the current canonical domain and exact employer-linked ATS slug (including case); try the existing authorized browser session (`accounts.browser`) for JavaScript rendering; inspect the employer's current careers index and its public listing/detail endpoints; use a different public primary route (for example an ATS account feed or a CMS job-listings REST index) when the page exposes that backend. Follow current links instead of repeatedly guessing slugs. Search indexes/aggregators can recover a canonical URL, but remain discovery evidence until a primary body is read. A role absent from a recovered complete current inventory differs from a blocked inventory, and an explicit closed body outweighs a stale careers card.

Continue through materially different available methods until content is recovered or a concrete remaining access boundary is established. Avoid replaying the same failed request. Record each method/result and a useful next route when unresolved; do not label a whole source unusable from one endpoint error. Existing authenticated sessions should be rechecked after the person reports authentication. Do not silently turn login, consent or assessment steps into read-only research.

Monthly hiring threads are scanned in full once per thread; later runs inspect only new comments after the saved timestamp. Record the delta window and avoid counting previously reviewed comments again.

## Progressive verification and publication

1. Triage discovery cards cheaply for work, location and application duplicates. Record a concrete exclusion/reopen condition for near misses; unknown commercial terms alone are not a rejection.
2. Retrieve the exact primary employer/agency description and country restrictions. A shell/HTTP 200, cached search result or sibling posting is insufficient live evidence. Use the access ladder for an inaccessible primary; preserve the distinction between unresolved access and a negative finding.
3. Verify promising candidates' company background using the shared dossier workflow. Reuse current same-day evidence. Incomplete financial/client coverage stays visible; distinguish anonymous reviews from established conduct.
4. Rank by actual work, realistic gaps, scope and practical risk. Keep unverified discoveries in the scout evidence. Publish primary-verified conditional leads to the working queue (under standing authority), with the unresolved questions visible.
5. Publish one coherent end-of-scout batch using `tools/job_pool.py` and `tools/tracker_publish.py`, preserving human holds, source dates and process history. Update the source ledger with measured yield and limits, then read back changed tracker data and run `python3 tools/tracker_publish.py checks`. Do not rebuild the entire historical archive after each individual discovery.

Suggested coverage fields: `source`, `query_or_filter`, `checked_at`, `state`, `pages_or_windows`, `observations`, `unique_roles`, `unique_employers`, `new_employers`, `primary_verified`, `retained`, `duplicate_or_reject_reasons`, `next_cursor`, `access_limit`, `evidence_path`. Unknown counts stay null; do not invent totals from search estimates.
