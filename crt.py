#!/usr/bin/env python3
"""
Client Relationship Tracker (CRT) — Circuit Entertainment
=========================================================
A zero-dependency terminal CRM for the B2B pipeline. All data lives in
data/leads.json (committed to git so the history IS the audit trail).

  python crt.py add      --company "X Mall" --type mall --city Bengaluru --state KA ...
  python crt.py list     [--status pitched] [--tier A] [--hot]
  python crt.py show     CRT-0001
  python crt.py update   CRT-0001 --status pitched --next "Call back" --next-date 2026-10-15
  python crt.py log      CRT-0001 --channel email --summary "Sent intro" --outcome "no reply yet"
  python crt.py due      [--on 2026-10-10]        # follow-ups due on/before a date
  python crt.py find     "orion"                  # search company / city / notes
  python crt.py pipeline                          # summary + writes PIPELINE.md
  python crt.py export   [--csv leads.csv]

Statuses: new researched pitched replied meeting proposal won lost parked do_not_contact
Tiers: A B C   Products: photo_booth mixed_reality dome_360 car_sim escape_room
"""

import argparse
import csv
import json
import os
import sys
from datetime import date

# Windows consoles default to cp1252, which can't print emoji or many non-ASCII
# names; make stdout UTF-8 (fall back to '?' rather than crashing).
try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except (AttributeError, ValueError):
    pass

BASE = os.path.dirname(os.path.abspath(__file__))
DATA = os.path.join(BASE, "data", "leads.json")
PIPELINE_MD = os.path.join(BASE, "PIPELINE.md")

STATUSES = ["new", "researched", "pitched", "replied", "meeting", "proposal",
            "won", "lost", "parked", "do_not_contact"]
TIERS = ["A", "B", "C"]
TYPES = ["mall", "fec", "resort", "park", "cinema", "developer", "arena",
         "township", "corporate", "event", "other"]
PRODUCTS = ["photo_booth", "mixed_reality", "dome_360", "car_sim", "escape_room"]


# --------------------------------------------------------------------------
def today():
    return date.today().isoformat()


def load():
    if not os.path.exists(DATA):
        return {"next_id": 1, "leads": []}
    with open(DATA, "r", encoding="utf-8") as f:
        return json.load(f)


def save(db):
    os.makedirs(os.path.dirname(DATA), exist_ok=True)
    tmp = DATA + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(db, f, indent=2, ensure_ascii=False)
    os.replace(tmp, DATA)


def get(db, lid):
    lid = lid.upper()
    for l in db["leads"]:
        if l["id"] == lid:
            return l
    sys.exit(f"!! no lead with id {lid}")


def tier_for(score):
    return "A" if score >= 70 else "B" if score >= 45 else "C"


def dm_parse(s):
    """name|role|channel|contact|verified|source  (any trailing parts optional)."""
    p = [x.strip() for x in s.split("|")]
    p += [""] * (6 - len(p))
    return {"name": p[0], "role": p[1], "channel": p[2], "contact": p[3],
            "verified": p[4].lower() in ("1", "true", "yes", "y"), "source": p[5]}


# --------------------------------------------------------------------------
def cmd_add(a):
    db = load()
    comp = a.company.strip()
    if not a.force:
        for l in db["leads"]:
            if l["company"].lower() == comp.lower() and \
               (not a.city or l["city"].lower() == (a.city or "").lower()):
                sys.exit(f"!! duplicate: {l['id']} {l['company']} ({l['city']}). "
                         f"Use --force to add anyway.")
    lid = f"CRT-{db['next_id']:04d}"
    db["next_id"] += 1
    score = int(a.score or 0)
    lead = {
        "id": lid, "company": comp, "type": a.type or "other",
        "city": a.city or "", "state": a.state or "",
        "website": a.website or "", "source_url": a.source or "",
        "trigger": a.trigger or "",
        "decision_makers": [dm_parse(d) for d in (a.dm or [])],
        "score": score, "tier": a.tier or tier_for(score),
        "status": a.status or "new",
        "products_fit": [p for p in (a.products or "").split(",") if p],
        "pitch_angle": a.angle or "",
        "next_action": a.next or "Research decision-maker and draft pitch",
        "next_action_date": a.next_date or today(),
        "owner": a.owner or "",
        "interactions": [{"date": today(), "channel": "system",
                          "summary": "Lead created", "outcome": ""}],
        "notes": a.notes or "",
        "created": today(), "updated": today(),
    }
    db["leads"].append(lead)
    save(db)
    print(f"added {lid}  {comp}  score={score} tier={lead['tier']} status={lead['status']}")


