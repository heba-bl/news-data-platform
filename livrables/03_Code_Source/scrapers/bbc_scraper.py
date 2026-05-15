import re
import feedparser
import logging
from typing import List, Optional
from base_scraper import BaseScraper, Article

logger = logging.getLogger(__name__)

BASE_URL = "https://www.bbc.com"

RSS_FEEDS = {
    "World": "https://feeds.bbci.co.uk/news/world/rss.xml",
    "Technology": "https://feeds.bbci.co.uk/news/technology/rss.xml",
    "Business": "https://feeds.bbci.co.uk/news/business/rss.xml",
    "Politics": "https://feeds.bbci.co.uk/news/politics/rss.xml",
    "Science": "https://feeds.bbci.co.uk/news/science_and_environment/rss.xml",
}


class BBCScraper(BaseScraper):
    def __init__(self):
        super().__init__(source_name="BBC", base_url=BASE_URL, delay=1.5)
        self._rss_entries = []

    def get_article_links(self) -> List[str]:
        links = []
        self._rss_entries = []
        for category, feed_url in RSS_FEEDS.items():
            feed = feedparser.parse(feed_url)
            for entry in feed.entries[:8]:
                link = entry.get("link", "")
                if link and "bbc.com" in link:
                    links.append(link)
                    self._rss_entries.append(
                        {
                            "url": link,
                            "title": entry.get("title", ""),
                            "published": entry.get("published", ""),
                            "summary": entry.get("summary", ""),
                            "category": category,
                        }
                    )
        seen = set()
        unique = []
        for e in self._rss_entries:
            if e["url"] not in seen:
                seen.add(e["url"])
                unique.append(e)
        self._rss_entries = unique
        return [e["url"] for e in self._rss_entries][:30]

    def parse_article(self, url: str) -> Optional[Article]:
        rss_data = next((e for e in self._rss_entries if e["url"] == url), {})

        soup = self.fetch(url)
        if not soup:
            return None

        title = rss_data.get("title") or ""
        if not title:
            h1 = soup.find("h1")
            title = h1.get_text(strip=True) if h1 else "N/A"

        author_tag = (
            soup.find("span", attrs={"data-testid": re.compile(r"byline", re.I)})
            or soup.find(class_=re.compile(r"byline|author", re.I))
        )
        author = author_tag.get_text(strip=True) if author_tag else "BBC News"

        published_at = rss_data.get("published", "N/A")
        if published_at == "N/A":
            time_tag = soup.find("time")
            if time_tag:
                published_at = time_tag.get("datetime", time_tag.get_text(strip=True))

        category = rss_data.get("category", "World")

        content_blocks = soup.select(
            "article p, div[data-component='text-block'] p, div.article__body p"
        )
        if not content_blocks:
            content_blocks = soup.select("p")

        content = " ".join(p.get_text(strip=True) for p in content_blocks if len(p.get_text(strip=True)) > 20)

        if not title or len(content) < 50:
            content = rss_data.get("summary", "")
            if len(content) < 50:
                return None

        return Article(
            title=title,
            author=author,
            published_at=published_at,
            category=category,
            content=content,
            source="BBC",
            url=url,
            language="en",
        )
