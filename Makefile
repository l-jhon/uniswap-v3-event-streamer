.PHONY: build
build:
	docker build -f devops/Dockerfile -t 0x-uniswap-event-streamer .

.PHONY: compose-up
compose-up:
	docker-compose --env-file .env -f devops/docker-compose.yaml up -d

.PHONY: compose-up-services
compose-up-services:
	docker-compose --env-file .env -f devops/docker-compose.yaml up -d --scale events-producer=0 --scale events-consumer=0

.PHONY: compose-rebuild
compose-rebuild:
	docker-compose --env-file .env -f devops/docker-compose.yaml up -d --build

.PHONY: compose-down
compose-down:
	docker-compose -f devops/docker-compose.yaml down

.PHONY: compose-logs
compose-logs:
	docker-compose -f devops/docker-compose.yaml logs -f

.PHONY: reset-consumer-offset
reset-consumer-offset:
	docker exec -it kafka kafka-consumer-groups \
		--bootstrap-server localhost:29092 \
		--group uniswap-v3-events-consumer \
		--topic uniswap-v3-events \
		--reset-offsets --to-earliest --execute

.PHONY: clean-up
clean-up:
	docker-compose -f devops/docker-compose.yaml down -v --remove-orphans
	docker rmi 0x-uniswap-event-streamer || true

.PHONY: help
help:
	@echo "Available commands:"
	@echo "  build                - Build Docker image"
	@echo "  compose-up           - Start services with docker-compose"
	@echo "  compose-up-services - Start infrastructure services only (excludes events-producer and events-consumer)"
	@echo "  compose-rebuild      - Start services with docker-compose (force rebuild)"
	@echo "  compose-down         - Stop services with docker-compose"
	@echo "  compose-logs         - Show logs from docker-compose services"
	@echo "  reset-consumer-offset - Reset Kafka consumer group offset to earliest"
	@echo "  clean-up             - Complete cleanup (stop services, remove volumes, delete image)"
	@echo "  help                 - Show this help message"

# Default target
.DEFAULT_GOAL := help
