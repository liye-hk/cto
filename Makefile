.PHONY: help build run stop clean test lint format

# Default target
help:
	@echo "Available targets:"
	@echo "  build    - Build the Docker image"
	@echo "  run      - Run the application with Docker Compose"
	@echo "  stop     - Stop the running containers"
	@echo "  clean    - Remove Docker images and containers"
	@echo "  test     - Run the test suite"
	@echo "  lint     - Run linting"
	@echo "  format   - Format code"

# Build the Docker image
build:
	docker build -t epub-converter .

# Run the application
run:
	docker-compose up --build

# Stop the application
stop:
	docker-compose down

# Clean up Docker resources
clean:
	docker-compose down -v
	docker rmi epub-converter 2>/dev/null || true
	docker volume prune -f

# Run tests
test:
	python -m pytest tests/ -v

# Run linting
lint:
	python -m flake8 app/ tests/
	python -m mypy app/

# Format code
format:
	python -m black app/ tests/
	python -m isort app/ tests/