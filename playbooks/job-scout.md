# job-scout: find new roles worth applying to

Read `README.md` (shared facts and rules) and `sources.md` (source catalogue) in this folder first, then `profile/SOURCES.md` (the person's live source ledger), `profile/PROFILE.md` (positioning and fit) and `profile/PREFERENCES.md` (gates, Workflow notes > job-scout). If the person keeps a detailed research brief or fit model, it is linked from those notes; where it conflicts with `profile/PREFERENCES.md`, the newer dated preference wins.

Argument: `[N picks | focus]`. Focus can be a source category, a country, `agencies`, a title or a company list. Default: up to 10 picks, all channels.

For `wide`, "expand the lookup", "unturned stones" or persistently thin discovery, read [scout-discovery.md](scout-discovery.md). Search beyond the known employer set; expanding discovery does not broaden the person's role or contract scope.

## Steps

1. **Recover the existing list before scouting.** Reconcile the full All roles catalogue with the smaller monitored pool and pipeline. Refresh the strongest unsubmitted entries that meet the current scope; give every omitted item a concrete disposition. Distinguish new finds from recovered existing records, and conditional discussions from confirmed eligibility. Do not treat general senior ownership as a required prior title the person does not hold. Then collect the **dedup list**:
   - Shortlist and All roles: company, role, URL;
   - `<paths.applications>/*`;
   - pipeline companies;
   - every earlier `scout-*/rejects.txt` and any known-roles/rejects files listed in the person's notes;
   - older discovery/expanded-search findings and their raw candidate indexes, including records omitted from the visible catalogue. Match exact requisition identifiers as well as canonical URLs; label a recovered overlooked record separately from a new requisition at a known employer. A previously collected card is evidence of discovery, not proof it was verified, applied to or rejected.

   A new requisition at a known company is allowed; mark it `known_company`. Skip companies the person already applied to in this round (one application per company by default), unless the new role is clearly better. Say so when you skip one.

2. **Search the channels** in `profile/SOURCES.md` (sources marked "every" each run, "rotate" in turns, all of them for `wide`), using the categories and methods in `sources.md`. Prefer free public APIs over web search. Afterwards update Last/Yield in `profile/SOURCES.md`, and add any new source you found.
   - **Known employers:** re-scan the ATS boards of companies in All roles and Shortlist for new requisitions, using public APIs (Ashby posting-api, Greenhouse boards-api, Lever, SmartRecruiters, Recruitee, Workable, Workday cxs).
   - **Boards:** the general, country, field-specific and remote boards in the ledger; the professional network's job search (signed-in, read-only); monthly hiring threads.
   - **Networks and agencies:** research concrete, scope-matching openings with no established failed gate; unspecified commercial/location terms may remain Screen first. Keep generic network enrolment separate from a vacancy. This scout does not authorize applying through an intermediary.
   - Subagents may split the channels between them. Give each one the gates, the title list, its part of the ledger and a web-search budget, and keep its outputs inside the scout folder.

3. **Gates** from `profile/PREFERENCES.md` (newest dated entry first): role scope and level, country eligibility, working hours and after-hours duties, contract form and minimum term, pay floor. Pay at or above the floor, or unpublished with credible signals. Quote published pay exactly with its country scope, and never estimate it.

   Unspecified country approval, hours overlap, contract route, budget, duration or support are `unclear`, not failed gates. Broad region/time-zone wording without an explicit exclusion may support a conditional screen; it does not prove country eligibility. A verified useful role can enter Screen first with these questions open. Distinguish required existing specialisms from optional skills or supported learning; do not reject every tool or framework gap as a hard failure. Preserve human holds separately from reversible agent risk holds.

   Skip the role types listed as out of scope in `profile/PREFERENCES.md`. Note the process weight: number of rounds, take-home or case-study size, live exercises, presentations. Apply the person's process preference.

4. **Verify** each pick live on the employer's own ATS or careers site on the day you check it. Aggregators and search results are only leads, and a JavaScript shell returning HTTP 200 is not proof the job exists. Complete or refresh the employer/agency/client [company background check](company-background.md) before presenting a retained pick; record unknown clients and incomplete evidence. Reuse a current company dossier across roles, keeping role-specific gates separate.

5. **Score** the fit against `profile/PROFILE.md`, applying current corrections first. Decide Pursue, Screen first, Stretch or Drop. Record the contract route, quoting the posting's wording. Keep discovery state (unverified lead / verified role), application suitability (conditional / fully cleared), and process status (unsubmitted / applied) distinct. A live form alone establishes an intake, not funded headcount or all eligibility gates.

6. **Write** `<paths.scouts>/scout-YYYY-MM-DD/`:
   - `findings.json` (one object per retained role: company, role, url, requisition, checked date, decision, fit note, published pay with scope, contract route, gates with pass/unclear/fail, process weight, plus a `background` companion object with dossier path, checked date and judgement);
   - `rejects.txt`: one line per near-miss, as `company | role | reason`;
   - `summary.md`: ranked picks with company, role, decision and fit, published pay, eligibility/contract route, process weight, why it fits (one line), company-background finding and dossier link, main risk or first question, posting link, and a suggested CV variant (see `profile/PROFILE.md` Materials).

   Don't pad the list. Zero picks is a valid result; say which channels were thin.

   For a wide run, also save `coverage.json` with exact queries/windows, pagination/access limits, unique roles and employers observed, primary verifications, dedup outcomes and remaining next cursors. Report how many retained roles are genuinely new, recovered or known-company new requisitions. Cached/indexed descriptions retain their own dates and do not become fresh employer verification.

7. **Update the tracker and supporting views** (under standing authority, else as a numbered proposal). Add retained, employer-verified leads to All roles and the published pool; show actionable candidates in the queue, including clearly labelled Screen first leads with unknown commercial terms. Do not add a scout lead to the pipeline until there is an actual conversation, application or task. Keep Shortlist as history rather than making the person approve/maintain another list. Match exact requisitions, preserve human holds and company/application dedup, copy safe native formatting/validation and read back the affected rows. Keep the local pool, audit and dashboard consistent in the same operation.

8. **Reply** with the best finds, what was added/changed, which to screen/apply to first and any material coverage gap. Do not contact or apply.
