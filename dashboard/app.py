import sys
import os
DB_PATH = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "news.db")
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import json as _json
from collections import Counter, defaultdict

from flask import Flask, render_template
import sqlite3
from collections import defaultdict
from datetime import datetime, timedelta

from processing.trends import hot_stories, top_terms_by_category
from processing.velocity import velocity_wow
from dotenv import load_dotenv
load_dotenv()


app = Flask(__name__)


def get_db_rows(limit=500):
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()

    # Columns: title,url,source,published,fetched_at,category,summary
    cur.execute("""
        SELECT title,url,source,published,fetched_at,category,companies,summary
        FROM articles
        ORDER BY id DESC
        LIMIT ?
    """, (limit,))
    rows = [
        {
            "title": r[0],
            "url": r[1],
            "source": r[2],
            "published": r[3] or "",
            "fetched_at": r[4] or "",
            "category": r[5] or "General",
            "companies": r[6] or "[]",
            "summary": r[7] or ""
        }
        for r in cur.fetchall()
    ]
    conn.close()
    return rows


def parse_iso_loose(s):
    if not s:
        return None
    try:
        # handles "2026-02-06T10:22:33+00:00"
        return datetime.fromisoformat(s.replace("Z", "+00:00"))
    except:
        return None

def company_velocity_wow(rows, now=None, top_n=20):
    """
    Velocity by company: mentions this week vs last week.
    Uses fetched_at (falls back to published).
    """
    now = (now or datetime.utcnow()).replace(tzinfo=None)
    start_this = now - timedelta(days=7)
    start_last = now - timedelta(days=14)

    def parse_dt(r):
        # prefer fetched_at (ISO), fallback to published (RSS-ish)
        dt = parse_iso_loose(r.get("fetched_at", ""))
        if dt:
            return dt.replace(tzinfo=None)
        # try published as iso too (sometimes it is)
        dt = parse_iso_loose(r.get("published", ""))
        if dt:
            return dt.replace(tzinfo=None)
        return None

    this_counts = Counter()
    last_counts = Counter()

    for r in rows:
        dt = parse_dt(r)
        if not dt:
            continue

        # companies stored as JSON string
        try:
            comps = _json.loads(r.get("companies", "[]"))
        except:
            comps = []

        if not comps:
            continue

        bucket = None
        if dt >= start_this:
            bucket = "this"
        elif start_last <= dt < start_this:
            bucket = "last"
        else:
            continue

        # count each company once per article (not multiple times)
        unique_comps = set(comps)
        if bucket == "this":
            this_counts.update(unique_comps)
        else:
            last_counts.update(unique_comps)

    all_companies = set(this_counts.keys()) | set(last_counts.keys())
    rows_out = []
    for c in all_companies:
        tw = this_counts[c]
        lw = last_counts[c]
        delta = tw - lw
        if tw == 0 and lw == 0:
            continue
        pct = 0
        if lw == 0 and tw > 0:
            pct = 999  # new spike
        elif lw > 0:
            pct = int(round((delta / lw) * 100))

        rows_out.append({
            "company": c,
            "this_week": tw,
            "last_week": lw,
            "delta": delta,
            "pct": pct
        })

    # sort by biggest increase, then biggest this-week
    rows_out.sort(key=lambda x: (x["delta"], x["this_week"]), reverse=True)
    return rows_out[:top_n]



@app.route("/")
def index():
    rows = get_db_rows(limit=800)

    company_velocity = company_velocity_wow(rows, top_n=20)

    company_counter = Counter()
    for r in rows:
        try:
            comps = _json.loads(r.get("companies", "[]"))
            company_counter.update(set(comps))
        except:
            pass
    top_companies = company_counter.most_common(20)

    # Group latest by category (show top N each)
    grouped = defaultdict(list)
    for r in rows:
        grouped[r["category"]].append(r)

    # keep only latest 12 per category
    grouped_limited = {k: v[:12] for k, v in sorted(grouped.items(), key=lambda x: x[0])}

    # Hot + trends + velocity
    hot = hot_stories(rows, similarity_threshold=0.82, max_groups=10)
    trends = top_terms_by_category(rows, top_n=10)
    velocity = velocity_wow(rows)

    # Chart data: articles per day (last 14 days) based on fetched_at
    today = datetime.utcnow().date()
    day_labels = []
    day_counts = []
    counts_map = { (today - timedelta(days=i)).isoformat(): 0 for i in range(13, -1, -1) }

    for r in rows:
        dt = parse_iso_loose(r.get("fetched_at", ""))
        if not dt:
            continue
        d = dt.date().isoformat()
        if d in counts_map:
            counts_map[d] += 1

    for d, c in counts_map.items():
        day_labels.append(d)
        day_counts.append(c)

    # Chart data: category counts (top 10)
    cat_counts = defaultdict(int)
    for r in rows:
        cat_counts[r["category"]] += 1
    top_cats = sorted(cat_counts.items(), key=lambda x: x[1], reverse=True)[:10]
    cat_labels = [x[0] for x in top_cats]
    cat_values = [x[1] for x in top_cats]

    return render_template(
        "index.html",
        hot=hot,
        grouped=grouped_limited,
        trends=trends,
        velocity=velocity,
        top_companies=top_companies,
        company_velocity=company_velocity,
        day_labels=day_labels,
        day_counts=day_counts,
        cat_labels=cat_labels,
        cat_values=cat_values
    )


if __name__ == "__main__":
    # http://127.0.0.1:5000
    app.run(debug=True)