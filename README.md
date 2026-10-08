# Client Relationship Tracker — Circuit Entertainment

A lead-generation engine + terminal CRM for selling Circuit Entertainment's five
attractions (Photo Booth, Mixed Reality, 360° Dome, Car Simulation, Escape Rooms)
to malls, FECs, resorts, parks and developers across India.

- **`MASTER_PROMPT.md`** — the brain: one operator running a world-class Research,
  Sales and Technical team. Defines the ICP, scoring rubric, pitch rules, site-fit
  checklist, data schema and the operating loop.
- **`crt.py`** — zero-dependency terminal CRM. All data in `data/leads.json`;
  git history is the audit trail.
- **`.claude/commands/`** — the automation. Run inside Claude Code:
  - `/find-clients [geo or segment]` — scan the web for buyers with a live trigger,
    score, de-dupe, add to the tracker, draft pitches for hot leads, commit & push.
  - `/pitch <ID>` — full personalised pitch pack for one lead.
  - `/followups` — everything due today + the next touch drafted for each.
- **`pitches/`** — one pitch pack per lead (drafts awaiting your approval).
- **`PIPELINE.md`** — auto-generated dashboard (`python crt.py pipeline`).

## Daily workflow

```
/find-clients                    # morning: discover + score + draft (10–20 leads)
/followups                       # what's due, with next-touch drafts
python crt.py pipeline           # the dashboard
```
Review the drafts in `pitches/`, send the ones you approve (from your own email /
WhatsApp / LinkedIn), then log them:
```
python crt.py log CRT-0007 --channel email --summary "Intro sent" --next "Nudge" --next-date 2026-10-14
python crt.py update CRT-0007 --status pitched
```

## Terminal CRM cheat-sheet

```
python crt.py add --company "ABC Mall" --type mall --city Hyderabad --state TS \
    --source "https://..." --trigger "New 40,000 sq ft entertainment wing opening Dec" \
    --score 82 --products "photo_booth,mixed_reality,car_sim" --angle "anchor the new wing" \
    --dm "Priya S|Head of Leasing|linkedin|<url>|true|https://..."
python crt.py list --hot              # score ≥ 70 and active
python crt.py show CRT-0001
python crt.py update CRT-0001 --status meeting --next "Send proposal" --next-date 2026-10-20
python crt.py log CRT-0001 --channel call --summary "20-min intro call" --outcome "wants ROI sheet"
python crt.py due                     # follow-ups due today / overdue
python crt.py find "orion"
python crt.py export --csv leads.csv
```
Statuses: `new researched pitched replied meeting proposal won lost parked do_not_contact`.

## Principles (non-negotiable)
1. **Real leads only.** Every fact and contact has a source URL; unknowns are marked `UNVERIFIED`. Nothing is invented.
2. **Drafts, not blasts.** Every pitch is written for a human to approve and send. Max 3 touches, then park. Opt-outs are honoured permanently (`do_not_contact`).
3. **Business contacts only.** Professional name/role/business channel — no personal data.
4. **Numbers with assumptions.** ROI frames always state their inputs and invite correction.

## Scheduling the scan
Inside Claude Code you can schedule `/find-clients` to run each morning (e.g. weekdays 9am) so new leads and drafts are waiting for you. Runs happen while the app is open.

## Setup
Python 3.10+ (stdlib only). Clone, then run any `crt.py` command. The repo is **private** — it contains prospect contact details.
