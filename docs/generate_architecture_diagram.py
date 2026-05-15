"""
Génère un schéma d'architecture visuel style PDF
Sortie : docs/architecture_diagram.png
"""
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
from matplotlib.patches import FancyBboxPatch, FancyArrowPatch
import sys
sys.stdout.reconfigure(encoding='utf-8')

fig, ax = plt.subplots(figsize=(14, 20))
ax.set_xlim(0, 14)
ax.set_ylim(0, 20)
ax.axis('off')
fig.patch.set_facecolor('#FFFFFF')

# ── COULEURS ─────────────────────────────────────────────────
C_SOURCES   = '#EBF5FB'   # bleu très clair
C_INGESTION = '#EAF4EA'   # vert très clair
C_DATALAKE  = '#FEF9E7'   # jaune très clair
C_DWH       = '#F4ECF7'   # violet très clair
C_VISU      = '#FDEDEC'   # rose très clair

C_SRC_BRD   = '#2E86C1'
C_ING_BRD   = '#1E8449'
C_DL_BRD    = '#D4AC0D'
C_DWH_BRD   = '#7D3C98'
C_VIS_BRD   = '#CB4335'

C_KAFKA     = '#FFF3E0'
C_AIRFLOW   = '#E8F5E9'
C_BRONZE    = '#FDEBD0'
C_SILVER    = '#EBF5FB'
C_GOLD      = '#FFFDE7'
C_FACT      = '#EDE7F6'
C_DIM       = '#E8F5E9'
C_AGG       = '#FFF8E1'
C_GRAFANA   = '#E3F2FD'
C_METABASE  = '#E8F5E9'
C_PROM      = '#FBE9E7'


def section_box(x, y, w, h, label, bg, border, fontsize=11):
    box = FancyBboxPatch((x, y), w, h,
                         boxstyle="round,pad=0.08",
                         linewidth=2, edgecolor=border,
                         facecolor=bg, zorder=2)
    ax.add_patch(box)
    ax.text(x + w/2, y + h - 0.22, label,
            ha='center', va='top', fontsize=fontsize,
            fontweight='bold', color=border, zorder=3)


def inner_box(x, y, w, h, title, lines, bg, border, title_fs=9, body_fs=8):
    box = FancyBboxPatch((x, y), w, h,
                         boxstyle="round,pad=0.05",
                         linewidth=1.2, edgecolor=border,
                         facecolor=bg, zorder=4)
    ax.add_patch(box)
    ax.text(x + w/2, y + h - 0.15, title,
            ha='center', va='top', fontsize=title_fs,
            fontweight='bold', color=border, zorder=5)
    for i, line in enumerate(lines):
        ax.text(x + w/2, y + h - 0.38 - i*0.22, line,
                ha='center', va='top', fontsize=body_fs,
                color='#333333', zorder=5)


def arrow(x1, y1, x2, y2, color='#555555'):
    ax.annotate('', xy=(x2, y2), xytext=(x1, y1),
                arrowprops=dict(arrowstyle='->', color=color,
                                lw=1.8, connectionstyle='arc3,rad=0'))


def etl_label(x, y):
    ax.text(x, y, 'ETL', ha='center', va='center', fontsize=8,
            color='#666666', style='italic',
            bbox=dict(boxstyle='round,pad=0.2', facecolor='white',
                      edgecolor='#aaaaaa', linewidth=0.8))


# ════════════════════════════════════════════════════════
# 1. SOURCES DE DONNÉES
# ════════════════════════════════════════════════════════
sy = 18.2
section_box(0.3, sy, 13.4, 1.55, 'SOURCES DE DONNÉES (Web)', C_SOURCES, C_SRC_BRD)

sources = [
    ('BBC\n(UK/EN)',      0.55),
    ('CNN\n(US/EN)',      3.05),
    ('Reuters\n(UK/EN)', 5.55),
    ('Hespress\n(MA/AR)', 8.05),
    ('Akhbarona\n(MA/AR)',10.55),
]
for label, x in sources:
    inner_box(x, sy + 0.3, 2.2, 0.9, '', [label], '#FFFFFF', C_SRC_BRD, body_fs=9)

ax.text(7.0, sy + 0.05, 'Python + BeautifulSoup (Scraping)',
        ha='center', va='bottom', fontsize=8.5, color=C_SRC_BRD, style='italic')

# ════════════════════════════════════════════════════════
# 2. COUCHE INGESTION
# ════════════════════════════════════════════════════════
arrow(7.0, sy, 7.0, 17.05)
iy = 14.85
section_box(0.3, iy, 13.4, 2.95, 'COUCHE INGESTION', C_INGESTION, C_ING_BRD)

# Airflow (bottom of section = lower Y)
inner_box(0.6, iy + 0.28, 12.8, 1.1, 'Apache Airflow  :8080',
          ['DAG 1: scraping_batch (@hourly)',
           'DAG 2: transformation_pipeline (@daily)  |  DAG 3: warehouse_load (@daily)'],
          C_AIRFLOW, '#1B5E20', title_fs=9.5)

# Kafka (top of section = higher Y)
inner_box(0.6, iy + 1.55, 12.8, 1.1, 'Apache Kafka  :9092',
          ['Topic: news-articles  |  Partitions: 3  |  Rétention: 7 jours  |  Format: JSON',
           'Producer ──▶  [P0]  [P1]  [P2]  ──▶  Consumer'],
          C_KAFKA, '#E65100', title_fs=9.5)

# ════════════════════════════════════════════════════════
# 3. DATA LAKE — MÉDAILLON
# ════════════════════════════════════════════════════════
arrow(7.0, iy, 7.0, 13.65)
dy = 10.95
section_box(0.3, dy, 13.4, 2.75, 'DATA LAKE — Architecture Médaillon  (MinIO :9000)', C_DATALAKE, C_DL_BRD)

