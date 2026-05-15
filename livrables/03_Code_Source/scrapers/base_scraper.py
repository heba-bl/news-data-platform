import requests
import time
import logging
from abc import ABC, abstractmethod
from datetime import datetime
from typing import List, Dict, Optional
from bs4 import BeautifulSoup
from fake_useragent import UserAgent

logger = logging.getLogger(__name__)


class Article:
    def __init__(
        self,
        title: str,
        author: str,
        published_at: str,
        category: str,
        content: str,
        source: str,
        url: str,
        language: str = "unknown",
        scraped_at: Optional[str] = None,
    ):
        self.title = title
        self.author = author
        self.published_at = published_at
        self.category = category
        self.content = content
        self.source = source
        self.url = url
        self.language = language
        self.scraped_at = scraped_at or datetime.utcnow().isoformat()

    def to_dict(self) -> Dict:
        return {
            "title": self.title,
            "author": self.author,
            "published_at": self.published_at,
            "category": self.category,
            "content": self.content,
            "source": self.source,
            "url": self.url,
            "language": self.language,
            "scraped_at": self.scraped_at,
        }


class BaseScraper(ABC):
    def __init__(self, source_name: str, base_url: str, delay: float = 2.0):
        self.source_name = source_name
        self.base_url = base_url
        self.delay = delay
        self.session = requests.Session()
        try:
            ua = UserAgent()
            self.headers = {"User-Agent": ua.random}
        except Exception:
            self.headers = {
                "User-Agent": (
                    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                    "AppleWebKit/537.36 (KHTML, like Gecko) "
                    "Chrome/120.0.0.0 Safari/537.36"
                )
            }

    def fetch(self, url: str) -> Optional[BeautifulSoup]:
        try:
            response = self.session.get(url, headers=self.headers, timeout=30)
            response.raise_for_status()
            return BeautifulSoup(response.content, "lxml")
        except requests.RequestException as e:
            logger.error(f"[{self.source_name}] Failed to fetch {url}: {e}")
            return None

    def fetch_text(self, url: str) -> Optional[str]:
        try:
            response = self.session.get(url, headers=self.headers, timeout=30)
            response.raise_for_status()
            return response.text
        except requests.RequestException as e:
            logger.error(f"[{self.source_name}] Failed to fetch {url}: {e}")
            return None

    @abstractmethod
    def get_article_links(self) -> List[str]:
        pass

    @abstractmethod
    def parse_article(self, url: str) -> Optional[Article]:
        pass

    def scrape(self) -> List[Dict]:
        articles = []
        links = self.get_article_links()
        logger.info(f"[{self.source_name}] Found {len(links)} article links")
        for url in links:
            article = self.parse_article(url)
            if article:
                articles.append(article.to_dict())
                logger.info(f"[{self.source_name}] Scraped: {article.title[:60]}")
            time.sleep(self.delay)
        return articles
