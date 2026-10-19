# Tracker

`roles.csv` is the working list. Create it from `roles.example.csv` during setup. It is gitignored.

## Columns

`company,role,url,status,decision,fit_score,work_model,location_eligibility,contract,compensation,pay_gate,hours_oncall,hours_gate,why_it_fits,gaps,risks,next_step,checked,notes`

Quote any field that contains a comma or a newline.

## Status

`New`, `Screen`, `Applied`, `Screening questions`, `Interviewing`, `Assessment`, `Offer`, `Rejected`, `Withdrawn`, `Archived`.

## Decision

`Pursue`, `Screen first`, `Stretch`, `Drop`.

`checked` is the date the posting was last verified. Older than `freshness_days` means stale.

`sync-state.md` records the last inbox sync. Applications that are quiet are handled by `commands/job-followup.md`.

A spreadsheet listed in the profile is a mirror. It becomes the status source only when `integrations.spreadsheet.is_source_of_truth` is true.
