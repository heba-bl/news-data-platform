import re
import logging
from typing import List, Optional
from base_scraper import BaseScraper, Article

logger = logging.getLogger(__name__)

BASE_URL = "https://www.barlamane.com"


class BarlamaneScraper(BaseScraper):
    def __init__(self):
        super().__init__(source_name="Barlamane", base_url=BASE_URL, delay=2.0)

    def get_article_links(self) -> List[str]:
        links = set()
        pages_to_check = [
            f"{BASE_URL}/",
            f"{BASE_URL}/politique/",
            f"{BASE_URL}/economie/",
            f"{BASE_URL}/societe/",
            f"{BASE_URL}/sport/",
            f"{BASE_URL}/international/",
            f"{BASE_URL}/culture/",
        ]
        for page_url in pages_to_check:
            soup = self.fetch(page_url)
            if not soup:
                continue
            for a_tag in soup.select("h2 a[href], h3 a[href], .entry-title a[href], .post-title a[href]"):
                href = a_tag.get("href", "")
                if not href:
                    continue
                full_url = href if href.startswith("http") else BASE_URL + href
                if BASE_URL in full_url and full_url != BASE_URL + "/":
                    links.add(full_url)
        return list(links)[:30]

    def parse_article(self, url: str) -> Optional[Article]:
        soup = self.fetch(url)
        if not soup:
            return None

        title_tag = (
            soup.find("h1", class_=re.compile(r"entry-title|post-title|title", re.I))
            or soup.find("h1")
        )
        title = title_tag.get_text(strip=True) if title_tag else "N/A"

        author_tag = (
            soup.find(class_=re.compile(r"author|writer", re.I))
            or soup.find("a", rel="author")
        )
        author = author_tag.get_text(strip=True) if author_tag else "Barlamane"

        date_tag = (
            soup.find("time")
            or soup.find(class_=re.compile(r"date|published|entry-date", re.I))
        )
        published_at = (
            date_tag.get("datetime") or date_tag.get_text(strip=True)
            if date_tag else "N/A"
        )

        cat_tag = (
            soup.find("a", class_=re.compile(r"categ|cat-link|rubrique", re.I))
            or soup.find("span", class_=re.compile(r"cat|categ", re.I))
        )
        category = cat_tag.get_text(strip=True) if cat_tag else "General"

        content_tag = (
            soup.find("div", class_=re.compile(r"entry-content|post-content|article-content|the-content", re.I))
            or soup.find("div", class_=re.compile(r"content", re.I))
            or soup.find("article")
        )
        content = content_tag.get_text(separator=" ", strip=True) if content_tag else ""

        if not title or title == "N/A" or len(content) < 50:
            return None

        return Article(
            title=title,
            author=author,
            published_at=published_at,
            category=category,
            content=content,
            source="Barlamane",
            url=url,
            language="ar",
        )
