# Architecture

## Configuration

`workspace.json` at the workspace root is the only place for person-specific settings that tools need: person (name, email, time zone, location, languages), accounts (email/calendar connectors, browser tool), tracker (spreadsheet ID, header row, five tab roles with title and numeric sheet ID), paths, search defaults and refresh schedule. Every tool imports `tools/workspace.py` (`load()`, `path(key)`, `tab(key)`, `tab_title(key)`, `sheet_url()`, `person()`), which finds the nearest ancestor containing `workspace.json` or uses `JOB_HUNT_WORKSPACE`.

Prose rules that agents need (positioning, gates, money, contract forms, dated decisions, writing, sources) live in `profile/`. Playbooks reference both by key or file and heading.

## Data flow

```text
sources (boards, ATS APIs, alerts, network, agencies)        email / messages / portals / calendar
        |  job-scout, job-refresh                                    |  job-status
        v                                                            v
scout runs <paths.scouts>/scout-YYYY-MM-DD/        status snapshots <paths.status>/YYYY-MM-DD.md
  findings.json, rejects.txt, summary.md, coverage.json
        |                                                            |
        v                                                            |
company dossiers <paths.companies>/<slug>.md  <-- company-background (every retained firm)
        |                                                            |
        v                                                            v
reviewed pool <paths.pool> (current-pool.json)  <-----------  application state changes
        |   queue rule + revision: tools/job_pool.py                 (job-archive, job-status)
        v
tracker tabs (Google Sheet)                          local dashboard (<paths.dashboard>)
  All roles   full catalogue; operational columns derived from the pool
  queue       live, unsubmitted, not failed/held: the next roles to work
  audit       every monitored original, incl. closed/blocked/held
  pipeline    concrete conversations, applications, tasks (edited in place)
  Shortlist   derived history
```

- **Sources → pool.** Scout and refresh collect leads, verify each live on the employer's own site, run the company background check and add retained roles to the reviewed pool. Scheduled refresh writes only to `<paths.automation>/` (cache, runs, proposals); a person or interactive agent reviews proposals into the pool.
- **Pool → tracker.** The pool is the source for the queue, audit and All roles operational columns. `tools/job_pool.py` holds the queue predicate and a content revision so every view can be compared.
- **Status → pipeline.** Status reconciles every personal source into a deduplicated inventory and updates the pipeline tab in place; archive records submissions and removes the company from the queue.
- **Tracker → dashboard.** Finalize rebuilds the dashboard from the same pool and readback, so tracker and dashboard show the same revision.

## Publication pattern

Google Sheets is written through the agent's Sheets connector (no local credentials). `tools/tracker_publish.py` does everything around that call:

1. **plan** `SPEC.json` → `OUTDIR/requests.json` (the exact batchUpdate requests) and `OUTDIR/readback-ranges.json`.
2. **batchUpdate:** the agent passes `requests.json` verbatim to `update_spreadsheet`.
3. **readback:** the agent calls `get_values` for each range and saves the raw responses as one JSON list.
4. **verify** `OUTDIR READBACK.json --find-replace N,M` compares the readback with the plan (and the findReplace reply counts).
5. **finalize** `OUTDIR` writes the pool, manifest, catalogue and dashboard data, moves `<paths.tracker_base>`, rebuilds the dashboard and runs every consistency check.

`tracker_publish.py checks` runs the consistency checks alone. During one-by-one applications, the working record (pipeline + queue + local exclusion) is updated at once and the full batch is run at the end of the round; deferred views are labelled pending.

## Ownership

| Kit-managed (replaced by `tools/kit_sync.py --apply`) | Instance-owned (never overwritten) |
|---|---|
| `playbooks/*.md` | `workspace.json` |
| `.agents/skills/*/SKILL.md`, `.claude/commands/*.md` | `AGENTS.md` (filled from the template; merge template changes by hand) |
| `tools/` (kit tools), `dashboard/` | `profile/PROFILE.md`, `PREFERENCES.md`, `SOURCES.md`, other profile notes |
| `templates/`, `AGENTS.template.md`, `SETUP.md`, `README.md`, `docs/` | data folders under `paths.*`: pool, automation, status, plans, scouts, applications, companies |
|  | the live Google Sheet and any local history |

Rule of thumb: if a rule names the person, a company, a date they decided something, or a specific account, it belongs in `profile/`. If it describes how a workflow works for anyone, it belongs in a playbook.
