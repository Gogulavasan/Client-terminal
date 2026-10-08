---
description: Show every lead whose follow-up is due and draft the next touch for each, per the outreach cadence.
---

Read `MASTER_PROMPT.md` §4 (cadence and outreach rules).

1. `python crt.py due` — list everything due today or overdue.
2. For each due lead: `python crt.py show <ID>`, check how many touches have been made (count outreach interactions). Apply the cadence: touch 1 = intro, touch 2 (+4d) = short nudge, touch 3 (+12d) = value-add (ROI sheet / case). **After 3 touches with no reply → `python crt.py update <ID> --status parked --next "Re-check in 90 days" --next-date <today+90>`** and stop.
3. Draft the next touch (≤60 words for nudges) and append it under a dated heading in `pitches/<ID>-*.md`.
4. Set `python crt.py update <ID> --next "Send touch N (awaiting approval)" --next-date <today>`.
5. Print all drafts grouped by lead. **Do not send.** Once the human confirms a send, log it (`crt.py log`) and advance `--next-date` by the cadence.
6. `python crt.py pipeline` and commit: `git add -A && git commit -m "followups: <date>"` (+ `git push` if a remote exists).
