import io
import json
import logging
import os
from datetime import datetime
from typing import Dict, List, Optional

import pyarrow as pa
import pyarrow.parquet as pq
from minio import Minio
from minio.error import S3Error

logger = logging.getLogger(__name__)

MINIO_ENDPOINT = os.getenv("MINIO_ENDPOINT", "localhost:9000")
MINIO_ACCESS_KEY = os.getenv("MINIO_ACCESS_KEY", "minioadmin")
MINIO_SECRET_KEY = os.getenv("MINIO_SECRET_KEY", "minioadmin123")
BUCKET_BRONZE = os.getenv("MINIO_BUCKET_BRONZE", "bronze")
BUCKET_SILVER = os.getenv("MINIO_BUCKET_SILVER", "silver")
BUCKET_GOLD = os.getenv("MINIO_BUCKET_GOLD", "gold")

ALL_BUCKETS = [BUCKET_BRONZE, BUCKET_SILVER, BUCKET_GOLD]


def get_client() -> Minio:
    return Minio(
        MINIO_ENDPOINT,
        access_key=MINIO_ACCESS_KEY,
        secret_key=MINIO_SECRET_KEY,
        secure=False,
    )


def ensure_buckets():
    client = get_client()
    for bucket in ALL_BUCKETS:
        if not client.bucket_exists(bucket):
            client.make_bucket(bucket)
            logger.info(f"Created bucket: {bucket}")


def _build_object_path(article: Dict, layer: str) -> str:
    now = datetime.utcnow()
    source = article.get("source", "unknown").lower().replace(" ", "_")
    date_path = now.strftime("%Y/%m/%d/%H")
    article_id = str(abs(hash(article.get("url", ""))))[:10]
    return f"{layer}/{source}/{date_path}/{article_id}.json"


def save_article_bronze(article: Dict) -> Optional[str]:
    client = get_client()
    ensure_buckets()
    object_path = _build_object_path(article, "raw")
    data = json.dumps(article, ensure_ascii=False).encode("utf-8")
    client.put_object(
        BUCKET_BRONZE,
        object_path,
        io.BytesIO(data),
        length=len(data),
        content_type="application/json",
    )
    logger.debug(f"Saved to Bronze: {BUCKET_BRONZE}/{object_path}")
    return object_path


def save_articles_bronze_batch(articles: List[Dict]) -> int:
    saved = 0
    for article in articles:
        try:
            save_article_bronze(article)
            saved += 1
        except S3Error as e:
            logger.error(f"MinIO error saving article: {e}")
    logger.info(f"Bronze: saved {saved}/{len(articles)} articles")
    return saved


def save_parquet_to_layer(df_records: List[Dict], bucket: str, object_path: str):
    client = get_client()
    ensure_buckets()
    import pandas as pd

    df = pd.DataFrame(df_records)
    table = pa.Table.from_pandas(df)
    buf = io.BytesIO()
    pq.write_table(table, buf)
    buf.seek(0)
    data = buf.read()
    client.put_object(
        bucket,
        object_path,
        io.BytesIO(data),
        length=len(data),
        content_type="application/octet-stream",
    )
    logger.info(f"Saved Parquet to {bucket}/{object_path} ({len(df_records)} rows)")


def list_objects(bucket: str, prefix: str = "") -> List[str]:
    client = get_client()
    objects = client.list_objects(bucket, prefix=prefix, recursive=True)
    return [obj.object_name for obj in objects]


def read_json_object(bucket: str, object_name: str) -> Optional[Dict]:
    client = get_client()
    try:
        response = client.get_object(bucket, object_name)
        data = json.loads(response.read().decode("utf-8"))
        response.close()
        return data
    except S3Error as e:
        logger.error(f"MinIO read error {bucket}/{object_name}: {e}")
        return None


def read_all_bronze(date_prefix: Optional[str] = None) -> List[Dict]:
    prefix = f"raw/{date_prefix}" if date_prefix else "raw/"
    object_names = list_objects(BUCKET_BRONZE, prefix=prefix)
    articles = []
    for name in object_names:
        article = read_json_object(BUCKET_BRONZE, name)
        if article:
            articles.append(article)
    logger.info(f"Read {len(articles)} articles from Bronze")
    return articles
