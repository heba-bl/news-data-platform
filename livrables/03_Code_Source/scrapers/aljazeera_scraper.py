import re
import feedparser
import logging
from typing import List, Optional
from base_scraper import BaseScraper, Article

logger = logging.getLogger(__name__)

BASE_URL = "https://www.aljazeera.net"

RSS_FEEDS = {
    "عاجل": "https://www.aljazeera.net/xml/rss2.0.xml",
    "أخبار": "https://www.aljazeera.net/xml/rss2.0.xml?taxonomy=category&term=news",
    "اقتصاد": "https://www.aljazeera.net/xml/rss2.0.xml?taxonomy=category&term=economy",
    "رياضة": "https://www.aljazeera.net/xml/rss2.0.xml?taxonomy=category&term=sport",
    "علوم": "https://www.aljazeera.net/xml/rss2.0.xml?taxonomy=category&term=science",
}

FALLBACK_FEEDS = {
    "World": "https://news.google.com/rss/search?q=aljazeera+arabic&hl=ar&gl=QA&ceid=QA:ar",
    "Middle East": "https://news.google.com/rss/search?q=aljazeera+middle+east&hl=en-US&gl=US&ceid=US:en",
}


class AlJazeeraScraper(BaseScraper):
    def __init__(self):
        super().__init__(source_name="AlJazeera", base_url=BASE_URL, delay=2.0)
        self._rss_entries = []

    def get_article_links(self) -> List[str]:
        self._rss_entries = []
        seen = set()

        for category, feed_url in RSS_FEEDS.items():
            feed = feedparser.parse(feed_url)
            for entry in feed.entries[:6]:
                link = entry.get("link", "")
                if not link or link in seen:
                    continue
                seen.add(link)
                self._rss_entries.append({
                    "url": link,
                    "title": entry.get("title", ""),
                    "published": entry.get("published", ""),
                    "summary": entry.get("summary", ""),
                    "category": category,
                })

        if not self._rss_entries:
            for category, feed_url in FALLBACK_FEEDS.items():
                feed = feedparser.parse(feed_url)
                for entry in feed.entries[:5]:
                    link = entry.get("link", "")
                    if not link or link in seen:
                        continue
                    seen.add(link)
                    self._rss_entries.append({
                        "url": link,
                        "title": entry.get("title", ""),
                        "published": entry.get("published", ""),
                        "summary": entry.get("summary", ""),
                        "category": category,
                    })

        return [e["url"] for e in self._rss_entries][:30]

    def parse_article(self, url: str) -> Optional[Article]:
        rss_data = next((e for e in self._rss_entries if e["url"] == url), {})

        soup = self.fetch(url)
        if not soup:
            return None

        title = rss_data.get("title", "")
        if not title:
            h1 = soup.find("h1")
            title = h1.get_text(strip=True) if h1 else "N/A"

        author_tag = (
            soup.find(class_=re.compile(r"author|byline|كاتب|مراسل", re.I))
            or soup.find("a", rel="author")
        )
        author = author_tag.get_text(strip=True) if author_tag else "Al Jazeera"

        published_at = rss_data.get("published", "N/A")
        if published_at == "N/A":
            time_tag = soup.find("time")
            if time_tag:
                published_at = time_tag.get("datetime", time_tag.get_text(strip=True))

        category = rss_data.get("category", "أخبار")

        content_selectors = [
            "div.wysiwyg p",
            "div[class*='article-body'] p",
            "div[class*='ArticleBody'] p",
            "div.article-p-wrapper p",
            "article p",
        ]
        content = ""
        for selector in content_selectors:
            blocks = soup.select(selector)
            if blocks:
                content = " ".join(
                    p.get_text(strip=True) for p in blocks if len(p.get_text(strip=True)) > 20
                )
                break

        if len(content) < 50:
            content = rss_data.get("summary", "")
            if len(content) < 50:
                return None

        return Article(
            title=title,
            author=author,
            published_at=published_at,
            category=category,
            content=content,
            source="AlJazeera",
            url=url,
            language="ar",
        )
