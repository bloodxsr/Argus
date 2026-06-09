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
	podman-compose up -d

build:
	podman-compose build

deploy:
	@echo "Deploying AGRUS to Production..."
	podman-compose down
	podman-compose up --build -d
	@echo "Deployment Complete! Services are running."

down:
	podman-compose down

logs:
	podman-compose logs -f

restart:
	podman-compose restart

clean:
	@echo "WARNING: Wiping all containers and database volumes!"
	podman-compose down -v
