import logging
import sys
from datetime import datetime, timedelta

from airflow import DAG
from airflow.operators.python import PythonOperator
from airflow.operators.empty import EmptyOperator
from airflow.providers.postgres.operators.postgres import PostgresOperator
from airflow.utils.dates import days_ago

logger = logging.getLogger(__name__)

DEFAULT_ARGS = {
    "owner": "data-engineering",
    "depends_on_past": False,
    "email_on_failure": False,
    "retries": 1,
    "retry_delay": timedelta(minutes=15),
}

WAREHOUSE_PATH = "/opt/airflow/warehouse"
INGESTION_PATH = "/opt/airflow/ingestion"


def load_articles_to_dw(**context):
    sys.path.insert(0, WAREHOUSE_PATH)
    sys.path.insert(0, INGESTION_PATH)
    from load_data import load_silver_to_dw
    load_silver_to_dw()
    logger.info("Silver → DWH articles loaded")


def load_aggregations_to_dw(**context):
    sys.path.insert(0, WAREHOUSE_PATH)
    sys.path.insert(0, INGESTION_PATH)
    from load_data import load_gold_aggregations
    load_gold_aggregations()
    logger.info("Gold → DWH aggregations loaded")


def log_pipeline_run(**context):
    sys.path.insert(0, WAREHOUSE_PATH)
    sys.path.insert(0, INGESTION_PATH)
    import psycopg2
    import os
    conn = psycopg2.connect(
        host=os.getenv("POSTGRES_HOST", "postgres"),
        port=os.getenv("POSTGRES_PORT", "5432"),
        dbname=os.getenv("POSTGRES_DB", "news_dw"),
        user=os.getenv("POSTGRES_USER", "newsadmin"),
        password=os.getenv("POSTGRES_PASSWORD", "newsadmin123"),
    )
    with conn.cursor() as cur:
        cur.execute(
            """INSERT INTO pipeline_runs (pipeline, started_at, finished_at, status)
               VALUES (%s, %s, %s, %s)""",
            ("warehouse_load", context["data_interval_start"], datetime.utcnow(), "success"),
        )
    conn.commit()
    conn.close()
    logger.info("Pipeline run logged to governance table")


REFRESH_STATS_SQL = """
-- Refresh pipeline stats view
SELECT
    COUNT(*) AS total_articles,
    COUNT(DISTINCT source_id) AS sources,
    MAX(inserted_at) AS last_inserted
FROM fact_articles;
"""


with DAG(
    dag_id="warehouse_load",
    description="Load processed data from MinIO → PostgreSQL DWH",
    default_args=DEFAULT_ARGS,
    schedule_interval="45 * * * *",
    start_date=days_ago(1),
    catchup=False,
    tags=["warehouse", "load"],
) as dag:

    start = EmptyOperator(task_id="start")
    end = EmptyOperator(task_id="end")

    t_load_articles = PythonOperator(
        task_id="load_articles",
        python_callable=load_articles_to_dw,
    )

    t_load_aggs = PythonOperator(
        task_id="load_aggregations",
        python_callable=load_aggregations_to_dw,
    )

    t_refresh_stats = PostgresOperator(
        task_id="refresh_stats",
        postgres_conn_id="postgres_news_dw",
        sql=REFRESH_STATS_SQL,
    )

    t_log_run = PythonOperator(
        task_id="log_pipeline_run",
        python_callable=log_pipeline_run,
    )

    start >> t_load_articles >> t_load_aggs >> t_refresh_stats >> t_log_run >> end
