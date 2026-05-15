# Schéma d'Architecture — Plateforme News Data

## Flux de Données Complet

```
╔══════════════════════════════════════════════════════════════════════════════════╗
║                      SOURCES DE DONNÉES — 8 sources Web                         ║
║                                                                                  ║
║  ┌───────┐ ┌─────┐ ┌────────┐ ┌──────────┐ ┌──────────┐ ┌──────────┐          ║
║  │  BBC  │ │ CNN │ │Reuters │ │AlJazeera │ │ Hespress │ │Akhbarona │          ║
║  │(UK/EN)│ │US/EN│ │(UK/EN) │ │ (QA/AR)  │ │ (MA/AR)  │ │ (MA/AR)  │          ║
║  └───┬───┘ └──┬──┘ └───┬────┘ └────┬─────┘ └────┬─────┘ └────┬─────┘          ║
║               ┌──────────┐  ┌───────────┐                                       ║
║               │  Lakom   │  │ Barlamane │                                       ║
║               │ (MA/AR)  │  │ (MA/AR)   │                                       ║
║               └────┬─────┘  └─────┬─────┘                                       ║
╚════════════════════╪══════════════╪═══════════════════════════════════════════════╝
                     └──────┬───────┘
                             │
         └───────────────────┴──────────────────────────┘
                                  │
                    Python + BeautifulSoup (Scraping)
                                  │
╔═════════════════════════════════▼════════════════════════════════════════════════╗
║                          COUCHE INGESTION                                        ║
║                                                                                  ║
║   ┌─────────────────────────────────────────────────────────────────────────┐   ║
║   │                    Apache Kafka                                          │   ║
║   │   Topic: news-articles                                                   │   ║
║   │   Partitions: 3  │  Retention: 7 jours  │  Format: JSON                │   ║
║   │                                                                          │   ║
║   │   Producer ──▶ [P0][P1][P2] ──▶ Consumer                               │   ║
║   └─────────────────────────────────────────────────────────────────────────┘   ║
║                                                                                  ║
║   ┌─────────────────────────────────────────────────────────────────────────┐   ║
║   │                   Apache Airflow                                         │   ║
║   │   DAG 1: scraping_batch      (schedule: @hourly)                        │   ║
║   │   DAG 2: transformation_pipeline (schedule: @daily)                     │   ║
║   │   DAG 3: warehouse_load      (schedule: @daily)                         │   ║
║   └─────────────────────────────────────────────────────────────────────────┘   ║
╚══════════════════════════════════╪═══════════════════════════════════════════════╝
                                   │
╔══════════════════════════════════▼════════════════════════════════════════════════╗
║                    DATA LAKE — Architecture Médaillon (MinIO)                     ║
║                                                                                   ║
║  ┌─────────────────┐     ETL      ┌─────────────────┐     ETL    ┌────────────┐  ║
║  │   BRONZE        │ ──────────▶  │    SILVER        │ ────────▶ │    GOLD    │  ║
║  │                 │              │                  │           │            │  ║
║  │ - Format: JSON  │              │ - Format: Parquet│           │ - Parquet  │  ║
║  │ - Brut/Raw      │              │ - HTML nettoyé   │           │ - Agrégats │  ║
║  │ - 900 fichiers  │              │ - Langue détect. │           │ - 20 files │  ║
║  │ - Historique    │              │ - Dédupliqué     │           │ - Optimisé │  ║
║  │   complet       │              │ - 13 fichiers    │           │   queries  │  ║
║  └─────────────────┘              └─────────────────┘            └────────────┘  ║
╚══════════════════════════════════════════════╪════════════════════════════════════╝
                                               │
╔══════════════════════════════════════════════▼════════════════════════════════════╗
║                    DATA WAREHOUSE — PostgreSQL (Modèle Étoile)                    ║
║                                                                                   ║
║          ┌────────────┐                                                           ║
║          │  dim_date  │                                                           ║
║          │ date_id PK │                                                           ║
║          │ full_date  │                                                           ║
║          │ day/month  │                                                           ║
║          │ year/qtr   │                                                           ║
║          └─────┬──────┘                                                           ║
║                │                                                                  ║
║  ┌─────────────┼─────────────────────────────┐                                   ║
║  │             │                             │                                   ║
║  │      ┌──────▼──────────────┐              │                                   ║
║  │      │   fact_articles     │              │                                   ║
║  │      │   article_id PK     │              │                                   ║
║  │      │   title             │              │                                   ║
║  │      │   author            │◄─────────────┘                                   ║
║  │      │   published_at      │                                                   ║
║  │      │   source_id FK ─────┼──▶ dim_source                                   ║
║  │      │   category_id FK ───┼──▶ dim_category                                 ║
║  │      └─────────────────────┘                                                   ║
║  │                                                                                ║
║  │  ┌──────────────────────┐      ┌──────────────────────┐                       ║
║  │  │     dim_source       │      │     dim_category      │                       ║
║  │  │  source_id PK        │      │  category_id PK       │                       ║
║  │  │  name                │      │  name                 │                       ║
║  │  │  country             │      └──────────────────────┘                       ║
║  │  └──────────────────────┘                                                       ║
║  │                                                                                ║
║  │  TABLES AGRÉGÉES (Gold Layer Matérialisé) :                                   ║
║  │  ┌──────────────────────┐  ┌──────────────────────┐                           ║
║  │  │ agg_articles_by_src  │  │  agg_articles_by_day │                           ║
║  │  │ agg_articles_by_ctry │  │  agg_articles_by_cat │                           ║
║  │  │ agg_top_keywords     │  │  agg_language_distrib│                           ║
║  │  └──────────────────────┘  └──────────────────────┘                           ║
║  │                                                                                ║
║  │  TABLES GOUVERNANCE :                                                          ║
║  │  ┌──────────────────────┐  ┌──────────────────────┐                           ║
║  │  │   pipeline_runs      │  │  data_quality_log    │                           ║
║  │  └──────────────────────┘  └──────────────────────┘                           ║
╚═══════════════════════════════════════════════╪════════════════════════════════════╝
                                                │
╔═══════════════════════════════════════════════▼════════════════════════════════════╗
║                    COUCHE VISUALISATION & MONITORING                               ║
║                                                                                    ║
║  ┌────────────────────────────┐    ┌────────────────────────────┐                ║
║  │         GRAFANA            │    │         METABASE            │                ║
║  │  :3001                     │    │  :3000                      │                ║
║  │  - 13 panels analytiques   │    │  - BI self-service          │                ║
║  │  - Total articles          │    │  - Exploration libre        │                ║
║  │  - Articles/source         │    │  - Graphiques avancés       │                ║
║  │  - Articles/pays           │    │  - Questions SQL            │                ║
║  │  - Tendances temporelles   │    │  - Dashboards partagés      │                ║
║  │  - Top mots-clés           │    └────────────────────────────┘                ║
║  │  - Qualité + Pipeline      │                                                   ║
║  └────────────────────────────┘    ┌────────────────────────────┐                ║
║                                    │       PROMETHEUS           │                ║
║                                    │  :9090                      │                ║
║                                    │  - Métriques système        │                ║
║                                    │  - CPU, RAM, réseau         │                ║
║                                    │  - Kafka lag                │                ║
║                                    │  - Scraper health           │                ║
║                                    │  - Pipeline duration        │                ║
║                                    └────────────────────────────┘                ║
╚════════════════════════════════════════════════════════════════════════════════════╝
```

