# Documentation Technique — Plateforme News Data

## Prérequis

| Outil | Version minimale | Installation |
|---|---|---|
| Docker Desktop | 4.x | https://www.docker.com/products/docker-desktop |
| Docker Compose | 2.x | Inclus avec Docker Desktop |
| RAM disponible | 5 GB | Configurer dans Docker Desktop → Settings → Resources |
| Espace disque | 10 GB | — |

---

## Installation et Démarrage

### 1. Cloner le projet
```bash
git clone <url-du-repo>
cd news-data-platform
```

### 2. Configurer Docker Desktop
- Ouvrir Docker Desktop
- Settings → Resources → Memory → **5 GB minimum**
- Apply & Restart

### 3. Démarrer tous les services
```bash
docker compose up -d --build
```

### 4. Attendre l'initialisation (~2-3 minutes)
```bash
docker ps
# Vérifier que tous les containers sont "healthy" ou "Up"
```

### 5. Vérifier l'état
```bash
docker compose ps
```

---

## Accès aux Interfaces

| Interface | URL | Login | Mot de passe |
|---|---|---|---|
| **Airflow** (Orchestration) | http://localhost:8080 | admin | admin123 |
| **MinIO** (Data Lake) | http://localhost:9200 | minioadmin | minioadmin123 |
| **Kafka UI** (Streaming) | http://localhost:8090 | — | — |
| **Grafana** (Dashboards) | http://localhost:3001 | admin | admin123 |
| **Metabase** (BI) | http://localhost:3000 | — | — |
| **PostgreSQL** (DWH) | localhost:5432 | newsadmin | newsadmin123 |

---

## Guide d'Utilisation

### Airflow — Gestion des Pipelines
1. Ouvrir http://localhost:8080
2. Login : `admin` / `admin123`
3. Dans la liste des DAGs, activer (toggle) :
   - `scraping_batch` — collecte hourly
   - `transformation_pipeline` — ETL daily
   - `warehouse_load` — chargement DWH daily
4. Pour déclencher manuellement : cliquer le bouton ▶ (Trigger DAG)

### MinIO — Explorer le Data Lake
1. Ouvrir http://localhost:9200
2. Login : `minioadmin` / `minioadmin123`
3. Buckets disponibles :
   - `bronze` → JSON bruts (900+ articles)
   - `silver` → Parquet nettoyés
   - `gold` → Parquet agrégés

### Grafana — Visualiser les Données
1. Ouvrir http://localhost:3001
2. Login : `admin` / `admin123`
3. Menu gauche → Dashboards → **News Data Platform - Complet**
4. Le dashboard contient 13 panels :
   - Total articles, Sources actives, Mots-clés, Taux qualité
   - Articles par Source / Pays / Langue
   - Tendance articles par jour
   - Top 20 mots-clés, Catégories/Thèmes
   - Pipeline runs, Rapport qualité

### Kafka UI — Monitoring Streaming
1. Ouvrir http://localhost:8090
2. Cliquer sur **Topics** → `news-articles`
3. Explorer les messages et partitions

---

## Structure du Projet