# Bronze
inner_box(0.6, dy + 0.32, 3.6, 2.2, 'BRONZE',
          ['Format: JSON', 'Brut/Raw', '~1012 fichiers', 'Historique complet', 'raw/YYYY/MM/DD/'],
          C_BRONZE, '#E65100')

etl_label(4.6, dy + 1.4)
arrow(4.2, dy + 1.4, 5.0, dy + 1.4, '#D4AC0D')

# Silver
inner_box(5.0, dy + 0.32, 3.6, 2.2, 'SILVER',
          ['Format: Parquet', 'HTML nettoyé', 'Langue détectée', 'Dédupliqué', '~14 fichiers'],
          C_SILVER, '#1565C0')

etl_label(8.95, dy + 1.4)
arrow(8.6, dy + 1.4, 9.3, dy + 1.4, '#D4AC0D')

# Gold
inner_box(9.3, dy + 0.32, 4.1, 2.2, 'GOLD',
          ['Format: Parquet', 'Agrégats', '~20 fichiers', 'Optimisé queries', ''],
          C_GOLD, '#F57F17')

# ════════════════════════════════════════════════════════
# 4. DATA WAREHOUSE
# ════════════════════════════════════════════════════════
arrow(7.0, dy, 7.0, 9.6)
wy = 5.5
section_box(0.3, wy, 13.4, 5.1, 'DATA WAREHOUSE — PostgreSQL :5432  (Modèle Étoile)', C_DWH, C_DWH_BRD)

# dim_date (top center)
inner_box(4.75, wy + 3.6, 3.0, 1.2, 'dim_date',
          ['date_id PK', 'full_date  |  day/month/year'], C_DIM, '#1B5E20')

# dim_source (left)
inner_box(0.55, wy + 1.5, 2.8, 1.7, 'dim_source',
          ['source_id PK', 'name', 'country'], C_DIM, '#1B5E20')

# fact_articles (centre)
inner_box(3.7, wy + 0.35, 5.0, 3.9, 'fact_articles',
          ['article_id PK', 'title, author', 'content',
           'published_at, url', 'source_id FK  │  category_id FK',
           'language, word_count'],
          C_FACT, '#4A148C', title_fs=10)

# dim_category (right)
inner_box(9.0, wy + 1.5, 2.8, 1.7, 'dim_category',
          ['category_id PK', 'name', ''], C_DIM, '#1B5E20')

# arrows dims → fact
arrow(3.35, wy + 2.3, 3.7, wy + 2.5, C_DWH_BRD)   # dim_source → fact
arrow(9.0,  wy + 2.3, 8.7, wy + 2.5, C_DWH_BRD)   # dim_category → fact
arrow(6.25, wy + 4.25, 6.25, wy + 3.7, C_DWH_BRD) # dim_date → fact

# Tables agrégées
inner_box(0.55, wy + 0.32, 2.8, 1.0, 'Tables Agrégées',
          ['agg_by_src  |  agg_by_day', 'agg_top_keywords'],
          C_AGG, '#E65100', title_fs=8.5, body_fs=7.5)

inner_box(9.0, wy + 0.32, 2.8, 1.0, 'Gouvernance',
          ['pipeline_runs', 'data_quality_log'],
          '#F5F5F5', '#555555', title_fs=8.5, body_fs=7.5)

inner_box(11.95, wy + 0.32, 1.5, 4.6, 'Seed',
          ['BBC → UK', 'CNN → US', 'Reuters→ UK', 'Hespress→ MA', 'Akhbarona→ MA'],
          '#F5F5F5', '#1B5E20', title_fs=7.5, body_fs=7)

# ════════════════════════════════════════════════════════
# 5. VISUALISATION & MONITORING
# ════════════════════════════════════════════════════════
arrow(7.0, wy, 7.0, 4.65)
vy = 0.3
section_box(0.3, vy, 13.4, 5.2, 'COUCHE VISUALISATION & MONITORING', C_VISU, C_VIS_BRD)

# Grafana
inner_box(0.55, vy + 0.35, 4.0, 4.6, 'GRAFANA  :3001',
          ['13 panels analytiques', 'Total articles', 'Articles/source',
           'Articles/pays', 'Tendances temporelles', 'Top mots-clés',
           'Qualité + Pipeline'],
          C_GRAFANA, '#0D47A1', title_fs=10)

# Metabase
inner_box(4.85, vy + 0.35, 4.0, 4.6, 'METABASE  :3000',
          ['BI self-service', 'Exploration libre', 'Graphiques avancés',
           'Questions SQL', 'Dashboards partagés', '', ''],
          C_METABASE, '#1B5E20', title_fs=10)

# Prometheus
inner_box(9.15, vy + 0.35, 4.2, 4.6, 'PROMETHEUS  :9090',
          ['Métriques système', 'CPU, RAM, réseau',
           'Kafka lag', 'Scraper health', 'Pipeline duration', '', ''],
          C_PROM, '#BF360C', title_fs=10)

# ════════════════════════════════════════════════════════
# FOOTER
# ════════════════════════════════════════════════════════
ax.text(7.0, 0.08,
        'Infrastructure: Docker Compose (news-net)  |  Zookeeper :2181  |  Kafka-UI :8090  |  MinIO Console :9200',
        ha='center', va='bottom', fontsize=7.5, color='#555555', style='italic')

plt.tight_layout(pad=0)
out = r'C:\Users\ayman\CascadeProjects\news-data-platform\docs\architecture_diagram.png'
plt.savefig(out, dpi=180, bbox_inches='tight', facecolor='white')
plt.close()
print(f'Sauvegarde : {out}')
