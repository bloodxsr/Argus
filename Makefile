.PHONY: build up down logs restart clean deploy

# Default target
help:
	@echo "AGRUS Deployment Commands:"
	@echo "  make up      - Start all services in the background"
	@echo "  make build   - Rebuild all container images"
	@echo "  make down    - Stop and remove all containers"
	@echo "  make logs    - Tail the logs for all services"
	@echo "  make restart - Restart all services"
	@echo "  make clean   - Remove containers and wipe the database volume (DANGER)"
	@echo "  make deploy  - Pull latest code, build, and run production daemon"

up:
	docker compose up -d

build:
	docker compose build

deploy:
	@echo "Deploying AGRUS to Production..."
	docker compose down
	docker compose up --build -d
	@echo "Deployment Complete! Services are running."

down:
	docker compose down

logs:
	docker compose logs -f

restart:
	docker compose restart

clean:
	@echo "WARNING: Wiping all containers and database volumes!"
	docker compose down -v
