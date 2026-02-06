import feedparser
from newspaper import Article


def collect(feed_url):
    feed = feedparser.parse(feed_url)
    articles = []

    for entry in feed.entries[:10]:
        url = getattr(entry, "link", None)
        if not url:
            continue

        published = (
            getattr(entry, "published", "") or
            getattr(entry, "updated", "") or
            ""
        )

        try:
            art = Article(url)
            art.download()
            art.parse()

            title = art.title or getattr(entry, "title", "") or url

            articles.append({
                "title": title,
                "url": url,
                "text": art.text or "",
                "source": getattr(feed.feed, "title", "") or "",
                "published": published
            })
        except:
            # If article extraction fails, still keep headline+link
            title = getattr(entry, "title", "") or url
            articles.append({
                "title": title,
                "url": url,
                "text": getattr(entry, "summary", "") or "",
                "source": getattr(feed.feed, "title", "") or "",
                "published": published
            })

    return articles