# job-status: the complete current pipeline and what changed

Read `README.md` in this folder first (shared facts and rules), then `profile/PREFERENCES.md` (Workflow notes > job-status).

Argument: `[since YYYY-MM-DD] [company]`. Default window: since the date of the latest `<paths.status>/*.md`, else the last 7 days.

## Scope

Check **all current applications, pending applications, recruiter conversations, interviews and recruitment tasks**, across the professional network, job boards, email, the tracker and every other relevant status source named in the profile, playbooks or applicable skills. The `since` window controls the changes section and discovery searches; it must never hide an older application, unanswered invitation, scheduled interview or unfinished task. A company argument narrows the requested report only when the person explicitly supplies it.

Build the current picture from the **union of sources**, not just the pipeline tab or recent email. Check submitted applications, explicitly planned/started but unsubmitted applications, pending invitations and unanswered questions, booking links, scheduled interviews, assignments, requested documents, consents and follow-ups. Saved jobs and a generic suggested application are not evidence of an application in progress. Keep dormant/declined leads and unresolved older inbound visible separately; do not silently reactivate or close them.

Use available connectors first, then the existing authorized personal browser session (`accounts.browser`; read that tool's own instructions before first use). Verify `person.email` on the relevant signed-in surface. A logged-out tab in one browser is not proof that another authorized browser is unavailable. Do not request login codes, log in, accept invitations, start assessments, submit forms or change consents during a status check.

## Steps

1. **Load the current picture.**
   - Latest status snapshot.
   - Shortlist rows with Status Applied, Asked screening Qs, Interviewing, Offer or On hold.
   - All pipeline rows.
   - Queue (live candidates), audit (complete monitored pool), `<paths.pool>` and All roles operational dispositions. Reconcile queued/unsubmitted targets against actual receipt evidence; retain reserve, held, excluded and research-backlog labels. Technical-fit decisions in All roles do not establish an intention or authority to apply.
   - Any additional tracker tabs listed in `profile/PREFERENCES.md` (Tracker notes), such as an inbox, channels or agencies tab: discover conversations and application records missing from the main tabs. Research recommendations and descriptions of a generic hiring process are not personal status.
   - Local `<paths.applications>/*/application.md`, task specifications, roadmaps, prep notes, plans and any explicitly linked task workspace. Read task progress without executing archived scripts or resuming implementation. Read applicable followup/interview/archive instructions for additional evidence sources. Historical exports supply leads to verify, not fresh status.
   - From the union, build a deduplicated inventory by company + exact role/requisition + contact. For each item retain stage, channel, source, last verified date, next owner and deadline. Distinguish unsent application, submitted application, recruiter lead, passed screen, booked interview and assigned task.

2. **Email** (read-only; never reply, label, archive or delete).
   - Search the window with:
     - tracked company and contact names;
     - hiring-platform senders: ashbyhq, greenhouse, lever, smartrecruiters, recruitee, workable, myworkday, teamtailor, personio, bamboohr, jazzhr, breezy, plus any listed in the person's notes;
     - notifications from the job boards and professional network the person uses;
     - words such as assignment, take-home, case study, test task, interview, unfortunately, "next steps".
   - Include Spam and Trash; real notices land there.
   - For every open item, retrieve its latest full thread even when the last message predates `since`. Check sent replies and job-related existing drafts so a reply already sent is not requested again and an unsent draft is not counted as submitted. Widen discovery when the inventory or another source shows an older unresolved item; exhaust relevant search pagination.
   - Read matching threads in full. Read attachments when they carry the substance (a job description, an assignment, a presentation). Summarise them; don't copy them into the workspace.
   - Job-alert emails are scout input: list new roles they contain under "From alerts" in the snapshot for the next scout to dedup and verify.

3. **Professional network** (for example LinkedIn). Read messaging threads with activity in the window, every thread linked from the current inventory, and older unresolved recruiter invitations discovered in any source. Include relevant message-request folders where available. Check the applied-jobs list and any visible application-in-progress state for missing applications or status changes. Record each question the other side asked, in short form. Those questions drive the reply drafts in `job-plan`. Do not treat a saved job as submitted or reclassify a user-declined lead as active.

4. **Application boards, portals, calendar and task sources.**
   - **Job boards with chats or invitations:** check chats, pending invitations and applications on each board the person uses. Include old entries that remain pending; read exact invitation-linked roles. Reading an invitation is different from accepting it and sharing profile data.
   - **Board application dashboards:** check the candidate application/status dashboard whenever an application, unresolved invitation or notification points there, even without a new email. Read history and recruiter questions if available.
   - **Employer/ATS candidate portals:** follow status links from confirmed applications in already signed-in personal sessions. If authentication, a new consent or an assessment is required, stop at that boundary and record the precise coverage gap; an email confirmation remains separate evidence.
   - **Personal calendar:** verify upcoming recruitment events, time zone, format, organizer, acceptance/cancellation and any changed date against the invitation thread. Use a bounded window through known future interviews; extend it when a known booking lies beyond the initial window. Do not expose unrelated calendar content or modify events.
   - **Tasks and preparation:** reconcile the latest task email, substantive attachment, linked task workspace and local roadmap/prep state. Record assigned/not started/in progress/paused/submitted, the evidence for that state, deadline conflicts and required follow-up. A plan, repository or generic hiring-process description is not proof of work completed or a task assigned. Never start an assessment to inspect its status.
   - Follow additional **relevant** status sources explicitly identified by applicable skills/playbooks or the current evidence. Do not enumerate unrelated installed skills, access employer accounts, or perform a new market-wide scout as part of status.

   Keep a coverage ledger: source/account, check time, scope, successful read or exact blocker, and which inventory items remain unverified. Reuse reads from the same run when still current; do not report a source as checked merely because its URL or email notification was found.

5. **Classify each new signal:**
   - confirmation; rejection; posting closed;
   - new recruiter inbound;
   - recruiter reply, with the questions asked;
   - intro or screen invite, with the booking link and its expiry;
   - interview invite, with stage, date and format;
   - assessment, take-home, case study or presentation, with the deadline and an effort estimate. If the email and the attachment disagree on the deadline, flag it and use the earlier date;
   - offer, with full terms;
   - other.

   For each open thread, note who is waiting (the person or them) and how many days since the last move.
   Reconcile conflicting statuses without silently choosing a convenient one. Link the evidence and distinguish an actual rejection from the person dropping a role, a closed posting from a closed candidacy, and an interview booking from a passed interview. Age alone does not close an application.

6. **Quick screen of new inbound**, 3–5 lines each:
   - who the company is (legal entity if it's easy to find);
   - role level and the skills asked for;
   - pay if stated;
   - eligibility from the person's country and the contract route (forms listed in `profile/PREFERENCES.md`);
   - red flags.

   Include the dated employer/agency/client [company background check](company-background.md), link its dossier, and surface material findings in the inbound summary. Reuse current dossiers for unchanged opportunities; refresh when a material new signal appears. An unknown client or incomplete company check remains explicit rather than being labelled vetted.

   Go deeper only when the person asks.

7. **Write the snapshot** `<paths.status>/YYYY-MM-DD.md`. These are local notes, so no approval is needed. Sections:
   - **Changes since <date>**: one line each, with a link.
   - **Board**: a table with opportunity/contact, channel, stage, waiting on, next deadline, last move (date) and link. Sort it by the most advanced stage first, then rejected/closed in a short list.
   - **Pending applications and tasks**: explicitly list unsubmitted applications, interviews/prep, assigned assessments, documents/consents and their evidence-backed progress. Say when no item was found; distinguish that from inaccessible sources. Keep older unresolved/dormant leads in a separate subsection rather than omitting them.
   - **Questions awaiting the person's answer**: per thread, each question the recruiter asked, quoted briefly (under 15 words each).
   - **Tracker changes made** (or proposed, without standing authority): concise list from step 8, plus any update blocked by missing evidence/access.
   - **From alerts (for scout)**.
   - **Threads opened**: the conversations this check marked as read.
   - **Source coverage and gaps**: the ledger from step 4, plus discrepancies or items discovered outside the tracker. State the boundary of completeness; do not claim all sources were verified when a portal or message folder was inaccessible.

8. **Update the tracker.** With standing authority recorded in `profile/PREFERENCES.md`, maintain the pipeline and affected supporting rows from verified evidence or the person's explicit report; otherwise propose the changes as a numbered list and write on approval. Every rejection, closure or stage change found above must appear; reporting it only in chat leaves the tracker stale. New role-bearing conversations go in the pipeline; closed records retain date/reason/history. Update application exclusions and remove submitted/rejected/held targets from the queue. Append a Timeline line to affected application dossiers when useful, and read back the changes. Ambiguous evidence stays labelled; never close for age alone or overturn a human hold.

9. **Reply** in at most 12 lines:
   - counts (active, waiting on the person, waiting on them, rejected);
   - what changed;
   - what is waiting on the person, with deadlines;
   - the tracker changes made;
   - any material coverage gap; keep overall inventory counts distinct from changes during the window and older unresolved leads.

   End by pointing to `job-plan` for what to do next.

Published queue membership must use `tools/job_pool.py`. Match exact requisition URLs, not company alone; compare gates and revision across published tracker/dashboard views. Run `python3 tools/tracker_publish.py checks` after updating published views. Research caches and old dated reports cannot silently overwrite published state.

Automation: run `python3 tools/status_portals.py` for step 4 portals and professional-network surfaces, and `tools/tracker_publish.py` for step 8 (see README "Automation tools").
