# Waypoint dashboard

A private, static job-search dashboard. One Python build turns your workspace
into a single `index.html` that you open locally. It covers candidate roles,
applications and conversations, company checks, the full research library,
insights, and the sources with their check dates. Opening the page makes no
network calls and has no write access. Bookmarks and notes stay in browser
`localStorage`.

## Build

```sh
python3 dashboard/build.py                 # workspace = nearest workspace.json
python3 dashboard/build.py --workspace DIR # or set JOB_HUNT_WORKSPACE
node dashboard/qa-static.mjs [DASHBOARD_DIR]
```

The build needs Python 3.9+ (stdlib only) and `tools/workspace.py` +
`tools/job_pool.py`. It uses the workspace's own `tools/` first, then the kit's.
It reads inputs from `paths.dashboard/data/` and writes `index.html` and
`data/reviewed-data.json` back to the same folder (`paths.dashboard`). Before
building, capture the tracker readback (`data/tracker-snapshot.json`). Its
`publication_revision` must match the pool revision.

A new workspace with an empty pool and header-only tracker tabs builds an
empty-state page. `qa-static.mjs` checks that mode automatically.

## Files

- `build.py`: assembles and validates the dataset. It checks counts against the tracker readback, pool membership and unique ids.
- `src/template.html`, `src/styles.css`, `src/presentation.js`, `src/app.js`: the page
- `qa-static.mjs`: browser-free smoke test of every view and dialog
- `DATA.md`: the input contract and the optional `data/instance.json` overrides

## Personalising

Keep the shared code unchanged. Put person-specific facts in `workspace.json`
(name, e-mail, time zone, tracker ids, paths, gate labels). Put dashboard copy,
hand-curated historical records and portal links in
`<dashboard>/data/instance.json`. Use `<dashboard>/data/instance.css` for company
logo colours. That way an instance can take kit updates by copying `build.py`,
`src/` and `qa-static.mjs`.

Treat the generated page and `reviewed-data.json` as private: they embed tracker
values, e-mail thread links and application records.
