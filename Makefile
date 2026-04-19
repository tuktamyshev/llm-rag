SHELL := /bin/bash

.PHONY: help up down logs ps backend frontend example eval migrate migration

help:
	@echo "Available commands:"
	@echo "  make up              - run full stack via docker compose"
	@echo "  make down            - stop and remove containers"
	@echo "  make logs            - tail compose logs"
	@echo "  make ps              - show running services"
	@echo "  make backend         - run backend locally (uvicorn)"
	@echo "  make frontend        - run main frontend locally"
	@echo "  make example         - run examples/cyber_threat_ui locally"
	@echo "  make eval            - run offline evaluation script"
	@echo "  make migrate         - apply pending alembic migrations"
	@echo "  make migration m=msg - create new migration (autogenerate)"

up:
	docker compose up --build -d

down:
	docker compose down

logs:
	docker compose logs -f --tail=200

ps:
	docker compose ps

backend:
	cd backend && uvicorn main:app --host 0.0.0.0 --port 8000 --reload

frontend:
	cd frontend && npm install && npm run dev

example:
	cd examples/cyber_threat_ui && npm install && npm run dev

eval:
	@echo "Usage: python -m evaluation.ragas.run_eval --dataset path/to/dataset.jsonl"

migrate:
	cd backend && alembic upgrade head

migration:
	cd backend && alembic revision --autogenerate -m "$(m)"