```
news-data-platform/
├── docker-compose.yml          # Orchestration des 11 services
├── .env                        # Variables d'environnement
├── README.md                   # Guide démarrage rapide
│
├── scrapers/                   # Web scraping
│   ├── run_scrapers.py         # Orchestrateur des scrapers
│   ├── bbc_scraper.py          # Scraper BBC News
│   ├── cnn_scraper.py          # Scraper CNN
│   ├── reuters_scraper.py      # Scraper Reuters
│   ├── hespress_scraper.py     # Scraper Hespress (AR)
│   ├── akhbarona_scraper.py    # Scraper Akhbarona (AR)
│   ├── kafka_producer.py       # Envoi vers Kafka
│   └── base_scraper.py         # Classe de base
│
├── ingestion/                  # Consommation Kafka
│   ├── kafka_consumer.py       # Consumer → MinIO Bronze
│   └── minio_client.py         # Client MinIO
│
├── processing/                 # Transformations ETL
│   ├── bronze_to_silver.py     # Nettoyage + normalisation
│   ├── silver_to_gold.py       # Agrégations analytiques
│   └── data_quality.py         # Contrôles qualité
│
├── warehouse/                  # Data Warehouse
│   ├── schema.sql              # Schéma PostgreSQL complet
│   └── load_data.py            # Chargement fact + dims + aggs
│
├── airflow/                    # Orchestration
│   └── dags/
│       ├── scraping_dag.py     # DAG scraping batch
│       ├── transformation_dag.py # DAG ETL
│       └── warehouse_dag.py    # DAG chargement DWH
│
├── governance/                 # Gouvernance
│   ├── lineage.py              # Data lineage catalog
│   └── logger.py               # Logging centralisé
│
├── monitoring/                 # Observabilité
│   ├── prometheus.yml          # Config Prometheus
│   └── grafana/provisioning/   # Dashboards Grafana
│
├── k8s/                        # Déploiement Kubernetes
│   ├── namespace.yaml
│   ├── configmap.yaml
│   ├── secrets.yaml
│   └── deployments/
│
└── docs/                       # Documentation
    ├── presentation.md         # Présentation projet
    ├── architecture.md         # Schéma d'architecture
    └── technical_documentation.md  # Ce fichier
```

---

## Variables d'Environnement

Fichier `.env` à la racine :

```env
# Kafka
KAFKA_BROKER=kafka:9092
KAFKA_TOPIC=news-articles

# MinIO
MINIO_ENDPOINT=minio:9000
MINIO_ACCESS_KEY=minioadmin
MINIO_SECRET_KEY=minioadmin123

# PostgreSQL
POSTGRES_HOST=postgres
POSTGRES_PORT=5432
POSTGRES_DB=news_dw
POSTGRES_USER=newsadmin
POSTGRES_PASSWORD=newsadmin123

# Airflow
AIRFLOW_ADMIN_USER=admin
AIRFLOW_ADMIN_PASSWORD=admin123
```

---

## Commandes Utiles

### Arrêter et redémarrer
```bash
# Arrêter tous les services
docker compose down

# Redémarrer un service spécifique
docker restart grafana

# Voir les logs d'un service
docker logs scraper --tail 50

# Voir l'état de tous les containers
docker ps
```

### Vérifier les données PostgreSQL
```bash
# Se connecter à PostgreSQL
docker exec -it postgres psql -U newsadmin -d news_dw

# Requêtes utiles
SELECT COUNT(*) FROM fact_articles;
SELECT source_name, article_count FROM agg_articles_by_source;
SELECT * FROM pipeline_runs ORDER BY started_at DESC LIMIT 5;
SELECT * FROM data_quality_log ORDER BY run_date DESC LIMIT 3;
```

### Vérifier MinIO
```bash
# Compter les fichiers par bucket
docker exec consumer python -c "
from minio import Minio
c = Minio('minio:9000', access_key='minioadmin', secret_key='minioadmin123', secure=False)
for b in ['bronze', 'silver', 'gold']:
    n = len(list(c.list_objects(b, recursive=True)))
    print(f'{b}: {n} fichiers')
"
```

---

## Résolution de Problèmes

### Docker Desktop manque de mémoire
- **Symptôme** : Containers qui s'arrêtent ou crashent
- **Solution** : Docker Desktop → Settings → Resources → Memory → 5GB

### Grafana affiche "No data"
- **Cause** : Datasource PostgreSQL mal configuré
- **Solution** :
  ```bash
  # Vérifier le datasource
  curl -u admin:admin123 http://localhost:3001/api/datasources/health
  ```

### Kafka InconsistentClusterIdException
- **Cause** : Volumes corrompus
- **Solution** :
  ```bash
  docker compose down -v
  docker compose up -d
  ```

### Airflow DAG non visible
- **Cause** : DAG en pause ou erreur de parsing
- **Solution** :
  ```bash
  docker exec airflow-webserver airflow dags list
  docker exec airflow-webserver airflow dags unpause scraping_batch
  ```
