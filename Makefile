.PHONY: up down build logs shell-backend shell-db reset scrape scrape-test

up:
	docker compose up --build

down:
	docker compose down

build:
	docker compose build

logs:
	docker compose logs -f

shell-backend:
	docker compose exec backend bash

shell-db:
	docker compose exec db psql -U mcfd -d mcfd

reset:
	docker compose down -v
	docker compose up --build

scrape:
	cd backend && .venv/bin/python3.12 -m app.scrapers.run_all

scrape-test:
	cd backend && .venv/bin/python3.12 -m app.scrapers.run_all --limit 5
