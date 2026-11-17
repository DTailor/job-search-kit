# Dashboard data contract

`build.py` turns a workspace into one self-contained, private `index.html` plus
`data/reviewed-data.json`. It reads only local files; it never calls Google,
email, a browser or the network. Paths below are `workspace.json` keys
(`paths.<key>`), resolved by `tools/workspace.py`.

## Configuration

| Input | Required | Used for |
|---|---|---|
| `workspace.json` → `person` | yes | Name/initials in the sidebar, page title, `short_name` as the "you" owner value, `email` for Gmail thread links, `timezone` for labels |
| `workspace.json` → `tracker` | yes | `spreadsheet_id` (fallback sheet URL), tab titles, `sheet_id` (gids in row links), `header_row` per tab (`tabs.<key>.header_row` overrides `tracker.header_row`) |
| `workspace.json` → `gates` | no | `dashboard`: ordered `{label: pool gate key}`; the first three show inline, all show in details. `all_roles_columns[0]` names the field for All roles column F. Default labels: Location, Pay, Hours, Term |
| `workspace.json` → `search` | no | Default sidebar line and search criteria when `instance.json` gives none |
| `<dashboard>/data/instance.json` | no | Instance-specific overrides (below) |
| `<dashboard>/data/instance.css` | no | Extra CSS inserted into the page, for example `.logo-<companyId>` colours |

## Inputs

| Input | Required | Shape |
|---|---|---|
| `<dashboard>/data/tracker-snapshot.json` | yes | `{spreadsheet_url, checked_at, publication_revision, coverage?, sheets:[{sheet, sheet_id, range, values, checked_at?}]}`. `values` is the Sheets values array. The five operational tabs are looked up by their workspace titles. `publication_revision` must equal the pool revision. |
| `paths.pool` (current pool) | yes | `{as_of, revision, jobs:[…]}` validated by `tools/job_pool.py`. `jobs: []` is valid. |
| `<dashboard>/data/presentation.json` | when the pool has jobs | `{source_revision, jobs:{pool_id:{company, role, work, location, pay, fit, question, watch}}, companies:{companyId: summary}}`. These are reviewed editorial briefs. The revision and pool ids must match the pool. |
| `paths.status` / `YYYY-MM-DD.md` | no | The latest file is the status document. Numbered items between `## Tracker changes made` and `## Threads opened` become the tracker-correction audit. Missing sections produce an empty list. |
| `paths.plans` / `YYYY-MM-DD*.md` | no | The latest file is the plan document, unless `instance.json` sets `plan_document`. |
| `paths.applications` / `*/application.md` | no | Application dossiers. The first line is the title. |
| `paths.companies` / `index.json` + dossiers | no | `index.json` is `{companies:[{company, dossier, checked_at, main_risk, judgement, …}]}`. Each dossier is Markdown, and its `[label](https://…)` links become sources. Missing `index.json` means no dossiers. |
| `paths.data` / `archive-*/submissions.json` | no | `{recorded_at, submissions:[{key, pool_id, company, role, date, time?, route, contract, gates, risk, background, receipt_url, original_url, folder, evidence_kind?, pay_sent?, prepared_date?}]}`. `evidence_kind` is one of `sent email`, `browser confirmation`, `user report` or an employer receipt (default). |
| `paths.data` / `apply-*/prepared.json` | no | `{items:[{key, state?, prepared_at?, next_step, ready?}]}` for prepared but unsubmitted drafts |

### Tracker column layout (0-based)

- **Pipeline:** A company · role, B stage/status, C next action, G notes, H verification, I evidence URLs. Row 3, column A may say `N current processes`. When present, the build checks it.
- **Shortlist:** D company, Q status, and the header row gives the keys for `sheetDetails`.
- **All roles:** A decision, B fit, C company, D role, E tech, F-H gates, I location, J model, K contract, L pay, M on-call, N why, O risk, P checked, Q application state, R disposition, S next action, V original URL.

## Optional `instance.json`

All keys are optional. If a key is absent, the build uses a generic default.

| Key | Meaning |
|---|---|
| `product` | Product name (default `Waypoint`) |
| `records.before_queue`, `records.after_submissions` | Hand-curated process records, such as recruiter threads, older leads or rejections. Each has `id, company, role, group, stage, owner, last, nextAction` plus optional `channel, pay, route, tags, gates, sources, questions, timeline, notes, summary, companyId`. `group` is one of `current, hold, older, closed, archived, declined, platform`. |
| `process_overrides` | Reviewed fields keyed by opportunity id, applied to curated and submission-derived process cards. Current primary owner comes from pipeline column D; explicit rejection evidence still closes the card. Use these fields for evidence-backed stage and last-move changes. |
| `card_ids` | `{pool_id: stable card id}` (default `market-<pool_id>`) |
| `shortlist_aliases` | `{record id: company name as written in the Shortlist}` |
| `summary_documents` | Paths under `paths.data`, tried in order, for the latest summary document. The default is the newest archive README. A status file dated on or after `as_of` takes precedence. |
| `status_fallback`, `plan_document` | Paths under `paths.data` |
| `submissions_glob`, `prepared_glob` | Override the archive/draft globs |
| `submission_defaults.prepared_date` | Default "materials prepared" date |
| `redact_patterns` | Regexes replaced with `[phone omitted]` in all output text |
| `constraints` | `{role, location, hours, money, term, pager}` for the search-criteria dialog |
| `tasks`, `coverage`, `sources` | Overview tasks, the coverage list (used when the snapshot has no `coverage`), and source links (the first two open as documents). Text may use `{pool}`, `{queue}`, `{priority}`, `{latest_summary}`, `{plan}`, `{sheet_checked_at}` and `{as_of}`. |
| `ui` | Page copy and labels: `title`, `description`, `northStar` (lines), `snapshotPill`, `footerEvidence`, `storageKey`, `snapshotFilename`, `initials` `{company: text}`, `overviewSubtitle`, `beyondStat {value, context}`, `nextStep {label, title, html, open|view, button}`, `attention [{tone, label, title, text, open|view, aria}]`, `progressingLabel`, `pipelineFoot [bold, rest]`, `statusAsOf`, `sourcePanels [{title, date, text}]`, `statusDocumentUrl`, `planDocumentUrl`, `updateBadge`, `updateStatusUrl`, `termsContext`, `compareNote`, `companyQuestionFallback`, `preferencesNote`, `gateText {label: [title, confirmed text]}`, `intermediaries {companyId: {title, text, company, button}}`, `insights {stagesNote, selfNote, themNote, ownerNote, waitingCohorts [[date, label]], waitingNote}` |

`ui.nextStep.html` is inserted as HTML; it is the workspace owner's own text.
All other `ui` text is escaped.

## Output

- `<dashboard>/index.html`: the template, styles, data and scripts in one file
- `<dashboard>/data/reviewed-data.json`: the embedded dataset, including `ui`, the resolved labels and links the page uses

`qa-static.mjs [dashboard-dir]` renders every view, dialog and drawer in a VM
without a browser or network. With an empty pool and no processes, it checks the
empty-state page instead.
