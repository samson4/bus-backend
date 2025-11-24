
# my_test_app Makefile


# Variables
COMPOSE_FILE := docker-compose.yml
TEST_COMPOSE_FILE := docker-compose.test.yml
API_SERVICE := bus-backend-api-1

include envs/.env.local
include envs/.env.test

help:
	@echo "my_test_app - Available Commands"
	@echo ""
	@echo "Setup:"
	@echo "  install      Install dependencies"
	@echo "  build        Build Docker images"
	@echo ""
	@echo "Development:"
	@echo "  dev          Start development environment"
	@echo "  up           Start services"
	@echo "  down         Stop services"
	@echo "  restart      Restart services"
	@echo "  logs         Show logs"
	@echo "  shell        Open API container shell"
	@echo ""
	@echo "Quality:"
	@echo "  test         Run tests"
	@echo ""
	@echo "Cleanup:"
	@echo "  clean        Clean containers/volumes"

# Setup
install:
	@uv sync

build:
	@docker compose -f $(COMPOSE_FILE) build

# Development
dev: build up
	@echo "Development environment ready!"
	@echo "API: http://localhost:8000"
	@echo "Docs: http://localhost:8000/docs"
	@echo "redoc: http://localhost:8000/redoc"

up:
	@echo "Using compose file: $(COMPOSE_FILE)"
	@docker compose -f $(COMPOSE_FILE) up -d

down:
	@docker compose -f $(COMPOSE_FILE) down

restart: down up

logs:
	@docker compose -f $(COMPOSE_FILE) logs -f

shell:
	@docker compose -f $(COMPOSE_FILE) exec $(API_SERVICE) /bin/bash

# test:
# 	@docker-compose -f $(TEST_COMPOSE_FILE) up --build -d

# Cleanup
clean:
	@docker compose -f $(COMPOSE_FILE) down -v
	@docker compose -f $(TEST_COMPOSE_FILE) down -v