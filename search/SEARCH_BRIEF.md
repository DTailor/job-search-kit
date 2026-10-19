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
- Score with the weights in the profile and include the breakdown. Any `fail` gate is decision `Drop`.

## Role identity

- A role is its exact employer or ATS URL plus requisition id. A different requisition is a different row, including at a company already tracked. Set `known_company` when that happens.
- Do not replace an old requisition with a different one.
- An HTTP 200 that is only a JavaScript shell is not proof the role is live. Use `live_status` `unverified`, or put the URL in `needs_browser_check`.
- Read `tracker/roles.csv` before searching. Skip a URL that is already there. A new requisition at a known company is still in scope.
- Slices come from `markets.slices` in the profile.

## Fit, pay, and vehicle

- `technical_class` is `direct_match`, `reasonable_ramp`, `specialist_mismatch`, or `unverified`.
- Each gap status is `known_absent`, `historical`, `unverified`, `accepted_ramp`, or `adjacent`. A generic skill overlap does not cancel a mandatory specialist requirement.
- Decision meanings are in `tracker/README.md`. `Pursue` and `Screen first` need a credible direct match or an accepted ramp, and no known hard location or hours failure.
- `pay_scope` is `local`, `location_independent`, `other_country`, or `unpublished`. `pay_verdict` uses the words in `tracker/README.md`. Label third-party numbers in `pay_note`.
- Convert a published figure to hourly or monthly only when `pay_note` states the hours and leave you assumed. Do not invent a tax or FX result.
- `vehicle_text` quotes employee, contractor, own company, EOR, or agency wording. `vehicle_fit` compares it with `vehicles` in the profile. An agency bill rate is not the person's rate. Name the client when the posting does, and say when the client is hidden.

## Forms and coverage

If the public posting shows application questions without submitting, copy them to `application_questions`. Do not start the application. Note questions about hours, country, pay, work rights, notice, clearance, or relocation.

Every source you actually check goes in `coverage`, including boards with nothing relevant. Near-misses go in `rejected` with one reason. Zero candidates is a valid result.

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

Write JSON that validates against `search/schema.json`. Save partial results as you go. Put a role in `candidates` when every gate is `pass` or `unclear` and the decision is not `Drop`. `Pursue` and `Screen first` also need `fit_score` at least `scoring.screen_at`. A lower `Stretch` stays in `candidates` only when it is worth keeping; otherwise it goes in `rejected`.

Then run:

```bash
python3 tools/tracker.py validate-run PATH.json
python3 tools/tracker.py import-run PATH.json
```

Write a short `BRIEF.md` next to the JSON: counts, the top roles with one line each, and anything a later pass should recheck. Import leaves rows that are already past `Not contacted` unchanged.
