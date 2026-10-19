# Job search kit

A job-search workspace an agent can run for anyone. The template has the method and no personal data. A setup prompt interviews the next person and writes their profile, gates, and preferences into this folder.

Give someone this repository and this prompt:

```text
Set up this job search for me. Follow SETUP.md. Interview me, draft my profile, and wait for my confirmation. Do not search for jobs until I confirm.
```

They can paste that on the first message after opening the repo. If `profile/profile.yml` is missing, the agent is supposed to run setup before it searches, drafts, or edits the tracker.

## What you get after setup

| Need | Where |
|---|---|
| Requirements, gates, and positioning | `profile/profile.yml` and `profile/PROFILE.md` |
| What the agent may do | `AGENTS.md` |
| A verified role search, then a recheck when it goes stale | `commands/job-search.md`, `commands/job-recheck.md` |
| Roles, coverage, companies, channels, inbox | `tracker/` via `tools/tracker.py` |
| Company and intermediary checks | `commands/job-diligence.md` |
| Public form questions, before anyone applies | `commands/job-screen.md` |
| What was applied and what was sent | `applications/<company>_<role>/` |
| Follow-ups and interview prep | `commands/job-followup.md`, `commands/job-interview.md` |
| CV review against private evidence | `commands/job-cv.md` and `cv/` |

The CSV tracker is the status source. A spreadsheet or Gmail connection is optional and stays off until setup turns it on.

## Commands

| Say this | Procedure |
|---|---|
| Set this up | `SETUP.md` and `commands/setup.md` |
| Find roles | `commands/job-search.md` |
| Recheck what is still live | `commands/job-recheck.md` |
| Check this company | `commands/job-diligence.md` |
| Read the form | `commands/job-screen.md` |
| Review my CV | `commands/job-cv.md` |
| I applied to this | `commands/job-archive.md` |
| Check for replies | `commands/job-sync.md` |
| Draft follow-ups | `commands/job-followup.md` |
| Prep me for this interview | `commands/job-interview.md` |

The same procedures are available as Claude slash commands under `.claude/commands/`.

## What stays private

Setup writes career details, and later searches add employers, pay, and messages. Those paths are listed in `.gitignore`:

- `profile/profile.yml`, `profile/PROFILE.md`, `profile/voice.md`, `profile/NEXT_SESSION.md`
- `cv/` except this kit's `cv/README.md`
- `applications/` except `applications/README.md`
- `screening/` except `screening/README.md`
- `tracker/*.csv` except the header-only examples, and `tracker/sync-state.md`
- `search/runs/`

Check `git status` before you push a fork. A filled-in profile does not belong in a public repository.

## Layout

- `SETUP.md`: the prompt.
- `AGENTS.md`: operating rules once a profile exists.
- `profile/`: example and template. The real profile is created locally.
- `search/`: how a research pass verifies a role, and the JSON shape it must write.
- `commands/`: one procedure per file. Claude slash commands point here; they do not carry a second copy.
- `templates/`: posting, application, prep, interview brief, evidence ledger, form screen, and next-session prompt.
- `writing/GUIDE.md`: how to draft application answers.
- `tools/check_setup.py`: reports a profile that is still incomplete.
- `tools/tracker.py`: the only writer for tracker CSVs. `tests/test_kit.py` checks the profile parser, the search schema, the CSV headers, and that an in-progress application is not overwritten.

The order after setup is: search a slice, diligence on the companies worth time, read the form, then archive only after the person has applied. Recheck on the freshness window. Sync, follow up, and interview prep follow from the tracker.
