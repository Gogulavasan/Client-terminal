---
description: Write or refresh the personalised pitch pack (email, WhatsApp/LinkedIn, ROI frame, Site Fit Note) for one lead ID.
---

Read `MASTER_PROMPT.md` first and act as the Sales + Technical teams.

Lead: `$ARGUMENTS` (a lead ID like `CRT-0007`, or a company name to look up with `python crt.py find "..."`).

1. `python crt.py show <ID>` — read everything known: trigger, products_fit, decision-makers, interactions, notes.
2. If key facts are thin, do a quick web search on the venue (footfall, size, recent news) and record new facts with `python crt.py update <ID> --notes "..."` (with the source).
3. Write `pitches/<ID>-<company-slug>.md` with:
   - **Email draft** (≤150 words): opens with their trigger, one specific product fit, one proof point (Orion Mall / 30+ venues), one CTA with two time options.
   - **WhatsApp / LinkedIn variant** (≤60 words).
   - **ROI frame**: low / base / high with every assumption stated; invite correction.
   - **Site Fit Note** (MASTER_PROMPT §5): footprint, power, timeline, staffing, phasing suggestion. Say "to confirm on site survey" where unknown.
   - **Objection prep**: the 2 most likely objections for this buyer and the planned response.
4. `python crt.py update <ID> --next "Send pitch (awaiting approval)" --next-date <today>`.
5. Print the email draft. **Do not send it** — the human reviews and sends; after they confirm it was sent, log it with `python crt.py log <ID> --channel email --summary "Intro sent" --next "Nudge" --next-date <today+4>` and set `--status pitched`.
