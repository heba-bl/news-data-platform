import json
import logging
import os
import sys
import time

from dotenv import load_dotenv
from kafka import KafkaConsumer
from kafka.errors import KafkaError

load_dotenv()

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s - %(message)s",
    handlers=[logging.StreamHandler(sys.stdout)],
)
logger = logging.getLogger(__name__)

KAFKA_BROKER = os.getenv("KAFKA_BROKER", "localhost:9092")
KAFKA_TOPIC = os.getenv("KAFKA_TOPIC", "news-articles")
KAFKA_GROUP_ID = os.getenv("KAFKA_GROUP_ID", "news-consumer-group")

sys.path.insert(0, os.path.join(os.path.dirname(__file__)))
from minio_client import save_article_bronze, ensure_buckets


def create_consumer() -> KafkaConsumer:
    return KafkaConsumer(
        KAFKA_TOPIC,
        bootstrap_servers=[KAFKA_BROKER],
        group_id=KAFKA_GROUP_ID,
        value_deserializer=lambda m: json.loads(m.decode("utf-8")),
        auto_offset_reset="earliest",
        enable_auto_commit=True,
        consumer_timeout_ms=5000,
    )


def consume_and_store():
    logger.info(f"Connecting to Kafka broker: {KAFKA_BROKER}")
    logger.info(f"Listening on topic: {KAFKA_TOPIC}")
    ensure_buckets()

    while True:
        try:
            consumer = create_consumer()
            logger.info("Kafka consumer ready")
            stats = {"received": 0, "stored": 0, "errors": 0}

            for message in consumer:
                article = message.value
                try:
                    path = save_article_bronze(article)
                    stats["stored"] += 1
                    stats["received"] += 1
                    logger.info(
                        f"[{article.get('source')}] Stored → Bronze: {path} | "
                        f"Title: {article.get('title', '')[:50]}"
                    )
                except Exception as e:
                    stats["errors"] += 1
                    stats["received"] += 1
                    logger.error(f"Failed to store article: {e}")

                if stats["received"] % 10 == 0:
                    logger.info(f"Consumer stats: {stats}")

            consumer.close()
            logger.info("Consumer idle — waiting for new messages...")
            time.sleep(10)

        except KafkaError as e:
            logger.error(f"Kafka error: {e} — retrying in 30s")
            time.sleep(30)
        except KeyboardInterrupt:
            logger.info("Consumer stopped by user")
            break


if __name__ == "__main__":
    consume_and_store()
