# Company diligence

The person may name a company. Otherwise check companies on `Pursue` and `Screen first` rows, plus any agency or marketplace already in the tracker.

Read `tracker/README.md` for Green, Amber, and Red. Do not contact the company.

1. Classify the type: employer, agency, marketplace, or undisclosed client.
2. Quote sources for pay signals, hours and on-call, hiring route, health, interview process, and how they treat employees and contractors. Label inference. A rating needs the site, the scope, the score, the review count, and the date. Under 20 reviews, or a snippet instead of the page, is weak evidence.
3. Compare the hiring route with `vehicles` in the profile. When there is an intermediary, name the actual client if the posting does, and say when the client is hidden. Record the contracting entity, payment terms, notice, and continuity risk. A bill rate is not the person's pay.
4. Upsert one JSON object per company:

```bash
python3 tools/tracker.py upsert companies row.json
```

5. Reply with the verdict, the one fact that drives it, and the question to ask first.
