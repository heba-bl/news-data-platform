import io
import logging
import os
import sys
from datetime import datetime
from typing import Dict, List, Optional

import pandas as pd
import pyarrow.parquet as pq
import psycopg2
from psycopg2.extras import execute_values, Json
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

from minio_client import BUCKET_SILVER, BUCKET_GOLD, get_client as get_minio, list_objects

PG_HOST = os.getenv("POSTGRES_HOST", "localhost")
PG_PORT = os.getenv("POSTGRES_PORT", "5432")
PG_DB = os.getenv("POSTGRES_DB", "news_dw")
PG_USER = os.getenv("POSTGRES_USER", "newsadmin")
PG_PASSWORD = os.getenv("POSTGRES_PASSWORD", "newsadmin123")


def get_pg_conn():
    return psycopg2.connect(
        host=PG_HOST, port=PG_PORT, dbname=PG_DB,
        user=PG_USER, password=PG_PASSWORD
    )


def upsert_dim_date(conn, date_val: datetime.date) -> Optional[int]:
    if not date_val:
        return None
    with conn.cursor() as cur:
        cur.execute(
            """
            INSERT INTO dim_date (full_date, day, month, year, quarter, day_of_week, week_of_year)
            VALUES (%s, %s, %s, %s, %s, %s, %s)
            ON CONFLICT (full_date) DO NOTHING
            RETURNING date_id
            """,
            (
                date_val,
                date_val.day,
                date_val.month,
                date_val.year,
                (date_val.month - 1) // 3 + 1,
                date_val.weekday(),
                date_val.isocalendar()[1],
            ),
        )
        row = cur.fetchone()
        if row:
            return row[0]
        cur.execute("SELECT date_id FROM dim_date WHERE full_date = %s", (date_val,))
        return cur.fetchone()[0]


def upsert_dim_category(conn, category: str) -> int:
    with conn.cursor() as cur:
        cur.execute(
            "INSERT INTO dim_category (category_name) VALUES (%s) ON CONFLICT (category_name) DO NOTHING RETURNING category_id",
            (category or "General",),
        )
        row = cur.fetchone()
        if row:
            return row[0]
        cur.execute("SELECT category_id FROM dim_category WHERE category_name = %s", (category,))
        return cur.fetchone()[0]


def get_source_id(conn, source_name: str) -> Optional[int]:
    with conn.cursor() as cur:
        cur.execute("SELECT source_id FROM dim_source WHERE source_name = %s", (source_name,))
        row = cur.fetchone()
        return row[0] if row else None


def load_silver_to_dw():
    logger.info("Loading Silver data → PostgreSQL DWH")
    minio = get_minio()
    object_names = list_objects(BUCKET_SILVER, prefix="cleaned/")

    if not object_names:
        logger.warning("No Silver objects found")
        return

    dfs = []
    for name in object_names:
        try:
            response = minio.get_object(BUCKET_SILVER, name)
            buf = io.BytesIO(response.read())
            response.close()
            dfs.append(pq.read_table(buf).to_pandas())
        except Exception as e:
            logger.error(f"Error reading {name}: {e}")

    if not dfs:
        return

    df = pd.concat(dfs, ignore_index=True).drop_duplicates(subset=["url"])
    logger.info(f"Loaded {len(df)} articles from Silver")

    conn = get_pg_conn()
    inserted = 0
    skipped = 0

    try:
        for _, row in df.iterrows():
            try:
                published = None
                if row.get("published_at"):
                    try:
                        published = pd.to_datetime(row["published_at"])
                    except Exception:
                        pass

                date_id = upsert_dim_date(conn, published.date() if published else None)
                source_id = get_source_id(conn, row.get("source", ""))
                category_id = upsert_dim_category(conn, row.get("category", "General"))

                with conn.cursor() as cur:
                    cur.execute(
                        """
                        INSERT INTO fact_articles
                            (title, author, published_at, date_id, source_id, category_id,
                             content, url, language, word_count, scraped_at, processed_at)
                        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                        ON CONFLICT (url) DO NOTHING
                        """,
                        (
                            row.get("title"),
                            row.get("author"),
                            published,
                            date_id,
                            source_id,
                            category_id,
                            row.get("content"),
                            row.get("url"),
                            row.get("language"),
                            int(row.get("word_count", 0)),
                            row.get("scraped_at"),
                            row.get("processed_at"),
                        ),
                    )
                    inserted += cur.rowcount
                conn.commit()
            except Exception as e:
                conn.rollback()
                skipped += 1
                logger.warning(f"Skipped article: {e}")

        logger.info(f"DWH load complete: inserted={inserted}, skipped={skipped}")

    finally:
        conn.close()


