.PHONY: help up down build restart logs clean init scrape process load status

help:
	@echo ""
	@echo "  News Data Platform — Commandes disponibles"
	@echo "  ─────────────────────────────────────────"
	@echo "  make up          Démarrer tous les services"
	@echo "  make down        Arrêter tous les services"
	@echo "  make build       Rebuild les images Docker"
	@echo "  make restart     Redémarrer tous les services"
	@echo "  make init        Initialiser Airflow (1ère fois)"
	@echo "  make scrape      Lancer le scraping manuellement"
	@echo "  make process     Lancer le pipeline ETL (Bronze→Gold)"
	@echo "  make load        Charger les données vers le DWH"
	@echo "  make logs        Voir tous les logs"
	@echo "  make status      État des services"
	@echo "  make clean       Arrêter et supprimer les volumes"
	@echo "  make psql        Accéder à PostgreSQL"
	@echo "  make kafka-list  Lister les messages Kafka"
	@echo ""

up:
	docker compose up -d

down:
	docker compose down

build:
	docker compose build --no-cache

restart:
	docker compose restart

init:
	docker compose run --rm airflow-init

scrape:
	docker compose run --rm scraper python run_scrapers.py

process:
	docker compose run --rm processor

load:
	docker compose run --rm warehouse-loader

logs:
	docker compose logs -f --tail=100

logs-scraper:
	docker compose logs -f scraper

logs-consumer:
	docker compose logs -f consumer

logs-airflow:
	docker compose logs -f airflow-scheduler airflow-webserver

status:
	docker compose ps

clean:
	docker compose down -v --remove-orphans

psql:
	docker compose exec postgres psql -U newsadmin -d news_dw

kafka-list:
	docker compose exec kafka kafka-console-consumer \
		--bootstrap-server localhost:9092 \
		--topic news-articles \
		--from-beginning \
		--max-messages 5

kafka-topics:
	docker compose exec kafka kafka-topics \
		--bootstrap-server localhost:9092 \
		--list

minio-ls:
	docker compose exec minio mc ls local/bronze --recursive
