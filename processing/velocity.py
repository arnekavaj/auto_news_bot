import re
from collections import Counter, defaultdict
from datetime import datetime, timedelta


STOPWORDS = set("""
a an and are as at be by for from has have he her his i in is it its of on or our she that the their them they this to was were will with you your
new over like line pro said says report reports year years week weeks day days company companies market markets
""".split())

BANNED_TERMS = {"delta", "line", "pro", "new", "over", "like"}

def tokenize(text: str):
    text = (text or "").lower()
    words = re.findall(r"[a-z][a-z0-9\-]{2,}", text)
    return [w for w in words if w not in STOPWORDS and w not in BANNED_TERMS and not w.isdigit()]


def _parse_date_loose(s: str):
    """
    Very forgiving parser. If it can't parse, returns None.
    We only need rough bucketing (this week vs last week).
    """
    if not s:
        return None
    s = s.strip()

    # Common RSS formats often include timezone names; we ignore exact tz
    patterns = [
        "%a, %d %b %Y %H:%M:%S %Z",
        "%a, %d %b %Y %H:%M:%S %z",
        "%a, %d %b %Y %H:%M:%S",
        "%Y-%m-%dT%H:%M:%S%z",
        "%Y-%m-%dT%H:%M:%S",
        "%Y-%m-%d",
    ]
    for p in patterns:
        try:
            dt = datetime.strptime(s, p)
            return dt.replace(tzinfo=None)
        except:
            pass
    return None


def velocity_wow(rows, now=None):
    """
    Computes WoW velocity:
    - this_week_count vs last_week_count by category
    - rising_terms: terms that increased most this week vs last week
    rows: list of dicts (title, summary, category, published)
    """
    now = (now or datetime.utcnow()).replace(tzinfo=None)
    start_this = now - timedelta(days=7)
    start_last = now - timedelta(days=14)

    by_cat = defaultdict(lambda: {"this_week": 0, "last_week": 0})
    terms_this = Counter()
    terms_last = Counter()

    for r in rows:
        dt = _parse_date_loose(r.get("fetched_at", "")) or _parse_date_loose(r.get("published", ""))
        # If missing dates, ignore for velocity calculations
        if not dt:
            continue

        bucket = None
        if dt >= start_this:
            bucket = "this"
        elif start_last <= dt < start_this:
            bucket = "last"
        else:
            continue

        cat = r.get("category", "General") or "General"
        if bucket == "this":
            by_cat[cat]["this_week"] += 1
            terms_this.update(tokenize((r.get("title", "") + " " + r.get("summary", ""))[:2500]))
        else:
            by_cat[cat]["last_week"] += 1
            terms_last.update(tokenize((r.get("title", "") + " " + r.get("summary", ""))[:2500]))

    # Turn counts into a sorted list with deltas
    cat_velocity = []
    for cat, c in by_cat.items():
        tw = c["this_week"]
        lw = c["last_week"]
        delta = tw - lw
        # simple growth % with guard
        pct = None
        if lw == 0 and tw > 0:
            pct = 999  # "new spike"
        elif lw > 0:
            pct = int(round((delta / lw) * 100))
        else:
            pct = 0

        cat_velocity.append({
            "category": cat,
            "this_week": tw,
            "last_week": lw,
            "delta": delta,
            "pct": pct
        })

    cat_velocity.sort(key=lambda x: (x["delta"], x["this_week"]), reverse=True)

    # Rising terms: biggest increase this week vs last week (min frequency filters)
    rising = []
    all_terms = set(terms_this.keys()) | set(terms_last.keys())
    for t in all_terms:
        tw = terms_this[t]
        lw = terms_last[t]
        if tw < 3:
            continue  # avoid noise
        diff = tw - lw
        if diff <= 0:
            continue
        rising.append({"term": t, "this_week": tw, "last_week": lw, "delta": diff})

    rising.sort(key=lambda x: (x["delta"], x["this_week"]), reverse=True)

    return {
        "cat_velocity": cat_velocity[:12],
        "rising_terms": rising[:15]
    }