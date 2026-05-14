import json
import logging
import os
from datetime import datetime
from typing import Dict, List

from kafka import KafkaProducer
from kafka.errors import KafkaError

logger = logging.getLogger(__name__)

KAFKA_BROKER = os.getenv("KAFKA_BROKER", "localhost:9092")
KAFKA_TOPIC = os.getenv("KAFKA_TOPIC", "news-articles")


def create_producer() -> KafkaProducer:
    return KafkaProducer(
        bootstrap_servers=[KAFKA_BROKER],
        value_serializer=lambda v: json.dumps(v, ensure_ascii=False).encode("utf-8"),
        key_serializer=lambda k: k.encode("utf-8") if k else None,
        acks="all",
        retries=3,
        max_block_ms=10000,
    )


def send_article(producer: KafkaProducer, article: Dict) -> bool:
    try:
        key = article.get("source", "unknown") + "_" + str(hash(article.get("url", "")))
        future = producer.send(KAFKA_TOPIC, key=key, value=article)
        record_metadata = future.get(timeout=10)
        logger.debug(
            f"Sent to Kafka: topic={record_metadata.topic} "
            f"partition={record_metadata.partition} offset={record_metadata.offset}"
        )
        return True
    except KafkaError as e:
        logger.error(f"Kafka send error: {e}")
        return False


def send_batch(articles: List[Dict]) -> Dict:
    producer = create_producer()
    stats = {"total": len(articles), "sent": 0, "failed": 0}

    for article in articles:
        if send_article(producer, article):
            stats["sent"] += 1
        else:
            stats["failed"] += 1

    producer.flush()
    producer.close()
    logger.info(f"Kafka batch done: {stats}")
    return stats
