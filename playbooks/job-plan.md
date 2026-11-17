# job-plan: what to do next

Read `README.md` in this folder first (shared facts and rules), then `profile/PREFERENCES.md` (money, availability, Workflow notes > job-plan).

Argument: `[today | week | <company>]`. Default: the next 7 days.

## Steps

1. **Inputs.**
   - The latest `<paths.status>/*.md`. Refresh the relevant stale or changed threads needed for this plan. Do not force a full pipeline reconciliation for a focused request; run full `job-status` when the person requests it or the plan genuinely needs complete coverage.
   - The pipeline tab and the open Shortlist rows.
   - Queue (live candidates), audit (all monitored originals), `<paths.pool>` and All roles operational dispositions: merge older unsubmitted candidates with new scout finds, avoid duplicate company applications, and retain explicit priority/reserve/research-backlog distinctions. Reconcile omissions and update relevant tracker priorities/next actions under any standing authority; keep human decisions separate.
   - The newest `scout-*/summary.md`: picks not yet applied to.
   - Dated employer/agency/client dossiers for proposed targets and imminent interviews. Follow [company-background.md](company-background.md); complete missing checks and refresh material changes before ranking. Include company-background findings and dossier links in the comparison, and let concrete stability/reputation/client risks affect priority without inventing a risk score.
   - The calendar (`accounts.calendar_connector`), read-only, for the next 14 days, so preparation and take-homes go where the person has time.
   - If the person hasn't said how many hours they have this week, use the default in `profile/PREFERENCES.md` (else about 10) and say so.

2. **Collect the candidate moves.**
   - **Hard dates:** take-home and case-study deadlines, booking-link expiries, interview dates.
   - **Waiting on the person:** every unanswered recruiter question becomes a reply draft (rules below).
   - **Follow-ups:** applications quiet for the follow-up threshold (default 10 days). Name them and hand off to `job-followup`. If quiet for the withdrawal threshold (default 60 days), propose Withdrawn.
   - **Preparation:** interviews within 7 days go to `job-interview`. A take-home, case study or presentation gets a scope plan: the smallest piece of work that meets every stated requirement, an hour estimate, and the questions to clear first (deadline, contracting route from the person's country, pay).
   - **Decisions:** compare terms side by side:
     - pay in the configured currencies, plus a net estimate where `profile/PREFERENCES.md` defines one;
     - hours, paid leave, minimum term, notice;
     - on-call or after-hours work;
     - project continuity (network membership is not a placement).
   - **Declines:** leads that fail a gate and aren't named backups. Write a one-line polite decline draft.
   - **Pipeline health:** count the processes past CV screening that could reach an offer clearing the floor before the person's target date (see availability in `profile/PREFERENCES.md`). If there are fewer than the minimum (default 3), recommend an apply round from the latest scout picks, or a new `job-scout`.

3. **Rank** the moves by:
   1. hard deadline;
   2. closeness to an offer that clears the floor;
   3. cost in the person's hours;
   4. how hard it is to undo.

   Say plainly what you would drop and why. Backups below the floor rank after everything above the floor unless the person says otherwise.

4. **Write** `<paths.plans>/YYYY-MM-DD.md` and reply with:
   - **Moves** (at most 7): who acts (the person or agent), what, by when, and why, in one line each.
   - **Drafts**, ready to paste, each labelled with its recipient and channel.
   - **Handoffs**: the commands to run next, for example `/job-followup 10`, `/job-interview <company>`, `/job-scout`.

5. **Send nothing.** When the person says they sent, booked or submitted something, record it in the pipeline and relevant supporting records (under standing authority, else as a proposal). Use `job-archive` for a new application without making them invoke another command. Keep their report distinct from independently checked receipts.

## Draft rules

- **Answer every question the other side asked, in their order,** before adding anything. Check them against the snapshot's "Questions awaiting the person's answer".
- **Keep it short and human,** like a person typing: 1–4 sentences, no "I hope this finds you well", no buzzwords, no list of demands. Ask one or two questions at most.
- **Language and tone** as recorded in `profile/PREFERENCES.md` (Writing), including per-language conventions.
- **Introductions vs direct questions:** unless the person's preferences say otherwise, initial applications and introductory messages open a discussion about the work and fit. Do not volunteer compensation figures or lead with contracting, location-approval, hours or on-call screening questions; keep those checks in private preparation and raise them once a conversation is open. Answer direct employer questions, including salary, total compensation and availability, with the known expectations from `profile/PREFERENCES.md`. Preserve earlier opportunity-specific asks as history; do not overwrite them.
- **Money:** use the recruiter wording and current default ask from `profile/PREFERENCES.md`, never the private floor.
- **Attachments:** name the exact file to attach (the current general CV, or a tailored one; see `profile/PROFILE.md` Materials).
- **Phone number:** leave a placeholder; the person types it.
- **Availability:** use the exact availability wording in `profile/PREFERENCES.md`; do not give a specific day unless the person supplies one.

Published queue membership must use `tools/job_pool.py`. Match exact requisition URLs, not company alone; compare gates and revision across published tracker/dashboard views. Run `python3 tools/tracker_publish.py checks` after publication. Research caches and old dated reports cannot silently overwrite published state.

### Full-library planning

Before calling a queue exhausted, reconcile All roles (the complete catalogue) with `<paths.pool>` (a monitored subset). Report remaining conditional screens separately from fully cleared roles, apply existing company-level exclusions and preserve human holds. Recover relevant older in-scope records before proposing a wider search. Show the next role's product, actual work, fit, gaps and contract/location evidence before asking about form fields. Complete one supporting-view batch on an explicit consolidation, then return to lean per-application updates.
