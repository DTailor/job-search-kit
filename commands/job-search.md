# Search

Find currently open roles. The person may name a slice, a craft, or a list of companies. If they do not, list `markets.slices` from the profile and ask which one to run.

1. Read `profile/profile.yml`, `profile/PROFILE.md`, and `AGENTS.md`. If the profile is not `ready`, follow `SETUP.md` and stop.
2. Read `search/SEARCH_BRIEF.md` and `tracker/README.md`. Load existing URLs from `tracker/roles.csv` so a known company can still produce a new requisition.
3. Search that slice only. Save `search/runs/YYYY-MM-DD/<slice>.json` as you go. The shape is `search/schema.json`.
4. Run `python3 tools/tracker.py validate-run FILE` and then `python3 tools/tracker.py import-run FILE`.
5. Write `BRIEF.md` beside the JSON: counts, the top roles, the failed gates behind drops, and anything that needs a browser or a person.

Do not apply or message anyone in this procedure.
