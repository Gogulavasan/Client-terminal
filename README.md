# Client Relationship Tracker — Circuit Entertainment

A lead-generation engine + terminal CRM for selling Circuit Entertainment's five
attractions (Photo Booth, Mixed Reality, 360° Dome, Car Simulation, Escape Rooms)
to malls, FECs, resorts, parks and developers across India.

- **`MASTER_PROMPT.md`** — the brain: one operator running a world-class Research,
  Sales and Technical team. Defines the ICP, scoring rubric, pitch rules, site-fit
  checklist, data schema and the operating loop.
- **`crt.py`** — zero-dependency terminal CRM. All data in `data/leads.json`;
  git history is the audit trail.
- **The 24-hour scanner** — a cloud routine ("Circuit Entertainment — 24h client
  scanner") runs **every 6 hours on Anthropic's servers**, app open or not. Each run
  scans the market, scores and de-dupes, adds leads here, writes a one-screen
  **opportunity brief** to `opportunities/` for every hot lead (score ≥ 70), and
  **raises a GitHub Issue** for it — so GitHub emails you the moment an opportunity
  is spotted. Target: **≥ 10 qualified clients per week**. Manage it at
  https://claude.ai/code/routines
- **`.claude/commands/`** — the same engine, on demand inside Claude Code:
  - `/find-clients [geo or segment]` — run a scan right now.
  - `/pitch <ID>` — a pitch pack if you want a head start on a proposal.
  - `/followups` — everything due today.
- **`opportunities/`** — briefs: why now, venue, product fit, who to contact, sources.
  **You write the proposal** from these.
- **`PIPELINE.md`** — auto-generated dashboard (`python crt.py pipeline`).

## Daily workflow

1. Check your email / the repo's **Issues** tab — each 🔥 issue is a hot opportunity
   with its brief attached.
2. Read the brief in `opportunities/`, draft your proposal, send it from your own
   email / WhatsApp / LinkedIn.
3. Log it so follow-ups are tracked:
```
python crt.py log CRT-0012 --channel email --summary "Proposal sent" --next "Follow up" --next-date 2026-10-14
python crt.py update CRT-0012 --status pitched
python crt.py due                # what's due today
python crt.py pipeline           # the dashboard
```
Close the GitHub Issue when the opportunity is actioned (won/lost/parked).

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

## How the scanner stays safe
- It never sends outreach and has no email/messaging access — notification is a GitHub Issue only.
- **Privacy guard:** it pushes to this repo only while the repo is **private** (an anonymous
  request to the repo URL must return 404). If the repo is ever public it keeps the run
  local and says so in its summary. Keep this repo private — it holds prospect details.
- Every fact it records carries a source URL; anything unconfirmed is marked `UNVERIFIED`.

## Setup
Python 3.10+ (stdlib only). Clone, then run any `crt.py` command. The repo is **private** — it contains prospect contact details.
