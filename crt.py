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
import html
import json
import os
import subprocess
import sys
from datetime import date, datetime, timedelta, timezone

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


# --------------------------------------------------------------------------
# Stats / dashboard
# --------------------------------------------------------------------------
DASHBOARD_HTML = os.path.join(BASE, "DASHBOARD.html")
EXPORT_CSV = os.path.join(BASE, "data", "leads_export.csv")
WEEKLY_TARGET = 10
SCAN_EVERY_H = 6          # the cloud scanner's cron: 0 */6 * * * (UTC)
IST = timezone(timedelta(hours=5, minutes=30))


def _scan_commits(limit=10):
    """Recent scanner commits (iso_date, message) from git log, newest first."""
    try:
        # git emits UTF-8; force it (Windows would otherwise decode as cp1252
        # and turn the em-dash in "scan: ... — n new leads" into mojibake).
        r = subprocess.run(["git", "log", "--format=%aI|%s", "-n", "80"],
                           capture_output=True, text=True, encoding="utf-8",
                           errors="replace", cwd=BASE, timeout=10)
    except (OSError, subprocess.TimeoutExpired):
        return []
    out = []
    for line in (r.stdout or "").splitlines():
        if "|" in line:
            d, m = line.split("|", 1)
            if m.startswith("scan:"):
                out.append((d, m))
    return out[:limit]


def _parse_iso(s):
    try:
        return datetime.fromisoformat(s.strip())
    except ValueError:
        return None


def compute_stats(db):
    leads = db["leads"]
    now = datetime.now(timezone.utc)
    week_ago = (date.today() - timedelta(days=7)).isoformat()
    by_status = {s: 0 for s in STATUSES}
    for l in leads:
        by_status[l["status"]] = by_status.get(l["status"], 0) + 1
    hot = sorted([l for l in leads if l["score"] >= 70 and active(l)], key=lambda l: -l["score"])
    due = sorted([l for l in leads if active(l) and l["next_action_date"] <= today()],
                 key=lambda l: (l["next_action_date"], -l["score"]))
    weekly = [l for l in leads if l["score"] >= 45 and l.get("created", "") >= week_ago]
    briefs = sorted(f for f in os.listdir(os.path.join(BASE, "opportunities"))
                    if f.endswith(".md")) if os.path.isdir(os.path.join(BASE, "opportunities")) else []
    scans = _scan_commits()
    last_scan = _parse_iso(scans[0][0]) if scans else None
    age_h = (now - last_scan.astimezone(timezone.utc)).total_seconds() / 3600 if last_scan else None
    nxt = now.replace(minute=0, second=0, microsecond=0)
    nxt = nxt + timedelta(hours=SCAN_EVERY_H - (nxt.hour % SCAN_EVERY_H))
    by_city, by_type = {}, {}
    for l in leads:
        if active(l):
            by_city[l["city"] or "—"] = by_city.get(l["city"] or "—", 0) + 1
            by_type[l["type"]] = by_type.get(l["type"], 0) + 1
    return {
        "now": now, "total": len(leads), "active": sum(1 for l in leads if active(l)),
        "by_status": by_status, "hot": hot, "due": due, "weekly": len(weekly),
        "in_conv": by_status["replied"] + by_status["meeting"] + by_status["proposal"],
        "won": by_status["won"], "lost": by_status["lost"], "briefs": briefs,
        "scans": scans, "last_scan": last_scan, "age_h": age_h, "next_scan": nxt,
        "online": age_h is not None and age_h <= SCAN_EVERY_H + 1.5,
        "by_city": sorted(by_city.items(), key=lambda x: -x[1])[:8],
        "by_type": sorted(by_type.items(), key=lambda x: -x[1]),
    }


def _ist(dt):
    return dt.astimezone(IST).strftime("%d %b %Y, %H:%M IST") if dt else "—"


def _ago(h):
    if h is None:
        return "never"
    if h < 1:
        return f"{int(h * 60)} min ago"
    if h < 48:
        return f"{h:.1f} h ago"
    return f"{h / 24:.1f} days ago"


def _bar(n, total, width=20):
    filled = 0 if total <= 0 else min(width, int(round(width * n / total)))
    return "▓" * filled + "░" * (width - filled)


