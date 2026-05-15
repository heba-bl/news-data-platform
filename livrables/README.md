# Livrables — Projet Architecture de Données
## News Data Platform

---

## 🔗 Code Source (GitHub)

**https://github.com/heba-bl/news-data-platform**

```
git clone https://github.com/heba-bl/news-data-platform.git
```

---

## 📁 Contenu de ce dossier

| Dossier | Livrable |
|---|---|
| `01_Presentation/` | Présentation détaillée du projet (PPTX — 27 slides) |
| `02_Schema_Architecture/` | Schéma d'architecture illustrant les couches et flux de données |
| `03_Code_Source/` | Code source (scrapers, ETL, warehouse, airflow, gouvernance) |
| `04_Deploiement/` | Fichiers de déploiement Docker Compose + Kubernetes |
| `05_Documentation/` | Documentation technique d'installation et d'utilisation |
| `06_Dashboards/` | Dashboards de visualisation (Grafana screenshots + config) |
| `07_Demo/` | Script de démonstration fonctionnelle du pipeline bout en bout |

---

## 🛠 Technologies utilisées

- **Scraping** : Python + BeautifulSoup
- **Streaming** : Apache Kafka :9092
- **Orchestration** : Apache Airflow :8080
- **Data Lake** : MinIO (Bronze / Silver / Gold)
- **Data Warehouse** : PostgreSQL :5432 (Modèle Étoile)
- **Visualisation** : Grafana :3001 · Metabase :3000
- **Monitoring** : Prometheus :9090
- **Déploiement** : Docker Compose · Kubernetes

---

## 🚀 Lancement rapide

```bash
git clone https://github.com/heba-bl/news-data-platform.git
cd news-data-platform
docker compose up -d
```

Accès aux interfaces :
- Grafana   → http://localhost:3001  (admin / admin123)
- Airflow   → http://localhost:8080  (admin / admin123)
- MinIO     → http://localhost:9200  (minioadmin / minioadmin123)
- Kafka UI  → http://localhost:8090
- Metabase  → http://localhost:3000
