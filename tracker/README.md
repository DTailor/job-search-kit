# Tracker

`tools/tracker.py` is the only writer for these CSVs. Column order is the header constants in that file, and the example files are those headers with no rows.

| File | Holds | Key |
|---|---|---|
| `roles.csv` | One row per exact posting URL | `url` |
| `companies.csv` | Employer and intermediary diligence | `company` |
| `channels.csv` | Boards, communities, and contract marketplaces | `name` |
| `coverage.csv` | Sources checked, drops, and rechecks | append only |
| `inbox.csv` | Messages and what they imply | append only |
| `watchlist.csv` | Companies whose boards should be rescanned | `company` |

`status`, `next_step`, and `notes` belong to the person. Import and recheck leave them alone once status is no longer `Not contacted`.

## Decisions

- **Pursue.** Gates pass or look resolvable. Ask the screening questions, then prepare.
- **Screen first.** The work fits, and one gate is unknown. Ask before investing more time.
- **Stretch.** A real gap in language, level, domain, or schedule. Keep it, and do not treat it as a first choice.
- **Drop.** A gate failed, the row is a duplicate, or the requisition closed. `coverage.csv` keeps the reason.

## Status

The only status values are: Not contacted, Asked screening Qs, Applied, Interviewing, Assessment, Offer, On hold, Rejected, Withdrawn.

`commands/job-archive.md` sets Applied, because the person already submitted. Every other status change waits for their approval, then:

```bash
python3 tools/tracker.py set-status URL "Interviewing" --next "prepare" --notes "invite 2026-10-20"
```

## Pay and vehicle

`pay_published` is a quote, or empty. `pay_scope` is `local`, `location_independent`, `other_country`, or `unpublished`. `pay_verdict` is Clears, At floor, Unclear, Likely below, or Below. A third-party figure goes in `pay_evidence` and is labelled third-party. Missing pay is Unclear.

`vehicle` quotes how the person would be engaged. `vehicle_fit` is `matches`, `likely`, `ask`, `unlikely`, or `no`, compared with `vehicles` in the profile. An intermediary's bill rate is not the person's pay.

## Company verdicts

- **Green.** No material concern in the sources checked.
- **Amber.** A specific concern to ask about before investing time.
- **Red.** Avoid unless the person says the facts have changed.

Label any inference. A rating taken from a search snippet, or from fewer than 20 reviews, is weak evidence. Say so in the row.

## Commands

```bash
python3 tools/tracker.py init
python3 tools/tracker.py validate-run search/runs/YYYY-MM-DD/slice.json
python3 tools/tracker.py import-run search/runs/YYYY-MM-DD/slice.json
python3 tools/tracker.py upsert companies row.json
python3 tools/tracker.py upsert watchlist row.json
python3 tools/tracker.py append inbox row.json
python3 tools/tracker.py append coverage row.json
python3 tools/tracker.py add-role --url URL --company NAME --role TITLE
python3 tools/tracker.py recheck recheck.json
```

`recheck.json` is an object or a list: `url`, `live_status` (`live`, `closed`, `unlisted`, `changed`), `checked`, `detail`, and optional `updates` for research columns. Updates apply only while status is `Not contacted`. A closed or unlisted posting becomes decision Drop only in that same case. An application already in progress stays as it is, and the result is still written to coverage.

`sync-state.md` records the last inbox sync and the last recheck. A spreadsheet is a mirror unless the profile says it is the source of truth.
