import re
from collections import Counter, defaultdict
from difflib import SequenceMatcher


STOPWORDS = set("""
a an and are as at be by for from has have he her his i in is it its of on or our she that the their them they this to was were will with you your
""".split())


def tokenize(text: str):
    text = (text or "").lower()
    words = re.findall(r"[a-z][a-z0-9\-]{2,}", text)
    return [w for w in words if w not in STOPWORDS and not w.isdigit()]


def top_terms_by_category(rows, top_n=10):
    # rows: list of dicts with category, title, summary
    counters = defaultdict(Counter)
    for r in rows:
        cat = r.get("category", "General")
        tokens = tokenize((r.get("title", "") + " " + r.get("summary", ""))[:3000])
        counters[cat].update(tokens)

    return {cat: cnt.most_common(top_n) for cat, cnt in counters.items()}


def title_key(title: str) -> str:
    t = (title or "").lower().strip()
    for ch in ["’", "'", "\"", "“", "”", ":", ";", ",", ".", "!", "?", "(", ")", "[", "]"]:
        t = t.replace(ch, "")
    t = " ".join(t.split())
    return t[:180]


def hot_stories(rows, similarity_threshold=0.82, max_groups=8):
    """
    Groups stories that look like the same news across sources using title similarity.
    Score = number of sources in the group.
    """
    items = []
    for r in rows:
        items.append({
            "title": r.get("title", ""),
            "url": r.get("url", ""),
            "source": r.get("source", ""),
            "category": r.get("category", "General"),
            "summary": r.get("summary", ""),
            "key": title_key(r.get("title", ""))
        })

    groups = []  # each group: {"items": [...], "rep_key": str}
    for it in items:
        placed = False
        for g in groups:
            sim = SequenceMatcher(None, it["key"], g["rep_key"]).ratio()
            if sim >= similarity_threshold:
                g["items"].append(it)
                placed = True
                break
        if not placed:
            groups.append({"rep_key": it["key"], "items": [it]})

    # sort by coverage (more sources = hotter)
    groups.sort(key=lambda g: len({x["source"] for x in g["items"]}), reverse=True)

    hot = []
    for g in groups[:max_groups]:
        sources = sorted({x["source"] for x in g["items"]})
        # pick a best representative (first item)
        rep = g["items"][0]
        hot.append({
            "title": rep["title"],
            "url": rep["url"],
            "category": rep["category"],
            "sources": sources,
            "coverage": len(sources)
        })
    return hot