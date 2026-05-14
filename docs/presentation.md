# Présentation du Projet : Plateforme Big Data News

## 1. Contexte et Objectifs

### Problématique
Les médias publient chaque jour des milliers d'articles. Ces données non structurées représentent une source précieuse d'information pour :
- Identifier les **tendances d'actualité** en temps réel
- Analyser les **thèmes dominants** par région et par langue
- Suivre l'**évolution des événements** dans le temps
- Comparer la **couverture médiatique** entre sources internationales et marocaines

### Objectif
Concevoir une **plateforme Big Data distribuée** capable de :
1. Collecter automatiquement des articles de presse (web scraping)
2. Stocker et transformer les données via une architecture Médaillon
3. Alimenter un entrepôt de données analytique
4. Visualiser les tendances via des dashboards interactifs

---

## 2. Architecture Générale

```
┌─────────────────────────────────────────────────────────────────┐
│                    SOURCES DE DONNÉES                           │
│   BBC News  │  CNN  │  Reuters  │  Hespress  │  Akhbarona      │
└──────────────────────┬──────────────────────────────────────────┘
                       │ Web Scraping (Python + BeautifulSoup)
                       ▼
┌─────────────────────────────────────────────────────────────────┐
│                    INGESTION                                     │
│         Apache Kafka (Streaming) + Apache Airflow (Batch)       │
└──────────────────────┬──────────────────────────────────────────┘
                       │
                       ▼
┌─────────────────────────────────────────────────────────────────┐
│                    DATA LAKE (MinIO)                             │
│  BRONZE (JSON brut) → SILVER (Parquet nettoyé) → GOLD (agrégé) │
└──────────────────────┬──────────────────────────────────────────┘
                       │ ETL Python
                       ▼
┌─────────────────────────────────────────────────────────────────┐
│                    DATA WAREHOUSE (PostgreSQL)                   │
│    fact_articles │ dim_source │ dim_category │ dim_date         │
│    agg_by_source │ agg_by_day │ agg_keywords │ agg_by_country   │
└──────────────────────┬──────────────────────────────────────────┘
                       │
                       ▼
┌─────────────────────────────────────────────────────────────────┐
│                    VISUALISATION                                  │
│              Grafana (13 panels) │ Metabase                     │
└─────────────────────────────────────────────────────────────────┘
```

---

## 3. Choix Technologiques

| Composant | Technologie | Justification |
|---|---|---|
| **Web Scraping** | Python + BeautifulSoup | Léger, flexible, supporte HTML statique et dynamique |
| **Message Broker** | Apache Kafka | Standard industrie pour streaming, haute disponibilité |
| **Orchestration** | Apache Airflow | DAGs Python, scheduler avancé, monitoring intégré |
| **Data Lake** | MinIO | Compatible S3, open-source, déployable on-premise |
| **Transformation** | Python + Pandas | Maîtrise équipe, riche écosystème data |
| **Data Warehouse** | PostgreSQL | ACID, SQL standard, performances analytiques solides |
| **Visualisation** | Grafana | Open-source, PostgreSQL natif, dashboards temps réel |
| **Conteneurisation** | Docker + Compose | Déploiement reproductible, isolation des services |
| **Monitoring** | Prometheus + Grafana | Stack standard, métriques système et applicatives |

---

## 4. Sources de Données

### Sites Marocains
| Source | URL | Langue | Catégories |
|---|---|---|---|
| **Hespress** | hespress.com | Arabe/Français | Politique, Sport, Économie |
| **Akhbarona** | akhbarona.com | Arabe | Actualité générale |

### Sites Internationaux
| Source | URL | Langue | Catégories |
|---|---|---|---|
| **BBC News** | bbc.com/news | Anglais | Monde, Tech, Science, Sport |
| **CNN** | edition.cnn.com | Anglais | Monde, Politique, Business |
| **Reuters** | reuters.com | Anglais | Finance, Politique, Marchés |

### Données Collectées
- Titre, Auteur, Date de publication
- Catégorie, Contenu complet
- Source, URL, Langue détectée
- Date de scraping

---

## 5. Architecture Médaillon (Data Lake)

### Couche Bronze — Données Brutes
- **Format** : JSON
- **Stockage** : `minio://bronze/raw/YYYY/MM/DD/`
- **Contenu** : Articles tels que scrapés, sans modification
- **Volume** : 900+ fichiers

### Couche Silver — Données Nettoyées
- **Format** : Parquet (compression Snappy)
- **Stockage** : `minio://silver/cleaned/`
- **Transformations** :
  - Suppression des balises HTML
  - Normalisation du texte (Unicode, espaces)
  - Détection automatique de la langue (langdetect)
  - Calcul du nombre de mots
  - Déduplication par URL

### Couche Gold — Données Analytiques
- **Format** : Parquet
- **Stockage** : `minio://gold/`
- **Contenu** : Agrégations pré-calculées (par source, jour, mots-clés)

---

## 6. Pipelines ETL / ELT

