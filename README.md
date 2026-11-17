# Job-hunt kit

A reusable workspace for running a job search with an AI coding agent (Claude Code, Codex or any agent that reads `AGENTS.md` and Agent Skills). It provides:

- six workflows as playbooks: `job-status`, `job-plan`, `job-scout`, `job-followup`, `job-interview`, `job-archive`, plus a scheduled `job-refresh` and the `job-setup` onboarding interview;
- a Google Sheets tracker with five tabs (All roles, Application queue, Research audit, Active pipeline, Shortlist) and a local dashboard;
- tools that prepare, verify and finalize tracker publications and sweep candidate portals;
- rules that keep the agent within the person's approvals, evidence standards and privacy.

The kit contains no personal data. Each person's values live in their own workspace (an "instance"): `workspace.json` and the `profile/` folder.

## Quickstart for a new person

1. Copy this folder to a private location (do not push it to a public repository).
2. Create an empty Google Sheet for the tracker and keep its ID handy.
3. Open Claude Code or Codex in the folder and run `/job-setup` (Codex: `$job-setup`), or ask the agent to follow [SETUP.md](SETUP.md).
4. Answer the five short interview rounds and confirm the summary. The agent writes `workspace.json`, `profile/PROFILE.md`, `profile/PREFERENCES.md`, `profile/SOURCES.md` and `AGENTS.md`, runs `python3 tools/new_workspace.py`, and (with your approval) creates the tracker tabs through the Sheets connector.
5. First runs: `/job-scout wide`, then `/job-status` and `/job-plan` as replies come in.

## Layout

```text
AGENTS.template.md      generic agent rules; SETUP fills it into AGENTS.md
SETUP.md                onboarding interview and generation steps
playbooks/              workflow instructions (single source)
.agents/skills/         thin Agent Skill entry points (job-*/SKILL.md)
.claude/commands/       thin Claude Code commands (incl. job-sync alias)
templates/
  workspace.example.json
  profile/              PROFILE.md, PREFERENCES.md, SOURCES.md templates
tools/                  workspace.py, tracker_publish.py, status_portals.py, new_workspace.py, kit_sync.py, ...
dashboard/              local dashboard build
docs/architecture.md    data flow, publication pattern, kit vs instance ownership
```

An instance adds: `workspace.json`, `AGENTS.md`, `profile/`, and the data folders named in `workspace.json` `paths.*` (pool, status snapshots, plans, scout runs, application folders, company dossiers, automation state).

## Precedence

The person's newest dated instruction (in `profile/PREFERENCES.md`) wins over older entries and over playbook defaults. Playbooks never hard-code a person; they refer to `workspace.json` keys and `profile/` files.

## Upgrading an instance

Kit-managed files (playbooks, skills, commands, tools, dashboard, templates, `AGENTS.template.md`, `SETUP.md`, this README and `docs/`) are copied into an instance with:

```sh
python3 tools/kit_sync.py PATH            # dry run: shows what would change
python3 tools/kit_sync.py PATH --apply    # copies kit-managed files
python3 tools/cleanup_audit.py PATH       # clutter report; --apply cleans reversibly
```

Instance-owned files (`workspace.json`, `AGENTS.md`, `profile/`, data folders) are never overwritten. If an instance needs a different rule, put it in `profile/PREFERENCES.md`, not in a playbook; a local playbook edit would be replaced on the next sync. Review the dry run before applying, and check `AGENTS.template.md` changes by hand against the instance's `AGENTS.md`.

See [docs/architecture.md](docs/architecture.md) for how data moves through the workspace.
