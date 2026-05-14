# News Data Platform — Architecture Big Data Distribuée

Plateforme complète de collecte, stockage, transformation et visualisation d'articles de presse.

## Architecture

```
[Hespress | Akhbarona | BBC | CNN | Reuters]
         ↓ Python Scrapers
    [Apache Kafka]  ← Streaming Events
         ↓ Kafka Consumer
  [MinIO — Data Lake]
    ├── Bronze (JSON brut)
    ├── Silver (Parquet nettoyé)
    └── Gold  (Parquet agrégé)
         ↓ ETL Pipeline
  [PostgreSQL — Data Warehouse]
    ├── fact_articles
    ├── dim_source / dim_category / dim_date
    └── agg_* (agrégations Gold)
         ↓
  [Metabase / Grafana — Dashboards]

  [Apache Airflow] → Orchestration de tous les pipelines
  [Prometheus + Grafana] → Monitoring
```

## Prérequis

- Docker Desktop ≥ 24.x
- Docker Compose ≥ 2.x
- RAM disponible : 8 Go minimum recommandé

## Installation et Démarrage

### 1. Cloner et configurer

```bash
git clone <repo-url>
cd news-data-platform
cp .env .env.local   # Modifier les mots de passe si nécessaire
```

### 2. Démarrer tous les services

```bash
docker compose up -d --build
```

### 3. Vérifier l'état des services

```bash
docker compose ps
```

### 4. Initialiser Airflow (première fois)

```bash
docker compose run --rm airflow-init
```

## Accès aux interfaces

| Service         | URL                        | Credentials         |
|----------------|---------------------------|---------------------|
| Airflow         | http://localhost:8080      | admin / admin123    |
| MinIO Console   | http://localhost:9001      | minioadmin / minioadmin123 |
| Kafka UI        | http://localhost:8090      | —                   |
| Metabase        | http://localhost:3000      | (setup initial)     |
| Grafana         | http://localhost:3001      | admin / admin123    |
| Prometheus      | http://localhost:9090      | —                   |
| PostgreSQL      | localhost:5432             | newsadmin / newsadmin123 |

## Structure du Projet

```
news-data-platform/
├── .env                          # Variables d'environnement
├── docker-compose.yml            # Déploiement complet
├── README.md
│
├── scrapers/                     # Collecte de données
│   ├── Dockerfile
│   ├── requirements.txt
│   ├── base_scraper.py           # Classe de base
│   ├── hespress_scraper.py
│   ├── akhbarona_scraper.py
│   ├── bbc_scraper.py
│   ├── cnn_scraper.py
│   ├── reuters_scraper.py
│   ├── kafka_producer.py         # Envoi vers Kafka
│   └── run_scrapers.py           # Point d'entrée
│
├── ingestion/                    # Consommation Kafka → Bronze
│   ├── Dockerfile
│   ├── requirements.txt
│   ├── kafka_consumer.py
│   └── minio_client.py           # Client MinIO (Data Lake)
│
├── processing/                   # ETL : Médaillon Bronze→Silver→Gold
│   ├── Dockerfile
│   ├── requirements.txt
│   ├── data_quality.py           # Contrôles qualité
│   ├── bronze_to_silver.py       # Nettoyage + normalisation
│   └── silver_to_gold.py         # Agrégations analytiques
│
├── warehouse/                    # Data Warehouse PostgreSQL
│   ├── schema.sql                # DDL complet
│   ├── init_airflow_db.sql       # Init bases Airflow + Metabase
│   └── load_data.py              # Loader MinIO → PostgreSQL
│
├── airflow/                      # Orchestration
│   ├── Dockerfile
│   ├── requirements.txt
│   └── dags/
│       ├── scraping_dag.py       # DAG scraping batch (toutes les heures)
│       ├── transformation_dag.py # DAG Bronze→Silver→Gold
│       └── warehouse_dag.py      # DAG chargement DWH
│
├── governance/                   # Qualité & Traçabilité
│   ├── logger.py                 # Logging centralisé + audit
│   └── lineage.py                # Catalogue de lignage de données
│
└── monitoring/                   # Observabilité
    ├── prometheus.yml
    └── grafana/
        └── dashboards/
            └── news_dashboard.json
```

