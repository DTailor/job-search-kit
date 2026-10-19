# Sync replies

The person may name a company or a start date. Otherwise start from `tracker/sync-state.md`.

1. Read open tracker rows: `Asked screening Qs`, `Applied`, `Interviewing`, `Assessment`, and `Offer`.
2. If `integrations.gmail.enabled` is false, ask what changed, or read files they point at. Do not open an inbox that is not configured.
3. If Gmail is enabled, use only `integrations.gmail.account`, read-only. Search company names and ATS senders that already appear in the archive (Ashby, Greenhouse, Lever, SmartRecruiters, Recruitee, Workable, and others). Classify each new message as confirmation, screen request, interview invite, assessment, rejection, offer, or other.
4. Present a numbered table: company, signal, a short quoted fragment, and the proposed status, next step, and note. Include applications quiet for `follow_up.quiet_days` and point at `commands/job-followup.md`.
5. Write nothing until they approve all or by number. Then:

```bash
python3 tools/tracker.py set-status URL "STATUS" --next "NEXT" --notes "NOTES"
python3 tools/tracker.py append inbox row.json
```

Append a timeline line in each `application.md`. Set `tracker/sync-state.md` to today, and read the rows back.

Do not reply, label, archive, or delete mail. Do not open LinkedIn threads.