def pipeline_text(db):
    s = compute_stats(db)
    status = "🟢 ONLINE" if s["online"] else ("🟠 STALE" if s["last_scan"] else "⚪ NO SCANS YET")
    out = [f"# Client Terminal — Pipeline", "",
           f"_Updated {_ist(s['now'])}_ · open **DASHBOARD.html** for the full view", "",
           f"**Scanner:** {status} · last scan {_ago(s['age_h'])} ({_ist(s['last_scan'])}) · "
           f"next ≈ {_ist(s['next_scan'])}", "",
           f"**This week:** `{_bar(s['weekly'], WEEKLY_TARGET)}` **{s['weekly']} / {WEEKLY_TARGET}** qualified clients", "",
           f"| Total | Active | 🔥 Hot | New this week | In conversation | Won | Briefs | Due |",
           f"|---|---|---|---|---|---|---|---|",
           f"| {s['total']} | {s['active']} | {len(s['hot'])} | {s['weekly']} | {s['in_conv']} "
           f"| {s['won']} | {len(s['briefs'])} | {len(s['due'])} |", "",
           "## By status", "", "| Status | Count |", "|---|---|"]
    out += [f"| {st} | {s['by_status'][st]} |" for st in STATUSES if s["by_status"][st]]
    out += ["", f"## 🔥 Hot leads ({len(s['hot'])})", "",
            "| ID | Score | Company | City | Status | Next |", "|---|---|---|---|---|---|"]
    out += [f"| {l['id']} | {l['score']} | {l['company']} | {l['city']} | {l['status']} "
            f"| {l['next_action_date']} {l['next_action']} |" for l in s["hot"]] or ["| – | | | | | |"]
    out += ["", f"## ⏰ Due today or overdue ({len(s['due'])})", "",
            "| ID | Due | Company | Status | Action |", "|---|---|---|---|---|"]
    out += [f"| {l['id']} | {l['next_action_date']} | {l['company']} | {l['status']} "
            f"| {l['next_action']} |" for l in s["due"]] or ["| – | | | | |"]
    out += ["", f"## 🛰 Recent scans", ""]
    out += [f"- {_ist(_parse_iso(d))} — {m}" for d, m in s["scans"]] or ["- (none yet)"]
    return "\n".join(out) + "\n"


