import logging
import os
import sys
import time
import schedule

from dotenv import load_dotenv

load_dotenv()

os.makedirs("/app/logs", exist_ok=True)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s - %(message)s",
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler("/app/logs/scraper.log", encoding="utf-8"),
    ],
)
logger = logging.getLogger(__name__)

from hespress_scraper import HespressScraper
from akhbarona_scraper import AkhbaronaScraper
from lakom_scraper import LakomScraper
from barlamane_scraper import BarlamaneScraper
from bbc_scraper import BBCScraper
from cnn_scraper import CNNScraper
from reuters_scraper import ReutersScraper
from aljazeera_scraper import AlJazeeraScraper
from kafka_producer import send_batch

SCRAPERS = [
    HespressScraper(),
    AkhbaronaScraper(),
    LakomScraper(),
    BarlamaneScraper(),
    BBCScraper(),
    CNNScraper(),
    ReutersScraper(),
    AlJazeeraScraper(),
]

INTERVAL_HOURS = int(os.getenv("SCRAPING_INTERVAL_HOURS", 1))


def run_all_scrapers():
    logger.info("═" * 60)
    logger.info("Starting scraping cycle")
    logger.info("═" * 60)
    all_articles = []

    for scraper in SCRAPERS:
        try:
            logger.info(f"Scraping source: {scraper.source_name}")
            articles = scraper.scrape()
            all_articles.extend(articles)
            logger.info(f"  → {len(articles)} articles from {scraper.source_name}")
        except Exception as e:
            logger.error(f"Scraper failed [{scraper.source_name}]: {e}", exc_info=True)

    logger.info(f"Total articles scraped: {len(all_articles)}")

    if all_articles:
        stats = send_batch(all_articles)
        logger.info(f"Kafka stats: {stats}")

    logger.info("Scraping cycle complete")
    return all_articles


if __name__ == "__main__":
    mode = os.getenv("SCRAPER_MODE", "scheduled")

    if mode == "once":
        run_all_scrapers()
    else:
        logger.info(f"Scheduled mode: every {INTERVAL_HOURS} hour(s)")
        run_all_scrapers()
        schedule.every(INTERVAL_HOURS).hours.do(run_all_scrapers)
        while True:
            schedule.run_pending()
            time.sleep(60)
