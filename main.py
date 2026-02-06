import json
from datetime import datetime, UTC

from collections import defaultdict

from scrapers.rss_collector import collect
from processing.summarizer import summarize
from processing.categorizer import pick_category
from processing.trends import top_terms_by_category, hot_stories
from processing.velocity import velocity_wow
from processing.companies import extract_companies

from storage.db import init_db, normalize_title
from output.email_builder import send_email
from jinja2 import Template
from dotenv import load_dotenv
load_dotenv()




def run_pipeline():
    conn = init_db()
    cur = conn.cursor()

    fetched_at = datetime.now(UTC).isoformat()

    with open("sources/rss_sources.json", encoding="utf-8") as f:
        sources = json.load(f)

    inserted_rows = []

    for src in sources:
        data = collect(src["url"])
        print(f"[RSS] {src.get('name','?')}: {len(data)} items")
        fallback_cats = src.get("categories", [])

        for a in data:
            cat = pick_category(a.get("title", ""), a.get("text", ""), fallback_cats)
            text = (a.get("text", "") or "")[:3000]
            summary = summarize(text) if text.strip() else "• (No text extracted)"

            title = a.get("title", "")
            companies_list = extract_companies(title, text)
            
            row = {
                "title": a.get("title", ""),
                "url": a.get("url", ""),
                "source": a.get("source", src.get("name", "")),
                "published": a.get("published", ""),
                "category": cat,
                "companies": json.dumps(companies_list),
                "summary": summary,
                "fetched_at": fetched_at,
                "title_key": normalize_title(a.get("title", ""))
            }

            try:
                cur.execute(
                    """
                    INSERT INTO articles(title,url,source,published,fetched_at,category,companies,summary,title_key)
                    VALUES(?,?,?,?,?,?,?,?,?)
                    ON CONFLICT(url) DO UPDATE SET
                        title=excluded.title,
                        source=excluded.source,
                        published=excluded.published,
                        fetched_at=excluded.fetched_at,
                        category=excluded.category,
                        companies=excluded.companies,
                        summary=excluded.summary,
                        title_key=excluded.title_key
                    """,
                    (
                        row["title"],
                        row["url"],
                        row["source"],
                        row["published"],
                        row["fetched_at"],
                        row["category"],
                        row["companies"],
                        row["summary"],
                        row["title_key"]
                    )
                )
                conn.commit()

                # Count as inserted only if it was new
                if cur.rowcount == 1:
                    inserted_rows.append(row)

            except Exception as e:
                print("DB WRITE FAILED:", e, "| URL:", row.get("url"))


    # If nothing new, still email “hot/trends” based on recent DB entries
    # Simple approach: use last ~200 articles in DB
    cur.execute("SELECT title,url,source,published,fetched_at,category,summary FROM articles ORDER BY id DESC LIMIT 200")
    db_rows = [
        {"title": r[0], "url": r[1], "source": r[2], "published": r[3], "fetched_at": r[4], "category": r[5], "summary": r[6]}
        for r in cur.fetchall()
    ]
    print(f"[DB] rows loaded for report: {len(db_rows)} (inserted this run: {len(inserted_rows)})")
    velocity = velocity_wow(db_rows)

    grouped = defaultdict(list)
    for r in (inserted_rows or db_rows):
        grouped[r["category"]].append(r)

    trends = top_terms_by_category(db_rows, top_n=10)
    hot = hot_stories(db_rows, similarity_threshold=0.82, max_groups=8)

    with open("output/templates.html", encoding="utf-8") as f:
        template = Template(f.read())

    html = template.render(
        grouped=dict(sorted(grouped.items(), key=lambda x: x[0])),
        trends=trends,
        hot_stories=hot,
        velocity=velocity
    )
    send_email(html)


if __name__ == "__main__":
    run_pipeline()