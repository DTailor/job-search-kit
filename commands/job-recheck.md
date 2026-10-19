# Recheck

The person may name companies or URLs. Otherwise recheck tracker rows whose `checked` date is older than `freshness_days`, and rescan `tracker/watchlist.csv` for new requisitions.

1. Fetch the exact URL already stored. Classify it `live`, `closed`, `unlisted`, or `changed`.
2. A different requisition is a new role. Record it through `commands/job-search.md` and `import-run`. Do not write it over the old URL.
3. Save a JSON object or list with `url`, `live_status`, `checked`, `detail`, and `updates` for research columns only.
4. Run `python3 tools/tracker.py recheck FILE`.
5. Set `Last recheck` in `tracker/sync-state.md` to today.
6. Summarize what closed, what changed, and which in-progress applications were left untouched.

An HTTP 200 that is only a JavaScript shell is `unverified`, not live. Do not apply or message anyone.
