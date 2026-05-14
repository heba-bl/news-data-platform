import logging
import sys
from datetime import datetime, timedelta

from airflow import DAG
from airflow.operators.python import PythonOperator
from airflow.operators.empty import EmptyOperator
from airflow.utils.dates import days_ago

logger = logging.getLogger(__name__)

DEFAULT_ARGS = {
    "owner": "data-engineering",
    "depends_on_past": False,
    "email_on_failure": False,
    "retries": 1,
    "retry_delay": timedelta(minutes=10),
}

PROCESSING_PATH = "/opt/airflow/processing"
INGESTION_PATH = "/opt/airflow/ingestion"


def run_bronze_to_silver(**context):
    sys.path.insert(0, PROCESSING_PATH)
    sys.path.insert(0, INGESTION_PATH)
    from bronze_to_silver import process_bronze_to_silver
    cleaned = process_bronze_to_silver()
    count = len(cleaned) if cleaned else 0
    logger.info(f"Bronze → Silver: {count} articles processed")
    context["task_instance"].xcom_push(key="silver_count", value=count)
    return count


def run_quality_checks(**context):
    sys.path.insert(0, PROCESSING_PATH)
    sys.path.insert(0, INGESTION_PATH)
    from minio_client import read_all_bronze
    from data_quality import run_quality_checks, check_completeness

    articles = read_all_bronze()
    if not articles:
        logger.warning("No articles to check")
        return {}

    valid, report = run_quality_checks(articles)
    completeness = check_completeness(valid)

    summary = report.summary()
    logger.info(f"Quality check: {summary}")
    logger.info(f"Completeness: {completeness}")

    context["task_instance"].xcom_push(key="quality_report", value=summary)
    return summary


def run_silver_to_gold(**context):
    sys.path.insert(0, PROCESSING_PATH)
    sys.path.insert(0, INGESTION_PATH)
    from silver_to_gold import process_silver_to_gold
    result = process_silver_to_gold()
    logger.info("Silver → Gold aggregations complete")
    return "done"


def notify_completion(**context):
    ti = context["task_instance"]
    silver_count = ti.xcom_pull(key="silver_count", task_ids="bronze_to_silver") or 0
    quality = ti.xcom_pull(key="quality_report", task_ids="quality_checks") or {}
    logger.info("=" * 50)
    logger.info("TRANSFORMATION PIPELINE COMPLETE")
    logger.info(f"  Silver articles: {silver_count}")
    logger.info(f"  Quality pass rate: {quality.get('pass_rate', 'N/A')}%")
    logger.info("=" * 50)


with DAG(
    dag_id="transformation_pipeline",
    description="Bronze → Silver → Gold transformation pipeline",
    default_args=DEFAULT_ARGS,
    schedule_interval="30 * * * *",
    start_date=days_ago(1),
    catchup=False,
    tags=["transformation", "etl"],
) as dag:

    start = EmptyOperator(task_id="start")
    end = EmptyOperator(task_id="end")

    t_quality = PythonOperator(task_id="quality_checks", python_callable=run_quality_checks)
    t_bronze_silver = PythonOperator(task_id="bronze_to_silver", python_callable=run_bronze_to_silver)
    t_silver_gold = PythonOperator(task_id="silver_to_gold", python_callable=run_silver_to_gold)
    t_notify = PythonOperator(task_id="notify_completion", python_callable=notify_completion)

    start >> t_quality >> t_bronze_silver >> t_silver_gold >> t_notify >> end
