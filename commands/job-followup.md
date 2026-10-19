# Follow-ups

The person may give a number of quiet days, or one company. The default is `follow_up.quiet_days`.

Drafts only. Do not send, and do not create mailbox drafts, unless this message explicitly asks for that.

1. Take tracker rows in `Asked screening Qs`, `Applied`, `Interviewing`, or `Assessment`. Use the applied date in `applications/*/application.md` when the tracker notes disagree. If the last sync is older than two days, say so and offer `commands/job-sync.md` first.
2. For each row quiet at least that many days, name the contact route. When none is known, say so. Draft 3–5 sentences: role, date applied, one concrete fit line from `posting.md`, one open question from the gates, and their real availability from the profile.
3. For rows quiet at least `follow_up.propose_close_days`, propose status `Withdrawn` and a note. Change the tracker only after they approve, with `python3 tools/tracker.py set-status`.
4. Reply with a table (company, days quiet, route) and each draft, ready to paste. Match `writing/GUIDE.md`.
