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
| A verified role search | `commands/job-search.md` writes `search/runs/` |
| Roles worth tracking | `tracker/roles.csv` |
| What was applied and what was sent | `applications/<company>_<role>/` |
| Follow-ups and interview prep | `commands/job-followup.md`, `commands/job-interview.md` |
| CV and private interview notes | `cv/` |

The CSV tracker is the status source. A spreadsheet or Gmail connection is optional and stays off until setup turns it on.

## Commands

| Say this | Procedure |
|---|---|
| Set this up | `SETUP.md` |
| Find roles | `commands/job-search.md` |
| I applied to this | `commands/job-archive.md` |
| Check for replies | `commands/job-sync.md` |
| Draft follow-ups | `commands/job-followup.md` |
| Prep me for this interview | `commands/job-interview.md` |

The same procedures are available as Claude slash commands under `.claude/commands/`.

## What stays private

Setup writes career details, and later searches add employers, pay, and messages. Those paths are listed in `.gitignore`:

- `profile/profile.yml`, `profile/PROFILE.md`, `profile/voice.md`
- `cv/` except this kit's `cv/README.md`
- `applications/` except `applications/README.md`
- `tracker/roles.csv`, `tracker/sync-state.md`
- `search/runs/`

Check `git status` before you push a fork. A filled-in profile does not belong in a public repository.

## Layout

- `SETUP.md`: the prompt.
- `AGENTS.md`: operating rules once a profile exists.
- `profile/`: example and template. The real profile is created locally.
- `search/`: how a research pass verifies roles, and the JSON shape it must write.
- `commands/`: the workflows.
- `templates/`: empty application, posting, prep, and interview-brief files.
- `writing/GUIDE.md`: how to draft application answers.
- `tools/check_setup.py`: reports a profile that is still incomplete.
