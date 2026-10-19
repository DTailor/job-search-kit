# Search brief

You are researching currently open roles for the person described in `profile/profile.yml` and `profile/PROFILE.md`. Read both, and `AGENTS.md`, before searching. Apply their gates. Quality over volume. Do not pad the list with weak fits.

If the profile `status` is not `ready`, stop and follow `SETUP.md`.

## Hard rules

- Read-only. Do not apply, submit, partially fill a form, create an account, log in, sign up for alerts, message anyone, or accept anything.
- Do not put the person's name, email, phone, or other personal detail into a query or an external service.
- Do not read files outside this kit for extra biography. The profile is the fit model.
- Prefer WebSearch, WebFetch, and polite HTTP requests. Use a browser-like User-Agent with curl, keep the rate low, and tolerate request failures.
- If a page needs JavaScript and has no usable API or server-rendered text, list it under `needs_browser_check`. Do not guess the posting.
- Use a signed-in browser only when the person has authorized that session for this task.

## Verification

- Verify each role on the employer or ATS posting, not only an aggregator card. Record the exact URL. If an aggregator is the only source, say so and lower confidence.
- Quote location wording. Compare it with `constraints.eligibility` in the profile. Regional wording that the profile calls "not enough" is `unclear`, not `pass`. A country list that omits them is `unclear` or `fail` as the profile defines.
- Copy published pay with currency, period, gross/net/invoice basis, and country scope. Do not estimate missing pay. Another country's band is not their band unless the company says pay does not depend on location.
- Quote hours, timezone, and on-call wording, or write `not stated`. Full-time is not a duration. Permanent is not a guarantee. "Extension possible" is not a funded term.
- Score with the weights in the profile and include the breakdown. Any `fail` gate keeps the role out of `candidates`.

## Endpoints that often return a whole board

Confirm the company's real ATS before calling these. A failure is a coverage note.

- Ashby: `https://api.ashbyhq.com/posting-api/job-board/{org}?includeCompensation=true`
- Greenhouse: `https://boards-api.greenhouse.io/v1/boards/{token}/jobs?content=true` (EU boards are often HTML on `job-boards.eu.greenhouse.io`)
- Lever: `https://api.lever.co/v0/postings/{org}?mode=json` and `https://api.eu.lever.co/v0/postings/{org}?mode=json`
- Workable: `https://apply.workable.com/api/v1/widget/accounts/{account}` and detail `https://apply.workable.com/api/v2/accounts/{account}/jobs/{shortcode}`
- SmartRecruiters: `https://api.smartrecruiters.com/v1/companies/{id}/postings?limit=100`
- Recruitee: `https://{sub}.recruitee.com/api/offers/`
- Personio: `https://{sub}.jobs.personio.de/xml`
- BambooHR: `https://{sub}.bamboohr.com/careers/list`
- Breezy: `https://{sub}.breezy.hr/json`
- Pinpoint: `https://{sub}.pinpointhq.com/postings.json`
- Workday: POST `https://{tenant}.wd{N}.myworkdayjobs.com/wday/cxs/{tenant}/{site}/jobs` with `{"appliedFacets":{},"limit":20,"offset":0,"searchText":"<skill>"}`

Public feeds, when relevant to the profile: Remotive, Remote OK, We Work Remotely RSS, Himalayas, Jobicy, Arbeitnow, and the current Hacker News "Who is hiring" thread via Algolia (`tags=story,author_whoishiring`). Aggregator cards are leads. Verify the employer posting before a role enters `candidates`.

## Output

Write JSON that validates against `search/schema.json`. Save partial results as you go. Put a role in `candidates` only when every gate is `pass` or `unclear` and `fit_score` is at least `scoring.screen_at`. Put notable near-misses in `rejected` with one reason, so coverage is visible.

Then write a short `BRIEF.md` next to the JSON: counts, the top roles with one line each, and anything a later pass should recheck. Merge qualifying new rows into `tracker/roles.csv`. Do not overwrite a row whose status is `Applied` or later.