def cmd_list(a):
    db = load()
    rows = db["leads"]
    if a.status:
        rows = [l for l in rows if l["status"] == a.status]
    if a.tier:
        rows = [l for l in rows if l["tier"] == a.tier.upper()]
    if a.hot:
        rows = [l for l in rows if l["score"] >= 70 and l["status"] not in
                ("won", "lost", "parked", "do_not_contact")]
    rows.sort(key=lambda l: (-l["score"], l["company"]))
    if not rows:
        print("(no leads)")
        return
    print(f"{'ID':9} {'SC':>3} {'T':1} {'STATUS':13} {'COMPANY':34} {'CITY':14} NEXT")
    for l in rows:
        nxt = f"{l['next_action_date']} {l['next_action'][:40]}"
        print(f"{l['id']:9} {l['score']:>3} {l['tier']:1} {l['status']:13} "
              f"{l['company'][:34]:34} {l['city'][:14]:14} {nxt}")
    print(f"\n{len(rows)} lead(s)")


def cmd_show(a):
    l = get(load(), a.id)
    print(json.dumps(l, indent=2, ensure_ascii=False))


def cmd_update(a):
    db = load()
    l = get(db, a.id)
    changes = []
    if a.status:
        if a.status not in STATUSES:
            sys.exit(f"!! status must be one of {STATUSES}")
        if a.status != l["status"]:
            l["interactions"].append({"date": today(), "channel": "system",
                                      "summary": f"Status {l['status']} -> {a.status}",
                                      "outcome": ""})
            changes.append(f"status={a.status}")
            l["status"] = a.status
    if a.score is not None:
        l["score"] = int(a.score); l["tier"] = a.tier or tier_for(l["score"])
        changes.append(f"score={l['score']} tier={l['tier']}")
    elif a.tier:
        l["tier"] = a.tier.upper(); changes.append(f"tier={l['tier']}")
    for k, v in (("next_action", a.next), ("next_action_date", a.next_date),
                 ("owner", a.owner), ("pitch_angle", a.angle),
                 ("trigger", a.trigger), ("website", a.website)):
        if v is not None:
            l[k] = v; changes.append(f"{k}={v!r}")
    if a.notes is not None:
        l["notes"] = (l["notes"] + "\n" if l["notes"] else "") + a.notes
        changes.append("notes+")
    if a.products is not None:
        l["products_fit"] = [p for p in a.products.split(",") if p]
        changes.append("products")
    for d in (a.dm or []):
        l["decision_makers"].append(dm_parse(d)); changes.append("dm+")
    l["updated"] = today()
    save(db)
    print(f"updated {l['id']}: " + (", ".join(changes) or "(no changes)"))


def cmd_log(a):
    db = load()
    l = get(db, a.id)
    l["interactions"].append({"date": a.date or today(), "channel": a.channel,
                              "summary": a.summary, "outcome": a.outcome or ""})
    if a.next:
        l["next_action"] = a.next
    if a.next_date:
        l["next_action_date"] = a.next_date
    l["updated"] = today()
    save(db)
    print(f"logged on {l['id']} ({a.channel}): {a.summary}")


def active(l):
    return l["status"] not in ("won", "lost", "parked", "do_not_contact")


def cmd_due(a):
    on = a.on or today()
    rows = [l for l in load()["leads"] if active(l) and l["next_action_date"] <= on]
    rows.sort(key=lambda l: (l["next_action_date"], -l["score"]))
    if not rows:
        print(f"nothing due on/before {on}")
        return
    print(f"follow-ups due on/before {on}:")
    for l in rows:
        print(f"  {l['id']} {l['next_action_date']} [{l['status']}] {l['company']} "
              f"({l['city']}) -> {l['next_action']}")


def cmd_find(a):
    q = a.text.lower()
    rows = [l for l in load()["leads"] if q in l["company"].lower()
            or q in l["city"].lower() or q in l["notes"].lower()
            or q in l["trigger"].lower()]
    if not rows:
        print("(no match)")
        return
    for l in rows:
        print(f"{l['id']} {l['company']} ({l['city']}) {l['status']} score={l['score']}")