def dashboard_html(db):
    s = compute_stats(db)
    e = html.escape
    dot = "on" if s["online"] else ("stale" if s["last_scan"] else "off")
    status_txt = {"on": "SCANNER ONLINE", "stale": "SCANNER STALE", "off": "NO SCANS YET"}[dot]
    pct = min(100, int(100 * s["weekly"] / WEEKLY_TARGET))

    def kpi(label, val, sub=""):
        return (f'<div class="kpi"><div class="v">{e(str(val))}</div>'
                f'<div class="l">{e(label)}</div><div class="s">{e(sub)}</div></div>')

    def pill(score):
        c = "hot" if score >= 70 else "warm" if score >= 45 else "cold"
        return f'<span class="score {c}">{score}</span>'

    hot_rows = "".join(
        f"<tr><td class='mono'>{e(l['id'])}</td><td>{pill(l['score'])}</td>"
        f"<td><b>{e(l['company'])}</b><div class='sub'>{e(l['trigger'][:110])}</div></td>"
        f"<td>{e(l['city'])}</td><td><span class='st st-{e(l['status'])}'>{e(l['status'])}</span></td>"
        f"<td class='sub'>{e(l['next_action_date'])}<br>{e(l['next_action'][:40])}</td></tr>"
        for l in s["hot"]) or "<tr><td colspan='6' class='sub'>No hot leads yet.</td></tr>"
    due_rows = "".join(
        f"<tr><td class='mono'>{e(l['id'])}</td><td>{e(l['next_action_date'])}</td>"
        f"<td>{e(l['company'])}</td><td><span class='st st-{e(l['status'])}'>{e(l['status'])}</span></td>"
        f"<td class='sub'>{e(l['next_action'][:60])}</td></tr>"
        for l in s["due"][:12]) or "<tr><td colspan='5' class='sub'>Nothing due.</td></tr>"
    scan_rows = "".join(
        f"<li><span class='mono'>{e(_ist(_parse_iso(d)))}</span><span>{e(m.replace('scan: ', ''))}</span></li>"
        for d, m in s["scans"]) or "<li class='sub'>No scans recorded yet.</li>"
    mx = max([c for _, c in s["by_status"].items()] + [1])
    funnel = "".join(
        f"<div class='frow'><span class='fl'>{e(st)}</span>"
        f"<span class='ft'><i style='width:{int(100 * s['by_status'][st] / mx)}%'></i></span>"
        f"<span class='fn'>{s['by_status'][st]}</span></div>"
        for st in STATUSES if s["by_status"][st])
    cities = "".join(f"<li><span>{e(c)}</span><b>{n}</b></li>" for c, n in s["by_city"]) or "<li class='sub'>—</li>"
    types = "".join(f"<li><span>{e(t)}</span><b>{n}</b></li>" for t, n in s["by_type"]) or "<li class='sub'>—</li>"
    briefs = "".join(f"<li><span class='mono'>{e(b)}</span></li>" for b in s["briefs"][-8:][::-1]) or "<li class='sub'>none yet</li>"

    return f"""<!doctype html>
<html lang="en"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>Client Terminal — Circuit Entertainment</title>
<style>
:root{{--bg:#0b0f17;--card:#121826;--line:#1f2a3d;--fg:#e8eef9;--dim:#8a97b2;--acc:#37e0a6;--acc2:#4c8dff;
--warn:#ffb020;--bad:#ff5d5d;--mono:ui-monospace,Consolas,"SF Mono",Menlo,monospace}}
@media (prefers-color-scheme:light){{:root:not([data-theme=dark]){{--bg:#f3f5f9;--card:#fff;--line:#dde3ee;--fg:#111827;--dim:#5b6780}}}}
*{{box-sizing:border-box;margin:0;padding:0}}
body{{background:var(--bg);color:var(--fg);font:14px/1.5 system-ui,-apple-system,"Segoe UI",Roboto,sans-serif;padding:20px 16px 40px}}
.wrap{{max-width:1240px;margin:0 auto}}
header{{display:flex;flex-wrap:wrap;gap:12px 24px;align-items:center;justify-content:space-between;margin-bottom:18px}}
h1{{font-size:18px;letter-spacing:.14em;text-transform:uppercase}} h1 small{{display:block;font-size:11px;color:var(--dim);letter-spacing:.2em;margin-top:2px}}
.status{{display:flex;flex-wrap:wrap;gap:8px 18px;align-items:center;font-family:var(--mono);font-size:12px;color:var(--dim)}}
.dot{{display:inline-flex;align-items:center;gap:8px;font-weight:700;color:var(--fg)}}
.dot i{{width:10px;height:10px;border-radius:50%;background:var(--dim);box-shadow:0 0 0 0 transparent}}
.dot.on i{{background:var(--acc);animation:pulse 2s infinite}} .dot.stale i{{background:var(--warn)}} .dot.off i{{background:var(--dim)}}
@keyframes pulse{{0%{{box-shadow:0 0 0 0 rgba(55,224,166,.6)}}100%{{box-shadow:0 0 0 10px rgba(55,224,166,0)}}}}
.grid{{display:grid;gap:14px}} .g4{{grid-template-columns:repeat(auto-fit,minmax(150px,1fr))}} .g2{{grid-template-columns:repeat(auto-fit,minmax(340px,1fr))}}
.card{{background:var(--card);border:1px solid var(--line);border-radius:14px;padding:16px}}
.card h2{{font-size:11px;letter-spacing:.18em;text-transform:uppercase;color:var(--dim);margin-bottom:12px}}
.kpi .v{{font-size:30px;font-weight:800;line-height:1;font-variant-numeric:tabular-nums}} .kpi .l{{font-size:12px;color:var(--dim);margin-top:6px}} .kpi .s{{font-size:11px;color:var(--dim)}}
.target{{display:flex;align-items:center;gap:18px;flex-wrap:wrap}} .target .big{{font-size:34px;font-weight:800;font-variant-numeric:tabular-nums}} .target .big small{{font-size:16px;color:var(--dim);font-weight:600}}
.prog{{flex:1;min-width:220px;height:14px;background:var(--line);border-radius:999px;overflow:hidden}} .prog i{{display:block;height:100%;width:{pct}%;background:linear-gradient(90deg,var(--acc2),var(--acc));border-radius:999px}}
table{{width:100%;border-collapse:collapse}} th{{text-align:left;font-size:11px;letter-spacing:.1em;text-transform:uppercase;color:var(--dim);padding:6px 8px;border-bottom:1px solid var(--line)}}
td{{padding:9px 8px;border-bottom:1px solid var(--line);vertical-align:top}} tr:last-child td{{border-bottom:0}}
.mono{{font-family:var(--mono);font-size:12px}} .sub{{color:var(--dim);font-size:12px}}
.score{{display:inline-block;min-width:38px;text-align:center;padding:3px 8px;border-radius:8px;font-weight:800;font-family:var(--mono)}}
.score.hot{{background:rgba(255,93,93,.15);color:#ff7b7b}} .score.warm{{background:rgba(255,176,32,.15);color:var(--warn)}} .score.cold{{background:var(--line);color:var(--dim)}}
.st{{display:inline-block;padding:2px 8px;border-radius:999px;font-size:11px;font-family:var(--mono);background:var(--line);color:var(--fg)}}
.st-new{{background:rgba(76,141,255,.18);color:#8db4ff}} .st-replied,.st-meeting,.st-proposal{{background:rgba(55,224,166,.15);color:var(--acc)}}
.st-won{{background:var(--acc);color:#04291c}} .st-lost,.st-do_not_contact{{background:rgba(255,93,93,.15);color:#ff7b7b}} .st-parked{{color:var(--dim)}}
.frow{{display:grid;grid-template-columns:120px 1fr 36px;gap:10px;align-items:center;margin:6px 0;font-size:12px}} .fl{{font-family:var(--mono);color:var(--dim)}}
.ft{{height:10px;background:var(--line);border-radius:999px;overflow:hidden}} .ft i{{display:block;height:100%;background:var(--acc2);border-radius:999px}} .fn{{text-align:right;font-weight:700;font-variant-numeric:tabular-nums}}
ul.feed{{list-style:none}} ul.feed li{{display:flex;gap:14px;padding:8px 0;border-bottom:1px solid var(--line);font-size:13px}} ul.feed li:last-child{{border-bottom:0}} ul.feed .mono{{color:var(--dim);white-space:nowrap}}
ul.kv{{list-style:none}} ul.kv li{{display:flex;justify-content:space-between;padding:6px 0;border-bottom:1px solid var(--line);font-size:13px}} ul.kv li:last-child{{border-bottom:0}}
footer{{margin-top:22px;color:var(--dim);font-size:12px;text-align:center}}
</style></head><body><div class="wrap">
<header>
  <h1>Client Terminal <small>Circuit Entertainment · B2B growth engine</small></h1>
  <div class="status">
    <span class="dot {dot}"><i></i>{status_txt}</span>
    <span>last scan <b>{e(_ago(s['age_h']))}</b> · {e(_ist(s['last_scan']))}</span>
    <span>next ≈ <b>{e(_ist(s['next_scan']))}</b></span>
    <span>every {SCAN_EVERY_H}h · updated {e(_ist(s['now']))}</span>
  </div>
</header>

<div class="card" style="margin-bottom:14px">
  <h2>Weekly target — qualified clients found</h2>
  <div class="target"><div class="big">{s['weekly']}<small> / {WEEKLY_TARGET}</small></div>
  <div class="prog"><i></i></div><div class="sub">{pct}% · leads scoring ≥45 found in the last 7 days</div></div>
</div>

<div class="grid g4" style="margin-bottom:14px">
  {kpi("Total leads", s['total'])}{kpi("Active", s['active'])}{kpi("Hot (≥70)", len(s['hot']), "ready for proposals")}
  {kpi("New this week", s['weekly'])}{kpi("In conversation", s['in_conv'], "replied · meeting · proposal")}
  {kpi("Won", s['won'])}{kpi("Opportunity briefs", len(s['briefs']), "opportunities/")}{kpi("Follow-ups due", len(s['due']))}
</div>

<div class="grid g2">
  <div class="card" style="grid-column:1/-1"><h2>🔥 Hot leads — draft a proposal</h2>
    <table><thead><tr><th>ID</th><th>Score</th><th>Company · why now</th><th>City</th><th>Status</th><th>Next</th></tr></thead>
    <tbody>{hot_rows}</tbody></table></div>
  <div class="card"><h2>🛰 Scanner activity</h2><ul class="feed">{scan_rows}</ul></div>
  <div class="card"><h2>⏰ Follow-ups due</h2>
    <table><thead><tr><th>ID</th><th>Due</th><th>Company</th><th>Status</th><th>Action</th></tr></thead><tbody>{due_rows}</tbody></table></div>
  <div class="card"><h2>Pipeline by status</h2>{funnel or "<div class='sub'>—</div>"}</div>
  <div class="card"><h2>Latest opportunity briefs</h2><ul class="feed">{briefs}</ul></div>
  <div class="card"><h2>Active leads by city</h2><ul class="kv">{cities}</ul></div>
  <div class="card"><h2>Active leads by venue type</h2><ul class="kv">{types}</ul></div>
</div>
<footer>Regenerated automatically after every scan (<span class="mono">python crt.py pipeline</span>) · data: <span class="mono">data/leads.json</span> · Power BI: <span class="mono">data/leads_export.csv</span></footer>
</div></body></html>
"""


def write_outputs(db):
    with open(PIPELINE_MD, "w", encoding="utf-8") as f:
        f.write(pipeline_text(db))
    with open(DASHBOARD_HTML, "w", encoding="utf-8") as f:
        f.write(dashboard_html(db))
    _export_csv(db, EXPORT_CSV)


def cmd_pipeline(a):
    db = load()
    write_outputs(db)
    print(pipeline_text(db))
    print(f"(written: PIPELINE.md, DASHBOARD.html, data/leads_export.csv)")


def _export_csv(db, path):
    """Flat CSV of all leads (Power BI / Excel friendly)."""
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
    return len(db["leads"])


def cmd_export(a):
    db = load()
    path = a.csv or EXPORT_CSV
    n = _export_csv(db, path)
    print(f"exported {n} leads -> {path}")


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
    s = sp.add_parser("pipeline", help="write PIPELINE.md + DASHBOARD.html + CSV"); s.set_defaults(fn=cmd_pipeline)
    s = sp.add_parser("dashboard", help="same as pipeline"); s.set_defaults(fn=cmd_pipeline)
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
