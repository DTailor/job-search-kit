---
name: job-search
description: >-
  Sets up and runs a personal job search in this repository: profile and fit
  gates, verified market search, rechecks, company diligence, application forms,
  CV review, archive, follow-ups, and interview prep. Use when the user wants
  to set up the kit, find or recheck roles, screen a company or a form, review
  a CV, track an application, sync replies, draft a follow-up, or prepare
  for an interview.
---

# Job search

Personal requirements are gitignored. If `profile/profile.yml` is missing or `status` is not `ready`, follow `SETUP.md` at the repository root and stop.

When the profile is ready, read `AGENTS.md`, then the procedure that matches the task:

| Task | Procedure |
|---|---|
| Find roles | `commands/job-search.md` |
| Recheck stale or named postings | `commands/job-recheck.md` |
| Check a company or intermediary | `commands/job-diligence.md` |
| Read a form before they apply | `commands/job-screen.md` |
| Review the CV | `commands/job-cv.md` |
| Archive a submitted application | `commands/job-archive.md` |
| Sync replies | `commands/job-sync.md` |
| Draft follow-ups | `commands/job-followup.md` |
| Interview prep | `commands/job-interview.md` |

Research rules and the JSON result shape are in `search/SEARCH_BRIEF.md`.
