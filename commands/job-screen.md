# Screen a form

The person is considering an application, or they name a tracked role. Do not apply, submit, log in, or create an account.

1. Read the public form, or the form definition the posting page loads. Copy the questions. A request that would submit an application is out of scope.
2. Write `screening/<company>_<role-slug>.md` from `templates/screening.md`.
3. Classify the writing need as one of: no message, optional message, required answers, the candidate's own writing, or a later step you could not see.
4. Draft only the fields that ask for writing, using `writing/GUIDE.md`, the interview brief, and the evidence ledger. A story that is not in those files is **Needs their input**, with the structure and no invented example.
5. Reply with flags for hours, country, pay, work rights, notice, clearance, and relocation, then the drafts, then what they still have to type themselves.

Saving this file does not change tracker status. Status becomes `Asked screening Qs` only after they say they asked or answered them, through `python3 tools/tracker.py set-status`.
