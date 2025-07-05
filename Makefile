
.PHONY: build
build:
	docker build -f devops/Dockerfile -t 0x-uniswap-event-streamer .

.PHONY: compose-up
compose-up:
	docker-compose -f devops/docker-compose.yaml up -d

.PHONY: compose-down
compose-down:
	docker-compose -f devops/docker-compose.yaml down

.PHONY: compose-logs
compose-logs:
	docker-compose -f devops/docker-compose.yaml logs -f

.PHONY: clean-up
clean-up:
	docker-compose -f devops/docker-compose.yaml down -v --remove-orphans
	docker rmi 0x-uniswap-event-streamer || true

.PHONY: help
help:
	@echo "Available commands:"
	@echo "  build          - Build Docker image"
	@echo "  compose-up     - Start services with docker-compose"
	@echo "  compose-down   - Stop services with docker-compose"
	@echo "  compose-logs   - Show logs from docker-compose services"
	@echo "  clean-up       - Complete cleanup (stop services, remove volumes, delete image)"
	@echo "  help           - Show this help message"

# Default target
.DEFAULT_GOAL := help