def pipeline_text(db):
    leads = db["leads"]
    by_status = {s: 0 for s in STATUSES}
    for l in leads:
        by_status[l["status"]] = by_status.get(l["status"], 0) + 1
    hot = sorted([l for l in leads if l["score"] >= 70 and active(l)],
                 key=lambda l: -l["score"])
    due = sorted([l for l in leads if active(l) and l["next_action_date"] <= today()],
                 key=lambda l: l["next_action_date"])
    out = [f"# Pipeline — {today()}", "",
           f"**Total leads:** {len(leads)}  |  **Active:** {sum(1 for l in leads if active(l))}"
           f"  |  **Won:** {by_status['won']}  |  **Lost:** {by_status['lost']}", "",
           "## By status", "", "| Status | Count |", "|---|---|"]
    out += [f"| {s} | {by_status[s]} |" for s in STATUSES if by_status[s]]
    out += ["", f"## 🔥 Hot leads ({len(hot)})", "",
            "| ID | Score | Company | City | Status | Next |", "|---|---|---|---|---|---|"]
    out += [f"| {l['id']} | {l['score']} | {l['company']} | {l['city']} | {l['status']} "
            f"| {l['next_action_date']} {l['next_action']} |" for l in hot] or ["| – | | | | | |"]
    out += ["", f"## ⏰ Due today or overdue ({len(due)})", "",
            "| ID | Due | Company | Status | Action |", "|---|---|---|---|---|"]
    out += [f"| {l['id']} | {l['next_action_date']} | {l['company']} | {l['status']} "
            f"| {l['next_action']} |" for l in due] or ["| – | | | | |"]
    return "\n".join(out) + "\n"


def cmd_pipeline(a):
    db = load()
    txt = pipeline_text(db)
    with open(PIPELINE_MD, "w", encoding="utf-8") as f:
        f.write(txt)
    print(txt)
    print(f"(written to {os.path.basename(PIPELINE_MD)})")