## Pipelines Airflow

### DAG 1 : `scraping_batch` (toutes les heures — `:00`)
```
start → [hespress | akhbarona | bbc | cnn | reuters] → log_summary → end
```

### DAG 2 : `transformation_pipeline` (toutes les heures — `:30`)
```
start → quality_checks → bronze_to_silver → silver_to_gold → notify → end
```

### DAG 3 : `warehouse_load` (toutes les heures — `:45`)
```
start → load_articles → load_aggregations → refresh_stats → log_run → end
```

## Architecture Médaillon

| Couche   | Stockage         | Format   | Contenu                          |
|----------|-----------------|----------|----------------------------------|
| Bronze   | MinIO/bronze    | JSON     | Articles bruts tels que scrapés  |
| Silver   | MinIO/silver    | Parquet  | Nettoyés, normalisés, enrichis   |
| Gold     | MinIO/gold      | Parquet  | Agrégations analytiques          |
| DWH      | PostgreSQL      | Tables   | Dimensions + Faits + Agrégats    |

## Contrôles Qualité

Tests implémentés dans `processing/data_quality.py` :
- `TITLE_EMPTY_OR_TOO_SHORT` : titre vide ou < 5 caractères
- `DATE_MISSING` : date de publication absente
- `CONTENT_TOO_SHORT` : contenu < 100 caractères
- `URL_INVALID` : URL malformée
- `SOURCE_MISSING` : source non renseignée

## Configuration Metabase (Dashboards)

1. Ouvrir http://localhost:3000
2. Setup : choisir PostgreSQL, saisir les credentials du `.env`
3. Créer les questions SQL suivantes :

**Tendances d'actualité :**
```sql
SELECT date, article_count FROM agg_articles_by_day
ORDER BY date DESC LIMIT 30;
```

**Articles par source :**
```sql
SELECT source_name, article_count FROM agg_articles_by_source
ORDER BY article_count DESC;
```

**Mots clés fréquents :**
```sql
SELECT keyword, frequency FROM agg_top_keywords
ORDER BY frequency DESC LIMIT 20;
```

## Déploiement Kubernetes (Optionnel)

```bash
# Installer Helm
helm repo add airflow-stable https://airflow.apache.org
helm install airflow airflow-stable/airflow -f k8s/airflow-values.yaml

# Déployer les autres composants
kubectl apply -f k8s/
```

## Commandes Utiles

```bash
# Voir les logs d'un service
docker compose logs -f scraper
docker compose logs -f consumer
docker compose logs -f airflow-scheduler

# Relancer uniquement un service
docker compose restart scraper

# Accéder à PostgreSQL
docker compose exec postgres psql -U newsadmin -d news_dw

# Voir les messages Kafka
docker compose exec kafka kafka-console-consumer \
  --bootstrap-server localhost:9092 \
  --topic news-articles --from-beginning

# Arrêter tout
docker compose down

# Tout réinitialiser (supprime les volumes)
docker compose down -v
```

## Lignage des Données

```
[hespress|akhbarona|bbc|cnn|reuters]
          ──[scrapers]──▶ raw_articles_bronze (MinIO/bronze)
  raw_articles_bronze ──[bronze_to_silver]──▶ cleaned_articles_silver (MinIO/silver)
  cleaned_articles_silver ──[silver_to_gold]──▶ articles_by_day_gold (MinIO/gold)
  cleaned_articles_silver ──[silver_to_gold]──▶ articles_by_source_gold (MinIO/gold)
  cleaned_articles_silver ──[silver_to_gold]──▶ top_keywords_gold (MinIO/gold)
  cleaned_articles_silver ──[warehouse_load]──▶ fact_articles_dw (PostgreSQL)
```
