from datetime import datetime, timedelta
import logging
import subprocess
import sys

from airflow import DAG
from airflow.operators.python import PythonOperator
from airflow.operators.empty import EmptyOperator
from airflow.utils.dates import days_ago

logger = logging.getLogger(__name__)

DEFAULT_ARGS = {
    "owner": "data-engineering",
    "depends_on_past": False,
    "email_on_failure": False,
    "email_on_retry": False,
    "retries": 2,
    "retry_delay": timedelta(minutes=5),
}

SCRAPERS_PATH = "/opt/airflow/scrapers"


def scrape_hespress(**context):
    sys.path.insert(0, SCRAPERS_PATH)
    from hespress_scraper import HespressScraper
    from kafka_producer import send_batch
    scraper = HespressScraper()
    articles = scraper.scrape()
    logger.info(f"Hespress: {len(articles)} articles scraped")
    if articles:
        stats = send_batch(articles)
        context["task_instance"].xcom_push(key="hespress_stats", value=stats)
    return len(articles)


def scrape_akhbarona(**context):
    sys.path.insert(0, SCRAPERS_PATH)
    from akhbarona_scraper import AkhbaronaScraper
    from kafka_producer import send_batch
    scraper = AkhbaronaScraper()
    articles = scraper.scrape()
    logger.info(f"Akhbarona: {len(articles)} articles scraped")
    if articles:
        stats = send_batch(articles)
        context["task_instance"].xcom_push(key="akhbarona_stats", value=stats)
    return len(articles)


def scrape_bbc(**context):
    sys.path.insert(0, SCRAPERS_PATH)
    from bbc_scraper import BBCScraper
    from kafka_producer import send_batch
    scraper = BBCScraper()
    articles = scraper.scrape()
    logger.info(f"BBC: {len(articles)} articles scraped")
    if articles:
        stats = send_batch(articles)
        context["task_instance"].xcom_push(key="bbc_stats", value=stats)
    return len(articles)


def scrape_cnn(**context):
    sys.path.insert(0, SCRAPERS_PATH)
    from cnn_scraper import CNNScraper
    from kafka_producer import send_batch
    scraper = CNNScraper()
    articles = scraper.scrape()
    logger.info(f"CNN: {len(articles)} articles scraped")
    if articles:
        stats = send_batch(articles)
        context["task_instance"].xcom_push(key="cnn_stats", value=stats)
    return len(articles)


def scrape_reuters(**context):
    sys.path.insert(0, SCRAPERS_PATH)
    from reuters_scraper import ReutersScraper
    from kafka_producer import send_batch
    scraper = ReutersScraper()
    articles = scraper.scrape()
    logger.info(f"Reuters: {len(articles)} articles scraped")
    if articles:
        stats = send_batch(articles)
        context["task_instance"].xcom_push(key="reuters_stats", value=stats)
    return len(articles)


def scrape_lakom(**context):
    sys.path.insert(0, SCRAPERS_PATH)
    from lakom_scraper import LakomScraper
    from kafka_producer import send_batch
    scraper = LakomScraper()
    articles = scraper.scrape()
    logger.info(f"Lakom: {len(articles)} articles scraped")
    if articles:
        stats = send_batch(articles)
        context["task_instance"].xcom_push(key="lakom_stats", value=stats)
    return len(articles)


def scrape_barlamane(**context):
    sys.path.insert(0, SCRAPERS_PATH)
    from barlamane_scraper import BarlamaneScraper
    from kafka_producer import send_batch
    scraper = BarlamaneScraper()
    articles = scraper.scrape()
    logger.info(f"Barlamane: {len(articles)} articles scraped")
    if articles:
        stats = send_batch(articles)
        context["task_instance"].xcom_push(key="barlamane_stats", value=stats)
    return len(articles)


def scrape_aljazeera(**context):
    sys.path.insert(0, SCRAPERS_PATH)
    from aljazeera_scraper import AlJazeeraScraper
    from kafka_producer import send_batch
    scraper = AlJazeeraScraper()
    articles = scraper.scrape()
    logger.info(f"AlJazeera: {len(articles)} articles scraped")
    if articles:
        stats = send_batch(articles)
        context["task_instance"].xcom_push(key="aljazeera_stats", value=stats)
    return len(articles)


def log_scraping_summary(**context):
    ti = context["task_instance"]
    sources = ["hespress", "akhbarona", "lakom", "barlamane", "bbc", "cnn", "reuters", "aljazeera"]
    total_sent = 0
    for source in sources:
        stats = ti.xcom_pull(key=f"{source}_stats", task_ids=f"scrape_{source}") or {}
        sent = stats.get("sent", 0)
        total_sent += sent
        logger.info(f"  {source.upper()}: sent={sent}")
    logger.info(f"Total articles sent to Kafka: {total_sent}")
    return total_sent


with DAG(
    dag_id="scraping_batch",
    description="Hourly batch scraping from all news sources → Kafka",
    default_args=DEFAULT_ARGS,
    schedule_interval="0 * * * *",
    start_date=days_ago(1),
    catchup=False,
    tags=["scraping", "ingestion"],
) as dag:

    start = EmptyOperator(task_id="start")
    end = EmptyOperator(task_id="end")

    t_hespress = PythonOperator(task_id="scrape_hespress", python_callable=scrape_hespress)
    t_akhbarona = PythonOperator(task_id="scrape_akhbarona", python_callable=scrape_akhbarona)
    t_lakom = PythonOperator(task_id="scrape_lakom", python_callable=scrape_lakom)
    t_barlamane = PythonOperator(task_id="scrape_barlamane", python_callable=scrape_barlamane)
    t_bbc = PythonOperator(task_id="scrape_bbc", python_callable=scrape_bbc)
    t_cnn = PythonOperator(task_id="scrape_cnn", python_callable=scrape_cnn)
    t_reuters = PythonOperator(task_id="scrape_reuters", python_callable=scrape_reuters)
    t_aljazeera = PythonOperator(task_id="scrape_aljazeera", python_callable=scrape_aljazeera)

    t_summary = PythonOperator(task_id="log_summary", python_callable=log_scraping_summary)

    start >> [t_hespress, t_akhbarona, t_lakom, t_barlamane, t_bbc, t_cnn, t_reuters, t_aljazeera] >> t_summary >> end