---

## Infrastructure Docker Compose

```
news-net (réseau interne Docker)
│
├── zookeeper       :2181  ──▶  coordination Kafka
├── kafka           :9092  ──▶  broker messages
├── kafka-ui        :8090  ──▶  interface web Kafka
│
├── minio           :9000  ──▶  object storage (API S3)
│                   :9200  ──▶  console web MinIO
├── minio-init             ──▶  initialisation buckets bronze/silver/gold
│
├── postgres        :5432  ──▶  data warehouse
│
├── scraper                ──▶  collecte articles (8 sources, toutes les heures)
├── consumer               ──▶  Kafka → MinIO Bronze
├── processor              ──▶  Bronze → Silver → Gold (ETL)
├── warehouse-loader       ──▶  Gold → PostgreSQL
│
├── airflow-webserver :8080 ──▶  UI orchestration
├── airflow-scheduler       ──▶  planificateur DAGs
│
├── metabase        :3000  ──▶  BI analytics
├── prometheus      :9090  ──▶  collecte métriques
└── grafana         :3001  ──▶  dashboards visuels
```

---

## Flux de Données Détaillé

```
1. SCRAPING (toutes les heures)
   Sites web ──[BeautifulSoup]──▶ Articles JSON ──[KafkaProducer]──▶ Topic: news-articles

2. CONSOMMATION STREAMING
   Topic: news-articles ──[KafkaConsumer]──▶ MinIO Bronze/raw/YYYY/MM/DD/*.json

3. TRANSFORMATION BATCH (quotidien)
   Bronze JSON ──[pandas/ETL]──▶ Nettoyage + Langue + Dédup ──▶ Silver Parquet
   Silver Parquet ──[aggregation]──▶ Métriques + Keywords ──▶ Gold Parquet

4. CHARGEMENT DWH (quotidien)
   Silver Parquet ──[warehouse_load]──▶ fact_articles + dims + aggs ──▶ PostgreSQL

5. VISUALISATION (temps réel)
   PostgreSQL ──[SQL queries]──▶ Grafana Dashboards (refresh: 1 min)
```

---

## Qualité et Gouvernance

```
┌─────────────────────────────────────────────────────────┐
│              PIPELINE DE QUALITÉ                         │
│                                                          │
│  Article ──▶ check_completude ──▶ check_validite        │
│              (titre, date,         (URL, format,        │
│               source)              longueur)            │
│                    │                    │               │
│                    ▼                    ▼               │
│              check_coherence ──▶ QualityReport          │
│              (langue/source)        │                   │
│                                     ▼                   │
│                            data_quality_log (PostgreSQL) │
└─────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────┐
│              DATA LINEAGE                                │
│                                                          │
│  [EXTERNAL] sources web                                  │
│       └──[kafka_consumer]──▶ [BRONZE] raw_articles      │
│            └──[bronze_to_silver]──▶ [SILVER] cleaned    │
│                 └──[silver_to_gold]──▶ [GOLD] aggregats │
│                      └──[warehouse_load]──▶ [DWH] facts │
└─────────────────────────────────────────────────────────┘