### Pipeline 1 : Scraping (Batch)
```
Airflow DAG: scraping_batch (toutes les heures)
  └── ScrapingTask(BBC) → KafkaProducer
  └── ScrapingTask(CNN) → KafkaProducer
  └── ScrapingTask(Reuters) → KafkaProducer
  └── ScrapingTask(Hespress) → KafkaProducer
  └── ScrapingTask(Akhbarona) → KafkaProducer
```

### Pipeline 2 : Transformation Bronze → Silver
```
Airflow DAG: transformation_pipeline (quotidien)
  └── ReadBronze → CleanHTML → NormalizeText → DetectLanguage
      → DeduplicateByURL → WriteParquetSilver → LogQuality
```

### Pipeline 3 : Silver → Gold → Warehouse
```
Airflow DAG: warehouse_load (quotidien)
  └── ReadSilver → AggregateBySource → AggregateByDay
      → ExtractKeywords → WriteGold → LoadPostgreSQL
```

---

## 7. Qualité des Données

### Contrôles Implémentés
| Contrôle | Dimension | Règle |
|---|---|---|
| Titre vide | Complétude | `len(title) >= 5` |
| Date manquante | Complétude | `published_at IS NOT NULL` |
| Contenu trop court | Validité | `len(content) >= 100 chars` |
| URL invalide | Validité | `url.startswith('http')` |
| Source manquante | Complétude | `source IS NOT NULL` |
| Langue incohérente | Cohérence | Langue détectée ↔ source attendue |

### Résultats
- **Taux de qualité global** : 75.7%
- **Articles valides** : 131/173
- **Log qualité** : table `data_quality_log` dans PostgreSQL

---

## 8. Gouvernance des Données

### Traçabilité (Data Lineage)
```
[EXTERNAL] hespress, akhbarona, bbc, cnn, reuters
    └──[kafka_consumer]──▶ [BRONZE] raw_articles_bronze (JSON, MinIO)
         └──[bronze_to_silver]──▶ [SILVER] cleaned_articles_silver (Parquet)
              └──[silver_to_gold]──▶ [GOLD] articles_by_day, by_source, keywords
                   └──[warehouse_load]──▶ [WAREHOUSE] fact_articles (PostgreSQL)
```

### Tables de Gouvernance
- `pipeline_runs` : historique de chaque exécution de pipeline
- `data_quality_log` : rapport qualité par pipeline et date
- `governance/lineage.py` : catalogue complet des datasets

---

## 9. Data Warehouse — Modèle Dimensionnel

### Schéma en Étoile (Star Schema)
```
                    dim_date
                       │
dim_source ──── fact_articles ──── dim_category
                       │
                   (language, word_count, content...)
```

### Tables Analytiques (Gold Layer)
- `agg_articles_by_source` — articles par source
- `agg_articles_by_day` — articles par jour (21 jours)
- `agg_articles_by_category` — articles par catégorie/thème
- `agg_articles_by_country` — articles par pays
- `agg_top_keywords` — top 131 mots-clés
- `agg_language_distribution` — distribution des langues

---

## 10. Monitoring et Observabilité

### Prometheus — Métriques Collectées
- Consommation CPU/RAM par container
- Latence des requêtes Kafka
- Nombre de messages traités
- État des healthchecks

### Grafana — Dashboards
- **News Data Platform** : 13 panels analytiques
- **KPIs** : Total articles, sources, qualité, dernier scraping
- **Tendances** : Articles par jour, source, pays, langue
- **Analytics** : Mots-clés, catégories, pipeline runs

---

## 11. Déploiement

### Infrastructure Docker Compose
```
11 services conteneurisés :
├── zookeeper        (coordination Kafka)
├── kafka            (message broker)
├── kafka-ui         (interface Kafka)
├── minio            (object storage)
├── postgres         (data warehouse)
├── scraper          (web scraping)
├── consumer         (Kafka → MinIO)
├── airflow-webserver (orchestration UI)
├── airflow-scheduler (scheduler DAGs)
├── metabase         (BI analytics)
├── prometheus       (monitoring)
└── grafana          (dashboards)
```

### Ports d'Accès
| Service | URL | Identifiants |
|---|---|---|
| Airflow | http://localhost:8080 | admin / admin123 |
| MinIO | http://localhost:9200 | minioadmin / minioadmin123 |
| Kafka UI | http://localhost:8090 | — |
| Grafana | http://localhost:3001 | admin / admin123 |
| Metabase | http://localhost:3000 | — |

---

## 12. Résultats et Métriques

### Données Collectées
- **900+ articles** bruts dans MinIO Bronze
- **173 articles** chargés dans PostgreSQL après ETL
- **5 sources** actives (BBC, Reuters, CNN, Akhbarona, Hespress)
- **131 mots-clés** extraits et indexés
- **3 pays** couverts (United Kingdom, United States, Morocco)
- **2 langues** (Anglais 99%, Arabe 1%)

### Performance Pipeline
| Pipeline | Entrée | Sortie | Durée |
|---|---|---|---|
| Scraping | — | 900 articles | ~10 min |
| Bronze → Silver | 900 | 173 (dédupliqués) | ~5 min |
| Silver → Gold | 173 | 20 agrégats | ~2 min |
| Gold → Warehouse | 173 | 173 chargés | ~1 min |
