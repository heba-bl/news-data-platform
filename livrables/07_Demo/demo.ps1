# =============================================================
# DEMO : Plateforme News Data - Pipeline Bout en Bout
# =============================================================

Write-Host ""
Write-Host "============================================================" -ForegroundColor Cyan
Write-Host "   DEMONSTRATION : PLATEFORME NEWS DATA                     " -ForegroundColor Cyan
Write-Host "   Pipeline complet : Scraping → Kafka → MinIO → PostgreSQL " -ForegroundColor Cyan
Write-Host "============================================================" -ForegroundColor Cyan
Write-Host ""

# --- 1. ETAT DES SERVICES ---
Write-Host ">>> ETAPE 1 : Verification des services" -ForegroundColor Yellow
Write-Host ""
docker ps --format "table {{.Names}}`t{{.Status}}" 2>&1
Write-Host ""
Start-Sleep 1

# --- 2. DONNEES DANS KAFKA ---
Write-Host ">>> ETAPE 2 : Messages dans Kafka (topic: news-articles)" -ForegroundColor Yellow
Write-Host ""
$kafkaInfo = docker exec kafka kafka-run-class.sh kafka.tools.GetOffsetShell `
    --broker-list localhost:9092 --topic news-articles 2>&1
Write-Host $kafkaInfo
Write-Host ""
Start-Sleep 1

# --- 3. DATA LAKE MINIO ---
Write-Host ">>> ETAPE 3 : Data Lake MinIO (Bronze/Silver/Gold)" -ForegroundColor Yellow
Write-Host ""
docker exec consumer python -c "
from minio import Minio
c = Minio('minio:9000', access_key='minioadmin', secret_key='minioadmin123', secure=False)
for b in ['bronze', 'silver', 'gold']:
    try:
        n = len(list(c.list_objects(b, recursive=True)))
        print(f'  Bucket {b:10s} : {n:4d} fichiers')
    except:
        print(f'  Bucket {b:10s} : non accessible')
" 2>&1
Write-Host ""
Start-Sleep 1

# --- 4. DATA WAREHOUSE ---
Write-Host ">>> ETAPE 4 : Data Warehouse PostgreSQL" -ForegroundColor Yellow
Write-Host ""
docker exec postgres psql -U newsadmin -d news_dw -c "
SELECT '  Total articles' AS indicateur, COUNT(*)::text AS valeur FROM fact_articles
UNION ALL SELECT '  Sources actives', COUNT(DISTINCT source_id)::text FROM fact_articles
UNION ALL SELECT '  Mots-cles indexes', COUNT(*)::text FROM agg_top_keywords
UNION ALL SELECT '  Pays couverts', COUNT(*)::text FROM agg_articles_by_country
UNION ALL SELECT '  Langues detectees', COUNT(*)::text FROM agg_language_distribution;
" 2>&1
Write-Host ""
Start-Sleep 1

# --- 5. ARTICLES PAR SOURCE ---
Write-Host ">>> ETAPE 5 : Distribution des articles par source" -ForegroundColor Yellow
Write-Host ""
docker exec postgres psql -U newsadmin -d news_dw -c "
SELECT source_name AS source, article_count AS articles
FROM agg_articles_by_source
ORDER BY article_count DESC;
" 2>&1
Write-Host ""
Start-Sleep 1

# --- 6. ARTICLES PAR PAYS ---
Write-Host ">>> ETAPE 6 : Distribution par pays" -ForegroundColor Yellow
Write-Host ""
docker exec postgres psql -U newsadmin -d news_dw -c "
SELECT country AS pays, article_count AS articles
FROM agg_articles_by_country
ORDER BY article_count DESC;
" 2>&1
Write-Host ""
Start-Sleep 1

# --- 7. QUALITE DES DONNEES ---
Write-Host ">>> ETAPE 7 : Rapport qualite des donnees" -ForegroundColor Yellow
Write-Host ""
docker exec postgres psql -U newsadmin -d news_dw -c "
SELECT pipeline, total, passed AS valides, failed AS echecs, pass_rate AS taux_pct
FROM data_quality_log
ORDER BY run_date DESC LIMIT 1;
" 2>&1
Write-Host ""
Start-Sleep 1

# --- 8. TOP MOTS CLES ---
Write-Host ">>> ETAPE 8 : Top 10 mots-cles" -ForegroundColor Yellow
Write-Host ""
docker exec postgres psql -U newsadmin -d news_dw -c "
SELECT keyword AS mot_cle, frequency AS frequence
FROM agg_top_keywords
ORDER BY frequency DESC LIMIT 10;
" 2>&1
Write-Host ""
Start-Sleep 1

# --- 9. PIPELINE RUNS ---
Write-Host ">>> ETAPE 9 : Historique des pipelines" -ForegroundColor Yellow
Write-Host ""
docker exec postgres psql -U newsadmin -d news_dw -c "
SELECT pipeline, status, records_in AS entree, records_out AS sortie
FROM pipeline_runs
WHERE records_in > 0
ORDER BY started_at DESC LIMIT 4;
" 2>&1
Write-Host ""

# --- 10. INTERFACES WEB ---
Write-Host "============================================================" -ForegroundColor Green
Write-Host "   DEMONSTRATION TERMINEE - INTERFACES DISPONIBLES          " -ForegroundColor Green
Write-Host "============================================================" -ForegroundColor Green
Write-Host ""
Write-Host "  Grafana (Dashboards)  : http://localhost:3001  [admin/admin123]" -ForegroundColor White
Write-Host "  Airflow (Pipelines)   : http://localhost:8080  [admin/admin123]" -ForegroundColor White
Write-Host "  MinIO (Data Lake)     : http://localhost:9200  [minioadmin/minioadmin123]" -ForegroundColor White
Write-Host "  Kafka UI (Streaming)  : http://localhost:8090" -ForegroundColor White
Write-Host "  Metabase (Analytics)  : http://localhost:3000" -ForegroundColor White
Write-Host ""
Write-Host "  Dashboard principal   : http://localhost:3001/d/news-complete/news-data-platform-complet" -ForegroundColor Cyan
Write-Host ""
