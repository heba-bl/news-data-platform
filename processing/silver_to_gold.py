import io
import logging
import os
import re
import sys
from collections import Counter
from datetime import datetime
from typing import List, Dict, Optional

import pandas as pd
import pyarrow as pa
import pyarrow.parquet as pq
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
    BUCKET_SILVER,
    BUCKET_GOLD,
    get_client,
    list_objects,
    save_parquet_to_layer,
    ensure_buckets,
)

STOPWORDS_EN = {
    "the", "a", "an", "and", "or", "but", "in", "on", "at", "to", "for",
    "of", "with", "by", "from", "is", "was", "are", "were", "be", "been",
    "has", "have", "had", "will", "would", "could", "should", "may", "might",
    "this", "that", "these", "those", "it", "its", "as", "said", "says",
    "not", "no", "also", "after", "before", "about", "up", "over",
}

STOPWORDS_AR = {
    "في", "من", "إلى", "على", "و", "أن", "ما", "هذا", "هذه", "كان", "كانت",
    "قد", "لا", "عن", "مع", "أو", "إن", "بعد", "قبل", "التي", "الذي",
    "لقد", "حيث", "كما", "منذ", "لم", "لن", "بل", "بين", "فإن", "ذلك",
}

ALL_STOPWORDS = STOPWORDS_EN | STOPWORDS_AR

SOURCE_COUNTRY_MAP = {
    "Hespress":   "Morocco",
    "Akhbarona":  "Morocco",
    "Lakom":      "Morocco",
    "Barlamane":  "Morocco",
    "BBC":        "United Kingdom",
    "CNN":        "United States",
    "Reuters":    "United Kingdom",
    "AlJazeera":  "Qatar",
}


def load_silver_data() -> pd.DataFrame:
    client = get_client()
    object_names = list_objects(BUCKET_SILVER, prefix="cleaned/")
    dfs = []
    for name in object_names:
        try:
            response = client.get_object(BUCKET_SILVER, name)
            buf = io.BytesIO(response.read())
            response.close()
            df = pq.read_table(buf).to_pandas()
            dfs.append(df)
        except Exception as e:
            logger.error(f"Error reading {name}: {e}")

    if not dfs:
        logger.warning("No Silver data found")
        return pd.DataFrame()

    combined = pd.concat(dfs, ignore_index=True)
    combined.drop_duplicates(subset=["url"], inplace=True)
    logger.info(f"Loaded {len(combined)} unique articles from Silver")
    return combined


def extract_keywords(text: str, top_n: int = 20) -> List[str]:
    if not text:
        return []
    words = re.findall(r"\b\w{4,}\b", text.lower())
    filtered = [w for w in words if w not in ALL_STOPWORDS and not w.isdigit()]
    counter = Counter(filtered)
    return [word for word, _ in counter.most_common(top_n)]


def build_articles_by_day(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()
    df["date"] = pd.to_datetime(df["published_at"], errors="coerce").dt.date
    result = (
        df.groupby("date")
        .agg(article_count=("url", "count"))
        .reset_index()
        .dropna(subset=["date"])
        .sort_values("date", ascending=False)
    )
    result["computed_at"] = datetime.utcnow().isoformat()
    return result


def build_articles_by_source(df: pd.DataFrame) -> pd.DataFrame:
    result = (
        df.groupby("source")
        .agg(
            article_count=("url", "count"),
            avg_word_count=("word_count", "mean"),
        )
        .reset_index()
        .sort_values("article_count", ascending=False)
    )
    result["avg_word_count"] = result["avg_word_count"].round(0).astype(int)
    result["computed_at"] = datetime.utcnow().isoformat()
    return result


def build_articles_by_category(df: pd.DataFrame) -> pd.DataFrame:
    result = (
        df.groupby(["category", "source"])
        .agg(article_count=("url", "count"))
        .reset_index()
        .sort_values("article_count", ascending=False)
    )
    result["computed_at"] = datetime.utcnow().isoformat()
    return result


def build_top_keywords(df: pd.DataFrame) -> pd.DataFrame:
    all_text = " ".join(df["content"].dropna().tolist())
    keywords = extract_keywords(all_text, top_n=100)
    words = re.findall(r"\b\w{4,}\b", all_text.lower())
    filtered = [w for w in words if w not in ALL_STOPWORDS and not w.isdigit()]
    counter = Counter(filtered)

    records = [
        {"keyword": word, "frequency": count, "computed_at": datetime.utcnow().isoformat()}
        for word, count in counter.most_common(100)
    ]
    return pd.DataFrame(records)


def build_articles_by_country(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()
    df["country"] = df["source"].map(SOURCE_COUNTRY_MAP).fillna("Unknown")
    result = (
        df.groupby("country")
        .agg(article_count=("url", "count"))
        .reset_index()
        .sort_values("article_count", ascending=False)
    )
    result["computed_at"] = datetime.utcnow().isoformat()
    return result


def build_language_distribution(df: pd.DataFrame) -> pd.DataFrame:
    result = (
        df.groupby("language")
        .agg(article_count=("url", "count"))
        .reset_index()
        .sort_values("article_count", ascending=False)
    )
    result["computed_at"] = datetime.utcnow().isoformat()
    return result


def process_silver_to_gold():
    logger.info("═" * 60)
    logger.info("Silver → Gold transformation started")
    ensure_buckets()

    df = load_silver_data()
    if df.empty:
        logger.warning("No Silver data to process")
        return

    now = datetime.utcnow()
    date_path = now.strftime("%Y/%m/%d")

    aggregations = {
        "articles_by_day": build_articles_by_day(df),
        "articles_by_source": build_articles_by_source(df),
        "articles_by_category": build_articles_by_category(df),
        "articles_by_country": build_articles_by_country(df),
        "top_keywords": build_top_keywords(df),
        "language_distribution": build_language_distribution(df),
    }

    for name, agg_df in aggregations.items():
        object_path = f"{name}/{date_path}/{name}.parquet"
        save_parquet_to_layer(agg_df.to_dict("records"), BUCKET_GOLD, object_path)
        logger.info(f"Gold: {name} → {len(agg_df)} rows saved")

    logger.info("Silver → Gold transformation complete")
    return aggregations


if __name__ == "__main__":
    process_silver_to_gold()
