import io
import logging
import os
import re
import sys
from datetime import datetime
from typing import Dict, List, Optional

import pandas as pd
import pyarrow as pa
import pyarrow.parquet as pq
from bs4 import BeautifulSoup
from dotenv import load_dotenv

load_dotenv()

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s - %(message)s",
    handlers=[logging.StreamHandler(sys.stdout)],
)
logger = logging.getLogger(__name__)

_base = os.path.dirname(os.path.abspath(__file__))
for _p in [_base, os.path.join(_base, "..", "ingestion"), "/opt/airflow/ingestion"]:
    if os.path.exists(os.path.join(_p, "minio_client.py")):
        sys.path.insert(0, os.path.abspath(_p))
        break

from minio_client import (
    BUCKET_BRONZE,
    BUCKET_SILVER,
    get_client,
    list_objects,
    read_all_bronze,
    save_parquet_to_layer,
    ensure_buckets,
)
from data_quality import run_quality_checks


def remove_html(text: str) -> str:
    if not text:
        return ""
    soup = BeautifulSoup(text, "lxml")
    return soup.get_text(separator=" ", strip=True)


def normalize_text(text: str) -> str:
    if not text:
        return ""
    text = re.sub(r"\s+", " ", text)
    text = re.sub(r"[^\w\s\u0600-\u06FF\u0750-\u077F.,!?;:()\-\"\'«»\n]", " ", text)
    text = text.strip()
    return text


def detect_language(text: str) -> str:
    if not text or len(text) < 20:
        return "unknown"
    try:
        from langdetect import detect, LangDetectException
        return detect(text[:500])
    except Exception:
        arabic_chars = len(re.findall(r"[\u0600-\u06FF]", text))
        if arabic_chars / max(len(text), 1) > 0.2:
            return "ar"
        return "unknown"


def normalize_date(date_str: str) -> str:
    if not date_str or date_str in ("N/A", "null", ""):
        return None
    formats = [
        "%Y-%m-%dT%H:%M:%S%z",
        "%Y-%m-%dT%H:%M:%SZ",
        "%Y-%m-%dT%H:%M:%S",
        "%a, %d %b %Y %H:%M:%S %z",
        "%a, %d %b %Y %H:%M:%S GMT",
        "%d/%m/%Y",
        "%Y-%m-%d",
    ]
    for fmt in formats:
        try:
            dt = datetime.strptime(date_str.strip(), fmt)
            return dt.strftime("%Y-%m-%d %H:%M:%S")
        except (ValueError, AttributeError):
            continue
    return date_str


def clean_article(article: Dict) -> Dict:
    title = remove_html(article.get("title", ""))
    title = normalize_text(title)

    content = remove_html(article.get("content", ""))
    content = normalize_text(content)

    author = remove_html(article.get("author", ""))
    author = normalize_text(author) or article.get("source", "Unknown")

    category = normalize_text(article.get("category", "General"))

    language = article.get("language", "unknown")
    if language in ("unknown", "", None):
        language = detect_language(content or title)

    published_at = normalize_date(article.get("published_at", ""))

    return {
        "title": title,
        "author": author,
        "published_at": published_at,
        "category": category,
        "content": content,
        "source": article.get("source", "unknown"),
        "url": article.get("url", ""),
        "language": language,
        "scraped_at": article.get("scraped_at", ""),
        "processed_at": datetime.utcnow().isoformat(),
        "word_count": len(content.split()) if content else 0,
    }


def process_bronze_to_silver(date_prefix: Optional[str] = None):
    logger.info("═" * 60)
    logger.info("Bronze → Silver transformation started")
    ensure_buckets()

    raw_articles = read_all_bronze(date_prefix)
    if not raw_articles:
        logger.warning("No articles found in Bronze layer")
        return

    logger.info(f"Loaded {len(raw_articles)} raw articles from Bronze")

    valid_articles, quality_report = run_quality_checks(raw_articles)
    logger.info(f"Quality report: {quality_report.summary()}")

    cleaned = [clean_article(a) for a in valid_articles]
    logger.info(f"Cleaned {len(cleaned)} articles")

    now = datetime.utcnow()
    object_path = f"cleaned/{now.strftime('%Y/%m/%d/%H')}/articles.parquet"
    save_parquet_to_layer(cleaned, BUCKET_SILVER, object_path)

    logger.info(f"Silver layer updated: {BUCKET_SILVER}/{object_path}")
    logger.info("Bronze → Silver transformation complete")
    return cleaned


if __name__ == "__main__":
    process_bronze_to_silver()