def cmd_export(a):
    db = load()
    path = a.csv or os.path.join(BASE, "data", "leads_export.csv")
    cols = ["id", "company", "type", "city", "state", "score", "tier", "status",
            "trigger", "products_fit", "pitch_angle", "next_action", "next_action_date",
            "owner", "website", "source_url", "created", "updated"]
    with open(path, "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(cols + ["decision_makers"])
        for l in db["leads"]:
            dms = "; ".join(f"{d['name']} ({d['role']}) {d['channel']}:{d['contact']}"
                            for d in l["decision_makers"])
            w.writerow([",".join(l[c]) if isinstance(l[c], list) else l[c] for c in cols] + [dms])
    print(f"exported {len(db['leads'])} leads -> {path}")


# --------------------------------------------------------------------------
def main():
    p = argparse.ArgumentParser(description="Client Relationship Tracker")
    sp = p.add_subparsers(dest="cmd", required=True)

    s = sp.add_parser("add", help="add a lead")
    s.add_argument("--company", required=True)
    s.add_argument("--type", choices=TYPES)
    for k in ("city", "state", "website", "source", "trigger", "angle", "next",
              "next-date", "owner", "notes", "products", "status", "tier"):
        s.add_argument("--" + k)
    s.add_argument("--score", type=int)
    s.add_argument("--dm", action="append", help="name|role|channel|contact|verified|source (repeatable)")
    s.add_argument("--force", action="store_true")
    s.set_defaults(fn=cmd_add)

    s = sp.add_parser("list"); s.add_argument("--status"); s.add_argument("--tier")
    s.add_argument("--hot", action="store_true"); s.set_defaults(fn=cmd_list)

    s = sp.add_parser("show"); s.add_argument("id"); s.set_defaults(fn=cmd_show)

    s = sp.add_parser("update"); s.add_argument("id")
    for k in ("status", "tier", "next", "next-date", "owner", "notes", "products",
              "angle", "trigger", "website"):
        s.add_argument("--" + k)
    s.add_argument("--score", type=int)
    s.add_argument("--dm", action="append")
    s.set_defaults(fn=cmd_update)

    s = sp.add_parser("log"); s.add_argument("id")
    s.add_argument("--channel", required=True); s.add_argument("--summary", required=True)
    s.add_argument("--outcome"); s.add_argument("--date")
    s.add_argument("--next"); s.add_argument("--next-date")
    s.set_defaults(fn=cmd_log)

    s = sp.add_parser("due"); s.add_argument("--on"); s.set_defaults(fn=cmd_due)
    s = sp.add_parser("find"); s.add_argument("text"); s.set_defaults(fn=cmd_find)
    s = sp.add_parser("pipeline"); s.set_defaults(fn=cmd_pipeline)
    s = sp.add_parser("export"); s.add_argument("--csv"); s.set_defaults(fn=cmd_export)

    s = sp.add_parser("import", help="import leads from the old Firebase tracker CSV")
    s.add_argument("csv"); s.add_argument("--dry-run", action="store_true")
    s.add_argument("--force", action="store_true", help="add even if company+city exists")
    s.set_defaults(fn=cmd_import)

    a = p.parse_args()
    # argparse turns --next-date into next_date
    a.fn(a)


# --------------------------------------------------------------------------
# Import from the older Firebase "Client Relationship Tracker" export
# (columns: Client Name, Company, City, Phone, Email, Priority, Product Fit,
#  Current Status, Potential, Relationship, Response Status, Next Follow-up,
#  Notes / Next Steps)
# --------------------------------------------------------------------------
_PRODUCT_MAP = [("escape", "escape_room"), ("dome", "dome_360"), ("360", "dome_360"),
                ("mixed", "mixed_reality"), ("mr", "mixed_reality"),
                ("photo", "photo_booth"), ("sim", "car_sim"), ("racing", "car_sim")]
_STATUS_MAP = [("not interested", "lost"), ("won", "won"), ("closed", "won"),
               ("most likely", "proposal"), ("likely accept", "proposal"),
               ("proposal", "proposal"), ("meeting", "meeting"),
               ("ongoing", "replied"), ("interested", "replied"),
               ("replied", "replied"), ("pitched", "pitched"),
               ("contacted", "pitched"), ("follow", "pitched"),
               ("lost", "lost"), ("parked", "parked")]
_TYPE_MAP = [("mall", "mall"), ("resort", "resort"), ("water park", "park"),
             ("theme park", "park"), ("game zone", "fec"), ("play zone", "fec"),
             ("gaming", "fec"), ("recreation", "fec"), ("entertainment", "fec"),
             ("amusement", "fec"), ("gokart", "arena"), ("go-kart", "arena"),
             ("karting", "arena"), ("arena", "arena"), ("stadium", "arena"),
             ("performance centre", "arena"), ("performance center", "arena"),
             ("sports", "arena"), ("cinema", "cinema"), ("multiplex", "cinema"),
             ("developer", "developer"), ("builder", "developer"),
             ("park", "park")]


def _map(text, table, default):
    t = (text or "").lower()
    for key, val in table:
        if key in t:
            return val
    return default


def _products(text):
    t = (text or "").lower()
    out = []
    for key, val in _PRODUCT_MAP:
        if key in t and val not in out:
            out.append(val)
    return out


def cmd_import(a):
    db = load()
    with open(a.csv, newline="", encoding="utf-8-sig") as f:
        rows = list(csv.DictReader(f))
    g = lambda r, k: (r.get(k) or "").strip()
    added = skipped = 0
    for r in rows:
        company = g(r, "Company") or g(r, "Client Name")
        city = g(r, "City")
        if not company:
            continue
        dup = next((l for l in db["leads"] if l["company"].lower() == company.lower()
                    and l["city"].lower() == city.lower()), None)
        if dup and not a.force:
            print(f"skip  {company} ({city}) — exists as {dup['id']}")
            skipped += 1
            continue
        try:
            potential = float(g(r, "Potential") or 0)
        except ValueError:
            potential = 0
        score = max(0, min(100, int(round(potential * 20))))     # 0–5 -> 0–100
        status = _map(g(r, "Current Status"), _STATUS_MAP, "new")
        if "no follow" in g(r, "Response Status").lower() and status == "lost":
            status = "lost"
        phone, email = g(r, "Phone"), g(r, "Email")
        dm = {"name": g(r, "Client Name"), "role": "",
              "channel": "phone" if phone else ("email" if email else ""),
              "contact": phone or email, "verified": False,
              "source": f"import:{os.path.basename(a.csv)}"}
        nxt = g(r, "Next Follow-up")
        notes = "; ".join(x for x in [
            f"Priority: {g(r, 'Priority')}" if g(r, "Priority") else "",
            f"Relationship: {g(r, 'Relationship')}" if g(r, "Relationship") else "",
            f"Response: {g(r, 'Response Status')}" if g(r, "Response Status") else "",
            g(r, "Notes / Next Steps")] if x)
        lid = f"CRT-{db['next_id']:04d}"
        lead = {
            "id": lid, "company": company, "type": _map(company, _TYPE_MAP, "other"),
            "city": city, "state": "", "website": "",
            "source_url": f"import:{os.path.basename(a.csv)}",
            "trigger": g(r, "Notes / Next Steps")[:120],
            "decision_makers": [dm] if dm["name"] else [],
            "score": score, "tier": tier_for(score), "status": status,
            "products_fit": _products(g(r, "Product Fit")),
            "pitch_angle": "", "owner": "",
            "next_action": ("Follow up" if status not in ("lost", "won", "parked")
                            else "None"),
            "next_action_date": nxt if len(nxt) == 10 and nxt[4] == "-" else today(),
            "interactions": [{"date": today(), "channel": "system",
                              "summary": f"Imported from {os.path.basename(a.csv)}",
                              "outcome": g(r, "Current Status")}],
            "notes": notes, "created": today(), "updated": today(),
        }
        print(f"{'would add' if a.dry_run else 'add  '} {lid} {company} ({city}) "
              f"status={status} score={score} products={lead['products_fit']}")
        if not a.dry_run:
            db["leads"].append(lead)
            db["next_id"] += 1
            added += 1
    if not a.dry_run:
        save(db)
    print(f"\n{'dry run: ' if a.dry_run else ''}{added} added, {skipped} skipped")


if __name__ == "__main__":
    main()
