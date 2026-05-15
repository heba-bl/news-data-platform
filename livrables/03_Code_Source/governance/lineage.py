import json
import os
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional

LINEAGE_FILE = Path(os.getenv("LOG_DIR", "/app/logs")) / "lineage.jsonl"
LINEAGE_FILE.parent.mkdir(parents=True, exist_ok=True)


class DatasetLineage:
    def __init__(
        self,
        dataset_name: str,
        layer: str,
        source_datasets: Optional[List[str]] = None,
        pipeline: str = "",
        location: str = "",
        format: str = "",
        schema: Optional[Dict] = None,
    ):
        self.dataset_name = dataset_name
        self.layer = layer
        self.source_datasets = source_datasets or []
        self.pipeline = pipeline
        self.location = location
        self.format = format
        self.schema = schema or {}
        self.created_at = datetime.utcnow().isoformat()
        self.updated_at = self.created_at

    def to_dict(self) -> Dict:
        return {
            "dataset_name": self.dataset_name,
            "layer": self.layer,
            "source_datasets": self.source_datasets,
            "pipeline": self.pipeline,
            "location": self.location,
            "format": self.format,
            "schema": self.schema,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
        }

    def record(self):
        record = {
            "timestamp": datetime.utcnow().isoformat(),
            **self.to_dict(),
        }
        with open(LINEAGE_FILE, "a", encoding="utf-8") as f:
            f.write(json.dumps(record, ensure_ascii=False) + "\n")


PLATFORM_LINEAGE = [
    DatasetLineage(
        dataset_name="raw_articles_bronze",
        layer="bronze",
        source_datasets=["hespress", "akhbarona", "bbc", "cnn", "reuters"],
        pipeline="kafka_consumer",
        location="minio://bronze/raw/",
        format="JSON",
        schema={
            "title": "string",
            "author": "string",
            "published_at": "string",
            "category": "string",
            "content": "string",
            "source": "string",
            "url": "string",
            "language": "string",
            "scraped_at": "string",
        },
    ),
    DatasetLineage(
        dataset_name="cleaned_articles_silver",
        layer="silver",
        source_datasets=["raw_articles_bronze"],
        pipeline="bronze_to_silver",
        location="minio://silver/cleaned/",
        format="Parquet",
        schema={
            "title": "string",
            "author": "string",
            "published_at": "timestamp",
            "category": "string",
            "content": "string",
            "source": "string",
            "url": "string",
            "language": "string",
            "word_count": "int",
            "processed_at": "timestamp",
        },
    ),
    DatasetLineage(
        dataset_name="articles_by_day_gold",
        layer="gold",
        source_datasets=["cleaned_articles_silver"],
        pipeline="silver_to_gold",
        location="minio://gold/articles_by_day/",
        format="Parquet",
        schema={"date": "date", "article_count": "int"},
    ),
    DatasetLineage(
        dataset_name="articles_by_source_gold",
        layer="gold",
        source_datasets=["cleaned_articles_silver"],
        pipeline="silver_to_gold",
        location="minio://gold/articles_by_source/",
        format="Parquet",
        schema={"source": "string", "article_count": "int", "avg_word_count": "int"},
    ),
    DatasetLineage(
        dataset_name="top_keywords_gold",
        layer="gold",
        source_datasets=["cleaned_articles_silver"],
        pipeline="silver_to_gold",
        location="minio://gold/top_keywords/",
        format="Parquet",
        schema={"keyword": "string", "frequency": "int"},
    ),
    DatasetLineage(
        dataset_name="fact_articles_dw",
        layer="warehouse",
        source_datasets=["cleaned_articles_silver"],
        pipeline="warehouse_load",
        location="postgresql://news_dw/fact_articles",
        format="PostgreSQL",
        schema={
            "article_id": "int",
            "title": "text",
            "published_at": "timestamp",
            "source_id": "int",
            "category_id": "int",
            "url": "text",
        },
    ),
]


def record_all_lineage():
    for dataset in PLATFORM_LINEAGE:
        dataset.record()


def get_lineage_catalog() -> List[Dict]:
    return [d.to_dict() for d in PLATFORM_LINEAGE]


def print_lineage_graph():
    print("\n═══ DATA LINEAGE GRAPH ═══")
    for d in PLATFORM_LINEAGE:
        sources = " + ".join(d.source_datasets) if d.source_datasets else "EXTERNAL"
        print(f"  [{d.layer.upper()}] {sources} ──[{d.pipeline}]──▶ {d.dataset_name}")
    print("══════════════════════════\n")


if __name__ == "__main__":
    print_lineage_graph()
    record_all_lineage()