def load_gold_aggregations():
    logger.info("Loading Gold aggregations → PostgreSQL DWH")
    minio = get_minio()
    conn = get_pg_conn()

    gold_tables = {
        "articles_by_day": ("agg_articles_by_day", load_articles_by_day),
        "articles_by_source": ("agg_articles_by_source", load_articles_by_source),
        "articles_by_category": ("agg_articles_by_category", load_articles_by_category),
        "top_keywords": ("agg_top_keywords", load_top_keywords),
        "language_distribution": ("agg_language_distribution", load_language_dist),
    }

    for prefix, (table, loader_fn) in gold_tables.items():
        objects = list_objects(BUCKET_GOLD, prefix=f"{prefix}/")
        if not objects:
            continue
        latest = sorted(objects)[-1]
        try:
            response = minio.get_object(BUCKET_GOLD, latest)
            buf = io.BytesIO(response.read())
            response.close()
            df = pq.read_table(buf).to_pandas()
            loader_fn(conn, df)
        except Exception as e:
            logger.error(f"Error loading {prefix}: {e}")

    conn.close()


def load_articles_by_day(conn, df: pd.DataFrame):
    with conn.cursor() as cur:
        for _, row in df.iterrows():
            cur.execute(
                """INSERT INTO agg_articles_by_day (date, article_count, computed_at)
                   VALUES (%s, %s, NOW())
                   ON CONFLICT (date) DO UPDATE SET article_count = EXCLUDED.article_count, computed_at = NOW()""",
                (row.get("date"), int(row.get("article_count", 0))),
            )
    conn.commit()


def load_articles_by_source(conn, df: pd.DataFrame):
    with conn.cursor() as cur:
        for _, row in df.iterrows():
            cur.execute(
                """INSERT INTO agg_articles_by_source (source_name, article_count, avg_word_count, computed_at)
                   VALUES (%s, %s, %s, NOW())
                   ON CONFLICT (source_name) DO UPDATE SET article_count = EXCLUDED.article_count, avg_word_count = EXCLUDED.avg_word_count, computed_at = NOW()""",
                (row.get("source"), int(row.get("article_count", 0)), int(row.get("avg_word_count", 0))),
            )
    conn.commit()


def load_articles_by_category(conn, df: pd.DataFrame):
    with conn.cursor() as cur:
        for _, row in df.iterrows():
            cur.execute(
                """INSERT INTO agg_articles_by_category (category_name, source_name, article_count, computed_at)
                   VALUES (%s, %s, %s, NOW())
                   ON CONFLICT (category_name, source_name) DO UPDATE SET article_count = EXCLUDED.article_count, computed_at = NOW()""",
                (row.get("category"), row.get("source"), int(row.get("article_count", 0))),
            )
    conn.commit()


def load_top_keywords(conn, df: pd.DataFrame):
    with conn.cursor() as cur:
        for _, row in df.iterrows():
            cur.execute(
                """INSERT INTO agg_top_keywords (keyword, frequency, computed_at)
                   VALUES (%s, %s, NOW())
                   ON CONFLICT (keyword) DO UPDATE SET frequency = EXCLUDED.frequency, computed_at = NOW()""",
                (row.get("keyword"), int(row.get("frequency", 0))),
            )
    conn.commit()


def load_language_dist(conn, df: pd.DataFrame):
    with conn.cursor() as cur:
        for _, row in df.iterrows():
            cur.execute(
                """INSERT INTO agg_language_distribution (language, article_count, computed_at)
                   VALUES (%s, %s, NOW())
                   ON CONFLICT (language) DO UPDATE SET article_count = EXCLUDED.article_count, computed_at = NOW()""",
                (row.get("language"), int(row.get("article_count", 0))),
            )
    conn.commit()


if __name__ == "__main__":
    load_silver_to_dw()
    load_gold_aggregations()
