# Setup prompt

Use this when the workspace has no ready profile. Say so in one line, then interview. Do not search for jobs, draft applications, or create tracker rows during setup.

## Read first

- `README.md`
- `AGENTS.md`
- `profile/profile.example.yml`
- `profile/PROFILE.template.md`

Copy `profile/profile.example.yml` to `profile/profile.yml` only as a scratch file. Leave `status: template` until the person confirms the draft. Do not treat example text as their requirements.

## How to interview

Ask for a CV, résumé, or career summary first, plus anything they already know they want. Extract what you can from that material, then ask one round of questions for the gaps only.

That round has to pin down the gates:

1. Target titles and level, in their words.
2. Where they can legally work, which work models they accept (remote, hybrid, on-site), and whether they will relocate.
3. The posting wording that counts as a location pass, the wording that is only unclear, and the wording that fails. Ask for an example of wording that looks acceptable and is not.
4. Working hours, timezone, and on-call limits.
5. Engagement they want (employee, contractor, or either), the pay floor for each, the currency, the period, and whether the number is gross, net, invoice, or total. Ask what a short contract would need to offer to be worth considering.
6. Start date or notice period.
7. Role types, domains, and companies they want excluded.
8. Skills they can defend, skills that are only adjacent, and skills they do not want implied.
9. Tone, language, and CV rules. Optional: a message they actually sent, so later drafts can match them.
10. Whether to enable Gmail sync or a spreadsheet. Default both to off. If they enable one, record the account or URL they name, and no other.

Do not invent a salary, a work-authorization fact, a metric, or a skill they did not state. Mark gaps as open questions.

## Write the draft

1. `profile/profile.yml` with their answers. Keep `status: template`.
2. `profile/PROFILE.md` from `profile/PROFILE.template.md`: who they are, what fits, what does not, the gate table, and the scoring note.
3. `cv/interview-brief.md` from `templates/interview-brief.md`, using only confirmed stories. Label missing stories as gaps.
4. `profile/voice.md` only if they gave a real sample.
5. `tracker/roles.csv` with the header from `tracker/roles.example.csv` if the file does not exist yet.
6. `tracker/sync-state.md` with `Last sync: never`.

Run `python3 tools/check_setup.py` and fix anything it reports except the final ready check. The script must still fail on `status: template` at this point.

## Confirm

Show a short brief:

- headline and level
- core skills, adjacent skills, and do-not-claim
- location, hours, and on-call gates
- pay floors, with basis
- exclusions
- integrations left off or turned on
- open questions

Ask them to correct it. On an explicit confirmation, set `status: ready` and `setup_date` to today, run `python3 tools/check_setup.py` again, and stop. Offer the next actions (search, CV pass, or tracker tour) and wait for them to choose. Do not start a search in the same turn as confirmation unless they also asked for one.
