# Preferences and decisions: {{NAME}}

<!--
Everything that decides whether a role is worth pursuing and how the agent works for this person.
Precedence: the newest dated entry wins over older entries and over playbook defaults.
Format for every new rule: "**<Topic> — <Name>, YYYY-MM-DD:** <rule as the person stated it>".
Never delete a superseded rule; mark it "(superseded by YYYY-MM-DD)" so history stays readable.
-->

## Dated decisions

<!-- Newest first. Copy the person's wording; do not paraphrase. -->
- **Setup — {{NAME}}, {{SETUP_DATE}}:** initial preferences recorded below.

## Standing authorities

<!-- What the person allowed without a per-item approval round, with date and limits. Default: none —
tracker writes are proposed as a numbered list and written on approval.
Example: "Standing authority, YYYY-MM-DD: maintain the tracker during interactive work (add leads, record verified status,
reorder/rename columns reversibly). Does not authorize contacting anyone, applying, uploading, consenting or booking." -->
- Tracker writes: {{TRACKER_AUTHORITY}}
- Browser tool: {{BROWSER_AUTHORITY}}
- Scheduled refresh: {{REFRESH_AUTHORITY}}

## Gates

| Gate | Pass | Ask first | Fail |
|---|---|---|---|
| Role scope and level | {{FIT_LIST}} at {{LEVEL}} | Mixed scope, unclear level | {{EXCLUSIONS}} |
| Location | Eligible from {{HOME_COUNTRY}} stated, or region/worldwide with stated contractor/EOR hiring | Region remote, no country list | Country list without {{HOME_COUNTRY}}; on-site/relocation elsewhere |
| Hours | {{HOURS_WINDOW}} | Partial overlap | Regular hours outside the window |
| After-hours | {{ONCALL}} | "Occasional" with no details | Regular after-hours rota or weekend work |
| Contract | {{CONTRACT_FORMS}} | Route not stated | {{EXCLUDED_FORMS}} |
| Term | Open-ended or at least {{MIN_TERM}} | "Extension possible" | Shorter |
| Pay | Published at/above floor | Unpublished, or published for another country | Published below floor |

Out of scope role types (skip in scout): {{EXCLUSIONS}}. Blocklist (companies): {{BLOCKLIST}}.

## Contract forms and country rules

<!-- Which forms the person can work under and how each is evaluated. Neutral examples:
"employee contract", "contractor via own business entity", "via Employer of Record", "freelance/project".
Record the country-specific facts the person confirmed (e.g. which entity they invoice from); do not assume a tax regime. -->
- {{CONTRACT_FORMS}}
- Country notes: {{COUNTRY_NOTES}}

## Money

<!-- PRIVATE. The floor never appears in a form, message or draft. -->
- Private floors (per contract form): {{FLOORS}}
- Recruiter wording / default ask when asked directly: {{ASK_WORDING}}
- Currency: {{CURRENCY}} first; secondary: {{SECONDARY_CURRENCY}}; FX source: {{FX_SOURCE}} with its date.
- Net estimates: {{TAX_NOTES}} (re-check the rules each tax year).

## Availability

- Exact wording to use: "{{AVAILABILITY}}"
- Current role ends: {{CURRENT_END}}

## Process preferences

- {{PROCESS_PREFS}}
- Applications per company per round: one.
- Follow-up after {{QUIET_DAYS}} quiet days; propose Withdrawn after {{WITHDRAW_DAYS}}.
- Minimum live processes before plan suggests a scout/apply round: {{MIN_LIVE}}.
- Job-hunt hours per week (plan assumes): {{HUNT_HOURS}}.

## Writing

- Languages and tone: {{LANGUAGES}}; {{TONE}}.
- Per-language conventions: {{LANGUAGE_CONVENTIONS}}
- Introductions: lead with the work, fit and interest; no unsolicited salary or screening checklist (change if the person prefers otherwise).
- Profile visibility: {{VISIBILITY}}

## Tracker notes

<!-- Instance-specific column letters, extra tabs (e.g. Inbox, Channels, Coverage), validation lists. -->
- {{TRACKER_NOTES}}

## Workflow notes

<!-- Person-specific additions per workflow. Each playbook reads its own subsection. Keep entries dated. -->

### Shared flow

### job-status
- Surfaces to check: {{STATUS_SURFACES}}

### job-plan

### job-scout

### scout-discovery

### company-background

### job-archive

### job-followup

### job-interview

### job-refresh
