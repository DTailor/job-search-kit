# Sources for job-scout

This file is the generic source catalogue: categories, how to read them, and the ledger format. The person's live ledger (actual sources, Last, Yield, run log and dated access notes) is `profile/SOURCES.md`. `job-scout` reads both and updates only `profile/SOURCES.md`.

## Rules

- Update **Last** and **Yield** in `profile/SOURCES.md` with actual coverage after each run. Low yield can reduce ordinary-run frequency; it does not permanently retire a source. Wide runs revisit cooled-down and previously inaccessible sources using [scout-discovery.md](scout-discovery.md).
- **Rotation:** "every" sources run on every scout. "rotate" sources run in turns, each at least every third run. `wide` runs all of them. "monthly" sources (hiring threads) run once per thread, then by delta.
- Access errors trigger another available method, not immediate deferral. A blocked or partial check is not a successful zero-yield inventory.
- Read-only. Never log in or create accounts; the person signs in where a board needs it, or pastes the content. Respect each site's terms and rate limits; skip paywalls unless the person has access.
- Aggregators, site searches and social posts are leads only. Verify every pick live on the employer's own site that day.
- Dated endpoint observations (dead, blocked, JavaScript-only) are not current source-wide bans. For wide runs, try the current domain, the authorized browser, the employer-linked ATS and exposed public listing endpoints before recording unresolved access.

## Categories

Build the person's ledger from these categories during setup (see `SETUP.md`). Aim for breadth: 40 or more sources is normal.

| Category | What to include | Universal examples |
|---|---|---|
| Job alerts | 5–10 alert queries (title variants × location) on the biggest boards. The person creates them; status/scout read the emails. | The professional network's job alerts, the largest country board |
| Site searches over ATS domains | Search-engine queries over hiring-platform domains, combining each title variant with "remote" or the country. Finds roles posted only on company career pages. | `site:boards.greenhouse.io`, `site:job-boards.greenhouse.io`, `site:jobs.lever.co`, `site:jobs.ashbyhq.com`, `site:apply.workable.com`, `site:jobs.smartrecruiters.com`, `site:*.teamtailor.com`, `site:*.recruitee.com`, `site:*.personio.com`, `site:*.bamboohr.com`, `site:*.myworkdayjobs.com`, `site:*.breezy.hr` |
| Public ATS APIs for tracked employers | Re-scan known employers for new requisitions | Ashby posting-api, Greenhouse boards-api, Lever postings API, SmartRecruiters, Recruitee, Workable account feeds, Workday cxs |
| Aggregators and country boards | General boards plus the market leaders in the person's country | LinkedIn Jobs, Indeed (country site), Google Jobs results, Adzuna; the local market leader |
| Field-specific boards | Professional-association boards, trade publications and niche sites for the person's field | Found during setup by searching `"<field> jobs board"` |
| Remote boards | If remote | We Work Remotely, Remotive, Remote OK, Working Nomads, Himalayas, 4dayweek.io |
| Startups and investors | Startup boards and investor portfolio boards (often on Getro or Consider) | Wellfound, Y Combinator Work at a Startup, Welcome to the Jungle, startup.jobs; `jobs.<investor>.com` boards |
| Target companies | 30–80 employers that hire this role, with careers URL and hiring platform | Built from the CV's industry, competitors of past employers and companies met while scouting |
| Freelance, contract networks and agencies | Only if those contract forms are acceptable; keep network enrolment separate from a vacancy | Contract networks and specialist recruiters for the field and country |
| Communities, newsletters and hiring threads | Job channels the person can see, newsletters with job sections, monthly hiring threads | HN "Who is hiring?" (Algolia API) for tech roles; field newsletters; community job channels (the person forwards posts) |
| Funding and hidden market | Companies likely to hire soon, for scouting or drafted speculative outreach | Startup funding news feeds for the person's region |
| Public and international | If relevant | National public-job portals, EU/UN career portals, NGO boards |

## Ledger format (in `profile/SOURCES.md`)

```markdown
| Source | How to read | Query / filter | Rotation | Last | Yield (latest check) | Notes |
|---|---|---|---|---|---|---|
```

Follow the table with a **Run log** (newest first, one dated paragraph per run: counts, coverage limits, report link), **Lower-frequency sources**, **Needs the person (no agent access)** and **Historical endpoint/access failures**, each entry dated.
