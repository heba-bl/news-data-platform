"""
Utility script to inject sample articles directly into Kafka
for testing the pipeline without running the actual scrapers.

Usage:
    docker compose run --rm scraper python /opt/airflow/scrapers/../samples/load_samples.py
  OR locally:
    python samples/load_samples.py
"""
import json
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "scrapers"))

from dotenv import load_dotenv
load_dotenv()

from kafka_producer import send_batch

SAMPLES_FILE = Path(__file__).parent / "sample_articles.json"


def main():
    with open(SAMPLES_FILE, "r", encoding="utf-8") as f:
        articles = json.load(f)

    print(f"Sending {len(articles)} sample articles to Kafka...")
    stats = send_batch(articles)
    print(f"Done: {stats}")


if __name__ == "__main__":
    main()
